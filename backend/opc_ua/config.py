"""Configuration management for OPC UA integration."""
import os
from typing import Optional
from pydantic import BaseModel, Field


class OPCUAConfig(BaseModel):
    """Configuration for OPC UA server and client."""
    
    # Server configuration
    server_endpoint: str = Field(
        default="opc.tcp://0.0.0.0:4840",
        description="OPC UA server endpoint"
    )
    server_name: str = Field(
        default="Wastewater Tunnel Optimization Server",
        description="Server application name"
    )
    server_uri: str = Field(
        default="urn:valmet:paskavesi:optimization",
        description="Server URI identifier"
    )
    
    # Client configuration (for connecting to PLC/SCADA)
    plc_endpoint: Optional[str] = Field(
        default=None,
        description="PLC/SCADA OPC UA server endpoint (e.g., opc.tcp://plc:4840)"
    )
    plc_security_policy: str = Field(
        default="None",
        description="Security policy: None, Basic128Rsa15, Basic256, Basic256Sha256"
    )
    plc_security_mode: str = Field(
        default="None",
        description="Security mode: None, Sign, SignAndEncrypt"
    )
    
    # Control mode
    control_mode: str = Field(
        default="advisory",
        description="Control mode: 'advisory' (read-only recommendations) or 'closed_loop' (automated control)"
    )
    
    # Safety limits
    max_water_level: float = Field(
        default=10.0,
        description="Maximum water level (RAJA_4) in meters - override threshold"
    )
    min_pump_runtime_minutes: int = Field(
        default=60,
        description="Minimum pump runtime in minutes before allowing shutdown"
    )
    
    # Update intervals
    sensor_update_interval_seconds: int = Field(
        default=15,
        description="Interval for reading sensor data in seconds"
    )
    optimization_trigger_interval_minutes: int = Field(
        default=15,
        description="Interval for triggering new optimization in minutes"
    )
    
    # Node ID configuration
    namespace_index: int = Field(
        default=2,
        description="OPC UA namespace index for our nodes"
    )
    
    @classmethod
    def from_env(cls) -> "OPCUAConfig":
        """Create configuration from environment variables."""
        return cls(
            server_endpoint=os.getenv("OPCUA_SERVER_ENDPOINT", "opc.tcp://0.0.0.0:4840"),
            server_name=os.getenv("OPCUA_SERVER_NAME", "Wastewater Tunnel Optimization Server"),
            server_uri=os.getenv("OPCUA_SERVER_URI", "urn:valmet:paskavesi:optimization"),
            plc_endpoint=os.getenv("OPCUA_PLC_ENDPOINT"),
            plc_security_policy=os.getenv("OPCUA_PLC_SECURITY_POLICY", "None"),
            plc_security_mode=os.getenv("OPCUA_PLC_SECURITY_MODE", "None"),
            control_mode=os.getenv("OPCUA_CONTROL_MODE", "advisory"),
            max_water_level=float(os.getenv("OPCUA_MAX_WATER_LEVEL", "10.0")),
            min_pump_runtime_minutes=int(os.getenv("OPCUA_MIN_PUMP_RUNTIME_MINUTES", "60")),
            sensor_update_interval_seconds=int(os.getenv("OPCUA_SENSOR_UPDATE_INTERVAL", "15")),
            optimization_trigger_interval_minutes=int(os.getenv("OPCUA_OPTIMIZATION_INTERVAL", "15")),
            namespace_index=int(os.getenv("OPCUA_NAMESPACE_INDEX", "2")),
        )

