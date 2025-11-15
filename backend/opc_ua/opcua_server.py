"""OPC UA server for exposing optimization results and receiving sensor data."""
import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime

try:
    from asyncua import Server, ua
    from asyncua.server import Server as AsyncUAServer
except ImportError:
    raise ImportError(
        "asyncua is required for OPC UA functionality. Install with: pip install asyncua"
    )

from .config import OPCUAConfig

logger = logging.getLogger(__name__)


class OPCUAServer:
    """
    OPC UA server that exposes optimization results and system state.
    
    Address Space Structure:
    Objects/
    ├── TunnelSystem
    │   ├── WaterLevel_L1 (Variable, Float, ReadOnly)
    │   ├── Volume (Variable, Float, ReadOnly)
    │   └── Inflow_F1 (Variable, Float, ReadOnly)
    ├── Pumps
    │   ├── Pump_1_1
    │   │   ├── State (Variable, Boolean, ReadWrite)
    │   │   ├── FlowRate (Variable, Float, ReadOnly)
    │   │   ├── Power (Variable, Float, ReadOnly)
    │   │   └── RecommendedState (Variable, Boolean, ReadOnly)
    │   └── ... (8 pumps)
    └── Optimization
        ├── Strategy (Variable, String, ReadOnly)
        ├── TotalCost (Variable, Float, ReadOnly)
        ├── Timestamp (Variable, DateTime, ReadOnly)
        └── Status (Variable, String, ReadOnly)
    """
    
    def __init__(self, config: OPCUAConfig):
        """Initialize OPC UA server."""
        self.config = config
        self.server: Optional[AsyncUAServer] = None
        self.namespace: Optional[ua.NodeId] = None
        
        # Node references
        self.nodes: Dict[str, ua.NodeId] = {}
        self.objects: Dict[str, ua.NodeId] = {}
        
        # Pump IDs
        self.pump_ids = ["1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4"]
        
    async def start(self):
        """Start the OPC UA server."""
        try:
            self.server = Server()
            await self.server.init()
            
            # Set server endpoint
            self.server.set_endpoint(self.config.server_endpoint)
            self.server.set_server_name(self.config.server_name)
            self.server.set_application_uri(self.config.server_uri)
            
            # Get or create namespace
            uri = self.config.server_uri
            idx = await self.server.register_namespace(uri)
            self.namespace = idx
            
            # Create address space
            await self._create_address_space()
            
            # Start server
            async with self.server:
                logger.info(f"OPC UA server started at {self.config.server_endpoint}")
                logger.info(f"Server URI: {self.config.server_uri}")
                logger.info(f"Namespace index: {self.namespace}")
                
                # Keep server running
                while True:
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Error starting OPC UA server: {e}", exc_info=True)
            raise
    
    async def _create_address_space(self):
        """Create the OPC UA address space structure."""
        objects = self.server.get_objects_node()
        
        # Create TunnelSystem object
        tunnel_obj = await objects.add_object(
            self.namespace, "TunnelSystem", "Tunnel System"
        )
        self.objects["TunnelSystem"] = tunnel_obj
        
        # Water level L1 (read-only, updated from sensors)
        water_level_node = await tunnel_obj.add_variable(
            self.namespace, "WaterLevel_L1", 0.0, varianttype=ua.VariantType.Float
        )
        await water_level_node.set_writable(False)
        self.nodes["WaterLevel_L1"] = water_level_node
        
        # Volume (read-only)
        volume_node = await tunnel_obj.add_variable(
            self.namespace, "Volume", 0.0, varianttype=ua.VariantType.Float
        )
        await volume_node.set_writable(False)
        self.nodes["Volume"] = volume_node
        
        # Inflow F1 (read-only)
        inflow_node = await tunnel_obj.add_variable(
            self.namespace, "Inflow_F1", 0.0, varianttype=ua.VariantType.Float
        )
        await inflow_node.set_writable(False)
        self.nodes["Inflow_F1"] = inflow_node
        
        # Create Pumps object
        pumps_obj = await objects.add_object(
            self.namespace, "Pumps", "Pumps"
        )
        self.objects["Pumps"] = pumps_obj
        
        # Create pump objects
        for pump_id in self.pump_ids:
            pump_obj = await pumps_obj.add_object(
                self.namespace, f"Pump_{pump_id.replace('.', '_')}", f"Pump {pump_id}"
            )
            
            # Pump state (read-write for control)
            state_node = await pump_obj.add_variable(
                self.namespace, "State", False, varianttype=ua.VariantType.Boolean
            )
            await state_node.set_writable(True)
            self.nodes[f"Pump_{pump_id.replace('.', '_')}_State"] = state_node
            
            # Flow rate (read-only)
            flow_node = await pump_obj.add_variable(
                self.namespace, "FlowRate", 0.0, varianttype=ua.VariantType.Float
            )
            await flow_node.set_writable(False)
            self.nodes[f"Pump_{pump_id.replace('.', '_')}_FlowRate"] = flow_node
            
            # Power consumption (read-only)
            power_node = await pump_obj.add_variable(
                self.namespace, "Power", 0.0, varianttype=ua.VariantType.Float
            )
            await power_node.set_writable(False)
            self.nodes[f"Pump_{pump_id.replace('.', '_')}_Power"] = power_node
            
            # Recommended state (read-only, from optimization)
            recommended_node = await pump_obj.add_variable(
                self.namespace, "RecommendedState", False, varianttype=ua.VariantType.Boolean
            )
            await recommended_node.set_writable(False)
            self.nodes[f"Pump_{pump_id.replace('.', '_')}_RecommendedState"] = recommended_node
        
        # Create Optimization object
        opt_obj = await objects.add_object(
            self.namespace, "Optimization", "Optimization Results"
        )
        self.objects["Optimization"] = opt_obj
        
        # Strategy (JSON string with full 24h strategy)
        strategy_node = await opt_obj.add_variable(
            self.namespace, "Strategy", "", varianttype=ua.VariantType.String
        )
        await strategy_node.set_writable(False)
        self.nodes["Optimization_Strategy"] = strategy_node
        
        # Total cost
        cost_node = await opt_obj.add_variable(
            self.namespace, "TotalCost", 0.0, varianttype=ua.VariantType.Float
        )
        await cost_node.set_writable(False)
        self.nodes["Optimization_TotalCost"] = cost_node
        
        # Timestamp
        timestamp_node = await opt_obj.add_variable(
            self.namespace, "Timestamp", datetime.now(), varianttype=ua.VariantType.DateTime
        )
        await timestamp_node.set_writable(False)
        self.nodes["Optimization_Timestamp"] = timestamp_node
        
        # Status
        status_node = await opt_obj.add_variable(
            self.namespace, "Status", "Idle", varianttype=ua.VariantType.String
        )
        await status_node.set_writable(False)
        self.nodes["Optimization_Status"] = status_node
        
        logger.info("OPC UA address space created successfully")
    
    async def update_water_level(self, level: float):
        """Update water level L1 node."""
        if "WaterLevel_L1" in self.nodes:
            await self.nodes["WaterLevel_L1"].write_value(level)
            logger.debug(f"Updated water level L1: {level} m")
    
    async def update_volume(self, volume: float):
        """Update volume node."""
        if "Volume" in self.nodes:
            await self.nodes["Volume"].write_value(volume)
    
    async def update_inflow(self, inflow: float):
        """Update inflow F1 node."""
        if "Inflow_F1" in self.nodes:
            await self.nodes["Inflow_F1"].write_value(inflow)
    
    async def update_pump_state(self, pump_id: str, state: bool):
        """Update pump state (actual state from PLC)."""
        node_name = f"Pump_{pump_id.replace('.', '_')}_State"
        if node_name in self.nodes:
            await self.nodes[node_name].write_value(state)
            logger.debug(f"Updated pump {pump_id} state: {state}")
    
    async def update_pump_flow(self, pump_id: str, flow: float):
        """Update pump flow rate."""
        node_name = f"Pump_{pump_id.replace('.', '_')}_FlowRate"
        if node_name in self.nodes:
            await self.nodes[node_name].write_value(flow)
    
    async def update_pump_power(self, pump_id: str, power: float):
        """Update pump power consumption."""
        node_name = f"Pump_{pump_id.replace('.', '_')}_Power"
        if node_name in self.nodes:
            await self.nodes[node_name].write_value(power)
    
    async def update_pump_recommendation(self, pump_id: str, recommended: bool):
        """Update recommended pump state from optimization."""
        node_name = f"Pump_{pump_id.replace('.', '_')}_RecommendedState"
        if node_name in self.nodes:
            await self.nodes[node_name].write_value(recommended)
            logger.debug(f"Updated pump {pump_id} recommendation: {recommended}")
    
    async def update_optimization_results(
        self,
        strategy: Dict[str, List[bool]],
        total_cost: float,
        timestamp: Optional[datetime] = None
    ):
        """Update optimization results nodes."""
        import json
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Update strategy (convert to JSON string)
        strategy_json = json.dumps(strategy)
        if "Optimization_Strategy" in self.nodes:
            await self.nodes["Optimization_Strategy"].write_value(strategy_json)
        
        # Update total cost
        if "Optimization_TotalCost" in self.nodes:
            await self.nodes["Optimization_TotalCost"].write_value(total_cost)
        
        # Update timestamp
        if "Optimization_Timestamp" in self.nodes:
            await self.nodes["Optimization_Timestamp"].write_value(timestamp)
        
        logger.info(f"Updated optimization results: cost={total_cost:.2f} EUR, timestamp={timestamp}")
    
    async def update_optimization_status(self, status: str):
        """Update optimization status."""
        if "Optimization_Status" in self.nodes:
            await self.nodes["Optimization_Status"].write_value(status)
    
    async def read_pump_state(self, pump_id: str) -> bool:
        """Read current pump state."""
        node_name = f"Pump_{pump_id.replace('.', '_')}_State"
        if node_name in self.nodes:
            return await self.nodes[node_name].read_value()
        return False
    
    async def read_water_level(self) -> float:
        """Read current water level."""
        if "WaterLevel_L1" in self.nodes:
            return await self.nodes["WaterLevel_L1"].read_value()
        return 0.0
    
    async def stop(self):
        """Stop the OPC UA server."""
        if self.server:
            await self.server.stop()
            logger.info("OPC UA server stopped")

