"""Launch configured USB Joy input and rover Joy-to-Twist conversion."""
import os
from pathlib import Path
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    config_root = Path(os.environ.get("ROVER_CONFIG_DIR", "/opt/rover/config"))
    device_id = int(os.environ.get("ROVER_JOY_DEVICE_ID", "0"))
    return LaunchDescription([
        Node(package="joy", executable="joy_node", name="joy_node", output="screen",
             parameters=[str(config_root / "joy.yaml"), {"device_id": device_id}]),
        Node(package="cometbot_control", executable="teleop_publisher", name="teleop_publisher",
             output="screen", parameters=[str(config_root / "controller.yaml")]),
    ])
