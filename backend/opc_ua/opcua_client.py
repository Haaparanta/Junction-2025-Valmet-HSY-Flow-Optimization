"""OPC UA client for reading sensor data from PLC/SCADA systems."""
import asyncio
import logging
from typing import Dict, Optional, Callable, List
from datetime import datetime

try:
    from asyncua import Client, ua
    from asyncua.client import Client as AsyncUAClient
except ImportError:
    raise ImportError(
        "asyncua is required for OPC UA functionality. Install with: pip install asyncua"
    )

from .config import OPCUAConfig

logger = logging.getLogger(__name__)


class OPCUAClient:
    """
    OPC UA client for connecting to PLC/SCADA OPC UA server.
    
    Reads real-time sensor data and can write control commands.
    """
    
    def __init__(self, config: OPCUAConfig):
        """Initialize OPC UA client."""
        self.config = config
        self.client: Optional[AsyncUAClient] = None
        self.connected = False
        
        # Subscriptions
        self.subscriptions: Dict[str, ua.Subscription] = {}
        self.subscribed_nodes: Dict[str, ua.Node] = {}
        
        # Callbacks for data changes
        self.data_callbacks: Dict[str, Callable] = {}
        
        # Pump IDs
        self.pump_ids = ["1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4"]
    
    async def connect(self):
        """Connect to PLC/SCADA OPC UA server."""
        if not self.config.plc_endpoint:
            logger.warning("No PLC endpoint configured. Client will run in mock mode.")
            self.connected = False
            return
        
        try:
            self.client = Client(url=self.config.plc_endpoint)
            
            # Set security policy and mode
            if self.config.plc_security_policy == "None":
                await self.client.set_security_strings(
                    ua.SecurityPolicyType.NoSecurity,
                    ua.MessageSecurityMode.None_
                )
            else:
                # For production, implement proper certificate-based security
                logger.warning(f"Security policy {self.config.plc_security_policy} not fully implemented")
            
            await self.client.connect()
            self.connected = True
            logger.info(f"Connected to PLC OPC UA server at {self.config.plc_endpoint}")
            
        except Exception as e:
            logger.error(f"Failed to connect to PLC OPC UA server: {e}", exc_info=True)
            self.connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from PLC/SCADA OPC UA server."""
        if self.client:
            try:
                # Cancel subscriptions
                for sub in self.subscriptions.values():
                    await sub.delete()
                self.subscriptions.clear()
                self.subscribed_nodes.clear()
                
                await self.client.disconnect()
                self.connected = False
                logger.info("Disconnected from PLC OPC UA server")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}", exc_info=True)
    
    async def read_water_level(self, node_id: str = "ns=2;s=WaterLevel.L1") -> Optional[float]:
        """
        Read water level L1 from PLC.
        
        Args:
            node_id: OPC UA node ID for water level sensor
            
        Returns:
            Water level in meters, or None if read fails
        """
        if not self.connected or not self.client:
            logger.warning("Client not connected. Returning mock value.")
            return 5.0  # Mock value
        
        try:
            node = self.client.get_node(node_id)
            value = await node.read_value()
            return float(value)
        except Exception as e:
            logger.error(f"Failed to read water level: {e}", exc_info=True)
            return None
    
    async def read_pump_state(self, pump_id: str, node_id_template: str = "ns=2;s=Pump.{pump_id}.State") -> Optional[bool]:
        """
        Read pump state from PLC.
        
        Args:
            pump_id: Pump identifier (e.g., "1.1")
            node_id_template: Template for node ID (use {pump_id} placeholder)
            
        Returns:
            Pump state (True=ON, False=OFF), or None if read fails
        """
        if not self.connected or not self.client:
            logger.warning(f"Client not connected. Returning mock value for pump {pump_id}.")
            return False  # Mock value
        
        try:
            node_id = node_id_template.format(pump_id=pump_id)
            node = self.client.get_node(node_id)
            value = await node.read_value()
            return bool(value)
        except Exception as e:
            logger.error(f"Failed to read pump {pump_id} state: {e}", exc_info=True)
            return None
    
    async def read_pump_flow(self, pump_id: str, node_id_template: str = "ns=2;s=Pump.{pump_id}.FlowRate") -> Optional[float]:
        """
        Read pump flow rate from PLC.
        
        Args:
            pump_id: Pump identifier
            node_id_template: Template for node ID
            
        Returns:
            Flow rate in m³/h, or None if read fails
        """
        if not self.connected or not self.client:
            return None
        
        try:
            node_id = node_id_template.format(pump_id=pump_id)
            node = self.client.get_node(node_id)
            value = await node.read_value()
            return float(value)
        except Exception as e:
            logger.error(f"Failed to read pump {pump_id} flow: {e}", exc_info=True)
            return None
    
    async def read_all_pump_states(self, node_id_template: str = "ns=2;s=Pump.{pump_id}.State") -> Dict[str, bool]:
        """Read all pump states."""
        states = {}
        for pump_id in self.pump_ids:
            state = await self.read_pump_state(pump_id, node_id_template)
            if state is not None:
                states[pump_id] = state
        return states
    
    async def write_pump_command(self, pump_id: str, state: bool, node_id_template: str = "ns=2;s=Pump.{pump_id}.Command") -> bool:
        """
        Write pump command to PLC.
        
        Args:
            pump_id: Pump identifier
            state: Desired state (True=ON, False=OFF)
            node_id_template: Template for command node ID
            
        Returns:
            True if write successful, False otherwise
        """
        if not self.connected or not self.client:
            logger.warning(f"Client not connected. Cannot write command for pump {pump_id}.")
            return False
        
        try:
            node_id = node_id_template.format(pump_id=pump_id)
            node = self.client.get_node(node_id)
            await node.write_value(state)
            logger.info(f"Wrote pump {pump_id} command: {'ON' if state else 'OFF'}")
            return True
        except Exception as e:
            logger.error(f"Failed to write pump {pump_id} command: {e}", exc_info=True)
            return False
    
    async def subscribe_to_water_level(
        self,
        callback: Callable[[float], None],
        node_id: str = "ns=2;s=WaterLevel.L1",
        sampling_interval: int = 1000
    ):
        """
        Subscribe to water level changes.
        
        Args:
            callback: Function to call when water level changes
            node_id: OPC UA node ID for water level
            sampling_interval: Sampling interval in milliseconds
        """
        if not self.connected or not self.client:
            logger.warning("Client not connected. Cannot subscribe.")
            return
        
        try:
            # Create subscription if not exists
            if "water_level" not in self.subscriptions:
                subscription = await self.client.create_subscription(
                    sampling_interval, callback
                )
                self.subscriptions["water_level"] = subscription
            
            # Get node and subscribe
            node = self.client.get_node(node_id)
            handle = await self.subscriptions["water_level"].subscribe_data_change(node)
            self.subscribed_nodes["water_level"] = node
            self.data_callbacks["water_level"] = callback
            
            logger.info(f"Subscribed to water level changes at {node_id}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to water level: {e}", exc_info=True)
    
    async def subscribe_to_pump_states(
        self,
        callback: Callable[[str, bool], None],
        node_id_template: str = "ns=2;s=Pump.{pump_id}.State",
        sampling_interval: int = 1000
    ):
        """
        Subscribe to all pump state changes.
        
        Args:
            callback: Function to call when pump state changes (pump_id, state)
            node_id_template: Template for node IDs
            sampling_interval: Sampling interval in milliseconds
        """
        if not self.connected or not self.client:
            logger.warning("Client not connected. Cannot subscribe.")
            return
        
        try:
            # Create subscription if not exists
            if "pump_states" not in self.subscriptions:
                subscription = await self.client.create_subscription(
                    sampling_interval, callback
                )
                self.subscriptions["pump_states"] = subscription
            
            # Subscribe to each pump
            for pump_id in self.pump_ids:
                node_id = node_id_template.format(pump_id=pump_id)
                node = self.client.get_node(node_id)
                handle = await self.subscriptions["pump_states"].subscribe_data_change(node)
                self.subscribed_nodes[f"pump_{pump_id}"] = node
            
            self.data_callbacks["pump_states"] = callback
            
            logger.info(f"Subscribed to pump state changes for {len(self.pump_ids)} pumps")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to pump states: {e}", exc_info=True)
    
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self.connected

