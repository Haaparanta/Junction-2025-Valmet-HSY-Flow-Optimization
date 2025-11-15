"""FastAPI application for simulation management."""
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    SimulationRequest, SimulationResponse, PumpData, PumpPerformanceCurve,
    SimulationMetadata, SingleDataResponse, PumpingStrategyResponse,
    PumpsResponse, TotalCostResponse
)
from .storage import save_simulation, get_latest, get_all
from .database import (
    list_simulations, get_simulation_by_id, get_simulation_name_by_id,
    get_rain_forecast, get_electricity_prices, get_inflow_estimates,
    get_water_levels, get_pumping_strategy, get_electricity_consumption,
    get_costs, get_pumps, get_total_cost
)
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
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create API router with /api prefix
api_router = APIRouter(prefix="/api")


def convert_simulator_to_response(
    simulator: Simulator,
    rain_forecast: List[float],
    electricity_prices: List[float],
    inflow_estimates: List[float],
    starting_water_level: float,
    simulation_id: str,
    simulation_name: str,
    simulation_timestamp: datetime
) -> SimulationResponse:
    """
    Convert Simulator instance to SimulationResponse DTO.
    
    Args:
        simulator: Simulator instance with completed simulation
        rain_forecast: 24h rain forecast (96 values)
        electricity_prices: 24h electricity prices (96 values)
        inflow_estimates: 24h inflow estimates (96 values)
        starting_water_level: Starting water level
        simulation_id: Simulation UUID
        simulation_name: Simulation name
        simulation_timestamp: Simulation timestamp
        
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
    
    # Generate timestamps: 96 timestamps, one every 15 minutes starting from simulation timestamp
    timestamps_24h = [
        (simulation_timestamp + timedelta(minutes=i * 15)).isoformat() + "Z"
        for i in range(96)
    ]
    
    # Create response
    response = SimulationResponse(
        id=simulation_id,
        name=simulation_name,
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


@api_router.get("/")
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


@api_router.get("/all")
async def get_all_simulations() -> List[SimulationResponse]:
    """
    Get all simulations in history.
    
    Returns:
        List of all SimulationResponse objects
    """
    return get_all()


@api_router.post("/simulate", response_model=SimulationResponse)
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
        
        # Derive target flowrates from inflow if not provided or invalid
        if request is None or request.target_flowrates is None:
            # Use inflow * 1.1 as buffer
            target_flowrates = [inflow * 1.1 for inflow in inflow_estimates]
        elif len(request.target_flowrates) != 96:
            # If provided but wrong length, derive from inflow instead of erroring
            target_flowrates = [inflow * 1.1 for inflow in inflow_estimates]
        else:
            target_flowrates = request.target_flowrates
        
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
        
        # Generate name from timestamp if not provided
        if request is not None and request.name is not None:
            simulation_name = request.name
        else:
            simulation_name = simulation_timestamp.isoformat()
        
        # Convert to response
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
        
        # Save to history (both in-memory and database)
        save_simulation(response, simulation_name)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Simulation failed: {str(e)}"
        )


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@api_router.get("/simulations", response_model=List[SimulationMetadata])
async def list_all_simulations() -> List[SimulationMetadata]:
    """
    List all simulations with metadata (id, name, timestamp, summary values).
    
    Returns:
        List of SimulationMetadata objects with summary values
    """
    simulations = list_simulations()
    return [
        SimulationMetadata(
            id=sim["id"],
            name=sim["name"],
            timestamp=sim["timestamp"],
            total_cost=sim["total_cost"],
            starting_water_level=sim["starting_water_level"],
            average_water_level=sim["average_water_level"],
            total_electricity_consumption=sim["total_electricity_consumption"]
        )
        for sim in simulations
    ]


@api_router.get("/simulations/{simulation_id}", response_model=SimulationResponse)
async def get_simulation_by_id_endpoint(simulation_id: str) -> SimulationResponse:
    """
    Get full simulation by UUID.
    
    Args:
        simulation_id: Simulation UUID
        
    Returns:
        SimulationResponse
        
    Raises:
        404: If simulation not found
    """
    simulation = get_simulation_by_id(simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    return simulation


@api_router.get("/simulations/{simulation_id}/rain_forecast", response_model=SingleDataResponse)
async def get_rain_forecast_endpoint(simulation_id: str) -> SingleDataResponse:
    """Get only rain forecast for a simulation by UUID."""
    name = get_simulation_name_by_id(simulation_id)
    if name is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    data = get_rain_forecast(simulation_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    return SingleDataResponse(id=simulation_id, name=name, data=data)


@api_router.get("/simulations/{simulation_id}/electricity_prices", response_model=SingleDataResponse)
async def get_electricity_prices_endpoint(simulation_id: str) -> SingleDataResponse:
    """Get only electricity prices for a simulation by UUID."""
    name = get_simulation_name_by_id(simulation_id)
    if name is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    data = get_electricity_prices(simulation_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    return SingleDataResponse(id=simulation_id, name=name, data=data)


@api_router.get("/simulations/{simulation_id}/inflow_estimates", response_model=SingleDataResponse)
async def get_inflow_estimates_endpoint(simulation_id: str) -> SingleDataResponse:
    """Get only inflow estimates for a simulation by UUID."""
    name = get_simulation_name_by_id(simulation_id)
    if name is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    data = get_inflow_estimates(simulation_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    return SingleDataResponse(id=simulation_id, name=name, data=data)


@api_router.get("/simulations/{simulation_id}/water_levels", response_model=SingleDataResponse)
async def get_water_levels_endpoint(simulation_id: str) -> SingleDataResponse:
    """Get only water levels for a simulation by UUID."""
    name = get_simulation_name_by_id(simulation_id)
    if name is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    data = get_water_levels(simulation_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    return SingleDataResponse(id=simulation_id, name=name, data=data)


@api_router.get("/simulations/{simulation_id}/pumping_strategy", response_model=PumpingStrategyResponse)
async def get_pumping_strategy_endpoint(simulation_id: str) -> PumpingStrategyResponse:
    """Get only pumping strategy for a simulation by UUID."""
    name = get_simulation_name_by_id(simulation_id)
    if name is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    data = get_pumping_strategy(simulation_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    return PumpingStrategyResponse(id=simulation_id, name=name, data=data)


@api_router.get("/simulations/{simulation_id}/electricity_consumption", response_model=SingleDataResponse)
async def get_electricity_consumption_endpoint(simulation_id: str) -> SingleDataResponse:
    """Get only electricity consumption for a simulation by UUID."""
    name = get_simulation_name_by_id(simulation_id)
    if name is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    data = get_electricity_consumption(simulation_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    return SingleDataResponse(id=simulation_id, name=name, data=data)


@api_router.get("/simulations/{simulation_id}/costs", response_model=SingleDataResponse)
async def get_costs_endpoint(simulation_id: str) -> SingleDataResponse:
    """Get only costs for a simulation by UUID."""
    name = get_simulation_name_by_id(simulation_id)
    if name is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    data = get_costs(simulation_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    return SingleDataResponse(id=simulation_id, name=name, data=data)


@api_router.get("/simulations/{simulation_id}/pumps", response_model=PumpsResponse)
async def get_pumps_endpoint(simulation_id: str) -> PumpsResponse:
    """Get only pump data for a simulation by UUID."""
    name = get_simulation_name_by_id(simulation_id)
    if name is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    pumps = get_pumps(simulation_id)
    if pumps is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    return PumpsResponse(id=simulation_id, name=name, pumps=pumps)


@api_router.get("/simulations/{simulation_id}/total_cost", response_model=TotalCostResponse)
async def get_total_cost_endpoint(simulation_id: str) -> TotalCostResponse:
    """Get only total cost for a simulation by UUID."""
    name = get_simulation_name_by_id(simulation_id)
    if name is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    total_cost = get_total_cost(simulation_id)
    if total_cost is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{simulation_id}' not found")
    return TotalCostResponse(id=simulation_id, name=name, total_cost=total_cost)


# Include the API router in the app
app.include_router(api_router)

