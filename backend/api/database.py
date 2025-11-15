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


def list_simulations() -> List[Dict[str, Any]]:
    """
    List all simulations with metadata and summary values.
    
    Returns:
        List of dicts with id, name, timestamp, total_cost, starting_water_level,
        average_water_level, total_electricity_consumption
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            s.id,
            s.name,
            s.timestamp,
            so.total_cost,
            si.starting_water_level,
            so.water_level_estimate_24h,
            so.electricity_consumption_24h
        FROM simulations s
        LEFT JOIN simulation_inputs si ON s.id = si.simulation_id
        LEFT JOIN simulation_outputs so ON s.id = so.simulation_id
        ORDER BY s.timestamp DESC
    """)
    rows = cursor.fetchall()
    
    conn.close()
    
    result = []
    for row in rows:
        # Calculate average water level
        water_levels = json.loads(row["water_level_estimate_24h"]) if row["water_level_estimate_24h"] else []
        avg_water_level = sum(water_levels) / len(water_levels) if water_levels else 0.0
        
        # Calculate total electricity consumption
        electricity_consumption = json.loads(row["electricity_consumption_24h"]) if row["electricity_consumption_24h"] else []
        total_electricity = sum(electricity_consumption) if electricity_consumption else 0.0
        
        result.append({
            "id": row["id"],
            "name": row["name"],
            "timestamp": row["timestamp"],
            "total_cost": row["total_cost"] if row["total_cost"] is not None else 0.0,
            "starting_water_level": row["starting_water_level"] if row["starting_water_level"] is not None else 0.0,
            "average_water_level": avg_water_level,
            "total_electricity_consumption": total_electricity
        })
    
    return result


def get_simulation_by_id(simulation_id: str) -> Optional[SimulationResponse]:
    """
    Get full simulation by UUID.
    
    Args:
        simulation_id: Simulation UUID
        
    Returns:
        SimulationResponse or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get simulation metadata
    cursor.execute("SELECT * FROM simulations WHERE id = ?", (simulation_id,))
    sim_row = cursor.fetchone()
    
    if sim_row is None:
        conn.close()
        return None
    
    # Get inputs
    cursor.execute("SELECT * FROM simulation_inputs WHERE simulation_id = ?", (simulation_id,))
    inputs_row = cursor.fetchone()
    
    # Get outputs
    cursor.execute("SELECT * FROM simulation_outputs WHERE simulation_id = ?", (simulation_id,))
    outputs_row = cursor.fetchone()
    
    # Get pumps
    cursor.execute("SELECT * FROM simulation_pumps WHERE simulation_id = ?", (simulation_id,))
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
        name=sim_row["name"],
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


def get_simulation_name_by_id(simulation_id: str) -> Optional[str]:
    """
    Get simulation name by UUID.
    
    Args:
        simulation_id: Simulation UUID
        
    Returns:
        Simulation name or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM simulations WHERE id = ?", (simulation_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    return row["name"] if row else None


def get_rain_forecast(simulation_id: str) -> Optional[List[float]]:
    """Get rain forecast for a simulation by UUID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT rain_forecast_24h FROM simulation_inputs WHERE simulation_id = ?", (simulation_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["rain_forecast_24h"]) if row else None


def get_electricity_prices(simulation_id: str) -> Optional[List[float]]:
    """Get electricity prices for a simulation by UUID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT electricity_price_24h FROM simulation_inputs WHERE simulation_id = ?", (simulation_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["electricity_price_24h"]) if row else None


def get_inflow_estimates(simulation_id: str) -> Optional[List[float]]:
    """Get inflow estimates for a simulation by UUID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT inflow_estimate_24h FROM simulation_inputs WHERE simulation_id = ?", (simulation_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["inflow_estimate_24h"]) if row else None


def get_water_levels(simulation_id: str) -> Optional[List[float]]:
    """Get water levels for a simulation by UUID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT water_level_estimate_24h FROM simulation_outputs WHERE simulation_id = ?", (simulation_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["water_level_estimate_24h"]) if row else None


def get_pumping_strategy(simulation_id: str) -> Optional[List[Dict[str, bool]]]:
    """Get pumping strategy for a simulation by UUID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT pumping_strategy_24h FROM simulation_outputs WHERE simulation_id = ?", (simulation_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["pumping_strategy_24h"]) if row else None


def get_electricity_consumption(simulation_id: str) -> Optional[List[float]]:
    """Get electricity consumption for a simulation by UUID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT electricity_consumption_24h FROM simulation_outputs WHERE simulation_id = ?", (simulation_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["electricity_consumption_24h"]) if row else None


def get_costs(simulation_id: str) -> Optional[List[float]]:
    """Get costs for a simulation by UUID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT cost_24h FROM simulation_outputs WHERE simulation_id = ?", (simulation_id,))
    row = cursor.fetchone()
    conn.close()
    
    return json.loads(row["cost_24h"]) if row else None


def get_pumps(simulation_id: str) -> Optional[List[PumpData]]:
    """Get pump data for a simulation by UUID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM simulation_pumps WHERE simulation_id = ?", (simulation_id,))
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


def get_total_cost(simulation_id: str) -> Optional[float]:
    """Get total cost for a simulation by UUID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT total_cost FROM simulation_outputs WHERE simulation_id = ?", (simulation_id,))
    row = cursor.fetchone()
    conn.close()
    
    return row["total_cost"] if row else None


# Initialize database on module import
init_database()

