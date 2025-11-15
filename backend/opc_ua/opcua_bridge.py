"""Bridge between FastAPI backend and OPC UA system."""
import asyncio
import logging
from typing import Dict, Optional, List
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .opcua_server import OPCUAServer
from .opcua_client import OPCUAClient
from .control_loop import ControlLoop
from .config import OPCUAConfig

logger = logging.getLogger(__name__)


class OPCUABridge:
    """
    Bridge that connects FastAPI backend with OPC UA server/client.
    
    This class provides methods to:
    - Sync simulation results to OPC UA server
    - Read sensor data from OPC UA client for simulations
    - Manage the control loop
    """
    
    def __init__(self, config: Optional[OPCUAConfig] = None):
        """Initialize OPC UA bridge."""
        self.config = config or OPCUAConfig.from_env()
        self.server: Optional[OPCUAServer] = None
        self.client: Optional[OPCUAClient] = None
        self.control_loop: Optional[ControlLoop] = None
        self.server_task: Optional[asyncio.Task] = None
        self.control_loop_task: Optional[asyncio.Task] = None
    
    async def initialize(self, optimization_callback=None):
        """
        Initialize OPC UA server, client, and control loop.
        
        Args:
            optimization_callback: Optional callback function for triggering optimizations
        """
        try:
            # Create server
            self.server = OPCUAServer(self.config)
            
            # Create client
            self.client = OPCUAClient(self.config)
            
            # Create control loop
            self.control_loop = ControlLoop(
                self.server,
                self.client,
                self.config,
                optimization_callback
            )
            
            logger.info("OPC UA bridge initialized")
            
        except Exception as e:
            logger.error(f"Error initializing OPC UA bridge: {e}", exc_info=True)
            raise
    
    async def start_server(self):
        """Start OPC UA server in background task."""
        if not self.server:
            await self.initialize()
        
        if self.server_task is None or self.server_task.done():
            self.server_task = asyncio.create_task(self.server.start())
            logger.info("OPC UA server task started")
    
    async def start_control_loop(self):
        """Start control loop in background task."""
        if not self.control_loop:
            await self.initialize()
        
        if self.control_loop_task is None or self.control_loop_task.done():
            self.control_loop_task = asyncio.create_task(self.control_loop.start())
            logger.info("Control loop task started")
    
    async def sync_simulation_results(self, simulation_response: Dict):
        """
        Sync simulation results to OPC UA server.
        
        Args:
            simulation_response: SimulationResponse dict from FastAPI
        """
        if not self.server:
            logger.warning("OPC UA server not initialized")
            return
        
        try:
            # Extract data
            strategy = simulation_response.get("pumping_strategy_24h", [])
            total_cost = simulation_response.get("total_cost", 0.0)
            timestamp_str = simulation_response.get("timestamp")
            
            # Parse timestamp
            from datetime import datetime
            if timestamp_str:
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                else:
                    timestamp = timestamp_str
            else:
                timestamp = datetime.now()
            
            # Convert strategy to pump-wise format
            pump_ids = ["1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4"]
            pump_strategy: Dict[str, List[bool]] = {}
            for pump_id in pump_ids:
                pump_strategy[pump_id] = [
                    step.get(pump_id, False) for step in strategy
                ]
            
            # Update server
            await self.server.update_optimization_results(
                pump_strategy,
                total_cost,
                timestamp
            )
            
            # Update recommended states for immediate next step
            if strategy and len(strategy) > 0:
                next_step = strategy[0]
                for pump_id, recommended in next_step.items():
                    await self.server.update_pump_recommendation(pump_id, recommended)
            
            logger.info("Simulation results synced to OPC UA server")
            
        except Exception as e:
            logger.error(f"Error syncing simulation results: {e}", exc_info=True)
    
    async def get_sensor_data(self) -> Dict:
        """
        Read sensor data from OPC UA client for use in simulations.
        
        Returns:
            Dict with sensor data:
            {
                "water_level": float,
                "pump_states": Dict[str, bool],
                "pump_flows": Dict[str, float]
            }
        """
        if not self.client:
            logger.warning("OPC UA client not initialized")
            return {
                "water_level": None,
                "pump_states": {},
                "pump_flows": {}
            }
        
        try:
            data = {}
            
            # Read water level
            water_level = await self.client.read_water_level()
            data["water_level"] = water_level
            
            # Read pump states
            pump_states = await self.client.read_all_pump_states()
            data["pump_states"] = pump_states
            
            # Read pump flows
            pump_flows = {}
            for pump_id in pump_states.keys():
                flow = await self.client.read_pump_flow(pump_id)
                if flow is not None:
                    pump_flows[pump_id] = flow
            data["pump_flows"] = pump_flows
            
            return data
            
        except Exception as e:
            logger.error(f"Error reading sensor data: {e}", exc_info=True)
            return {
                "water_level": None,
                "pump_states": {},
                "pump_flows": {}
            }
    
    async def control_pump(self, pump_id: str, state: bool, force: bool = False) -> Dict:
        """
        Control a single pump (turn ON or OFF).
        
        Args:
            pump_id: Pump identifier (e.g., "1.1", "2.3")
            state: Desired state (True=ON, False=OFF)
            force: If True, bypass safety checks (use with caution)
            
        Returns:
            Dict with result:
            {
                "success": bool,
                "pump_id": str,
                "state": bool,
                "message": str
            }
        """
        if not self.client:
            return {
                "success": False,
                "pump_id": pump_id,
                "state": state,
                "message": "OPC UA client not initialized"
            }
        
        if not self.client.is_connected():
            return {
                "success": False,
                "pump_id": pump_id,
                "state": state,
                "message": "Not connected to PLC/SCADA"
            }
        
        try:
            # Safety checks (unless forced)
            if not force:
                # Check if turning OFF - verify minimum runtime
                if not state:  # Turning OFF
                    current_states = await self.client.read_all_pump_states()
                    if current_states.get(pump_id, False):  # Currently ON
                        # Check runtime in control loop if available
                        if self.control_loop and pump_id in self.control_loop.pump_runtime_tracking:
                            from datetime import datetime
                            runtime_start = self.control_loop.pump_runtime_tracking[pump_id]
                            runtime_minutes = (datetime.now() - runtime_start).total_seconds() / 60
                            
                            if runtime_minutes < self.config.min_pump_runtime_minutes:
                                return {
                                    "success": False,
                                    "pump_id": pump_id,
                                    "state": state,
                                    "message": f"Pump cannot be turned off yet. Runtime: {runtime_minutes:.1f} min < {self.config.min_pump_runtime_minutes} min"
                                }
            
            # Write command to PLC
            success = await self.client.write_pump_command(pump_id, state)
            
            if success:
                # Update server state
                if self.server:
                    await self.server.update_pump_state(pump_id, state)
                
                # Track runtime if turning ON
                if state and self.control_loop:
                    from datetime import datetime
                    self.control_loop.pump_runtime_tracking[pump_id] = datetime.now()
                elif not state and self.control_loop:
                    # Remove from tracking if turning OFF
                    self.control_loop.pump_runtime_tracking.pop(pump_id, None)
                
                logger.info(f"Pump {pump_id} command executed: {'ON' if state else 'OFF'}")
                return {
                    "success": True,
                    "pump_id": pump_id,
                    "state": state,
                    "message": f"Pump {pump_id} turned {'ON' if state else 'OFF'}"
                }
            else:
                return {
                    "success": False,
                    "pump_id": pump_id,
                    "state": state,
                    "message": "Failed to write command to PLC"
                }
                
        except Exception as e:
            logger.error(f"Error controlling pump {pump_id}: {e}", exc_info=True)
            return {
                "success": False,
                "pump_id": pump_id,
                "state": state,
                "message": f"Error: {str(e)}"
            }
    
    async def control_pumps(self, pump_commands: Dict[str, bool], force: bool = False) -> Dict:
        """
        Control multiple pumps at once.
        
        Args:
            pump_commands: Dict mapping pump_id to desired state
                Example: {"1.1": True, "1.2": False, "2.1": True}
            force: If True, bypass safety checks
            
        Returns:
            Dict with results for each pump:
            {
                "results": [
                    {"pump_id": str, "success": bool, "state": bool, "message": str},
                    ...
                ],
                "summary": {"total": int, "successful": int, "failed": int}
            }
        """
        results = []
        for pump_id, state in pump_commands.items():
            result = await self.control_pump(pump_id, state, force)
            results.append(result)
        
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        return {
            "results": results,
            "summary": {
                "total": len(results),
                "successful": successful,
                "failed": failed
            }
        }
    
    async def stop(self):
        """Stop OPC UA bridge and all components."""
        try:
            # Stop control loop
            if self.control_loop:
                await self.control_loop.stop()
            
            # Cancel tasks
            if self.server_task and not self.server_task.done():
                self.server_task.cancel()
                try:
                    await self.server_task
                except asyncio.CancelledError:
                    pass
            
            if self.control_loop_task and not self.control_loop_task.done():
                self.control_loop_task.cancel()
                try:
                    await self.control_loop_task
                except asyncio.CancelledError:
                    pass
            
            # Stop server
            if self.server:
                await self.server.stop()
            
            # Disconnect client
            if self.client:
                await self.client.disconnect()
            
            logger.info("OPC UA bridge stopped")
            
        except Exception as e:
            logger.error(f"Error stopping OPC UA bridge: {e}", exc_info=True)

