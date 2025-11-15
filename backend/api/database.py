"""SQLite database for storing simulation data."""
import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import SimulationResponse, PumpData, PumpPerformanceCurve


# Database file path (ephemeral storage in Cloud Run)
DB_PATH = "/tmp/simulations.db"


def get_db_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create simulations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulations (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create simulation_inputs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_inputs (
            simulation_id TEXT PRIMARY KEY,
            timestamps_24h TEXT NOT NULL,
            rain_forecast_24h TEXT NOT NULL,
            electricity_price_24h TEXT NOT NULL,
            inflow_estimate_24h TEXT NOT NULL,
            starting_water_level REAL NOT NULL,
            FOREIGN KEY (simulation_id) REFERENCES simulations(id) ON DELETE CASCADE
        )
    """)
    
    # Create simulation_outputs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_outputs (
            simulation_id TEXT PRIMARY KEY,
            pumping_strategy_24h TEXT NOT NULL,
            water_level_estimate_24h TEXT NOT NULL,
            electricity_consumption_24h TEXT NOT NULL,
            cost_24h TEXT NOT NULL,
            total_cost REAL NOT NULL,
            FOREIGN KEY (simulation_id) REFERENCES simulations(id) ON DELETE CASCADE
        )
    """)
    
    # Create simulation_pumps table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_pumps (
            simulation_id TEXT NOT NULL,
            pump_name TEXT NOT NULL,
            performance_curve_head TEXT NOT NULL,
            performance_curve_flow TEXT NOT NULL,
            values_24h TEXT NOT NULL,
            PRIMARY KEY (simulation_id, pump_name),
            FOREIGN KEY (simulation_id) REFERENCES simulations(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()


def save_simulation_to_db(simulation: SimulationResponse, name: str) -> None:
    """
    Save simulation to database.
    
    Args:
        simulation: SimulationResponse to save
        name: Simulation name (timestamp if not provided)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert into simulations table
        cursor.execute("""
            INSERT INTO simulations (id, name, timestamp, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            simulation.id,
            name,
            simulation.timestamp.isoformat(),
            datetime.utcnow().isoformat()
        ))
        
        # Insert into simulation_inputs table
        cursor.execute("""
            INSERT INTO simulation_inputs (
                simulation_id, timestamps_24h, rain_forecast_24h,
                electricity_price_24h, inflow_estimate_24h, starting_water_level
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            simulation.id,
            json.dumps(simulation.timestamps_24h),
            json.dumps(simulation.rain_forecast_24h),
            json.dumps(simulation.electricity_price_24h),
            json.dumps(simulation.inflow_estimate_24h),
            simulation.starting_water_level
        ))
        
        # Insert into simulation_outputs table
        cursor.execute("""
            INSERT INTO simulation_outputs (
                simulation_id, pumping_strategy_24h, water_level_estimate_24h,
                electricity_consumption_24h, cost_24h, total_cost
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            simulation.id,
            json.dumps(simulation.pumping_strategy_24h),
            json.dumps(simulation.water_level_estimate_24h),
            json.dumps(simulation.electricity_consumption_24h),
            json.dumps(simulation.cost_24h),
            simulation.total_cost
        ))
        
        # Insert pump data
        for pump in simulation.pumps:
            cursor.execute("""
                INSERT INTO simulation_pumps (
                    simulation_id, pump_name, performance_curve_head,
                    performance_curve_flow, values_24h
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                simulation.id,
                pump.pump_name,
                json.dumps(pump.performance_curve.head_values),
                json.dumps(pump.performance_curve.flow_values),
                json.dumps(pump.values_24h)
            ))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_simulation_by_name(name: str) -> Optional[SimulationResponse]:
    """
    Get full simulation by name.
    
    Args:
        name: Simulation name
        
    Returns:
        SimulationResponse or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get simulation metadata
    cursor.execute("SELECT * FROM simulations WHERE name = ?", (name,))
    sim_row = cursor.fetchone()
    
    if sim_row is None:
        conn.close()
        return None
    
    sim_id = sim_row["id"]
    
    # Get inputs
    cursor.execute("SELECT * FROM simulation_inputs WHERE simulation_id = ?", (sim_id,))
    inputs_row = cursor.fetchone()
    
    # Get outputs
    cursor.execute("SELECT * FROM simulation_outputs WHERE simulation_id = ?", (sim_id,))
    outputs_row = cursor.fetchone()
    
    # Get pumps
    cursor.execute("SELECT * FROM simulation_pumps WHERE simulation_id = ?", (sim_id,))
    pumps_rows = cursor.fetchall()
    
    conn.close()
    
    if inputs_row is None or outputs_row is None:
        return None
    
    # Reconstruct SimulationResponse
    pumps_data = []
    for pump_row in pumps_rows:
        pump_data = PumpData(
            pump_name=pump_row["pump_name"],
            performance_curve=PumpPerformanceCurve(
                head_values=json.loads(pump_row["performance_curve_head"]),
                flow_values=json.loads(pump_row["performance_curve_flow"])
            ),
            values_24h=json.loads(pump_row["values_24h"])
        )
        pumps_data.append(pump_data)
    
    response = SimulationResponse(
        id=sim_row["id"],
        timestamp=datetime.fromisoformat(sim_row["timestamp"]),
        timestamps_24h=json.loads(inputs_row["timestamps_24h"]),
        rain_forecast_24h=json.loads(inputs_row["rain_forecast_24h"]),
        electricity_price_24h=json.loads(inputs_row["electricity_price_24h"]),
        inflow_estimate_24h=json.loads(inputs_row["inflow_estimate_24h"]),
        pumping_strategy_24h=json.loads(outputs_row["pumping_strategy_24h"]),
        water_level_estimate_24h=json.loads(outputs_row["water_level_estimate_24h"]),
        electricity_consumption_24h=json.loads(outputs_row["electricity_consumption_24h"]),
        cost_24h=json.loads(outputs_row["cost_24h"]),
        pumps=pumps_data,
        total_cost=outputs_row["total_cost"],
        starting_water_level=inputs_row["starting_water_level"]
    )
    
    return response


def list_simulations() -> List[Dict[str, Any]]:
    """
    List all simulations with metadata.
    
    Returns:
        List of dicts with id, name, timestamp
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, timestamp FROM simulations ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    
    conn.close()
    
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "timestamp": row["timestamp"]
        }
        for row in rows
    ]


def get_simulation_id_by_name(name: str) -> Optional[str]:
    """
    Get simulation ID by name.
    
    Args:
        name: Simulation name
        
    Returns:
        Simulation ID or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM simulations WHERE name = ?", (name,))
    row = cursor.fetchone()
    
    conn.close()
    
    return row["id"] if row else None


def get_rain_forecast(name: str) -> Optional[List[float]]:
    """Get rain forecast for a simulation by name."""
    sim_id = get_simulation_id_by_name(name)
    if sim_id is None:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT rain_forecast_24h FROM simulation_inputs WHERE simulation_id = ?", (sim_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["rain_forecast_24h"]) if row else None


def get_electricity_prices(name: str) -> Optional[List[float]]:
    """Get electricity prices for a simulation by name."""
    sim_id = get_simulation_id_by_name(name)
    if sim_id is None:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT electricity_price_24h FROM simulation_inputs WHERE simulation_id = ?", (sim_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["electricity_price_24h"]) if row else None


def get_inflow_estimates(name: str) -> Optional[List[float]]:
    """Get inflow estimates for a simulation by name."""
    sim_id = get_simulation_id_by_name(name)
    if sim_id is None:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT inflow_estimate_24h FROM simulation_inputs WHERE simulation_id = ?", (sim_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["inflow_estimate_24h"]) if row else None


def get_water_levels(name: str) -> Optional[List[float]]:
    """Get water levels for a simulation by name."""
    sim_id = get_simulation_id_by_name(name)
    if sim_id is None:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT water_level_estimate_24h FROM simulation_outputs WHERE simulation_id = ?", (sim_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["water_level_estimate_24h"]) if row else None


def get_pumping_strategy(name: str) -> Optional[List[Dict[str, bool]]]:
    """Get pumping strategy for a simulation by name."""
    sim_id = get_simulation_id_by_name(name)
    if sim_id is None:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT pumping_strategy_24h FROM simulation_outputs WHERE simulation_id = ?", (sim_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["pumping_strategy_24h"]) if row else None


def get_electricity_consumption(name: str) -> Optional[List[float]]:
    """Get electricity consumption for a simulation by name."""
    sim_id = get_simulation_id_by_name(name)
    if sim_id is None:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT electricity_consumption_24h FROM simulation_outputs WHERE simulation_id = ?", (sim_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["electricity_consumption_24h"]) if row else None


def get_costs(name: str) -> Optional[List[float]]:
    """Get costs for a simulation by name."""
    sim_id = get_simulation_id_by_name(name)
    if sim_id is None:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT cost_24h FROM simulation_outputs WHERE simulation_id = ?", (sim_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["cost_24h"]) if row else None


def get_pumps(name: str) -> Optional[List[PumpData]]:
    """Get pump data for a simulation by name."""
    sim_id = get_simulation_id_by_name(name)
    if sim_id is None:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM simulation_pumps WHERE simulation_id = ?", (sim_id,))
    pumps_rows = cursor.fetchall()
    conn.close()
    
    if not pumps_rows:
        return None
    
    pumps_data = []
    for pump_row in pumps_rows:
        pump_data = PumpData(
            pump_name=pump_row["pump_name"],
            performance_curve=PumpPerformanceCurve(
                head_values=json.loads(pump_row["performance_curve_head"]),
                flow_values=json.loads(pump_row["performance_curve_flow"])
            ),
            values_24h=json.loads(pump_row["values_24h"])
        )
        pumps_data.append(pump_data)
    
    return pumps_data


def get_total_cost(name: str) -> Optional[float]:
    """Get total cost for a simulation by name."""
    sim_id = get_simulation_id_by_name(name)
    if sim_id is None:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT total_cost FROM simulation_outputs WHERE simulation_id = ?", (sim_id,))
    row = cursor.fetchone()
    conn.close()
    
    return row["total_cost"] if row else None


# Initialize database on module import
init_database()

