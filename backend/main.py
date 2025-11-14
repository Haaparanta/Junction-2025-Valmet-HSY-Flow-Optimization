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
    
    # Create figure with subplots (larger to accommodate comparison plots)
    fig = plt.figure(figsize=(24, 20))
    gs = fig.add_gridspec(5, 2, hspace=0.35, wspace=0.3)
    
    # 1. Water Level over Time (with CSV comparison)
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(time_hours, data['water_levels'], 'b-', linewidth=2, label='Simulated Water Level', alpha=0.8)
    if csv_data is not None:
        csv_levels = [safe_float_convert(x) for x in csv_data['Water level in tunnel L2'].tolist()[:96]]
        ax1.plot(time_hours, csv_levels, 'b--', linewidth=1.5, label='CSV Water Level', alpha=0.6)
    ax1.axhline(y=14.1, color='r', linestyle='--', linewidth=2, label='Max Level (14.1 m)')
    ax1.axhline(y=0.5, color='orange', linestyle='--', linewidth=1, label='Min Target (0.5 m)')
    ax1.set_xlabel('Time (hours)')
    ax1.set_ylabel('Water Level (m)')
    ax1.set_title('Water Level in Tunnel Over Time')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 2. Volume over Time (with CSV comparison)
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(time_hours, data['volumes'], 'g-', linewidth=2, label='Simulated Volume', alpha=0.8)
    if csv_data is not None:
        csv_volumes = [safe_float_convert(x) for x in csv_data['Water volume in tunnel V'].tolist()[:96]]
        ax2.plot(time_hours, csv_volumes, 'g--', linewidth=1.5, label='CSV Volume', alpha=0.6)
    ax2.set_xlabel('Time (hours)')
    ax2.set_ylabel('Volume (m³)')
    ax2.set_title('Water Volume in Tunnel Over Time')
    ax2.grid(True, alpha=0.3)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.1f}k'))
    if csv_data is not None:
        ax2.legend()
    
    # 3. Inflow and Outflow (with CSV comparison)
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.plot(time_hours, data['inflows'], 'b-', linewidth=2, label='Simulated Inflow', alpha=0.7)
    ax3.plot(time_hours, data['outflows'], 'r-', linewidth=2, label='Simulated Outflow', alpha=0.7)
    ax3.plot(time_hours, data['target_flowrates'], 'g--', linewidth=1.5, label='Target Flowrate', alpha=0.8)
    if csv_data is not None:
        csv_inflows = [safe_float_convert(x) for x in csv_data['Inflow to tunnel F1'].tolist()[:96]]
        csv_outflows = [safe_float_convert(x) for x in csv_data['Sum of pumped flow to WWTP F2'].tolist()[:96]]
        csv_outflows_15min = [x / 4.0 for x in csv_outflows]  # Convert m³/h to m³/15min
        ax3.plot(time_hours, csv_inflows, 'b--', linewidth=1.5, label='CSV Inflow', alpha=0.5)
        ax3.plot(time_hours, csv_outflows_15min, 'r--', linewidth=1.5, label='CSV Outflow', alpha=0.5)
    ax3.set_xlabel('Time (hours)')
    ax3.set_ylabel('Flow Rate (m³/15min)')
    ax3.set_title('Inflow vs Outflow vs Target Flowrate')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # 4. Energy Prices (with CSV comparison)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.plot(time_hours, data['energy_prices'], 'purple', linewidth=2, marker='o', markersize=3, label='Simulated Energy Price', alpha=0.8)
    if csv_data is not None:
        csv_energy_prices = [safe_float_convert(x) for x in csv_data['Electricity price 2: normal'].tolist()[:96]]
        csv_energy_prices_eur = [x / 100.0 for x in csv_energy_prices]  # Convert from snt to EUR
        ax4.plot(time_hours, csv_energy_prices_eur, 'purple', linewidth=1.5, linestyle='--', label='CSV Energy Price', alpha=0.6)
    ax4.set_xlabel('Time (hours)')
    ax4.set_ylabel('Energy Price (EUR/kWh)')
    ax4.set_title('Energy Prices Over Time')
    ax4.grid(True, alpha=0.3)
    if csv_data is not None:
        ax4.legend()
    
    # 5. Cumulative Cost
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.plot(time_hours, data['cumulative_costs'], 'darkgreen', linewidth=2)
    ax5.set_xlabel('Time (hours)')
    ax5.set_ylabel('Cumulative Cost (EUR)')
    ax5.set_title('Cumulative Cost Over Time')
    ax5.grid(True, alpha=0.3)
    ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.1f}k'))
    
    # 6. Time Step Costs
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.bar(time_hours, data['costs'], width=0.25, alpha=0.7, color='orange')
    ax6.set_xlabel('Time (hours)')
    ax6.set_ylabel('Cost per Time Step (EUR)')
    ax6.set_title('Cost per 15-Minute Period')
    ax6.grid(True, alpha=0.3, axis='y')
    
    # 7. Pump States (Heatmap)
    ax7 = fig.add_subplot(gs[3, :])
    pump_ids = sorted(simulator.pumps.keys())
    pump_state_matrix = np.array([data['pump_states'][pid] for pid in pump_ids])
    
    im = ax7.imshow(pump_state_matrix, aspect='auto', cmap='RdYlGn', interpolation='nearest',
                    extent=[0, 24, 0, len(pump_ids)], vmin=0, vmax=1)
    ax7.set_xlabel('Time (hours)')
    ax7.set_ylabel('Pump ID')
    ax7.set_yticks(np.arange(len(pump_ids)) + 0.5)
    ax7.set_yticklabels(pump_ids)
    ax7.set_title('Pump States Over Time (Green=On, Red=Off)')
    cbar = plt.colorbar(im, ax=ax7, ticks=[0, 1])
    cbar.set_label('State (0=Off, 1=On)')
    
    # Save figure
    # Use /app/output in Docker, or local output directory
    output_dir = Path('/app/output') if Path('/app/output').exists() else Path(__file__).parent.parent / 'output'
    output_dir.mkdir(exist_ok=True, parents=True)
    plot_path = output_dir / 'simulation_results.png'
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    print(f"Plots saved to: {plot_path}")
    
    # Also create a detailed pump usage plot
    fig2, ax = plt.subplots(figsize=(14, 8))
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
    
    pump_plot_path = output_dir / 'pump_usage.png'
    plt.savefig(pump_plot_path, dpi=150, bbox_inches='tight')
    print(f"Pump usage plot saved to: {pump_plot_path}")
    
    plt.close('all')


if __name__ == '__main__':
    try:
        cost = main()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

