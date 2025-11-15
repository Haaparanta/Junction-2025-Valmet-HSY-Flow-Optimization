import os
from pathlib import Path

import pickle
import numpy as np

from simulation.simulator import Simulator
from .rl_model import TransformerFlowPolicy
from .train import TrainData, CustomDataset, data_into_dataset
from .csv_reader import read_csv_with_european_format

from main import plot_simulation_results

CSV_PATH = os.getenv(
    "CSV_DATA_PATH",
    str(
        Path(__file__).parent.parent.parent
        / "Valmet-HSY-Docs"
        / "Hackathon_HSY_data.csv"
    ),
)


def test(train_data: list[TrainData], sample_index: int):
    policy = TransformerFlowPolicy(input_shape=[96, 11])
    policy.load_weights()

    data = CustomDataset(train_data)

    sample = data[sample_index]

    print(sample)

    current_water_level = float(sample[0, 2])
    print(current_water_level)

    action = policy.forward(sample)

    current_water_level = float(sample[0, 2])
    print(current_water_level)
    electricity_price = sample[:, 0].tolist()
    estimated_inflow_rate = sample[:, 1].tolist()
    target_flowrates = (6 * 1400.0 / 4.0 + 2 * 400.0 / 4.0 * action.squeeze()).tolist()
    print("target flow:", np.mean(target_flowrates))
    simulator = Simulator(
        current_water_level,
        electricity_price,
        estimated_inflow_rate,
        target_flowrates,
    )

    simulator.simulate()
    plot_simulation_results(simulator, CSV_PATH)


if __name__ == "__main__":
    print("Using csv:", CSV_PATH)

    assert os.path.exists(CSV_PATH)

    print(f"Reading CSV data from: {CSV_PATH}")

    # Read CSV data
    if not os.path.exists("/tmp/dataset.pickle"):
        df = read_csv_with_european_format(CSV_PATH)
        dataset = data_into_dataset(df)
        with open("/tmp/dataset.pickle", "wb+") as f:
            pickle.dump(dataset, f)
    else:
        with open("/tmp/dataset.pickle", "rb") as f:
            dataset = pickle.load(f)
    print(dataset[0])
    while True:
        index = int(input("Select number to test: "))
        test(dataset, index)
