"""Example integration of OPC UA with FastAPI backend."""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, Body, Query
from pydantic import BaseModel, Field
from opc_ua import OPCUABridge, OPCUAConfig
from api.main import create_simulation, convert_simulator_to_response
from api.data_fetcher import (
    fetch_rain_forecast_24h,
    fetch_electricity_prices_24h,
    calculate_average_daily_inflow,
    get_starting_water_level
)
from simulation.simulator import Simulator
from datetime import datetime
from uuid import uuid4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="OPC UA Integrated Simulation API")

# Initialize OPC UA bridge
bridge = OPCUABridge()


async def optimization_callback(water_level: float, pump_states: Dict[str, bool]) -> Dict:
    """
    Callback function for control loop to trigger optimization.
    
    This function is called by the control loop when optimization is needed.
    It runs the simulation and returns the results.
    """
    try:
        logger.info(f"Running optimization with water level: {water_level} m")
        
        # Fetch data
        rain_forecast = fetch_rain_forecast_24h()
        electricity_prices = fetch_electricity_prices_24h()
        inflow_estimates = calculate_average_daily_inflow()
        
        # Use provided water level or fallback
        starting_water_level = water_level if water_level else get_starting_water_level()
        
        # Derive target flowrates
        target_flowrates = [inflow * 1.1 for inflow in inflow_estimates]
        
        # Create and run simulator
        simulator = Simulator(
            starting_water_level=starting_water_level,
            energy_prices=electricity_prices,
            water_inflows=inflow_estimates,
            target_flowrates=target_flowrates
        )
        
        # Run simulation
        total_cost = simulator.simulate()
        
        # Generate simulation ID and name
        simulation_id = str(uuid4())
        simulation_timestamp = datetime.utcnow()
        simulation_name = simulation_timestamp.isoformat()
        
        # Convert to response format
        response = convert_simulator_to_response(
            simulator=simulator,
            rain_forecast=rain_forecast,
            electricity_prices=electricity_prices,
            inflow_estimates=inflow_estimates,
            starting_water_level=starting_water_level,
            simulation_id=simulation_id,
            simulation_name=simulation_name,
            simulation_timestamp=simulation_timestamp
        )
        
        # Convert to dict for return
        return response.dict()
        
    except Exception as e:
        logger.error(f"Error in optimization callback: {e}", exc_info=True)
        return {}


@app.on_event("startup")
async def startup_event():
    """Initialize OPC UA bridge on startup."""
    try:
        await bridge.initialize(optimization_callback=optimization_callback)
        await bridge.start_server()
        await bridge.start_control_loop()
        logger.info("OPC UA bridge started successfully")
    except Exception as e:
        logger.error(f"Error starting OPC UA bridge: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Stop OPC UA bridge on shutdown."""
    try:
        await bridge.stop()
        logger.info("OPC UA bridge stopped")
    except Exception as e:
        logger.error(f"Error stopping OPC UA bridge: {e}", exc_info=True)


@app.post("/api/simulate")
async def simulate_with_opcua():
    """
    Create simulation and sync results to OPC UA.
    
    This endpoint:
    1. Reads sensor data from OPC UA client (if connected)
    2. Runs optimization simulation
    3. Syncs results to OPC UA server
    """
    try:
        # Get sensor data from OPC UA
        sensor_data = await bridge.get_sensor_data()
        water_level = sensor_data.get("water_level")
        
        # Use sensor data if available, otherwise use defaults
        if water_level is None:
            water_level = get_starting_water_level()
        
        # Fetch data
        rain_forecast = fetch_rain_forecast_24h()
        electricity_prices = fetch_electricity_prices_24h()
        inflow_estimates = calculate_average_daily_inflow()
        
        # Derive target flowrates
        target_flowrates = [inflow * 1.1 for inflow in inflow_estimates]
        
        # Create and run simulator
        simulator = Simulator(
            starting_water_level=water_level,
            energy_prices=electricity_prices,
            water_inflows=inflow_estimates,
            target_flowrates=target_flowrates
        )
        
        # Run simulation
        total_cost = simulator.simulate()
        
        # Generate simulation ID and name
        simulation_id = str(uuid4())
        simulation_timestamp = datetime.utcnow()
        simulation_name = simulation_timestamp.isoformat()
        
        # Convert to response
        response = convert_simulator_to_response(
            simulator=simulator,
            rain_forecast=rain_forecast,
            electricity_prices=electricity_prices,
            inflow_estimates=inflow_estimates,
            starting_water_level=water_level,
            simulation_id=simulation_id,
            simulation_name=simulation_name,
            simulation_timestamp=simulation_timestamp
        )
        
        # Sync to OPC UA
        await bridge.sync_simulation_results(response.dict())
        
        return response
        
    except Exception as e:
        logger.error(f"Error in simulation: {e}", exc_info=True)
        raise


@app.get("/api/opcua/sensors")
async def get_sensors():
    """Get current sensor data from OPC UA."""
    sensor_data = await bridge.get_sensor_data()
    return sensor_data


@app.get("/api/opcua/status")
async def get_opcua_status():
    """Get OPC UA bridge status."""
    return {
        "server_running": bridge.server is not None,
        "client_connected": bridge.client.is_connected() if bridge.client else False,
        "control_mode": bridge.config.control_mode,
    }


class PumpControlRequest(BaseModel):
    """Request model for pump control."""
    state: bool = Field(..., description="Desired state: True=ON, False=OFF")
    force: bool = Field(default=False, description="Bypass safety checks (use with caution)")


class MultiPumpControlRequest(BaseModel):
    """Request model for controlling multiple pumps."""
    pump_commands: Dict[str, bool] = Field(..., description="Dict mapping pump_id to desired state")
    force: bool = Field(default=False, description="Bypass safety checks")


@app.post("/api/opcua/pumps/{pump_id}/control")
async def control_pump(pump_id: str, request: PumpControlRequest):
    """
    Control a single pump (turn ON or OFF).
    
    Args:
        pump_id: Pump identifier (e.g., "1.1", "2.3")
        request: PumpControlRequest with state and optional force flag
        
    Returns:
        Result dict with success status and message
        
    Example:
        POST /api/opcua/pumps/1.1/control
        {
            "state": true,
            "force": false
        }
    """
    result = await bridge.control_pump(pump_id, request.state, request.force)
    return result


@app.post("/api/opcua/pumps/control")
async def control_pumps(request: MultiPumpControlRequest):
    """
    Control multiple pumps at once.
    
    Args:
        request: MultiPumpControlRequest with pump_commands dict and optional force flag
            
    Returns:
        Dict with results for each pump and summary
        
    Example:
        POST /api/opcua/pumps/control
        {
            "pump_commands": {
                "1.1": true,
                "1.2": false,
                "2.1": true
            },
            "force": false
        }
    """
    result = await bridge.control_pumps(request.pump_commands, request.force)
    return result


@app.get("/api/opcua/pumps/{pump_id}/state")
async def get_pump_state(pump_id: str):
    """Get current state of a pump."""
    sensor_data = await bridge.get_sensor_data()
    pump_states = sensor_data.get("pump_states", {})
    state = pump_states.get(pump_id, None)
    
    return {
        "pump_id": pump_id,
        "state": state,
        "status": "ON" if state else "OFF" if state is False else "Unknown"
    }


@app.get("/api/opcua/pumps/states")
async def get_all_pump_states():
    """Get current states of all pumps."""
    sensor_data = await bridge.get_sensor_data()
    pump_states = sensor_data.get("pump_states", {})
    
    return {
        "pump_states": pump_states,
        "pump_count": len(pump_states),
        "pumps_on": sum(1 for state in pump_states.values() if state),
        "pumps_off": sum(1 for state in pump_states.values() if not state)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

