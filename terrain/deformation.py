"""Bounded, calibratable wheel-rut model for the LunaLab height grid.

Coordinates are in the terrain mesh's local XY frame. The model keeps the
original DEM as its undeformed reference and accumulates compaction plus a
small side berm. It does not pretend to resolve individual sand grains.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class SoilParameters:
    wheel_radius_m: float = 0.098
    wheel_width_m: float = 0.080
    contact_length_m: float = 0.120
    reference_load_n: float = 135.0
    reference_sinkage_m: float = 0.006
    pressure_exponent: float = 1.1
    maximum_sinkage_m: float = 0.012
    compaction_time_s: float = 0.30
    slip_sinkage_gain: float = 0.30
    displaced_volume_fraction: float = 0.15
    maximum_berm_m: float = 0.003
    contact_tolerance_m: float = 0.025
    maximum_stamp_spacing_m: float = 0.025


@dataclass(frozen=True)
class WheelSample:
    x_m: float
    y_m: float
    center_height_m: float
    heading_rad: float
    ground_speed_m_s: float
    spin_rad_s: float
    normal_load_n: float


@dataclass(frozen=True)
class DirtyRegion:
    row_min: int
    row_max: int  # inclusive
    col_min: int
    col_max: int  # inclusive

    def merge(self, other: "DirtyRegion") -> "DirtyRegion":
        return DirtyRegion(
            min(self.row_min, other.row_min), max(self.row_max, other.row_max),
            min(self.col_min, other.col_min), max(self.col_max, other.col_max),
        )


class RutField:
    """A height grid whose wheel stamps can be mirrored to render and collision meshes."""

    def __init__(self, baseline: np.ndarray, resolution_m: float,
                 parameters: SoilParameters = SoilParameters()):
        if baseline.ndim != 2 or min(baseline.shape) < 3:
            raise ValueError("baseline must be a two-dimensional height grid")
        if resolution_m <= 0:
            raise ValueError("resolution_m must be positive")
        self.baseline = np.asarray(baseline, dtype=np.float32).copy()
        self.height = self.baseline.copy()
        self.resolution_m = float(resolution_m)
        self.parameters = parameters

    def height_at(self, x_m: float, y_m: float) -> float | None:
        col = int(round(x_m / self.resolution_m))
        row = int(round(y_m / self.resolution_m))
        if 0 <= row < self.height.shape[0] and 0 <= col < self.height.shape[1]:
            return float(self.height[row, col])
        return None

    def stamp(self, wheel: WheelSample, dt_s: float,
              previous_xy_m: tuple[float, float] | None = None) -> DirtyRegion | None:
        """Imprint one wheel trajectory segment and return the changed grid bounds.

        The normal load can come from a contact sensor. Callers without that
        signal may use a documented mass/4 estimate, but must still reject
        airborne wheels before calling this method.
        """
        if dt_s <= 0 or wheel.normal_load_n <= 0:
            return None
        surface = self.height_at(wheel.x_m, wheel.y_m)
        p = self.parameters
        if surface is None or wheel.center_height_m > surface + p.wheel_radius_m + p.contact_tolerance_m:
            return None
        if previous_xy_m is None:
            centers = [(wheel.x_m, wheel.y_m)]
        else:
            distance = math.hypot(wheel.x_m - previous_xy_m[0], wheel.y_m - previous_xy_m[1])
            count = max(1, math.ceil(distance / p.maximum_stamp_spacing_m))
            centers = [
                (previous_xy_m[0] + (wheel.x_m - previous_xy_m[0]) * i / count,
                 previous_xy_m[1] + (wheel.y_m - previous_xy_m[1]) * i / count)
                for i in range(1, count + 1)
            ]
        wheel_surface_speed = abs(wheel.spin_rad_s * p.wheel_radius_m)
        slip = min(1.0, abs(wheel_surface_speed - abs(wheel.ground_speed_m_s)) /
                   max(wheel_surface_speed, abs(wheel.ground_speed_m_s), 0.05))
        target_depth = min(
            p.maximum_sinkage_m,
            p.reference_sinkage_m *
            (wheel.normal_load_n / p.reference_load_n) ** (1.0 / p.pressure_exponent) *
            (1.0 + p.slip_sinkage_gain * slip),
        )
        dirty = None
        for x_m, y_m in centers:
            patch = self._stamp_at(x_m, y_m, wheel.heading_rad,
                                   target_depth, dt_s / len(centers))
            if patch is not None:
                dirty = patch if dirty is None else dirty.merge(patch)
        return dirty

    def _stamp_at(self, x_m: float, y_m: float, heading: float,
                  target_depth: float, dt_s: float) -> DirtyRegion | None:
        p = self.parameters
        longitudinal_radius = p.contact_length_m * 0.75
        lateral_radius = p.wheel_width_m * 0.5
        berm_center = lateral_radius * 1.45
        berm_width = max(self.resolution_m, lateral_radius * 0.45)
        extent = max(longitudinal_radius, berm_center + 2.5 * berm_width)
        col0 = max(0, math.floor((x_m - extent) / self.resolution_m))
        col1 = min(self.height.shape[1] - 1, math.ceil((x_m + extent) / self.resolution_m))
        row0 = max(0, math.floor((y_m - extent) / self.resolution_m))
        row1 = min(self.height.shape[0] - 1, math.ceil((y_m + extent) / self.resolution_m))
        if col0 > col1 or row0 > row1:
            return None
        yy, xx = np.mgrid[row0:row1 + 1, col0:col1 + 1]
        dx = xx * self.resolution_m - x_m
        dy = yy * self.resolution_m - y_m
        c, s = math.cos(heading), math.sin(heading)
        longitudinal = c * dx + s * dy
        lateral = -s * dx + c * dy
        along = np.clip(1.0 - (longitudinal / longitudinal_radius) ** 2, 0.0, 1.0) ** 2
        across = np.clip(1.0 - (lateral / lateral_radius) ** 2, 0.0, 1.0) ** 2
        footprint = along * across
        if not np.any(footprint):
            return None
        h = self.height[row0:row1 + 1, col0:col1 + 1]
        base = self.baseline[row0:row1 + 1, col0:col1 + 1]
        current_depth = np.maximum(base - h, 0.0)
        response = 1.0 - math.exp(-dt_s / p.compaction_time_s)
        depression = np.maximum(target_depth - current_depth, 0.0) * footprint * response
        if not np.any(depression > 1e-7):
            return None
        h -= depression
        berm = along * np.exp(-0.5 * ((np.abs(lateral) - berm_center) / berm_width) ** 2)
        berm *= (np.abs(lateral) >= lateral_radius)
        if berm.sum() > 0:
            addition = depression.sum() * p.displaced_volume_fraction * berm / berm.sum()
            np.minimum(h + addition, base + p.maximum_berm_m, out=h)
        return DirtyRegion(row0, row1, col0, col1)
