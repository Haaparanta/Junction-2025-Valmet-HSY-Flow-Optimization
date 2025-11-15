import pandas as pd
import numpy as np

# Read the CSV file
df = pd.read_csv('Valmet-HSY-Docs/Hackathon_HSY_data.csv', skiprows=1)

# Rename columns for easier access
df.columns = [
    'Time stamp', 'Water level L2', 'Water volume V', 'Sum pumped flow F2',
    'Inflow F1', 'Pump flow 1.1', 'Pump flow 1.2', 'Pump flow 1.3', 'Pump flow 1.4',
    'Pump flow 2.1', 'Pump flow 2.2', 'Pump flow 2.3', 'Pump flow 2.4',
    'Pump efficiency 1.1', 'Pump efficiency 1.2', 'Pump efficiency 1.3', 'Pump efficiency 1.4',
    'Pump efficiency 2.1', 'Pump efficiency 2.2', 'Pump efficiency 2.3', 'Pump efficiency 2.4',
    'Pump frequency 1.1', 'Pump frequency 1.2', 'Pump frequency 1.3', 'Pump frequency 1.4',
    'Pump frequency 2.1', 'Pump frequency 2.2', 'Pump frequency 2.3', 'Pump frequency 2.4',
    'Electricity price 1', 'Electricity price 2'
]

# Convert time stamp to datetime
df['Time stamp'] = pd.to_datetime(df['Time stamp'], format='%d.%m.%Y %H.%M.%S')

# Calculate time differences in hours (15 minutes = 0.25 hours)
df['Time diff hours'] = df['Time stamp'].diff().dt.total_seconds() / 3600
df.loc[0, 'Time diff hours'] = 0.25  # First row assumed to be 15 minutes

print("=" * 80)
print("CSV DATA VALIDATION REPORT")
print("=" * 80)
print()

# Check 1: Sum of individual pump flows vs Sum of pumped flow F2
print("CHECK 1: Pump Flow Consistency")
print("-" * 80)
pump_flow_cols = ['Pump flow 1.1', 'Pump flow 1.2', 'Pump flow 1.3', 'Pump flow 1.4',
                  'Pump flow 2.1', 'Pump flow 2.2', 'Pump flow 2.3', 'Pump flow 2.4']

df['Sum of individual pump flows'] = df[pump_flow_cols].sum(axis=1)
df['Pump flow difference'] = df['Sum of individual pump flows'] - df['Sum pumped flow F2']
df['Pump flow relative error'] = np.abs(df['Pump flow difference'] / (df['Sum pumped flow F2'] + 1e-10)) * 100

max_diff_idx = df['Pump flow difference'].abs().idxmax()
max_diff = df.loc[max_diff_idx, 'Pump flow difference']
max_rel_error = df.loc[max_diff_idx, 'Pump flow relative error']

print(f"Total rows checked: {len(df)}")
print(f"Rows with mismatch (difference > 0.1 m³/h): {(df['Pump flow difference'].abs() > 0.1).sum()}")
print(f"Rows with mismatch (difference > 1.0 m³/h): {(df['Pump flow difference'].abs() > 1.0).sum()}")
print(f"Rows with mismatch (difference > 10.0 m³/h): {(df['Pump flow difference'].abs() > 10.0).sum()}")
print()
print(f"Maximum difference: {max_diff:.4f} m³/h")
print(f"Maximum relative error: {max_rel_error:.4f}%")
print(f"Location: Row {max_diff_idx} ({df.loc[max_diff_idx, 'Time stamp']})")
print(f"  Sum of individual flows: {df.loc[max_diff_idx, 'Sum of individual pump flows']:.4f} m³/h")
print(f"  Sum pumped flow F2: {df.loc[max_diff_idx, 'Sum pumped flow F2']:.4f} m³/h")
print()

# Check 2: Volume change vs (Inflow - Pumped Flow)
print("CHECK 2: Volume Balance (Inflow - Pumped Flow = Volume Change)")
print("-" * 80)
# Volume change per hour (convert from m³ per 15 min to m³/h)
df['Volume change'] = df['Water volume V'].diff()
df['Volume change per hour'] = df['Volume change'] / df['Time diff hours']

# Net flow = Inflow - Pumped Flow (both should be in m³/h)
# Note: Inflow F1 is in m³/15min, so convert to m³/h
df['Inflow F1 per hour'] = df['Inflow F1'] * 4  # Convert from m³/15min to m³/h
df['Net flow'] = df['Inflow F1 per hour'] - df['Sum pumped flow F2']
df['Volume balance difference'] = df['Net flow'] - df['Volume change per hour']
df['Volume balance relative error'] = np.abs(df['Volume balance difference'] / (np.abs(df['Net flow']) + 1e-10)) * 100

# Skip first row for volume change calculation
volume_check_df = df.iloc[1:].copy()

max_vol_diff_idx = volume_check_df['Volume balance difference'].abs().idxmax()
max_vol_diff = volume_check_df.loc[max_vol_diff_idx, 'Volume balance difference']
max_vol_rel_error = volume_check_df.loc[max_vol_diff_idx, 'Volume balance relative error']

print(f"Total rows checked: {len(volume_check_df)}")
print(f"Rows with mismatch (difference > 1.0 m³/h): {(volume_check_df['Volume balance difference'].abs() > 1.0).sum()}")
print(f"Rows with mismatch (difference > 10.0 m³/h): {(volume_check_df['Volume balance difference'].abs() > 10.0).sum()}")
print(f"Rows with mismatch (difference > 50.0 m³/h): {(volume_check_df['Volume balance difference'].abs() > 50.0).sum()}")
print()
print(f"Maximum difference: {max_vol_diff:.4f} m³/h")
print(f"Maximum relative error: {max_vol_rel_error:.4f}%")
print(f"Location: Row {max_vol_diff_idx} ({df.loc[max_vol_diff_idx, 'Time stamp']})")
print(f"  Inflow F1 (per hour): {df.loc[max_vol_diff_idx, 'Inflow F1 per hour']:.4f} m³/h")
print(f"  Sum pumped flow F2: {df.loc[max_vol_diff_idx, 'Sum pumped flow F2']:.4f} m³/h")
print(f"  Net flow: {df.loc[max_vol_diff_idx, 'Net flow']:.4f} m³/h")
print(f"  Volume change per hour: {df.loc[max_vol_diff_idx, 'Volume change per hour']:.4f} m³/h")
print()

# Check 3: Water level vs Water volume relationship
print("CHECK 3: Water Level vs Water Volume Consistency")
print("-" * 80)
from scipy import stats
from numpy.polynomial import Polynomial

# Remove any rows with NaN values
valid_data = df[(df['Water level L2'].notna()) & (df['Water volume V'].notna())].copy()

if len(valid_data) > 0:
    # Try linear relationship: V = a * L + b
    slope, intercept, r_value, p_value, std_err = stats.linregress(valid_data['Water level L2'], valid_data['Water volume V'])
    
    print(f"Linear relationship: Volume = {slope:.2f} * Level + {intercept:.2f}")
    print(f"R-squared: {r_value**2:.6f}")
    print(f"Standard error: {std_err:.2f}")
    print()
    
    # Check minimum volume (volume at zero level)
    zero_level_data = valid_data[valid_data['Water level L2'].abs() < 0.1]
    if len(zero_level_data) > 0:
        min_volume = zero_level_data['Water volume V'].min()
        avg_volume_at_zero = zero_level_data['Water volume V'].mean()
        print(f"Volume at near-zero level (|level| < 0.1 m):")
        print(f"  Minimum: {min_volume:.2f} m³")
        print(f"  Average: {avg_volume_at_zero:.2f} m³")
        print(f"  Number of observations: {len(zero_level_data)}")
        print()
    
    # Try polynomial fit (degree 2): V = a*L² + b*L + c
    try:
        poly_coeffs = np.polyfit(valid_data['Water level L2'], valid_data['Water volume V'], 2)
        poly_pred = np.polyval(poly_coeffs, valid_data['Water level L2'])
        poly_r2 = np.corrcoef(valid_data['Water volume V'], poly_pred)[0, 1]**2
        poly_rmse = np.sqrt(np.mean((valid_data['Water volume V'] - poly_pred)**2))
        
        print(f"Polynomial (degree 2) relationship:")
        print(f"  Volume = {poly_coeffs[0]:.2f} * Level² + {poly_coeffs[1]:.2f} * Level + {poly_coeffs[2]:.2f}")
        print(f"  R-squared: {poly_r2:.6f}")
        print(f"  RMSE: {poly_rmse:.2f} m³")
        print()
    except:
        print("Could not fit polynomial model")
        print()
    
    # Calculate predicted volume from linear model
    valid_data['Predicted volume'] = slope * valid_data['Water level L2'] + intercept
    valid_data['Level-volume difference'] = valid_data['Water volume V'] - valid_data['Predicted volume']
    valid_data['Level-volume relative error'] = np.abs(valid_data['Level-volume difference'] / (valid_data['Water volume V'] + 1e-10)) * 100
    
    max_lv_diff_idx = valid_data['Level-volume difference'].abs().idxmax()
    max_lv_diff = valid_data.loc[max_lv_diff_idx, 'Level-volume difference']
    max_lv_rel_error = valid_data.loc[max_lv_diff_idx, 'Level-volume relative error']
    
    print(f"Rows with mismatch (difference > 10 m³): {(valid_data['Level-volume difference'].abs() > 10).sum()}")
    print(f"Rows with mismatch (difference > 50 m³): {(valid_data['Level-volume difference'].abs() > 50).sum()}")
    print(f"Rows with mismatch (difference > 100 m³): {(valid_data['Level-volume difference'].abs() > 100).sum()}")
    print()
    print(f"Maximum difference: {max_lv_diff:.4f} m³")
    print(f"Maximum relative error: {max_lv_rel_error:.4f}%")
    print(f"Location: Row {max_lv_diff_idx} ({df.loc[max_lv_diff_idx, 'Time stamp']})")
    print(f"  Water level: {df.loc[max_lv_diff_idx, 'Water level L2']:.4f} m")
    print(f"  Water volume: {df.loc[max_lv_diff_idx, 'Water volume V']:.4f} m³")
    print(f"  Predicted volume: {valid_data.loc[max_lv_diff_idx, 'Predicted volume']:.4f} m³")
    print()

# Summary statistics
print("=" * 80)
print("SUMMARY STATISTICS")
print("=" * 80)
print()
print("Pump Flow Consistency:")
print(f"  Mean absolute difference: {df['Pump flow difference'].abs().mean():.4f} m³/h")
print(f"  Median absolute difference: {df['Pump flow difference'].abs().median():.4f} m³/h")
print(f"  Std deviation: {df['Pump flow difference'].std():.4f} m³/h")
print()
print("Volume Balance:")
print(f"  Mean absolute difference: {volume_check_df['Volume balance difference'].abs().mean():.4f} m³/h")
print(f"  Median absolute difference: {volume_check_df['Volume balance difference'].abs().median():.4f} m³/h")
print(f"  Std deviation: {volume_check_df['Volume balance difference'].std():.4f} m³/h")
print()
print("Level-Volume Relationship:")
if len(valid_data) > 0:
    print(f"  Mean absolute difference: {valid_data['Level-volume difference'].abs().mean():.4f} m³")
    print(f"  Median absolute difference: {valid_data['Level-volume difference'].abs().median():.4f} m³")
    print(f"  Std deviation: {valid_data['Level-volume difference'].std():.4f} m³")
    print(f"  Correlation coefficient: {r_value:.6f}")
print()

# Show some problematic rows
print("=" * 80)
print("SAMPLE OF ROWS WITH LARGEST DISCREPANCIES")
print("=" * 80)
print()

print("Top 5 pump flow discrepancies:")
top_pump = df.nlargest(5, 'Pump flow difference', keep='all')[['Time stamp', 'Sum of individual pump flows', 'Sum pumped flow F2', 'Pump flow difference']]
print(top_pump.to_string(index=False))
print()

print("Top 5 volume balance discrepancies:")
top_vol = volume_check_df.nlargest(5, 'Volume balance difference', keep='all')[['Time stamp', 'Inflow F1 per hour', 'Sum pumped flow F2', 'Net flow', 'Volume change per hour', 'Volume balance difference']]
print(top_vol.to_string(index=False))
print()

if len(valid_data) > 0:
    print("Top 5 level-volume discrepancies:")
    top_lv = valid_data.nlargest(5, 'Level-volume difference', keep='all')[['Time stamp', 'Water level L2', 'Water volume V', 'Predicted volume', 'Level-volume difference']]
    print(top_lv.to_string(index=False))

