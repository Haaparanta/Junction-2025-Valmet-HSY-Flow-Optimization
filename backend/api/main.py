"""FastAPI application for simulation management."""
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import SimulationRequest, SimulationResponse, PumpData, PumpPerformanceCurve
from .storage import save_simulation, get_latest, get_all
from .data_fetcher import (
    fetch_rain_forecast_24h,
    fetch_electricity_prices_24h,
    calculate_average_daily_inflow,
    get_starting_water_level
)

# Add parent directory to path to import simulation modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from simulation.simulator import Simulator

app = FastAPI(
    title="Simulation API",
    description="API for managing wastewater tunnel system simulations",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


def convert_simulator_to_response(
    simulator: Simulator,
    rain_forecast: List[float],
    electricity_prices: List[float],
    inflow_estimates: List[float],
    starting_water_level: float
) -> SimulationResponse:
    """
    Convert Simulator instance to SimulationResponse DTO.
    
    Args:
        simulator: Simulator instance with completed simulation
        rain_forecast: 24h rain forecast (96 values)
        electricity_prices: 24h electricity prices (96 values)
        inflow_estimates: 24h inflow estimates (96 values)
        starting_water_level: Starting water level
        
    Returns:
        SimulationResponse DTO
    """
    data = simulator.time_series_data
    
    # Create pumping strategy: list of dicts with pump states
    pumping_strategy_24h = []
    pump_ids = sorted(simulator.pumps.keys())
    
    for i in range(96):
        pump_state_dict = {}
        for pump_id in pump_ids:
            pump_state_dict[pump_id] = bool(data['pump_states'][pump_id][i])
        pumping_strategy_24h.append(pump_state_dict)
    
    # Calculate electricity consumption per time step
    electricity_consumption_24h = []
    for i in range(96):
        # Get pumps that were on at this time step
        pumps_on = [
            pump_id for pump_id in pump_ids
            if data['pump_states'][pump_id][i]
        ]
        # Calculate total power consumption
        total_power_kw = sum(
            simulator.pumps[pump_id].get_power()
            for pump_id in pumps_on
        )
        # Convert to energy: power (kW) * time (hours)
        # 15 minutes = 0.25 hours
        energy_kwh = total_power_kw * 0.25
        electricity_consumption_24h.append(energy_kwh)
    
    # Create pump data list
    pumps_data = []
    for pump_id in pump_ids:
        pump = simulator.pumps[pump_id]
        
        # Extract performance curve
        performance_curve = PumpPerformanceCurve(
            head_values=list(pump.head_array),
            flow_values=list(pump.flow_array)
        )
        
        # Get 24h flow values (already in m³/h from simulator)
        flow_values_24h = data['pump_flows'][pump_id]
        
        pump_data = PumpData(
            pump_name=pump_id,
            performance_curve=performance_curve,
            values_24h=flow_values_24h
        )
        pumps_data.append(pump_data)
    
    # Generate timestamps: 96 timestamps, one every 15 minutes starting from now
    simulation_timestamp = datetime.utcnow()
    timestamps_24h = [
        (simulation_timestamp + timedelta(minutes=i * 15)).isoformat() + "Z"
        for i in range(96)
    ]
    
    # Create response
    response = SimulationResponse(
        id=str(uuid4()),
        timestamp=simulation_timestamp,
        timestamps_24h=timestamps_24h,
        rain_forecast_24h=rain_forecast,
        electricity_price_24h=electricity_prices,
        inflow_estimate_24h=inflow_estimates,
        pumping_strategy_24h=pumping_strategy_24h,
        water_level_estimate_24h=data['water_levels'],
        electricity_consumption_24h=electricity_consumption_24h,
        cost_24h=data['costs'],
        pumps=pumps_data,
        total_cost=simulator.total_cost,
        starting_water_level=starting_water_level
    )
    
    return response


@app.get("/")
async def get_latest_simulation() -> SimulationResponse:
    """
    Get the latest simulation.
    
    Returns:
        Latest SimulationResponse
        
    Raises:
        404: If no simulations exist
    """
    simulation = get_latest()
    if simulation is None:
        raise HTTPException(status_code=404, detail="No simulations found")
    return simulation


@app.get("/all")
async def get_all_simulations() -> List[SimulationResponse]:
    """
    Get all simulations in history.
    
    Returns:
        List of all SimulationResponse objects
    """
    return get_all()


@app.post("/simulate", response_model=SimulationResponse)
async def create_simulation(request: Optional[SimulationRequest] = None) -> SimulationResponse:
    """
    Create a new simulation with real-time data.
    
    If request is None or fields are missing, automatically fetches:
    - Rain forecast from FMI API
    - Electricity prices (from API or CSV average)
    - Average daily inflow pattern from CSV
    - Starting water level from CSV
    
    Args:
        request: Optional SimulationRequest with manual data
        
    Returns:
        SimulationResponse with simulation results
        
    Raises:
        400: If input validation fails
        500: If simulation fails
    """
    try:
        # Fetch or use provided data
        if request is None or request.rain_forecast is None or (request.rain_forecast is not None and len(request.rain_forecast) != 96):
            rain_forecast = fetch_rain_forecast_24h()
        else:
            rain_forecast = request.rain_forecast
        
        if request is None or request.electricity_prices is None or (request.electricity_prices is not None and len(request.electricity_prices) != 96):
            electricity_prices = fetch_electricity_prices_24h()
        else:
            electricity_prices = request.electricity_prices
        
        if request is None or request.inflow_estimates is None or (request.inflow_estimates is not None and len(request.inflow_estimates) != 96):
            inflow_estimates = calculate_average_daily_inflow()
        else:
            inflow_estimates = request.inflow_estimates
        
        if request is None or request.starting_water_level is None or request.starting_water_level == 0.0:
            starting_water_level = get_starting_water_level()
        else:
            starting_water_level = request.starting_water_level
        
        # Validate array lengths
        if len(rain_forecast) != 96:
            raise HTTPException(
                status_code=400,
                detail=f"rain_forecast must have 96 values, got {len(rain_forecast)}"
            )
        if len(electricity_prices) != 96:
            raise HTTPException(
                status_code=400,
                detail=f"electricity_prices must have 96 values, got {len(electricity_prices)}"
            )
        if len(inflow_estimates) != 96:
            raise HTTPException(
                status_code=400,
                detail=f"inflow_estimates must have 96 values, got {len(inflow_estimates)}"
            )
        
        # Derive target flowrates from inflow if not provided
        if request is None or request.target_flowrates is None:
            # Use inflow * 1.1 as buffer
            target_flowrates = [inflow * 1.1 for inflow in inflow_estimates]
        else:
            target_flowrates = request.target_flowrates
            if len(target_flowrates) != 96:
                raise HTTPException(
                    status_code=400,
                    detail=f"target_flowrates must have 96 values, got {len(target_flowrates)}"
                )
        
        # Create and run simulator
        simulator = Simulator(
            starting_water_level=starting_water_level,
            energy_prices=electricity_prices,
            water_inflows=inflow_estimates,
            target_flowrates=target_flowrates
        )
        
        # Run simulation
        total_cost = simulator.simulate()
        
        # Convert to response
        response = convert_simulator_to_response(
            simulator=simulator,
            rain_forecast=rain_forecast,
            electricity_prices=electricity_prices,
            inflow_estimates=inflow_estimates,
            starting_water_level=starting_water_level
        )
        
        # Save to history
        save_simulation(response)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Simulation failed: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

