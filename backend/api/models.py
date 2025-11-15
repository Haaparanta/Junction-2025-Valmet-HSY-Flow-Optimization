"""Pydantic models for FastAPI DTOs."""
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class PumpPerformanceCurve(BaseModel):
    """Pump performance curve data."""
    head_values: List[float] = Field(..., description="Head values in meters")
    flow_values: List[float] = Field(..., description="Flow values in m³/s")


class PumpData(BaseModel):
    """Per-pump 24h data."""
    pump_name: str = Field(..., description="Pump identifier (e.g., '1.1', '2.3')")
    performance_curve: PumpPerformanceCurve = Field(..., description="Pump performance curve")
    values_24h: List[float] = Field(..., description="24h flow values in m³/h (96 values)")


class SimulationRequest(BaseModel):
    """Optional input for POST /simulate (if None, fetch automatically)."""
    name: Optional[str] = Field(None, description="Optional simulation name (if not provided, timestamp will be used)")
    rain_forecast: Optional[List[float]] = Field(None, description="24h rain forecast in mm (96 values)")
    electricity_prices: Optional[List[float]] = Field(None, description="24h electricity prices in EUR/kWh (96 values)")
    inflow_estimates: Optional[List[float]] = Field(None, description="24h inflow estimates in m³/15min (96 values)")
    starting_water_level: Optional[float] = Field(None, description="Starting water level in meters")
    target_flowrates: Optional[List[float]] = Field(None, description="24h target flowrates in m³/15min (96 values)")


class SimulationResponse(BaseModel):
    """Complete simulation result."""
    id: str = Field(..., description="Simulation UUID")
    timestamp: datetime = Field(..., description="Simulation timestamp")
    timestamps_24h: List[str] = Field(..., description="24h timestamps in ISO format, one every 15 minutes (96 values)")
    rain_forecast_24h: List[float] = Field(..., description="24h rain forecast in mm (96 values)")
    electricity_price_24h: List[float] = Field(..., description="24h electricity prices in EUR/kWh (96 values)")
    inflow_estimate_24h: List[float] = Field(..., description="24h inflow estimates in m³/15min (96 values)")
    pumping_strategy_24h: List[Dict[str, bool]] = Field(..., description="24h pumping strategy - list of 96 dicts with pump_id -> on/off")
    water_level_estimate_24h: List[float] = Field(..., description="24h simulated water level estimates in meters (96 values)")
    electricity_consumption_24h: List[float] = Field(..., description="24h simulated electricity consumption in kWh (96 values)")
    cost_24h: List[float] = Field(..., description="24h simulated costs in EUR (96 values)")
    pumps: List[PumpData] = Field(..., description="8 pumps with their 24h data")
    total_cost: float = Field(..., description="Total simulation cost in EUR")
    starting_water_level: float = Field(..., description="Starting water level in meters")


class SimulationMetadata(BaseModel):
    """Simulation metadata for listing."""
    id: str = Field(..., description="Simulation UUID")
    name: str = Field(..., description="Simulation name")
    timestamp: str = Field(..., description="Simulation timestamp")


class SingleDataResponse(BaseModel):
    """Response for single data type endpoints."""
    name: str = Field(..., description="Simulation name")
    data: List[float] = Field(..., description="Data values")


class PumpingStrategyResponse(BaseModel):
    """Response for pumping strategy endpoint."""
    name: str = Field(..., description="Simulation name")
    data: List[Dict[str, bool]] = Field(..., description="Pumping strategy data")


class PumpsResponse(BaseModel):
    """Response for pumps endpoint."""
    name: str = Field(..., description="Simulation name")
    pumps: List[PumpData] = Field(..., description="Pump data")


class TotalCostResponse(BaseModel):
    """Response for total cost endpoint."""
    name: str = Field(..., description="Simulation name")
    total_cost: float = Field(..., description="Total cost")

