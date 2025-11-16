"""CSV reader module for parsing Hackathon_HSY_data.csv with European number format."""

import pandas as pd


def read_csv_with_european_format(csv_path: str) -> pd.DataFrame:
    """
    Read CSV file with European number format (comma as decimal separator).

    Args:
        csv_path: Path to the CSV file

    Returns:
        DataFrame with parsed data (skipping unit row)
    """
    # Read CSV, skipping the unit row (row index 1)
    df = pd.read_csv(csv_path, skiprows=[1], encoding="utf-8")

    # Parse timestamp column
    df["Time stamp"] = pd.to_datetime(
        df["Time stamp"], format="%d.%m.%Y %H.%M.%S", errors="coerce"
    )

    # Convert numeric columns from European format (comma to dot)
    numeric_columns = [
        "Water level in tunnel L2",
        "Water volume in tunnel V",
        "Sum of pumped flow to WWTP F2",
        "Inflow to tunnel F1",
        "Pump flow 1.1",
        "Pump flow 1.2",
        "Pump flow 1.3",
        "Pump flow 1.4",
        "Pump flow 2.1",
        "Pump flow 2.2",
        "Pump flow 2.3",
        "Pump flow 2.4",
        "Pump efficiency 1.1",
        "Pump efficiency 1.2",
        "Pump efficiency 1.3",
        "Pump efficiency 1.4",
        "Pump efficiency 2.1",
        "Pump efficiency 2.2",
        "Pump efficiency 2.3",
        "Pump efficiency 2.4",
        "Pump frequency 1.1",
        "Pump frequency 1.2",
        "Pump frequency 1.3",
        "Pump frequency 1.4",
        "Pump frequency 2.1",
        "Pump frequency 2.2",
        "Pump frequency 2.3",
        "Pump frequency 2.4",
        "Electricity price 1: high",
        "Electricity price 2: normal",
    ]

    for col in numeric_columns:
        if col in df.columns:
            # Replace comma with dot and convert to float
            df[col] = (
                df[col].astype(str).str.replace(",", ".").astype(float, errors="ignore")
            )

    return df

