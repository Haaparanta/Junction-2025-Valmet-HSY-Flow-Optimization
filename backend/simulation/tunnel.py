"""Tunnel volume and water level conversion functions using 4-case formula."""

# Tunnel constants
TUNNEL_WIDTH = 5.0  # meters
TUNNEL_HEIGHT = 5.5  # meters
TUNNEL_LENGTH = 8200.0  # meters

# Level boundaries
RAJA_1 = 0.4  # meters
RAJA_2 = 5.9  # meters
RAJA_3 = 8.6  # meters
RAJA_4 = 14.1  # meters (maximum)

# Base volumes for each case
VA_MAX = 350.0  # m³ (Case 1: < 0.4 m)
VB_MAX = 75975.0  # m³ (Case 2: 0.4 - 5.9 m)
VC_MAX = 150225.0  # m³ (Case 3: 5.9 - 8.6 m)
VD_MAX = 225850.0  # m³ (Case 4: 8.6 - 14.1 m)


def calculate_volume_from_level(level: float) -> float:
    """
    Calculate tunnel water volume from water level using 4-case formula.

    Args:
        level: Water level LC001 in meters

    Returns:
        Volume in m³
    """
    if level < RAJA_1:
        # Case 1: LC001 < Raja 1 (Va)
        return VA_MAX

    elif level < RAJA_2:
        # Case 2: Raja 1 < LC001 < Raja 2 (Vb)
        # Vbx = LC001 - Raja 1
        vbx = level - RAJA_1
        # Volume = (((1000 * Vbx * Vbx) / 2) * 5) + 350
        volume = (((1000.0 * vbx * vbx) / 2.0) * TUNNEL_WIDTH) + VA_MAX
        return volume

    elif level < RAJA_3:
        # Case 3: Raja 2 < LC001 < Raja 3 (Vc)
        # Vcx = LC001 - Raja 2
        vcx = level - RAJA_2
        # Volume = (5500 * Vcx * 5) + 75975
        volume = (5500.0 * vcx * TUNNEL_WIDTH) + VB_MAX
        return volume

    elif level < RAJA_4:
        # Case 4: Raja 3 < LC001 < Raja 4 (Vd)
        # Vdx = LC001 - Raja 3
        vdx = level - RAJA_3
        # Volume = (((5.5 * 5500 / 2) - ((5.5 - Vdx) * (5.5 - Vdx) * 1000 / 2)) * 5) + 150225
        volume = (
            (
                (TUNNEL_HEIGHT * 5500.0 / 2.0)
                - ((TUNNEL_HEIGHT - vdx) * (TUNNEL_HEIGHT - vdx) * 1000.0 / 2.0)
            )
            * TUNNEL_WIDTH
        ) + VC_MAX
        return volume

    else:
        # Level >= RAJA_4 (14.1 m) - exceeds maximum
        return VD_MAX


def calculate_level_from_volume(
    volume: float, tolerance: float = 0.001, max_iterations: int = 100
) -> float:
    """
    Calculate water level from volume using iterative method (binary search).

    Args:
        volume: Water volume in m³
        tolerance: Convergence tolerance in meters (default: 0.001)
        max_iterations: Maximum iterations (default: 100)

    Returns:
        Water level in meters
    """
    # Handle edge cases
    if volume <= VA_MAX:
        # Case 1: volume <= 350 m³
        # For simplicity, assume linear relationship in Case 1
        if volume <= 0:
            return 0.0
        return (volume / VA_MAX) * RAJA_1

    if volume >= VD_MAX:
        return RAJA_4 + volume / VD_MAX

    # Binary search for the correct level
    low = RAJA_1
    high = RAJA_4

    for _ in range(max_iterations):
        mid = (low + high) / 2.0
        mid_volume = calculate_volume_from_level(mid)

        if abs(mid_volume - volume) < tolerance:
            return mid

        if mid_volume < volume:
            low = mid
        else:
            high = mid

    # Return best estimate
    return (low + high) / 2.0


def validate_level(level: float) -> tuple[bool, float]:
    """
    Validate water level and return penalty cost if exceeded.

    Args:
        level: Water level in meters

    Returns:
        Tuple of (is_valid, penalty_cost)
        - is_valid: True if level <= 14.1 m, False otherwise
        - penalty_cost: 1,000,000 EUR if invalid, 0 otherwise
    """
    if level > RAJA_4:
        return False, 1000.0
    return True, 0.0
