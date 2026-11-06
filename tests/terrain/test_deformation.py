import numpy as np
import pytest

from terrain.deformation import RutField, WheelSample
from terrain.generate import apply_wheel_trace
from terrain.deformation import SoilParameters


def wheel(*, load=135.0, speed=0.2, spin=0.2 / 0.098, height=0.098):
    return WheelSample(1.0, 1.0, height, 0.0, speed, spin, load)


def test_wheel_makes_bounded_rut_and_side_berm():
    field = RutField(np.zeros((201, 201), dtype=np.float32), 0.01)
    region = field.stamp(wheel(), 0.4)
    assert region is not None
    assert -0.018 < field.height[100, 100] < -0.005
    assert np.max(field.height[region.row_min:region.row_max + 1,
                               region.col_min:region.col_max + 1]) > 0
    assert field.height[10, 10] == 0
    for _ in range(100):
        field.stamp(wheel(), 0.2)
    assert field.height.min() >= -field.parameters.maximum_sinkage_m - 1e-5
    assert field.height.max() <= field.parameters.maximum_berm_m + 1e-5


def test_airborne_wheel_and_zero_load_leave_ground_unchanged():
    field = RutField(np.zeros((201, 201), dtype=np.float32), 0.01)
    assert field.stamp(wheel(height=0.3), 0.3) is None
    assert field.stamp(wheel(load=0), 0.3) is None
    assert not np.any(field.height)


def test_slip_and_load_increase_sinkage():
    baseline = np.zeros((201, 201), dtype=np.float32)
    low = RutField(baseline, 0.01)
    high = RutField(baseline, 0.01)
    low.stamp(wheel(load=80, spin=0.2 / 0.098), 0.2)
    high.stamp(wheel(load=160, spin=0.8 / 0.098), 0.2)
    assert high.height[100, 100] < low.height[100, 100]


def test_long_step_interpolates_without_gaps():
    field = RutField(np.zeros((201, 201), dtype=np.float32), 0.01)
    sample = WheelSample(1.2, 1.0, 0.098, 0.0, 0.4, 0.4 / 0.098, 135)
    field.stamp(sample, 0.5, previous_xy_m=(0.8, 1.0))
    assert np.all(field.height[100, 82:119] < 0)


def test_offline_wheel_trace_uses_the_runtime_stamp(tmp_path):
    trace = tmp_path / "wheels.csv"
    trace.write_text(
        "time_s,wheel,x_m,y_m,center_height_m,heading_rad,ground_speed_m_s,spin_rad_s,normal_load_n\n"
        "0,left,0.8,1,0.098,0,0.4,4.081633,135\n"
        "0.5,left,1.2,1,0.098,0,0.4,4.081633,135\n",
        encoding="utf-8")
    dem, count = apply_wheel_trace(np.zeros((201, 201), dtype=np.float32),
                                   0.01, trace, SoilParameters())
    assert count == 2
    assert np.all(dem[100, 82:119] < 0)
    assert np.max(dem) > 0


def test_offline_wheel_trace_rejects_nonincreasing_time(tmp_path):
    trace = tmp_path / "wheels.csv"
    trace.write_text(
        "time_s,wheel,x_m,y_m,center_height_m,heading_rad,ground_speed_m_s,spin_rad_s,normal_load_n\n"
        "0,left,1,1,0.098,0,0,0,135\n"
        "0,left,1,1,0.098,0,0,0,135\n",
        encoding="utf-8")
    with pytest.raises(ValueError, match="times must increase"):
        apply_wheel_trace(np.zeros((201, 201), dtype=np.float32),
                          0.01, trace, SoilParameters())
