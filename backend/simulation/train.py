from dataclasses import dataclass
import os
from pathlib import Path

import torch
import torch.optim as optim


from .csv_reader import read_csv_with_european_format, data_into_dataset
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


def train(train_data: list[TrainData]):
    policy = TransformerFlowPolicy(input_shape=[96, 11])
    optimizer = optim.Adam(policy.parameters(), lr=1e-3)

    for episode, data in enumerate(train_data):
        target_flow_rate = policy(
            input_tensor(
                data.previous_pump_height,
                data.current_fill_percent,
                data.electricity_price,
                data.estimated_inflow_rate,
                data.previous_flow_rate,
            )
        ).to_list()  # outputs 96-step flow sequence
        total_cost = Simulator(
            data.previous_flow_rate[-1],
            data.electricity_price,
            data.estimated_inflow_rate,
            target_flow_rate,
        ).simulate()

        loss = -total_cost
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if episode % 10 == 0:
            print(
                f"Episode {episode}, Total Cost: {total_cost:.2f}, Cost: {total_cost:.2f}"
            )


if __name__ == "__main__":
    csv_path = os.getenv(
        "CSV_DATA_PATH",
        str(
            Path(__file__).parent.parent / "Valmet-HSY-Docs" / "Hackathon_HSY_data.csv"
        ),
    )

    assert os.path.exists(csv_path)

    print(f"Reading CSV data from: {csv_path}")

    # Read CSV data
    df = read_csv_with_european_format(csv_path)
    dataset = data_into_dataset(df)
    train(dataset)
