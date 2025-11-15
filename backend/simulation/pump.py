"""Pump class for calculating flow and power consumption."""
import numpy as np

# Constant water level at WWTP (pump pressure side)
L2 = 30.0  # meters


class Pump:
    """
    Pump class for calculating flow rate and power consumption.
    
    Big pumps: 400 kW power
    Small pumps: 250 kW power
    """
    
    def __init__(self, pump_id: str, is_big: bool):
        """
        Initialize pump.
        
        Args:
            pump_id: Unique identifier for the pump (e.g., '1.1', '2.3')
            is_big: True for big pump (400 kW), False for small pump (250 kW)
        """
        self.pump_id = pump_id
        self.is_big = is_big
        self.power = 400.0 if is_big else 250.0  # kW
        # Flow rates in m³/s for different head values
        # Small pumps: max flow ~1600 m³/h = ~0.444 m³/s
        # Big pumps: max flow ~3000 m³/h = ~0.833 m³/s
        self.flow_array = [0.33, 0.5, 0.6, 0.67, 0.75, 0.82] if is_big else [0.15, 0.25, 0.30, 0.35, 0.40, 0.44]
        # Head values H = L2 - L1 (in meters) corresponding to flow_array
        self.head_array = [35, 30, 25, 20, 15, 10] if is_big else [40, 35, 30, 25, 20, 15]
        # Usage time tracking (in minutes)
        self.usage_time_minutes = 0.0

    def calculate_flow(self, water_level_l1: float) -> float:
        """
        Calculate flow rate based on water level in tunnel.
        
        Args:
            water_level_l1: Water level L1 in tunnel (suction side) in meters
            
        Returns:
            Flow rate in m³/s
        """
        # Calculate head H = L2 - L1
        head = L2 - water_level_l1
        
        # Clamp head to valid range
        head = max(min(head, max(self.head_array)), min(self.head_array))
        
        # Interpolate flow rate based on head
        flow_m3s = np.interp(head, self.head_array, self.flow_array)
        #flow_m3s *= 0.95
        return flow_m3s

    def calculate_flow_m3_per_15min(self, water_level_l1: float) -> float:
        """
        Calculate flow rate in m³ per 15 minutes.
        
        Args:
            water_level_l1: Water level L1 in tunnel (suction side) in meters
            
        Returns:
            Flow rate in m³/15min
        """
        flow_m3s = self.calculate_flow(water_level_l1)
        # Convert m³/s to m³/15min: multiply by 60 seconds * 15 minutes = 900 seconds
        return flow_m3s * 900.0

    def get_power(self) -> float:
        """
        Get pump power consumption.
        
        Returns:
            Power in kW
        """
        return self.power

    def add_usage_time(self, minutes: float):
        """
        Add usage time to pump.
        
        Args:
            minutes: Minutes to add to usage time
        """
        self.usage_time_minutes += minutes

    def get_usage_time(self) -> float:
        """
        Get total usage time.
        
        Returns:
            Usage time in minutes
        """
        return self.usage_time_minutes


