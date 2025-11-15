"""In-memory storage for simulation history."""
from typing import List, Optional
from datetime import datetime
from .models import SimulationResponse


# In-memory storage for simulations
_simulations: List[SimulationResponse] = []


def save_simulation(simulation: SimulationResponse) -> None:
    """
    Save a simulation to history.
    
    Args:
        simulation: SimulationResponse to save
    """
    _simulations.append(simulation)


def get_latest() -> Optional[SimulationResponse]:
    """
    Get the latest simulation.
    
    Returns:
        Latest SimulationResponse or None if no simulations exist
    """
    if not _simulations:
        return None
    return _simulations[-1]


def get_all() -> List[SimulationResponse]:
    """
    Get all simulations in history.
    
    Returns:
        List of all SimulationResponse objects
    """
    return _simulations.copy()


def get_by_id(simulation_id: str) -> Optional[SimulationResponse]:
    """
    Get a simulation by ID.
    
    Args:
        simulation_id: UUID of the simulation
        
    Returns:
        SimulationResponse with matching ID or None if not found
    """
    for sim in _simulations:
        if sim.id == simulation_id:
            return sim
    return None

