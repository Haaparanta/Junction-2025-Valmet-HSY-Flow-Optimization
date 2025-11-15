"""Control loop for managing pump operations with safety interlocks."""
import asyncio
import logging
from typing import Dict, Optional, Callable
from datetime import datetime, timedelta

from .opcua_server import OPCUAServer
from .opcua_client import OPCUAClient
from .config import OPCUAConfig

logger = logging.getLogger(__name__)


class ControlLoop:
    """
    Control loop that manages bidirectional communication between optimization
    system and physical equipment with safety interlocks.
    """
    
    def __init__(
        self,
        server: OPCUAServer,
        client: OPCUAClient,
        config: OPCUAConfig,
        optimization_callback: Optional[Callable] = None
    ):
        """
        Initialize control loop.
        
        Args:
            server: OPC UA server instance
            client: OPC UA client instance
            config: Configuration
            optimization_callback: Function to call when optimization should be triggered
                                  Signature: async def callback(water_level: float, pump_states: Dict[str, bool]) -> Dict
        """
        self.server = server
        self.client = client
        self.config = config
        self.optimization_callback = optimization_callback
        
        # State tracking
        self.current_water_level: Optional[float] = None
        self.current_pump_states: Dict[str, bool] = {}
        self.pump_runtime_tracking: Dict[str, datetime] = {}  # When pump was turned on
        self.last_optimization_time: Optional[datetime] = None
        
        # Safety override flags
        self.safety_override_active = False
        
        # Running flag
        self.running = False
    
    async def start(self):
        """Start the control loop."""
        self.running = True
        
        # Connect client if PLC endpoint configured
        if self.config.plc_endpoint:
            try:
                await self.client.connect()
            except Exception as e:
                logger.error(f"Failed to connect to PLC: {e}")
                logger.warning("Continuing in simulation-only mode")
        
        # Set up subscriptions
        if self.client.is_connected():
            await self.client.subscribe_to_water_level(self._on_water_level_change)
            await self.client.subscribe_to_pump_states(self._on_pump_state_change)
        
        # Start main control loop
        logger.info("Control loop started")
        await self._main_loop()
    
    async def stop(self):
        """Stop the control loop."""
        self.running = False
        if self.client.is_connected():
            await self.client.disconnect()
        logger.info("Control loop stopped")
    
    async def _main_loop(self):
        """Main control loop."""
        while self.running:
            try:
                # Read current sensor values
                await self._read_sensors()
                
                # Check safety conditions
                await self._check_safety_interlocks()
                
                # Trigger optimization if needed
                await self._check_optimization_trigger()
                
                # Execute control actions
                await self._execute_control()
                
                # Wait before next iteration
                await asyncio.sleep(self.config.sensor_update_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in control loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _read_sensors(self):
        """Read sensor values from PLC."""
        if not self.client.is_connected():
            return
        
        # Read water level
        water_level = await self.client.read_water_level()
        if water_level is not None:
            self.current_water_level = water_level
            await self.server.update_water_level(water_level)
        
        # Read pump states
        pump_states = await self.client.read_all_pump_states()
        if pump_states:
            self.current_pump_states = pump_states
            for pump_id, state in pump_states.items():
                await self.server.update_pump_state(pump_id, state)
    
    async def _check_safety_interlocks(self):
        """Check safety conditions and activate overrides if needed."""
        if self.current_water_level is None:
            return
        
        # Safety check: Water level exceeds maximum
        if self.current_water_level >= self.config.max_water_level:
            if not self.safety_override_active:
                logger.warning(
                    f"SAFETY OVERRIDE: Water level {self.current_water_level:.2f} m "
                    f"exceeds maximum {self.config.max_water_level} m"
                )
                self.safety_override_active = True
                await self.server.update_optimization_status("SAFETY_OVERRIDE")
            
            # Force all pumps ON
            if self.config.control_mode == "closed_loop":
                for pump_id in self.current_pump_states.keys():
                    if not self.current_pump_states.get(pump_id, False):
                        await self.client.write_pump_command(pump_id, True)
                        logger.warning(f"SAFETY: Forced pump {pump_id} ON")
        else:
            if self.safety_override_active:
                logger.info("Safety override cleared")
                self.safety_override_active = False
                await self.server.update_optimization_status("Normal")
    
    async def _check_optimization_trigger(self):
        """Check if optimization should be triggered."""
        if not self.optimization_callback:
            return
        
        # Check if enough time has passed since last optimization
        now = datetime.now()
        if self.last_optimization_time:
            elapsed = (now - self.last_optimization_time).total_seconds() / 60
            if elapsed < self.config.optimization_trigger_interval_minutes:
                return
        
        # Trigger optimization
        try:
            logger.info("Triggering optimization...")
            await self.server.update_optimization_status("Running")
            
            # Call optimization callback
            result = await self.optimization_callback(
                self.current_water_level or 5.0,
                self.current_pump_states.copy()
            )
            
            # Update server with results
            if result:
                await self._update_optimization_results(result)
            
            self.last_optimization_time = now
            await self.server.update_optimization_status("Idle")
            
        except Exception as e:
            logger.error(f"Error in optimization callback: {e}", exc_info=True)
            await self.server.update_optimization_status("Error")
    
    async def _update_optimization_results(self, result: Dict):
        """Update OPC UA server with optimization results."""
        try:
            # Extract data from result (assuming it matches SimulationResponse format)
            strategy = result.get("pumping_strategy_24h", [])
            total_cost = result.get("total_cost", 0.0)
            timestamp = result.get("timestamp")
            
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            
            # Convert strategy to pump-wise format
            pump_strategy: Dict[str, List[bool]] = {}
            for pump_id in self.current_pump_states.keys():
                pump_strategy[pump_id] = [
                    step.get(pump_id, False) for step in strategy
                ]
            
            # Update optimization results
            await self.server.update_optimization_results(
                pump_strategy,
                total_cost,
                timestamp
            )
            
            # Update recommended states for next time step
            if strategy and len(strategy) > 0:
                next_step = strategy[0]  # First time step (next 15 minutes)
                for pump_id, recommended in next_step.items():
                    await self.server.update_pump_recommendation(pump_id, recommended)
            
        except Exception as e:
            logger.error(f"Error updating optimization results: {e}", exc_info=True)
    
    async def _execute_control(self):
        """Execute control actions based on optimization results."""
        if self.config.control_mode != "closed_loop":
            return  # Advisory mode - don't write commands
        
        if self.safety_override_active:
            return  # Safety override is handling control
        
        # Read recommended states from server
        for pump_id in self.current_pump_states.keys():
            try:
                # Read recommended state from server
                recommended_node_name = f"Pump_{pump_id.replace('.', '_')}_RecommendedState"
                if recommended_node_name in self.server.nodes:
                    recommended = await self.server.nodes[recommended_node_name].read_value()
                else:
                    continue
                
                current = self.current_pump_states.get(pump_id, False)
                
                # Check minimum runtime before allowing shutdown
                if current and not recommended:
                    if pump_id in self.pump_runtime_tracking:
                        runtime_start = self.pump_runtime_tracking[pump_id]
                        runtime_minutes = (datetime.now() - runtime_start).total_seconds() / 60
                        
                        if runtime_minutes < self.config.min_pump_runtime_minutes:
                            logger.debug(
                                f"Pump {pump_id} cannot be turned off yet "
                                f"(runtime: {runtime_minutes:.1f} min < {self.config.min_pump_runtime_minutes} min)"
                            )
                            continue
                
                # Execute command if state differs
                if current != recommended:
                    success = await self.client.write_pump_command(pump_id, recommended)
                    if success:
                        # Track runtime
                        if recommended:
                            self.pump_runtime_tracking[pump_id] = datetime.now()
                        else:
                            self.pump_runtime_tracking.pop(pump_id, None)
                        
                        logger.info(
                            f"Control: Pump {pump_id} {'ON' if recommended else 'OFF'}"
                        )
                
            except Exception as e:
                logger.error(f"Error executing control for pump {pump_id}: {e}", exc_info=True)
    
    async def _on_water_level_change(self, node, value, data):
        """Callback for water level changes."""
        try:
            level = float(value)
            self.current_water_level = level
            await self.server.update_water_level(level)
            logger.debug(f"Water level changed: {level} m")
        except Exception as e:
            logger.error(f"Error handling water level change: {e}", exc_info=True)
    
    async def _on_pump_state_change(self, node, value, data):
        """Callback for pump state changes."""
        try:
            # Extract pump ID from node
            node_id = str(node.nodeid)
            # This is a simplified version - in production, parse node_id properly
            logger.debug(f"Pump state changed: {node_id} = {bool(value)}")
            
            # Update local state
            # Note: In production, maintain a mapping from node IDs to pump IDs
        except Exception as e:
            logger.error(f"Error handling pump state change: {e}", exc_info=True)

