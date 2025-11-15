from dataclasses import dataclass
import os
from pathlib import Path
from numpy.random import random, shuffle
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

import tqdm

import torch
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

from main import plot_simulation_results


from .csv_reader import read_csv_with_european_format
from .rl_model import TransformerFlowPolicy, input_tensor
from .simulator import Simulator
from .tunnel import VD_MAX, calculate_volume_from_level

MIN_FLOW = 600.0

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("use device:", DEVICE)


@dataclass
class TrainData:
    # previous_pump_height (list[float]): m last 1h, 15 min bins. 4 values
    previous_pump_height: list[float]
    # current_fill_percent (float): % filled
    current_fill_percent: float
    # current water level (m)
    current_water_level: float
    # electricity_price (list[float]): Price of electricity (e/kWh) for next 24h, 15 min bins. 96 values
    electricity_price: list[float]
    # estimated_inflow_rate (list[float]): Estimated amount of water incoming (m3/h) 24h, 15 min bins. 96 values
    estimated_inflow_rate: list[float]
    # previous_flow_rate (list[float]): last 1h of flow rate (m3/h), 15 min bins. 4 values
    previous_flow_rate: list[float]


def data_into_dataset(data: pd.DataFrame) -> list[TrainData]:
    def calc_prev_flow_rate(row):
        return (
            row["Pump flow 1.1"]
            + row["Pump flow 1.2"]
            + row["Pump flow 1.3"]
            + row["Pump flow 1.4"]
            + row["Pump flow 2.1"]
            + row["Pump flow 2.2"]
            + row["Pump flow 2.3"]
            + row["Pump flow 2.4"]
        )

    dataset = []
    for i in tqdm.tqdm(range(len(data)), desc="Parse data"):
        try:
            water_level = 14.1 * (random() * 0.95)
            dataset.append(
                TrainData(
                    previous_pump_height=[
                        water_level * 0.85,
                        water_level * 0.90,
                        water_level * 0.95,
                        water_level,
                    ],
                    current_fill_percent=calculate_volume_from_level(water_level)
                    / VD_MAX,
                    current_water_level=water_level,
                    electricity_price=[
                        data.iloc[time]["Electricity price 2: normal"] / 100.0
                        for time in range(i, i + 96)
                    ],
                    estimated_inflow_rate=[
                        # Unit was m3/15min
                        data.iloc[time]["Inflow to tunnel F1"]
                        for time in range(i, i + 96)
                    ],
                    previous_flow_rate=[
                        calc_prev_flow_rate(data.iloc[i - 3]),
                        calc_prev_flow_rate(data.iloc[i - 2]),
                        calc_prev_flow_rate(data.iloc[i - 1]),
                        calc_prev_flow_rate(data.iloc[i]),
                    ],
                )
            )
        except Exception:
            pass
    print(f"Loaded dataset with {len(dataset)} samples")
    return dataset


class CustomDataset(Dataset):
    def __init__(self, data: list[TrainData]):
        self.data = data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return input_tensor(
            self.data[idx].previous_pump_height,
            self.data[idx].current_fill_percent,
            self.data[idx].electricity_price,
            self.data[idx].estimated_inflow_rate,
            self.data[idx].previous_flow_rate,
        )


def compute_returns(rewards, gamma=0.99):
    G = 0
    returns = []
    for r in reversed(rewards):
        G = r + gamma * G
        returns.append(G)
    return list(reversed(returns))


def penalize_min_flow_rate(target_flowrates):
    min_flow_penalizer = torch.relu(MIN_FLOW - target_flowrates) ** 2
    return min_flow_penalizer


def run_single_simulation(args):
    """
    Helper function to run a single simulation.
    This function needs to be at module level for pickling with ProcessPoolExecutor.

    Args:
        args: Tuple of (current_water_level, electricity_price, estimated_inflow_rate, target_flowrates)

    Returns:
        Total cost from simulation
    """
    current_water_level, electricity_price, estimated_inflow_rate, target_flowrates = (
        args
    )
    simulator = Simulator(
        current_water_level,
        electricity_price,
        estimated_inflow_rate,
        target_flowrates,
    )
    return simulator.simulate()


def train(
    train_data: list[TrainData],
    batch_size=64,
    epochs=10,
    csv_path: str = None,
    max_workers=None,
):
    """
    Train the policy model with multithreaded simulator execution.

    Args:
        train_data: List of training data samples
        csv_path: Path to CSV file for plotting results (optional)
        max_workers: Maximum number of worker processes. If None, uses os.cpu_count()
    """
    policy = TransformerFlowPolicy(input_shape=[96, 11]).to(DEVICE)
    optimizer = optim.Adam(policy.parameters(), lr=1e-3)

    data = CustomDataset(train_data)
    loader = DataLoader(data, batch_size=batch_size, shuffle=True)

    time_spent = {"data_loader": 0.0, "forward": 0.0, "sim": 0.0}

    # Use ProcessPoolExecutor for CPU-bound simulator tasks
    if max_workers is None:
        import multiprocessing

        max_workers = multiprocessing.cpu_count()

    simulator: Simulator

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        last_end_time = time.time()
        for epoch in tqdm.tqdm(range(epochs), desc="Train"):
            time_spent["data_loader"] += time.time() - last_end_time
            epoch_loss = []
            # for episode, data in enumerate(train_data):
            for batch in loader:
                forward_start = time.time()
                action, log_prob = policy.get_action_and_logprob(batch.to(DEVICE))
                action = action.to("cpu")
                log_prob = log_prob.to("cpu")
                time_spent["forward"] += time.time() - forward_start

                # Prepare simulation arguments for parallel execution
                simulation_args = []
                sim_start = time.time()
                for sample_i in range(batch.shape[0]):
                    sample_action = action[sample_i, :]
                    current_water_level = float(batch[sample_i, 0, 2])
                    electricity_price = batch[sample_i, :, 0].tolist()
                    estimated_inflow_rate = batch[sample_i, :, 1].tolist()
                    target_flowrates = (
                        # scale flow of from 0..1 into maximum flow rate of 16_000 m3/h and convert into m3/15min
                        16_000.0 / 4.0 * sample_action.squeeze()
                    ).tolist()
                    simulation_args.append(
                        (
                            current_water_level,
                            electricity_price,
                            estimated_inflow_rate,
                            target_flowrates,
                        )
                    )

                    # Keep the last simulator for plotting (will run it after training)
                    if sample_i == batch.shape[0] - 1:
                        simulator = Simulator(
                            current_water_level,
                            electricity_price,
                            estimated_inflow_rate,
                            target_flowrates,
                        )

                # Run simulations in parallel
                all_costs = torch.zeros((batch.shape[0]))
                future_to_index = {
                    executor.submit(run_single_simulation, args): i
                    for i, args in enumerate(simulation_args)
                }

                for future in as_completed(future_to_index):
                    sample_i = future_to_index[future]
                    try:
                        total_cost = future.result()
                        all_costs[sample_i] = total_cost
                    except Exception as exc:
                        tqdm.tqdm.write(
                            f"Sample {sample_i} generated an exception: {exc}"
                        )
                        all_costs[sample_i] = float(
                            "inf"
                        )  # Penalize failed simulations

                time_spent["sim"] += time.time() - sim_start
                # loss = -(log_prob * total_cost + penalize_min_flow_rate(action.detach()))
                advantage = all_costs / (all_costs.std() + 1e-8)
                loss = (log_prob * advantage).mean()
                epoch_loss.append(loss)
                # print(loss)
                # print(
                #     torch.autograd.grad(loss, policy.parameters(), retain_graph=True)[
                #         0
                #     ].norm()
                # )

                # loss = -(log_prob * total_cost + penalize_min_flow_rate(action.detach()))
                loss = -(log_prob * all_costs).mean()

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            mean_epoch_loss = sum(epoch_loss) / len(epoch_loss)
            tqdm.tqdm.write(
                f"Epoch {epoch} Mean epoch loss: {mean_epoch_loss}. Time spent: {time_spent}"
            )
            last_end_time = time.time()

    if simulator is not None and csv_path is not None:
        # Run the simulator to get results for plotting
        simulator.simulate()
        plot_simulation_results(simulator, csv_path)


if __name__ == "__main__":
    csv_path = os.getenv(
        "CSV_DATA_PATH",
        str(
            Path(__file__).parent.parent.parent
            / "Valmet-HSY-Docs"
            / "Hackathon_HSY_data.csv"
        ),
    )
    print("Using csv:", csv_path)

    assert os.path.exists(csv_path)

    print(f"Reading CSV data from: {csv_path}")

    # Read CSV data
    df = read_csv_with_european_format(csv_path)
    dataset = data_into_dataset(df)
    train(dataset, csv_path=csv_path)
