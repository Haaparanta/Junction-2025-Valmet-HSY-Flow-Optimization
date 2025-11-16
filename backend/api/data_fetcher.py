"""Services to fetch real-time data for simulations."""
import os
from pathlib import Path
from typing import List
from datetime import datetime, timedelta
import requests
from xml.etree import ElementTree
import pandas as pd
import sys

# Add parent directory to path to import simulation modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from simulation.csv_reader import read_csv_with_european_format


def get_csv_path() -> str:
    """Get path to CSV data file."""
    # Try environment variable first
    csv_path = os.getenv('CSV_DATA_PATH')
    if csv_path and os.path.exists(csv_path):
        return csv_path
    
    # Try relative to backend directory (for local development)
    backend_csv = Path(__file__).parent.parent.parent / 'Valmet-HSY-Docs' / 'Hackathon_HSY_data.csv'
    if backend_csv.exists():
        return str(backend_csv)
    
    # Try Docker path (Valmet-HSY-Docs copied to /Valmet-HSY-Docs)
    docker_csv = Path('/Valmet-HSY-Docs') / 'Hackathon_HSY_data.csv'
    if docker_csv.exists():
        return str(docker_csv)
    
    # Fallback to default
    return str(backend_csv)


def downsample_10min_to_15min(rain_values: List[float]) -> List[float]:
    """
    Downsample rain values from 10-minute to 15-minute intervals.
    
    Args:
        rain_values: List of rain values at 10-minute intervals
        
    Returns:
        List of rain values at 15-minute intervals (96 values for 24h)
    """
    downsampled = []
    i = 0
    n = len(rain_values)
    target_count = 96  # 24 hours * 4 periods
    
    while i < n and len(downsampled) < target_count:
        # Take first value as-is
        downsampled.append(rain_values[i])
        i += 1
        # Take next two values and average
        if i + 1 < n and len(downsampled) < target_count:
            avg = (rain_values[i] + rain_values[i + 1]) / 2
            downsampled.append(avg)
            i += 2
    
    # Pad if needed
    while len(downsampled) < target_count:
        if downsampled:
            downsampled.append(downsampled[-1])
        else:
            downsampled.append(0.0)
    
    return downsampled[:target_count]


def fetch_rain_forecast_24h(station_id: int = 852678) -> List[float]:
    """
    Fetch 24h rain forecast from FMI API.
    
    Args:
        station_id: FMI station ID (default: 852678 for Nuuksio)
        
    Returns:
        List of 96 rain forecast values in mm per 15min
    """
    try:
        now = datetime.utcnow()
        start_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time = (now + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        url = (
            "https://opendata.fmi.fi/wfs"
            "?service=WFS"
            "&version=2.0.0"
            "&request=getFeature"
            "&storedquery_id=fmi::forecast::harmonie::surface::point::multipointcoverage"
            f"&fmisid={station_id}"
            f"&starttime={start_time}"
            f"&endtime={end_time}"
            "&parameters=Precipitation1h"
        )
        
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        root = ElementTree.fromstring(r.content)
        
        ns = {
            'gml': "http://www.opengis.net/gml/3.2",
            'swe': "http://www.opengis.net/swe/2.0"
        }
        
        rain_values = []
        
        # Extract rainfall values
        for datablock in root.findall(".//gml:rangeSet/gml:DataBlock", ns):
            axis_elem = datablock.find(".//gml:tupleList", ns)
            if axis_elem is None:
                axis_elem = datablock.find(".//gml:doubleOrNilReasonTupleList", ns)
            if axis_elem is None:
                continue
            
            lines = axis_elem.text.strip().split("\n")
            for line in lines:
                parts = line.split()
                try:
                    rain = float(parts[-1])
                    rain_values.append(rain)
                except (ValueError, IndexError):
                    continue
        
        if rain_values:
            # Downsample to 15-minute intervals
            return downsample_10min_to_15min(rain_values)
        else:
            # Fallback: return zeros
            return [0.0] * 96
            
    except Exception as e:
        print(f"Warning: Could not fetch rain forecast: {e}")
        # Fallback: return zeros
        return [0.0] * 96


def calculate_average_daily_inflow() -> List[float]:
    """
    Calculate average daily inflow pattern from CSV historical data.
    Uses first 5 days of data, shifted to start from current hour.
    
    Returns:
        List of 96 average inflow values in m³/15min (one per 15-min period)
    """
    try:
        csv_path = get_csv_path()
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found at {csv_path}")
        
        df = read_csv_with_european_format(csv_path)
        
        # Ensure timestamp column exists
        if 'Time stamp' not in df.columns:
            raise ValueError("CSV file missing 'Time stamp' column")
        
        # Parse timestamp if not already datetime
        if not pd.api.types.is_datetime64_any_dtype(df['Time stamp']):
            df['Time stamp'] = pd.to_datetime(df['Time stamp'], errors='coerce')
        
        if 'Inflow to tunnel F1' not in df.columns:
            raise ValueError("CSV file missing 'Inflow to tunnel F1' column")
        
        # Get current hour to align the data
        current_hour = datetime.now().hour
        current_minute = (datetime.now().minute // 15) * 15  # Round to nearest 15-min
        current_period = current_hour * 4 + (current_minute // 15)
        
        # Take only first 5 days (5 * 96 = 480 periods)
        df_first_5_days = df.head(480).copy()
        
        # Extract hour and minute
        df_first_5_days['hour'] = df_first_5_days['Time stamp'].dt.hour
        df_first_5_days['minute'] = df_first_5_days['Time stamp'].dt.minute
        df_first_5_days['period'] = df_first_5_days['hour'] * 4 + (df_first_5_days['minute'] // 15)
        
        # Get the starting period from the first row
        first_period = df_first_5_days['period'].iloc[0]
        
        # Shift periods so they start from current_period
        shift_amount = current_period - first_period
        df_first_5_days['shifted_period'] = (df_first_5_days['period'] + shift_amount) % 96
        
        # Average by shifted period
        avg_inflows = df_first_5_days.groupby('shifted_period')['Inflow to tunnel F1'].mean()
        
        # Create list of 96 values (24 hours * 4 periods)
        result = []
        for period in range(96):
            if period in avg_inflows.index:
                result.append(float(avg_inflows[period]))
            else:
                # Use overall average if period not found
                overall_avg = df_first_5_days['Inflow to tunnel F1'].mean()
                result.append(float(overall_avg) if pd.notna(overall_avg) else 0.0)
        
        return result
        
    except Exception as e:
        print(f"Warning: Could not calculate average daily inflow: {e}")
        # Fallback: return a constant value
        return [100.0] * 96  # Default 100 m³/15min


def fetch_electricity_prices_24h() -> List[float]:
    """
    Fetch 24h electricity prices from Spot-hinta API.
    
    Uses https://api.spot-hinta.fi/DayForward?region=FI&priceResolution=15
    Falls back to CSV average pattern if API fails.
    
    Returns:
        List of 96 electricity prices in EUR/kWh
    """
    try:
        # Fetch from Spot-hinta API
        url = "https://api.spot-hinta.fi/DayForward?region=FI&priceResolution=15"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("API returned empty or invalid data")
        
        # Extract prices (use PriceNoTax - prices without tax)
        # Sort by DateTime to ensure chronological order
        sorted_data = sorted(data, key=lambda x: x.get('DateTime', ''))
        
        prices = []
        for item in sorted_data:
            if 'PriceNoTax' in item:
                prices.append(float(item['PriceNoTax']))
            elif 'PriceWithTax' in item:
                # If only PriceWithTax available, estimate PriceNoTax (remove ~25% tax)
                prices.append(float(item['PriceWithTax']) / 1.25)
            else:
                raise ValueError("API response missing price data")
        
        # Ensure we have exactly 96 values (24 hours * 4 periods)
        if len(prices) >= 96:
            # Take first 96 values
            return prices[:96]
        elif len(prices) > 0:
            # Pad with last value if we have fewer than 96
            last_price = prices[-1]
            while len(prices) < 96:
                prices.append(last_price)
            return prices
        else:
            raise ValueError("No price data received from API")
        
    except Exception as e:
        print(f"Warning: Could not fetch electricity prices from API: {e}")
        print("Falling back to CSV average pattern...")
        
        # Fallback to CSV average pattern
        try:
            csv_path = get_csv_path()
            if not os.path.exists(csv_path):
                raise FileNotFoundError(f"CSV file not found at {csv_path}")
            
            df = read_csv_with_european_format(csv_path)
            
            # Ensure timestamp column exists
            if 'Time stamp' not in df.columns:
                raise ValueError("CSV file missing 'Time stamp' column")
            
            # Parse timestamp if not already datetime
            if not pd.api.types.is_datetime64_any_dtype(df['Time stamp']):
                df['Time stamp'] = pd.to_datetime(df['Time stamp'], errors='coerce')
            
            # Extract hour and minute
            df['hour'] = df['Time stamp'].dt.hour
            df['minute'] = df['Time stamp'].dt.minute
            
            # Group by hour and minute (0, 15, 30, 45)
            df['period'] = df['hour'] * 4 + (df['minute'] // 15)
            
            # Calculate average electricity price for each 15-min period
            if 'Electricity price 2: normal' not in df.columns:
                raise ValueError("CSV file missing 'Electricity price 2: normal' column")
            
            # Convert from snt/kWh to EUR/kWh
            df['price_eur'] = df['Electricity price 2: normal'] / 100.0
            
            avg_prices = df.groupby('period')['price_eur'].mean()
            
            # Create list of 96 values (24 hours * 4 periods)
            result = []
            for period in range(96):
                if period in avg_prices.index:
                    result.append(float(avg_prices[period]))
                else:
                    # Use overall average if period not found
                    overall_avg = df['price_eur'].mean()
                    result.append(float(overall_avg) if pd.notna(overall_avg) else 0.1)
            
            return result
            
        except Exception as csv_error:
            print(f"Warning: CSV fallback also failed: {csv_error}")
            # Final fallback: return a constant value
            return [0.1] * 96  # Default 0.1 EUR/kWh


def get_starting_water_level() -> float:
    """
    Get starting water level from CSV (latest value).
    
    Returns:
        Starting water level in meters
    """
    try:
        csv_path = get_csv_path()
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found at {csv_path}")
        
        df = read_csv_with_european_format(csv_path)
        
        if 'Water level in tunnel L2' not in df.columns:
            raise ValueError("CSV file missing 'Water level in tunnel L2' column")
        
        # Get last value
        last_level = df['Water level in tunnel L2'].iloc[-1]
        return float(last_level)
        
    except Exception as e:
        print(f"Warning: Could not get starting water level: {e}")
        # Fallback: return a safe default
        return 5.0  # Default 5 meters


def get_historical_pump_heights() -> List[float]:
    """
    Get last 4 water level readings from CSV (1 hour history at 15-min intervals).
    
    Returns:
        List of 4 water levels in meters (oldest to newest)
    """
    try:
        csv_path = get_csv_path()
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found at {csv_path}")
        
        df = read_csv_with_european_format(csv_path)
        
        if 'Water level in tunnel L2' not in df.columns:
            raise ValueError("CSV file missing 'Water level in tunnel L2' column")
        
        # Get last 4 values (1 hour of history)
        last_4_levels = df['Water level in tunnel L2'].iloc[-4:].tolist()
        
        # If we have fewer than 4 values, pad with the first value
        while len(last_4_levels) < 4:
            if last_4_levels:
                last_4_levels.insert(0, last_4_levels[0])
            else:
                last_4_levels.append(5.0)
        
        return [float(level) for level in last_4_levels]
        
    except Exception as e:
        print(f"Warning: Could not get historical pump heights: {e}")
        # Fallback: return default values
        return [5.0, 5.0, 5.0, 5.0]


def get_historical_flow_rates() -> List[float]:
    """
    Get last 4 total flow rate readings from CSV (1 hour history at 15-min intervals).
    Calculates total flow from all pumps.
    
    Returns:
        List of 4 flow rates in m³/15min (oldest to newest)
    """
    try:
        csv_path = get_csv_path()
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found at {csv_path}")
        
        df = read_csv_with_european_format(csv_path)
        
        # List of all pump flow columns
        pump_columns = [
            'Pump flow 1.1', 'Pump flow 1.2', 'Pump flow 1.3', 'Pump flow 1.4',
            'Pump flow 2.1', 'Pump flow 2.2', 'Pump flow 2.3', 'Pump flow 2.4'
        ]
        
        # Check if all pump columns exist
        missing_columns = [col for col in pump_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"CSV file missing pump flow columns: {missing_columns}")
        
        # Calculate total flow for each row
        df['total_flow'] = df[pump_columns].sum(axis=1)
        
        # Get last 4 values (1 hour of history)
        last_4_flows = df['total_flow'].iloc[-4:].tolist()
        
        # If we have fewer than 4 values, pad with the first value
        while len(last_4_flows) < 4:
            if last_4_flows:
                last_4_flows.insert(0, last_4_flows[0])
            else:
                last_4_flows.append(300.0)  # Default ~300 m³/15min
        
        return [float(flow) for flow in last_4_flows]
        
    except Exception as e:
        print(f"Warning: Could not get historical flow rates: {e}")
        # Fallback: return default values
        return [300.0, 300.0, 300.0, 300.0]

