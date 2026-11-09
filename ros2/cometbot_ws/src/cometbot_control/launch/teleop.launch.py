"""Launch configured USB Joy input and rover Joy-to-Twist conversion."""
import os
from pathlib import Path
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    config_root = Path(os.environ.get("ROVER_CONFIG_DIR", "/opt/rover/config"))
    layout = os.environ.get("ROVER_JOY_LAYOUT", "single")
    device_ids = [int(value) for value in os.environ.get("ROVER_JOY_DEVICE_IDS", "0").split(",")]
    if layout == "pair" and len(device_ids) == 2:
        joy_nodes = [
            Node(package="joy", executable="joy_node", name="joy_left", output="screen",
                 parameters=[str(config_root / "joy.yaml"), {"device_id": device_ids[0]}],
                 remappings=[("joy", "/joy_left")]),
            Node(package="joy", executable="joy_node", name="joy_right", output="screen",
                 parameters=[str(config_root / "joy.yaml"), {"device_id": device_ids[1]}],
                 remappings=[("joy", "/joy_right")]),
        ]
        teleop_overrides = {
            "linear_joy_topic": "/joy_left",
            "angular_joy_topic": "/joy_right",
            "linear_axis": 1,
            "angular_axis": 0,
        }
    else:
        joy_nodes = [
            Node(package="joy", executable="joy_node", name="joy_node", output="screen",
                 parameters=[str(config_root / "joy.yaml"), {"device_id": device_ids[0]}]),
        ]
        teleop_overrides = {}
    return LaunchDescription([
        *joy_nodes,
        Node(package="cometbot_control", executable="teleop_publisher", name="teleop_publisher",
             output="screen", parameters=[str(config_root / "controller.yaml"), teleop_overrides]),
    ])
