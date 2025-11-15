"""Pump class for calculating flow and power consumption."""

import numpy as np
import numba

# Constant water level at WWTP (pump pressure side)
L2 = 30.0  # meters

# m3/h
FLOW_BIG = np.array([400, 1000, 1200, 1300, 1500]) / 1000.0 * 60 * 60
# m
HEAD_ARRAY_BIG = [35, 30, 25, 20, 15]
MULTIPLIERS_BIG = np.polyfit(HEAD_ARRAY_BIG, FLOW_BIG, 2)

# m3/h
FLOW_SMALL = np.array([310, 500, 600, 670, 750, 850]) / 1000.0 * 60 * 60
# m
HEAD_ARRAY_SMALL = [35, 30, 25, 20, 15, 10]
MULTIPLIERS_SMALL = np.polyfit(HEAD_ARRAY_SMALL, FLOW_SMALL, 2)


@numba.njit()
def calculate_flow_small_m3_per_15_min_small(pump_height: float):
    return (
        MULTIPLIERS_SMALL[0] * pump_height**2
        + MULTIPLIERS_SMALL[1] * pump_height
        + MULTIPLIERS_SMALL[2]
    ) / 4.0


@numba.njit()
def calculate_flow_big_m3_per_15_min_big(pump_height: float):
    return (
        MULTIPLIERS_BIG[0] * pump_height**2
        + MULTIPLIERS_BIG[1] * pump_height
        + MULTIPLIERS_BIG[2]
    ) / 4.0


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


        self.flow_array = FLOW_BIG if is_big else FLOW_SMALL
        self.head_array = (
            HEAD_ARRAY_BIG if is_big else HEAD_ARRAY_SMALL
        )
        # Usage time tracking (in minutes)
        self.usage_time_minutes = 0.0


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

    def calculate_flow_m3_per_15min(self, pump_lift_height: float) -> float:
        if self.is_big:
            return calculate_flow_big_m3_per_15_min_big(pump_lift_height)
        else:
            return calculate_flow_small_m3_per_15_min_small(pump_lift_height)
