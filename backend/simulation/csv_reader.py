"""CSV reader module for parsing Hackathon_HSY_data.csv with European number format."""
import pandas as pd
from typing import Dict, Any


def read_csv_with_european_format(csv_path: str) -> pd.DataFrame:
    """
    Read CSV file with European number format (comma as decimal separator).
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        DataFrame with parsed data (skipping unit row)
    """
    # Read CSV, skipping the unit row (row index 1)
    df = pd.read_csv(csv_path, skiprows=[1], encoding='utf-8')
    
    # Parse timestamp column
    df['Time stamp'] = pd.to_datetime(df['Time stamp'], format='%d.%m.%Y %H.%M.%S', errors='coerce')
    
    # Convert numeric columns from European format (comma to dot)
    numeric_columns = [
        'Water level in tunnel L2',
        'Water volume in tunnel V',
        'Sum of pumped flow to WWTP F2',
        'Inflow to tunnel F1',
        'Pump flow 1.1', 'Pump flow 1.2', 'Pump flow 1.3', 'Pump flow 1.4',
        'Pump flow 2.1', 'Pump flow 2.2', 'Pump flow 2.3', 'Pump flow 2.4',
        'Pump efficiency 1.1', 'Pump efficiency 1.2', 'Pump efficiency 1.3', 'Pump efficiency 1.4',
        'Pump efficiency 2.1', 'Pump efficiency 2.2', 'Pump efficiency 2.3', 'Pump efficiency 2.4',
        'Pump frequency 1.1', 'Pump frequency 1.2', 'Pump frequency 1.3', 'Pump frequency 1.4',
        'Pump frequency 2.1', 'Pump frequency 2.2', 'Pump frequency 2.3', 'Pump frequency 2.4',
        'Electricity price 1: high',
        'Electricity price 2: normal'
    ]
    
    for col in numeric_columns:
        if col in df.columns:
            # Replace comma with dot and convert to float
            df[col] = df[col].astype(str).str.replace(',', '.').astype(float, errors='ignore')
    
    return df


def get_last_state(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Extract the last row as current state.
    
    Args:
        df: DataFrame with parsed CSV data
        
    Returns:
        Dictionary with current state values
    """
    last_row = df.iloc[-1]
    
    return {
        'timestamp': last_row['Time stamp'],
        'water_level': last_row['Water level in tunnel L2'],
        'volume': last_row['Water volume in tunnel V'],
        'inflow': last_row['Inflow to tunnel F1'],
        'pump_flows': {
            '1.1': last_row['Pump flow 1.1'],
            '1.2': last_row['Pump flow 1.2'],
            '1.3': last_row['Pump flow 1.3'],
            '1.4': last_row['Pump flow 1.4'],
            '2.1': last_row['Pump flow 2.1'],
            '2.2': last_row['Pump flow 2.2'],
            '2.3': last_row['Pump flow 2.3'],
            '2.4': last_row['Pump flow 2.4'],
        },
        'pump_efficiencies': {
            '1.1': last_row['Pump efficiency 1.1'],
            '1.2': last_row['Pump efficiency 1.2'],
            '1.3': last_row['Pump efficiency 1.3'],
            '1.4': last_row['Pump efficiency 1.4'],
            '2.1': last_row['Pump efficiency 2.1'],
            '2.2': last_row['Pump efficiency 2.2'],
            '2.3': last_row['Pump efficiency 2.3'],
            '2.4': last_row['Pump efficiency 2.4'],
        },
        'pump_frequencies': {
            '1.1': last_row['Pump frequency 1.1'],
            '1.2': last_row['Pump frequency 1.2'],
            '1.3': last_row['Pump frequency 1.3'],
            '1.4': last_row['Pump frequency 1.4'],
            '2.1': last_row['Pump frequency 2.1'],
            '2.2': last_row['Pump frequency 2.2'],
            '2.3': last_row['Pump frequency 2.3'],
            '2.4': last_row['Pump frequency 2.4'],
        },
        'electricity_price_high': last_row['Electricity price 1: high'],
        'electricity_price_normal': last_row['Electricity price 2: normal'],
    }


def get_historical_inflow(df: pd.DataFrame) -> float:
    """
    Get the last historical inflow value from F1 column.
    
    Args:
        df: DataFrame with parsed CSV data
        
    Returns:
        Last inflow value (m³/15min)
    """
    return df.iloc[-1]['Inflow to tunnel F1']


def derive_level_volume_relationship(df: pd.DataFrame) -> Dict[str, float]:
    """
    Derive level-volume relationship from historical data using simple linear regression.
    
    Args:
        df: DataFrame with parsed CSV data
        
    Returns:
        Dictionary with slope and intercept for linear relationship
    """
    import numpy as np
    
    # Use non-null values
    valid_data = df[['Water level in tunnel L2', 'Water volume in tunnel V']].dropna()
    
    if len(valid_data) < 2:
        # Fallback: simple linear approximation
        return {'slope': 1.0, 'intercept': 0.0}
    
    # Simple linear regression: y = ax + b
    # a = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
    # b = (Σy - a*Σx) / n
    x = valid_data['Water level in tunnel L2'].values
    y = valid_data['Water volume in tunnel V'].values
    
    n = len(x)
    sum_x = np.sum(x)
    sum_y = np.sum(y)
    sum_xy = np.sum(x * y)
    sum_x2 = np.sum(x * x)
    
    denominator = n * sum_x2 - sum_x * sum_x
    if abs(denominator) < 1e-10:
        # Avoid division by zero
        return {'slope': 1.0, 'intercept': 0.0}
    
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n
    
    return {
        'slope': slope,
        'intercept': intercept
    }

