"""In-memory storage for simulation history."""
from typing import List, Optional
from datetime import datetime
from .models import SimulationResponse
from .database import save_simulation_to_db


# In-memory storage for simulations
_simulations: List[SimulationResponse] = []


def save_simulation(simulation: SimulationResponse, name: Optional[str] = None) -> None:
    """
    Save a simulation to history (both in-memory and database).
    
    Args:
        simulation: SimulationResponse to save
        name: Optional simulation name (if None, timestamp will be used)
    """
    # Save to in-memory storage (backward compatibility)
    _simulations.append(simulation)
    
    # Generate name from timestamp if not provided
    if name is None:
        name = simulation.timestamp.isoformat()
    
    # Save to database
    try:
        save_simulation_to_db(simulation, name)
    except Exception:
        # If database save fails, continue (backward compatibility)
        # In-memory storage still works
        pass


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

