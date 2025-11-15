"""Main entry point for running the 24-hour simulation."""
import os
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for Docker
import matplotlib.pyplot as plt
import numpy as np
from simulation.simulator import Simulator
from simulation.csv_reader import read_csv_with_european_format


def main():
    """Run simulation with data from CSV file."""
    # Get CSV file path (default to data file in Valmet-HSY-Docs)
    csv_path = os.getenv(
        'CSV_DATA_PATH',
        str(Path(__file__).parent.parent / 'Valmet-HSY-Docs' / 'Hackathon_HSY_data.csv')
    )
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)
    
    print(f"Reading CSV data from: {csv_path}")
    
    # Read CSV data
    df = read_csv_with_european_format(csv_path)
    
    # Get starting water level from first row and ensure it's a float
    starting_water_level = float(df.iloc[0]['Water level in tunnel L2'])
    print(f"Starting water level: {starting_water_level:.2f} m")
    
    # Extract 96 consecutive rows (24 hours * 4 periods)
    # Use first 96 rows for simulation
    simulation_data = df.head(96)
    
    if len(simulation_data) < 96:
        print(f"Warning: Only {len(simulation_data)} rows available, need 96 rows")
        # Pad with last value if needed
        while len(simulation_data) < 96:
            last_row = simulation_data.iloc[[-1]]
            simulation_data = pd.concat([simulation_data, last_row], ignore_index=True)
    
    # Extract energy prices (convert from snt/kWh to EUR/kWh by dividing by 100)
    energy_prices_snt = [float(x) for x in simulation_data['Electricity price 2: normal'].tolist()]
    energy_prices = [price / 100.0 for price in energy_prices_snt]  # Convert cents to euros
    
    # Extract water inflows (already in m³/15min) and ensure they're floats
    water_inflows = [float(x) for x in simulation_data['Inflow to tunnel F1'].tolist()]
    
    # Extract target flowrates
    # "Sum of pumped flow to WWTP F2" is in m³/h, convert to m³/15min
    target_flowrates_m3h = [float(x) for x in simulation_data['Sum of pumped flow to WWTP F2'].tolist()]
    target_flowrates = [flow / 4.0 for flow in target_flowrates_m3h]  # Convert m³/h to m³/15min
    
    print(f"Energy prices range: {min(energy_prices):.3f} - {max(energy_prices):.3f} EUR/kWh")
    print(f"Water inflows range: {min(water_inflows):.2f} - {max(water_inflows):.2f} m³/15min")
    print(f"Target flowrates range: {min(target_flowrates):.2f} - {max(target_flowrates):.2f} m³/15min")
    
    # Create simulator
    simulator = Simulator(
        starting_water_level=starting_water_level,
        energy_prices=energy_prices,
        water_inflows=water_inflows,
        target_flowrates=target_flowrates
    )
    
    # Run simulation
    print("\nRunning 24-hour simulation...")
    total_cost = simulator.simulate()
    
    # Print results
    print(f"\n{'='*60}")
    print(f"Simulation Results")
    print(f"{'='*60}")
    print(f"Total cost: {total_cost:,.2f} EUR")
    print(f"Final water level: {simulator.current_water_level:.2f} m")
    print(f"Final volume: {simulator.current_volume:,.2f} m³")
    
    # Print pump usage statistics
    print(f"\nPump Usage Statistics:")
    print(f"{'Pump ID':<10} {'Usage Time (hours)':<20} {'Usage Time (minutes)':<25} {'Cost (EUR)':<15}")
    print("-" * 75)
    for pump_id, pump in sorted(simulator.pumps.items()):
        usage_hours = pump.get_usage_time() / 60.0
        usage_minutes = pump.get_usage_time()
        pump_cost = simulator.pump_costs.get(pump_id, 0.0)
        print(f"{pump_id:<10} {usage_hours:<20.2f} {usage_minutes:<25.2f} {pump_cost:<15.2f}")
    
    # Print usage balance statistics
    usage_times = [pump.get_usage_time() / 60.0 for pump in simulator.pumps.values()]
    if usage_times:
        avg_usage = sum(usage_times) / len(usage_times)
        min_usage = min(usage_times)
        max_usage = max(usage_times)
        print(f"\nUsage Balance:")
        print(f"  Average: {avg_usage:.2f} hours")
        print(f"  Min: {min_usage:.2f} hours")
        print(f"  Max: {max_usage:.2f} hours")
        print(f"  Range: {max_usage - min_usage:.2f} hours")
        print(f"  Balance ratio (min/max): {min_usage/max_usage:.2%}" if max_usage > 0 else "  Balance ratio: N/A")
    
    # Print violations if any
    if simulator.violations:
        print(f"\n{'='*60}")
        print(f"Violations ({len(simulator.violations)}):")
        print(f"{'='*60}")
        for violation in simulator.violations:
            print(f"  - {violation}")
    else:
        print(f"\nNo violations detected!")
    
    print(f"\n{'='*60}")
    
    # Generate plots
    print("\nGenerating plots...")
    csv_path = os.getenv(
        'CSV_DATA_PATH',
        str(Path(__file__).parent.parent / 'Valmet-HSY-Docs' / 'Hackathon_HSY_data.csv')
    )
    plot_simulation_results(simulator, csv_path)
    
    return total_cost


def safe_float_convert(value):
    """
    Safely convert value to float, handling special characters like minus signs.
    
    Args:
        value: Value to convert (can be string, float, or other numeric type)
        
    Returns:
        float value, or 0.0 if conversion fails
    """
    if pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    # Convert to string and replace special minus sign (U+2212) with regular minus
    str_value = str(value).replace('−', '-').replace(',', '.')
    try:
        return float(str_value)
    except (ValueError, TypeError):
        return 0.0


def plot_simulation_results(simulator: Simulator, csv_path: str = None):
    """
    Generate comprehensive plots of simulation results with comparison to CSV data.
    Each plot is saved as a separate image file.
    
    Args:
        simulator: Simulator instance with completed simulation data
        csv_path: Optional path to CSV file for comparison
    """
    data = simulator.time_series_data
    time_steps = np.arange(96)  # 96 time steps of 15 minutes each
    time_hours = time_steps * 15 / 60  # Convert to hours
    
    # Load CSV data for comparison if provided
    csv_data = None
    if csv_path and os.path.exists(csv_path):
        try:
            df_csv = read_csv_with_european_format(csv_path)
            csv_data = df_csv.head(96)  # First 96 rows for comparison
        except Exception as e:
            print(f"Warning: Could not load CSV data for comparison: {e}")
            csv_data = None
    
    # Use /app/output in Docker, or local output directory
    output_dir = Path('/app/output') if Path('/app/output').exists() else Path(__file__).parent.parent / 'output'
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Create separate plots
    plot_water_level(simulator, csv_data, time_hours, output_dir)
    plot_volume(simulator, csv_data, time_hours, output_dir)
    plot_inflow_outflow(simulator, csv_data, time_hours, output_dir)
    plot_energy_prices(simulator, csv_data, time_hours, output_dir)
    plot_cumulative_cost(simulator, time_hours, output_dir)
    plot_time_step_costs(simulator, time_hours, output_dir)
    plot_pump_states(simulator, csv_data, time_hours, output_dir)
    create_pump_flow_comparison_plot(simulator, csv_data, time_hours, output_dir)
    plot_pump_usage(simulator, output_dir)
    
    print(f"\nAll plots saved to: {output_dir}")


def plot_water_level(simulator: Simulator, csv_data, time_hours, output_dir: Path):
    """Plot water level over time."""
    fig, ax = plt.subplots(figsize=(12, 6))
    data = simulator.time_series_data
    
    ax.plot(time_hours, data['water_levels'], 'b-', linewidth=2, label='Simulated Water Level', alpha=0.8)
    if csv_data is not None:
        csv_levels = [safe_float_convert(x) for x in csv_data['Water level in tunnel L2'].tolist()[:96]]
        ax.plot(time_hours, csv_levels, 'b--', linewidth=1.5, label='CSV Water Level', alpha=0.6)
    ax.axhline(y=14.1, color='r', linestyle='--', linewidth=2, label='Max Level (14.1 m)')
    ax.axhline(y=0.5, color='orange', linestyle='--', linewidth=1, label='Min Target (0.5 m)')
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('Water Level (m)')
    ax.set_title('Water Level in Tunnel Over Time')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    plot_path = output_dir / 'water_level.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Water level plot saved to: {plot_path}")
    plt.close()


def plot_volume(simulator: Simulator, csv_data, time_hours, output_dir: Path):
    """Plot water volume over time."""
    fig, ax = plt.subplots(figsize=(12, 6))
    data = simulator.time_series_data
    
    ax.plot(time_hours, data['volumes'], 'g-', linewidth=2, label='Simulated Volume', alpha=0.8)
    if csv_data is not None:
        csv_volumes = [safe_float_convert(x) for x in csv_data['Water volume in tunnel V'].tolist()[:96]]
        ax.plot(time_hours, csv_volumes, 'g--', linewidth=1.5, label='CSV Volume', alpha=0.6)
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('Volume (m³)')
    ax.set_title('Water Volume in Tunnel Over Time')
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.1f}k'))
    if csv_data is not None:
        ax.legend()
    
    plt.tight_layout()
    plot_path = output_dir / 'volume.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Volume plot saved to: {plot_path}")
    plt.close()


def plot_inflow_outflow(simulator: Simulator, csv_data, time_hours, output_dir: Path):
    """Plot inflow and outflow over time."""
    fig, ax = plt.subplots(figsize=(12, 6))
    data = simulator.time_series_data
    
    # Lines behind others (lower zorder) get thicker lines to show through better
    # CSV lines are behind everything (zorder=2) - thickest
    if csv_data is not None:
        csv_inflows = [safe_float_convert(x) for x in csv_data['Inflow to tunnel F1'].tolist()[:96]]
        csv_outflows = [safe_float_convert(x) for x in csv_data['Sum of pumped flow to WWTP F2'].tolist()[:96]]
        csv_outflows_15min = [x / 4.0 for x in csv_outflows]  # Convert m³/h to m³/15min
        ax.plot(time_hours, csv_inflows, '--', linewidth=4.0, label='CSV Inflow', alpha=0.8, zorder=2, color='#4169E1')
        ax.plot(time_hours, csv_outflows_15min, '--', linewidth=4.0, label='CSV Outflow', alpha=0.8, zorder=2, color='#DC143C')
    
    # Simulated lines are in the middle (zorder=3) - medium thickness
    ax.plot(time_hours, data['inflows'], 'b-', linewidth=2.5, label='Simulated Inflow', alpha=0.9, zorder=3)
    ax.plot(time_hours, data['outflows'], 'r-', linewidth=2.5, label='Simulated Outflow', alpha=0.9, zorder=3)
    
    # Target Flowrate is on top (zorder=4) - thinnest since it doesn't need to show through
    ax.plot(time_hours, data['target_flowrates'], 'g--', linewidth=2.0, label='Target Flowrate', alpha=0.9, zorder=4)
    
    ax.set_xlabel('Time (hours)', fontsize=12)
    ax.set_ylabel('Flow Rate (m³/15min)', fontsize=12)
    ax.set_title('Inflow vs Outflow vs Target Flowrate', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=10, framealpha=0.9)
    
    plt.tight_layout()
    plot_path = output_dir / 'inflow_outflow.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Inflow/outflow plot saved to: {plot_path}")
    plt.close()


def plot_energy_prices(simulator: Simulator, csv_data, time_hours, output_dir: Path):
    """Plot energy prices over time."""
    fig, ax = plt.subplots(figsize=(12, 6))
    data = simulator.time_series_data
    
    ax.plot(time_hours, data['energy_prices'], 'purple', linewidth=2, marker='o', markersize=3, label='Simulated Energy Price', alpha=0.8)
    if csv_data is not None:
        csv_energy_prices = [safe_float_convert(x) for x in csv_data['Electricity price 2: normal'].tolist()[:96]]
        csv_energy_prices_eur = [x / 100.0 for x in csv_energy_prices]  # Convert from snt to EUR
        ax.plot(time_hours, csv_energy_prices_eur, 'purple', linewidth=1.5, linestyle='--', label='CSV Energy Price', alpha=0.6)
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('Energy Price (EUR/kWh)')
    ax.set_title('Energy Prices Over Time')
    ax.grid(True, alpha=0.3)
    if csv_data is not None:
        ax.legend()
    
    plt.tight_layout()
    plot_path = output_dir / 'energy_prices.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Energy prices plot saved to: {plot_path}")
    plt.close()


def plot_cumulative_cost(simulator: Simulator, time_hours, output_dir: Path):
    """Plot cumulative cost over time."""
    fig, ax = plt.subplots(figsize=(12, 6))
    data = simulator.time_series_data
    
    ax.plot(time_hours, data['cumulative_costs'], 'darkgreen', linewidth=2)
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('Cumulative Cost (EUR)')
    ax.set_title('Cumulative Cost Over Time')
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.1f}k'))
    
    plt.tight_layout()
    plot_path = output_dir / 'cumulative_cost.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Cumulative cost plot saved to: {plot_path}")
    plt.close()


def plot_time_step_costs(simulator: Simulator, time_hours, output_dir: Path):
    """Plot cost per time step."""
    fig, ax = plt.subplots(figsize=(12, 6))
    data = simulator.time_series_data
    
    ax.bar(time_hours, data['costs'], width=0.25, alpha=0.7, color='orange')
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('Cost per Time Step (EUR)')
    ax.set_title('Cost per 15-Minute Period')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plot_path = output_dir / 'time_step_costs.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Time step costs plot saved to: {plot_path}")
    plt.close()


def plot_pump_states(simulator: Simulator, csv_data, time_hours, output_dir: Path):
    """Plot pump states comparison (simulated vs CSV)."""
    pump_ids = sorted(simulator.pumps.keys())
    data = simulator.time_series_data
    
    # Create figure with two subplots side by side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 6))
    
    # Simulated pump states
    pump_state_matrix_sim = np.array([data['pump_states'][pid] for pid in pump_ids])
    im_sim = ax1.imshow(pump_state_matrix_sim, aspect='auto', cmap='RdYlGn', interpolation='nearest',
                        extent=[0, 24, 0, len(pump_ids)], vmin=0, vmax=1)
    ax1.set_xlabel('Time (hours)')
    ax1.set_ylabel('Pump ID')
    ax1.set_yticks(np.arange(len(pump_ids)) + 0.5)
    ax1.set_yticklabels(pump_ids)
    ax1.set_title('Simulated Pump States (Green=On, Red=Off)')
    cbar_sim = plt.colorbar(im_sim, ax=ax1, ticks=[0, 1])
    cbar_sim.set_label('State (0=Off, 1=On)')
    
    # CSV pump states (inferred from pump flows)
    if csv_data is not None:
        # Extract pump states from CSV flows (flow > 0 means pump is on)
        csv_pump_states = {}
        for pump_id in pump_ids:
            csv_column = f'Pump flow {pump_id}'
            if csv_column in csv_data.columns:
                csv_flows = [safe_float_convert(x) for x in csv_data[csv_column].tolist()[:96]]
                # Pump is on if flow > 0, off if flow == 0
                csv_pump_states[pump_id] = [1.0 if flow > 0 else 0.0 for flow in csv_flows]
            else:
                # If column doesn't exist, assume all off
                csv_pump_states[pump_id] = [0.0] * 96
        
        pump_state_matrix_csv = np.array([csv_pump_states[pid] for pid in pump_ids])
        im_csv = ax2.imshow(pump_state_matrix_csv, aspect='auto', cmap='RdYlGn', interpolation='nearest',
                            extent=[0, 24, 0, len(pump_ids)], vmin=0, vmax=1)
        ax2.set_xlabel('Time (hours)')
        ax2.set_ylabel('Pump ID')
        ax2.set_yticks(np.arange(len(pump_ids)) + 0.5)
        ax2.set_yticklabels(pump_ids)
        ax2.set_title('CSV Pump States (Green=On, Red=Off)')
        cbar_csv = plt.colorbar(im_csv, ax=ax2, ticks=[0, 1])
        cbar_csv.set_label('State (0=Off, 1=On)')
    else:
        ax2.text(0.5, 0.5, 'No CSV data available', ha='center', va='center', transform=ax2.transAxes)
        ax2.set_title('CSV Pump States (No Data)')
        ax2.axis('off')
    
    plt.tight_layout()
    plot_path = output_dir / 'pump_states.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Pump states plot saved to: {plot_path}")
    plt.close()


def plot_pump_usage(simulator: Simulator, output_dir: Path):
    """Plot pump usage time distribution."""
    pump_ids = sorted(simulator.pumps.keys())
    fig, ax = plt.subplots(figsize=(14, 8))
    
    pump_usage_data = [simulator.pumps[pid].get_usage_time() / 60.0 for pid in pump_ids]
    # Small pumps: 1.1, 2.1; Big pumps: 1.2, 1.3, 1.4, 2.2, 2.3, 2.4
    colors = ['#2ecc71' if pid in ['1.1', '2.1'] else '#3498db' for pid in pump_ids]
    bars = ax.bar(pump_ids, pump_usage_data, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax.set_xlabel('Pump ID', fontsize=12)
    ax.set_ylabel('Usage Time (hours)', fontsize=12)
    ax.set_title('Pump Usage Time Distribution (24-hour simulation)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, usage in zip(bars, pump_usage_data):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{usage:.1f}h',
                ha='center', va='bottom', fontsize=10)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#3498db', alpha=0.7, label='Big Pumps (400 kW)'),
        Patch(facecolor='#2ecc71', alpha=0.7, label='Small Pumps (250 kW)')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    pump_plot_path = output_dir / 'pump_usage.png'
    plt.savefig(pump_plot_path, dpi=150, bbox_inches='tight')
    print(f"Pump usage plot saved to: {pump_plot_path}")
    plt.close()


def create_pump_flow_comparison_plot(simulator: Simulator, csv_data, time_hours, output_dir: Path):
    """
    Create a plot comparing pump flows from CSV and simulator.
    
    Args:
        simulator: Simulator instance with completed simulation data
        csv_data: CSV DataFrame with historical data (or None)
        time_hours: Array of time values in hours
        output_dir: Directory to save the plot
    """
    pump_ids = sorted(simulator.pumps.keys())
    data = simulator.time_series_data
    
    # Create figure with subplots for each pump (2 rows x 4 columns for 8 pumps)
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    fig.suptitle('Pump Flow Comparison: CSV vs Simulator', fontsize=16, fontweight='bold')
    
    for idx, pump_id in enumerate(pump_ids):
        row = idx // 4
        col = idx % 4
        ax = axes[row, col]
        
        # Get simulated pump flow (stored in m³/h, convert to m³/15min)
        sim_flows_m3h = data['pump_flows'][pump_id]
        sim_flows = [flow / 4.0 for flow in sim_flows_m3h]  # Convert m³/h to m³/15min
        
        # Plot simulated flow
        ax.plot(time_hours, sim_flows, 'b-', linewidth=2, label='Simulated', alpha=0.8)
        
        # Get CSV pump flow if available (CSV flows are in m³/h, convert to m³/15min)
        if csv_data is not None:
            csv_column = f'Pump flow {pump_id}'
            if csv_column in csv_data.columns:
                csv_flows_m3h = [safe_float_convert(x) for x in csv_data[csv_column].tolist()[:96]]
                csv_flows = [flow / 4.0 for flow in csv_flows_m3h]  # Convert m³/h to m³/15min
                ax.plot(time_hours, csv_flows, 'r--', linewidth=1.5, label='CSV', alpha=0.7)
        
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Flow (m³/15min)')
        ax.set_title(f'Pump {pump_id}')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
    
    plt.tight_layout()
    pump_flow_plot_path = output_dir / 'pump_flow_comparison.png'
    plt.savefig(pump_flow_plot_path, dpi=150, bbox_inches='tight')
    print(f"Pump flow comparison plot saved to: {pump_flow_plot_path}")
    plt.close()


if __name__ == '__main__':
    try:
        cost = main()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

