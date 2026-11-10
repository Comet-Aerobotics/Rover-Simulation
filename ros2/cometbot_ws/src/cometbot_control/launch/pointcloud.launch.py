"""Convert the OAK depth stream to a point cloud with its matching CameraInfo."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package="depth_image_proc",
            executable="point_cloud_xyz_node",
            name="oak_depth_point_cloud",
            output="screen",
            parameters=[{"use_sim_time": True}],
            remappings=[
                ("image_rect", "/oak_d/depth"),
                ("/camera_info", "/oak_d/camera_info"),
                ("points", "/oak_d/points"),
            ],
        ),
    ])
