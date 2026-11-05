"""ROS 2 Joy subscriber and Twist publisher for the rover."""
import time
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import Joy
from cometbot_control.mapping import joy_to_pair

class TeleopPublisher(Node):
    def __init__(self):
        super().__init__("teleop_publisher")
        defaults = {"joy_topic": "/joy", "cmd_vel_topic": "/cmd_vel",
                    "cmd_vel_pub_frequency": 20.0, "linear_axis": 1,
                    "angular_axis": 3, "deadzone": 0.1,
                    "joystick_power": 3, "enable_button_index": -1}
        for name, value in defaults.items(): self.declare_parameter(name, value)
        self._joy_topic = self.get_parameter("joy_topic").value
        self._cmd_vel_topic = self.get_parameter("cmd_vel_topic").value
        self._linear_axis = self.get_parameter("linear_axis").value
        self._angular_axis = self.get_parameter("angular_axis").value
        self._deadzone = self.get_parameter("deadzone").value
        self._power = self.get_parameter("joystick_power").value
        self._enable_button_index = self.get_parameter("enable_button_index").value
        frequency = float(self.get_parameter("cmd_vel_pub_frequency").value)
        if frequency <= 0: raise ValueError("cmd_vel_pub_frequency must be greater than zero")
        self._axes, self._buttons, self._last_joy_time = [], [], 0.0
        self.create_subscription(Joy, self._joy_topic, self._joy_callback, 10)
        self._publisher = self.create_publisher(Twist, self._cmd_vel_topic, 10)
        self.create_timer(1.0 / frequency, self._publish_twist)
        self.get_logger().info(f"Publishing {self._cmd_vel_topic} from {self._joy_topic} at {frequency:g} Hz")

    def _joy_callback(self, msg: Joy) -> None:
        self._axes, self._buttons = list(msg.axes), list(msg.buttons)
        self._last_joy_time = time.monotonic()

    def _publish_twist(self) -> None:
        fresh = time.monotonic() - self._last_joy_time < 0.5
        linear, angular = joy_to_pair(self._axes if fresh else [], self._buttons,
            linear_axis=self._linear_axis, angular_axis=self._angular_axis,
            deadzone=self._deadzone, power=self._power,
            enable_button_index=self._enable_button_index)
        msg = Twist()
        msg.linear.x, msg.angular.z = linear, angular
        self._publisher.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = TeleopPublisher()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__": main()
