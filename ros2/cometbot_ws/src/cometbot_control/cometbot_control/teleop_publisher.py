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
                    "joystick_power": 3, "enable_button_index": -1,
                    "linear_joy_topic": "", "angular_joy_topic": ""}
        for name, value in defaults.items(): self.declare_parameter(name, value)
        self._joy_topic = self.get_parameter("joy_topic").value
        self._cmd_vel_topic = self.get_parameter("cmd_vel_topic").value
        self._linear_axis = self.get_parameter("linear_axis").value
        self._angular_axis = self.get_parameter("angular_axis").value
        self._deadzone = self.get_parameter("deadzone").value
        self._power = self.get_parameter("joystick_power").value
        self._enable_button_index = self.get_parameter("enable_button_index").value
        self._linear_joy_topic = self.get_parameter("linear_joy_topic").value
        self._angular_joy_topic = self.get_parameter("angular_joy_topic").value
        frequency = float(self.get_parameter("cmd_vel_pub_frequency").value)
        if frequency <= 0: raise ValueError("cmd_vel_pub_frequency must be greater than zero")
        self._axes, self._buttons, self._last_joy_time = [], [], 0.0
        self._linear_axes, self._angular_axes = [], []
        self._linear_joy_time = self._angular_joy_time = 0.0
        self._paired_sources = bool(self._linear_joy_topic and self._angular_joy_topic)
        if self._paired_sources:
            self.create_subscription(Joy, self._linear_joy_topic, self._linear_joy_callback, 10)
            self.create_subscription(Joy, self._angular_joy_topic, self._angular_joy_callback, 10)
        else:
            self.create_subscription(Joy, self._joy_topic, self._joy_callback, 10)
        self._publisher = self.create_publisher(Twist, self._cmd_vel_topic, 10)
        self.create_timer(1.0 / frequency, self._publish_twist)
        sources = (f"{self._linear_joy_topic} + {self._angular_joy_topic}" if self._paired_sources
                   else self._joy_topic)
        self.get_logger().info(f"Publishing {self._cmd_vel_topic} from {sources} at {frequency:g} Hz")

    def _joy_callback(self, msg: Joy) -> None:
        self._axes, self._buttons = list(msg.axes), list(msg.buttons)
        self._last_joy_time = time.monotonic()

    def _linear_joy_callback(self, msg: Joy) -> None:
        self._linear_axes = list(msg.axes)
        self._linear_joy_time = time.monotonic()

    def _angular_joy_callback(self, msg: Joy) -> None:
        self._angular_axes = list(msg.axes)
        self._angular_joy_time = time.monotonic()

    def _publish_twist(self) -> None:
        now = time.monotonic()
        if self._paired_sources:
            fresh = now - self._linear_joy_time < 0.5 and now - self._angular_joy_time < 0.5
            linear_value = (self._linear_axes[self._linear_axis]
                            if fresh and self._linear_axis < len(self._linear_axes) else 0.0)
            angular_value = (self._angular_axes[self._angular_axis]
                             if fresh and self._angular_axis < len(self._angular_axes) else 0.0)
            linear, angular = joy_to_pair([linear_value, angular_value], [],
                linear_axis=0, angular_axis=1, deadzone=self._deadzone,
                power=self._power, enable_button_index=-1)
        else:
            fresh = now - self._last_joy_time < 0.5
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
