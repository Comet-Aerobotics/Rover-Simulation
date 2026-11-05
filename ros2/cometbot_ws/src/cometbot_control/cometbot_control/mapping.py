"""Pure joystick-to-Twist mapping logic, independent of ROS for unit testing."""
import math
from typing import Sequence, Tuple


def shape_pair(linear: float, angular: float, *, deadzone: float = 0.1,
               power: int = 3, enabled: bool = True) -> Tuple[float, float]:
    """Apply radial deadzone and odd-power shaping, preserving input sign."""
    if not enabled:
        return 0.0, 0.0
    if not 0.0 <= deadzone <= 1.0:
        raise ValueError("deadzone must be between 0 and 1")
    if power < 1 or power % 2 == 0:
        raise ValueError("power must be a positive odd integer")
    linear = max(-1.0, min(1.0, float(linear)))
    angular = max(-1.0, min(1.0, float(angular)))
    if math.hypot(linear, angular) < deadzone:
        return 0.0, 0.0

    def signed_power(value: float) -> float:
        return math.copysign(abs(value) ** power, value)

    return signed_power(linear), signed_power(angular)


def joy_to_pair(axes: Sequence[float], buttons: Sequence[int], *,
                linear_axis: int = 1, angular_axis: int = 3,
                deadzone: float = 0.1, power: int = 3,
                enable_button_index: int = -1) -> Tuple[float, float]:
    """Map Joy arrays to linear-x and angular-z values; missing inputs fail safe."""
    if linear_axis < 0 or angular_axis < 0:
        raise ValueError("axis indices must be non-negative")
    if linear_axis >= len(axes) or angular_axis >= len(axes):
        return 0.0, 0.0
    enabled = True
    if enable_button_index >= 0:
        enabled = enable_button_index < len(buttons) and bool(buttons[enable_button_index])
    return shape_pair(axes[linear_axis], axes[angular_axis],
                      deadzone=deadzone, power=power, enabled=enabled)
