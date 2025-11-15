from dataclasses import dataclass
import os
from pathlib import Path
import pandas as pd

import torch
import torch.optim as optim

from main import plot_simulation_results


from .csv_reader import read_csv_with_european_format
from .rl_model import TransformerFlowPolicy, input_tensor
from .simulator import Simulator


@dataclass
class TrainData:
    # previous_pump_height (list[float]): m last 1h, 15 min bins. 4 values
    previous_pump_height: list[float]
    # current_fill_percent (float): % filled
    current_fill_percent: float
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
    for i in range(len(data)):
        try:
            dataset.append(
                TrainData(
                    previous_pump_height=[
                        data.iloc[i - 3]["Water level in tunnel L2"],
                        data.iloc[i - 2]["Water level in tunnel L2"],
                        data.iloc[i - 1]["Water level in tunnel L2"],
                        data.iloc[i]["Water level in tunnel L2"],
                    ],
                    current_fill_percent=0.4,
                    electricity_price=[
                        data.iloc[time]["Electricity price 2: normal"]
                        for time in range(i, i + 96)
                    ],
                    estimated_inflow_rate=[
                        # Unit was m3/15min
                        4 * data.iloc[time]["Inflow to tunnel F1"]
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


def compute_returns(rewards, gamma=0.99):
    G = 0
    returns = []
    for r in reversed(rewards):
        G = r + gamma * G
        returns.append(G)
    return list(reversed(returns))


def train(train_data: list[TrainData]):
    policy = TransformerFlowPolicy(input_shape=[96, 11])
    optimizer = optim.Adam(policy.parameters(), lr=1e-3)

    for episode, data in enumerate(train_data):
        action, log_prob = policy.get_action_and_logprob(
            input_tensor(
                data.previous_pump_height,
                data.current_fill_percent,
                data.electricity_price,
                data.estimated_inflow_rate,
                data.previous_flow_rate,
            )
        )

        simulator = Simulator(
            data.previous_flow_rate[-1],
            data.electricity_price,
            data.estimated_inflow_rate,
            action.squeeze().tolist(),
        )
        total_cost = simulator.simulate()

        loss = -(log_prob * total_cost)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if episode % 100 == 0:
            print(
                f"Episode {episode}, Total Cost: {total_cost:.2f}, Cost: {total_cost:.2f}"
            )
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
    train(dataset)
