"""24-hour simulation engine for wastewater tunnel system."""
from typing import List, Dict, Set
from .pump import Pump
from .tunnel import (
    calculate_volume_from_level,
    calculate_level_from_volume,
    validate_level,
    RAJA_4
)

# Constants
MINIMUM_RUNTIME_PERIODS = 4  # 1 hour = 4 * 15 minutes
PENALTY_COST = 1_000_000.0  # EUR
TIME_STEP_MINUTES = 15  # minutes per time step


class Simulator:
    """
    Simulator for 24-hour wastewater tunnel system simulation.
    
    Simulates 96 time steps (15 minutes each) with intelligent pump control,
    cost calculation, and constraint validation.
    """
    
    def __init__(
        self,
        starting_water_level: float,
        energy_prices: List[float],
        water_inflows: List[float],
        target_flowrates: List[float]
    ):
        """
        Initialize simulator.
        
        Args:
            starting_water_level: Initial water level L1 in meters
            energy_prices: List of 96 energy prices in EUR/kWh (one per 15-min period)
            water_inflows: List of 96 inflow rates in m³/15min (one per 15-min period)
            target_flowrates: List of 96 target flowrates in m³/15min (one per 15-min period)
        """
        if len(energy_prices) != 96 or len(water_inflows) != 96 or len(target_flowrates) != 96:
            raise ValueError("All input vectors must have exactly 96 elements (24 hours * 4 periods)")
        
        self.starting_water_level = starting_water_level
        self.energy_prices = energy_prices
        self.water_inflows = water_inflows
        self.target_flowrates = target_flowrates
        
        # Initialize pumps: 6 big pumps + 2 small pumps
        # Big pumps: 1.2, 1.3, 1.4, 2.2, 2.3, 2.4
        # Small pumps: 1.1, 2.1
        self.pumps: Dict[str, Pump] = {}
        big_pump_ids = ['1.2', '1.3', '1.4', '2.2', '2.3', '2.4']
        small_pump_ids = ['1.1', '2.1']
        
        for pump_id in big_pump_ids:
            self.pumps[pump_id] = Pump(pump_id, is_big=True)
        for pump_id in small_pump_ids:
            self.pumps[pump_id] = Pump(pump_id, is_big=False)
        
        # Initialize state
        self.current_water_level = starting_water_level
        self.current_volume = calculate_volume_from_level(starting_water_level)
        
        # Pump state tracking: dict[pump_id] -> list of bool (on/off states for last 4 periods)
        self.pump_state_history: Dict[str, List[bool]] = {
            pump_id: [] for pump_id in self.pumps.keys()
        }
        
        # Track when each pump was turned on (time step when it started running)
        self.pump_turn_on_time: Dict[str, int] = {}
        
        # Track which pumps have been used at least once
        self.pumps_used: Set[str] = set()
        
        # Track cost per pump
        self.pump_costs: Dict[str, float] = {pump_id: 0.0 for pump_id in self.pumps.keys()}
        
        # Total cost accumulator
        self.total_cost = 0.0
        
        # Violation log
        self.violations: List[str] = []
        
        # Time series data for plotting
        self.time_series_data: Dict[str, List[float]] = {
            'water_levels': [],
            'volumes': [],
            'inflows': [],
            'outflows': [],
            'energy_prices': [],
            'target_flowrates': [],
            'costs': [],
            'cumulative_costs': [],
            'pump_states': {pump_id: [] for pump_id in self.pumps.keys()},
            'pump_flows': {pump_id: [] for pump_id in self.pumps.keys()}  # Flow in m³/h
        }
    
    def _select_pumps(self, target_flowrate: float, current_level: float, time_step: int) -> Set[str]:
        """
        Select pumps to meet or exceed target flowrate while balancing usage and respecting minimum runtime.
        
        Algorithm:
        1. Identify pumps that MUST stay on (currently on and haven't run for minimum 4 periods)
        2. Identify pumps that CAN be turned off (currently on and have run for at least 4 periods)
        3. Calculate flow from pumps that must stay on
        4. If more flow needed, add pumps starting from least-used until target is met
        5. Ensure at least one pump is always on
    
    Args:
            target_flowrate: Target flowrate in m³/15min
            current_level: Current water level L1 in meters
            time_step: Current time step (for checking runtime)
            
        Returns:
            Set of pump IDs that should be turned on
        """
        # Identify pumps that MUST stay on (currently on and haven't run for minimum 4 periods)
        pumps_must_stay_on: Set[str] = set()
        pumps_can_turn_off: Set[str] = set()
        
        for pump_id in self.pumps.keys():
            # Check if pump is currently on
            is_currently_on = (
                len(self.pump_state_history[pump_id]) > 0 and
                self.pump_state_history[pump_id][-1]
            )
            
            if is_currently_on:
                # Check how long it's been running
                if pump_id in self.pump_turn_on_time:
                    turn_on_time = self.pump_turn_on_time[pump_id]
                    runtime_periods = time_step - turn_on_time
                    
                    if runtime_periods < MINIMUM_RUNTIME_PERIODS:
                        # Must stay on - hasn't completed minimum runtime
                        pumps_must_stay_on.add(pump_id)
                    else:
                        # Can be turned off - has completed minimum runtime
                        pumps_can_turn_off.add(pump_id)
                else:
                    # Pump is on but not tracked - assume it must stay on (shouldn't happen)
                    pumps_must_stay_on.add(pump_id)
        
        # Start with pumps that must stay on
        selected_pumps: Set[str] = set(pumps_must_stay_on)
        total_flow = sum(
            self.pumps[pump_id].calculate_flow_m3_per_15min(current_level)
            for pump_id in pumps_must_stay_on
        )
        
        # If we need more flow, first check if we should keep pumps that can turn off
        # (they're already on and providing flow)
        if total_flow < target_flowrate and pumps_can_turn_off:
            # Keep pumps that can turn off if we need their flow
            # Sort by usage time (keep least-used ones first)
            sorted_can_turn_off = sorted(
                pumps_can_turn_off,
                key=lambda pid: self.pumps[pid].get_usage_time()
            )
            
            for pump_id in sorted_can_turn_off:
                if total_flow >= target_flowrate:
                    break
                flow = self.pumps[pump_id].calculate_flow_m3_per_15min(current_level)
                total_flow += flow
                selected_pumps.add(pump_id)
        
        # If we still need more flow, add pumps from those that are currently off
        # Prioritize pumps that haven't been used yet, then sort by usage time
        available_pumps = [
            (pump_id, pump) for pump_id, pump in self.pumps.items()
            if pump_id not in selected_pumps
        ]
        
        # Separate unused pumps from used pumps
        unused_pumps = [(pid, p) for pid, p in available_pumps if pid not in self.pumps_used]
        used_pumps = [(pid, p) for pid, p in available_pumps if pid in self.pumps_used]
        
        # Sort unused pumps by usage time (should all be 0, but sort anyway)
        sorted_unused = sorted(unused_pumps, key=lambda x: x[1].get_usage_time())
        # Sort used pumps by usage time (ascending) - least used first
        sorted_used = sorted(used_pumps, key=lambda x: x[1].get_usage_time())
        
        # Ensure all pumps are used during the day
        # Strategy: Aggressively prioritize unused pumps
        # After 12 hours (48 time steps), start forcing unused pumps
        # After 18 hours (72 time steps), force all remaining unused pumps
        if sorted_unused:
            if time_step >= 72:
                # Force all remaining unused pumps (we're in last quarter of day)
                for pump_id, pump in sorted_unused:
                    flow = pump.calculate_flow_m3_per_15min(current_level)
                    total_flow += flow
                    selected_pumps.add(pump_id)
            elif time_step >= 48:
                # Force at least one unused pump every 4 time steps (1 hour)
                if time_step % 4 == 0 and len(sorted_unused) > 0:
                    pump_id, pump = sorted_unused[0]
                    flow = pump.calculate_flow_m3_per_15min(current_level)
                    total_flow += flow
                    selected_pumps.add(pump_id)
            elif time_step >= 24:
                # After 6 hours, start prioritizing unused pumps more
                # Force one unused pump every 12 time steps (3 hours)
                if time_step % 12 == 0 and len(sorted_unused) > 0:
                    pump_id, pump = sorted_unused[0]
                    flow = pump.calculate_flow_m3_per_15min(current_level)
                    total_flow += flow
                    selected_pumps.add(pump_id)
        
        # Combine: unused first (always prioritized), then used (both sorted by usage time)
        sorted_used_by_usage = sorted(used_pumps, key=lambda x: x[1].get_usage_time())
        sorted_available = sorted_unused + sorted_used_by_usage
        
        # Add pumps until we're close to target (allow rounding down if close enough)
        # Always prioritize unused pumps first - they get selected before used pumps
        # Then select used pumps starting with least-used ones
        # Allow rounding down if we're within tolerance of target
        tolerance = target_flowrate * 0.15  # 15% tolerance
        
        for pump_id, pump in sorted_available:
            # Check if adding this pump would exceed target significantly
            flow = pump.calculate_flow_m3_per_15min(current_level)
            new_total = total_flow + flow
            
            # If we're already close to target (within tolerance), stop adding pumps
            if total_flow >= target_flowrate - tolerance:
                # Only add if it doesn't exceed target by too much (more than 10%)
                if new_total <= target_flowrate * 1.1:
                    total_flow = new_total
                    selected_pumps.add(pump_id)
                break
            
            # If adding this pump gets us close to or exceeds target, add it
            if new_total >= target_flowrate - tolerance:
                total_flow = new_total
                selected_pumps.add(pump_id)
                # Stop if we've met or slightly exceeded target
                if new_total >= target_flowrate:
                    break
            else:
                # Still far from target, add the pump
                total_flow = new_total
                selected_pumps.add(pump_id)
        
        # If we still have unused pumps and haven't met target, add them anyway
        # This ensures unused pumps get a chance even if target is already met
        if sorted_unused and time_step >= 24:
            # Add at least one unused pump if we haven't used all pumps yet
            remaining_unused = [pid for pid, _ in sorted_unused if pid not in selected_pumps]
            if remaining_unused and len(self.pumps_used) < len(self.pumps):
                # Add one unused pump to ensure all pumps are used
                pump_id = remaining_unused[0]
                pump = self.pumps[pump_id]
                flow = pump.calculate_flow_m3_per_15min(current_level)
                total_flow += flow
                selected_pumps.add(pump_id)
        
        # Ensure at least one pump is always on
        if len(selected_pumps) == 0:
            # Select the least-used pump
            if sorted_available:
                least_used_pump_id = sorted_available[0][0]
                selected_pumps.add(least_used_pump_id)
            elif pumps_can_turn_off:
                # Keep one of the pumps that can turn off
                selected_pumps.add(list(pumps_can_turn_off)[0])
            else:
                # Fallback: select any pump
                selected_pumps.add(list(self.pumps.keys())[0])
        
        return selected_pumps
    
    def _check_minimum_runtime(self, time_step: int, pumps_on: Set[str]) -> float:
        """
        Check if pumps meet minimum runtime requirement (1 hour = 4 periods).
        
        A pump that is turned on must run for at least 4 consecutive periods (1 hour)
        before it can be turned off.
        
        Args:
            time_step: Current time step (0-95)
            pumps_on: Set of pump IDs that are currently on
            
        Returns:
            Penalty cost (0 if no violations, PENALTY_COST per violation)
        """
        penalty = 0.0
        
        for pump_id in self.pumps.keys():
            # Check if pump was on in previous time step
            was_on = (
                len(self.pump_state_history[pump_id]) > 0 and
                self.pump_state_history[pump_id][-1]
            ) if len(self.pump_state_history[pump_id]) > 0 else False
            is_on = pump_id in pumps_on
            
            # Pump was turned off
            if was_on and not is_on:
                # Check if it ran for at least 4 periods
                if pump_id in self.pump_turn_on_time:
                    turn_on_time = self.pump_turn_on_time[pump_id]
                    runtime_periods = time_step - turn_on_time
                    
                    if runtime_periods < MINIMUM_RUNTIME_PERIODS:
                        penalty += PENALTY_COST
                        self.violations.append(
                            f"Time step {time_step}: Pump {pump_id} violated minimum runtime "
                            f"(ran for {runtime_periods * TIME_STEP_MINUTES} minutes, "
                            f"minimum is {MINIMUM_RUNTIME_PERIODS * TIME_STEP_MINUTES} minutes)"
                        )
                    
                    # Remove from turn-on tracking
                    del self.pump_turn_on_time[pump_id]
            
            # Pump was turned on
            elif not was_on and is_on:
                # Record turn-on time
                self.pump_turn_on_time[pump_id] = time_step
        
        return penalty
    
    def _update_state(self, inflow: float, outflow: float) -> float:
        """
        Update water level and volume based on inflow and outflow.
        
        Args:
            inflow: Inflow in m³/15min
            outflow: Outflow in m³/15min
        
    Returns:
            New water level in meters
        """
        # Calculate volume change
        volume_change = inflow - outflow
        
        # Update volume
        self.current_volume += volume_change
        
        # Ensure volume is non-negative
        if self.current_volume < 0:
            self.current_volume = 0.0
        
        # Calculate new water level from volume
        self.current_water_level = calculate_level_from_volume(self.current_volume)
        
        return self.current_water_level
    
    def _calculate_time_step_cost(
        self,
        pumps_on: Set[str],
        energy_price: float
    ) -> float:
        """
        Calculate energy cost for one 15-minute time step.
        
        Args:
            pumps_on: Set of pump IDs that are on
            energy_price: Energy price in EUR/kWh
            
        Returns:
            Cost in EUR
        """
        # Calculate total power consumption
        total_power_kw = sum(
            self.pumps[pump_id].get_power()
            for pump_id in pumps_on
        )
        
        # Convert to energy: power (kW) * time (hours)
        # 15 minutes = 0.25 hours
        energy_kwh = total_power_kw * 0.25
        
        # Calculate cost
        cost = energy_kwh * energy_price
        
        return cost
    
    def simulate(self) -> float:
        """
        Run 24-hour simulation (96 time steps of 15 minutes each).
        
        Returns:
            Total cost in EUR (including penalties)
        """
        # Reset state
        self.current_water_level = self.starting_water_level
        self.current_volume = calculate_volume_from_level(self.starting_water_level)
        self.total_cost = 0.0
        self.violations = []
        
        # Reset pump usage times and state history
        for pump in self.pumps.values():
            pump.usage_time_minutes = 0.0
        self.pump_state_history = {
            pump_id: [] for pump_id in self.pumps.keys()
        }
        self.pump_turn_on_time = {}
        self.pumps_used = set()
        self.pump_costs = {pump_id: 0.0 for pump_id in self.pumps.keys()}
        
        # Reset time series data
        self.time_series_data = {
            'water_levels': [],
            'volumes': [],
            'inflows': [],
            'outflows': [],
            'energy_prices': [],
            'target_flowrates': [],
            'costs': [],
            'cumulative_costs': [],
            'pump_states': {pump_id: [] for pump_id in self.pumps.keys()},
            'pump_flows': {pump_id: [] for pump_id in self.pumps.keys()}  # Flow in m³/h
        }
        
        # Main simulation loop
        for time_step in range(96):
            # Get inputs for this time step
            energy_price = self.energy_prices[time_step]
            inflow = self.water_inflows[time_step]
            target_flowrate = self.target_flowrates[time_step]
            
            # Select pumps to meet target flowrate (respecting minimum runtime)
            pumps_on = self._select_pumps(target_flowrate, self.current_water_level, time_step)
            
            # Calculate speed factor for each pump
            # Pump speed is halved when starting (first period after turn-on) and when stopping (last period before turn-off)
            pump_speed_factors = {}
            for pump_id in self.pumps.keys():
                is_on = pump_id in pumps_on
                was_on = (
                    len(self.pump_state_history[pump_id]) > 0 and
                    self.pump_state_history[pump_id][-1]
                ) if len(self.pump_state_history[pump_id]) > 0 else False
                
                speed_factor = 1.0
                if is_on:
                    # Check if pump is starting (just turned on this period)
                    if not was_on:
                        speed_factor = 0.5  # Starting: half speed in first period
                    # Check if pump is stopping (last period before turn-off)
                    # A pump is stopping if it was on, has completed minimum runtime,
                    # and we need to check if it will be turned off next period
                    # Since we can't know the future, we'll check if pump has been on for minimum runtime
                    # and might be turned off (heuristic: if it's been on for exactly minimum runtime, it might stop soon)
                    elif was_on and pump_id in self.pump_turn_on_time:
                        turn_on_time = self.pump_turn_on_time[pump_id]
                        runtime_periods = time_step - turn_on_time
                        # If pump has completed minimum runtime, it can potentially be turned off
                        # Apply half speed if it's been on for exactly minimum runtime (last period before possible turn-off)
                        if runtime_periods == MINIMUM_RUNTIME_PERIODS:
                            speed_factor = 0.5  # Stopping: half speed (might be turned off soon)
                
                pump_speed_factors[pump_id] = speed_factor
            
            # Calculate actual outflow from selected pumps
            total_outflow = sum(
                self.pumps[pump_id].calculate_flow_m3_per_15min(self.current_water_level) * pump_speed_factors[pump_id]
                for pump_id in pumps_on
            )
            
            # Update water level and volume
            new_level = self._update_state(inflow, total_outflow)
            
            # Validate water level constraint
            is_valid_level, level_penalty = validate_level(new_level)
            if not is_valid_level:
                self.total_cost += level_penalty
                self.violations.append(
                    f"Time step {time_step}: Water level {new_level:.2f} m exceeds maximum "
                    f"{RAJA_4} m"
                )
            
            # Check minimum runtime constraint (before updating history)
            runtime_penalty = self._check_minimum_runtime(time_step, pumps_on)
            self.total_cost += runtime_penalty
            
            # Update pump state history
            for pump_id in self.pumps.keys():
                is_on = pump_id in pumps_on
                self.pump_state_history[pump_id].append(is_on)
                
                # Keep only last 4 periods for minimum runtime check
                if len(self.pump_state_history[pump_id]) > MINIMUM_RUNTIME_PERIODS:
                    self.pump_state_history[pump_id].pop(0)
                
                # Update usage time and track which pumps have been used
                if is_on:
                    self.pumps[pump_id].add_usage_time(TIME_STEP_MINUTES)
                    self.pumps_used.add(pump_id)
            
            # Check at-least-one-pump constraint
            if len(pumps_on) == 0:
                self.total_cost += PENALTY_COST
                self.violations.append(
                    f"Time step {time_step}: No pumps are on (at least one pump must always be on)"
                )
            
            # Calculate and add energy cost
            step_cost = self._calculate_time_step_cost(pumps_on, energy_price)
            self.total_cost += step_cost
            
            # Track cost per pump (distribute cost proportionally by power)
            total_power = sum(self.pumps[pump_id].get_power() for pump_id in pumps_on)
            if total_power > 0:
                for pump_id in pumps_on:
                    pump_power = self.pumps[pump_id].get_power()
                    pump_cost_share = step_cost * (pump_power / total_power)
                    self.pump_costs[pump_id] += pump_cost_share
            
            # Store time series data
            self.time_series_data['water_levels'].append(self.current_water_level)
            self.time_series_data['volumes'].append(self.current_volume)
            self.time_series_data['inflows'].append(inflow)
            self.time_series_data['outflows'].append(total_outflow)
            self.time_series_data['energy_prices'].append(energy_price)
            self.time_series_data['target_flowrates'].append(target_flowrate)
            self.time_series_data['costs'].append(step_cost + runtime_penalty + (level_penalty if not is_valid_level else 0.0))
            self.time_series_data['cumulative_costs'].append(self.total_cost)
            
            # Store pump states and flows
            for pump_id in self.pumps.keys():
                is_on = pump_id in pumps_on
                self.time_series_data['pump_states'][pump_id].append(1.0 if is_on else 0.0)
                # Calculate pump flow in m³/h (convert from m³/15min by multiplying by 4)
                # Use the speed factor calculated earlier
                if is_on:
                    flow_15min = self.pumps[pump_id].calculate_flow_m3_per_15min(self.current_water_level) * pump_speed_factors[pump_id]
                    flow_m3h = flow_15min * 4.0  # Convert to m³/h
                else:
                    flow_m3h = 0.0
                self.time_series_data['pump_flows'][pump_id].append(flow_m3h)
        
        # Final check for minimum runtime violations at end of simulation
        # Check if any pumps are still running but haven't completed minimum runtime
        for pump_id in self.pump_turn_on_time.keys():
            turn_on_time = self.pump_turn_on_time[pump_id]
            runtime_periods = 96 - turn_on_time  # End of simulation is time step 96
            
            if runtime_periods < MINIMUM_RUNTIME_PERIODS:
                self.total_cost += PENALTY_COST
                self.violations.append(
                    f"End of simulation: Pump {pump_id} violated minimum runtime "
                    f"(ran for {runtime_periods * TIME_STEP_MINUTES} minutes at end, "
                    f"minimum is {MINIMUM_RUNTIME_PERIODS * TIME_STEP_MINUTES} minutes)"
                )
        
        # Final check: Ensure all pumps were used at least once
        unused_pumps = set(self.pumps.keys()) - self.pumps_used
        if unused_pumps:
            self.violations.append(
                f"Warning: The following pumps were never used during the simulation: {', '.join(sorted(unused_pumps))}"
            )
        
        return self.total_cost
