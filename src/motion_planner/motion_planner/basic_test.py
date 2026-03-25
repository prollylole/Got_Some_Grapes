import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, String

class ObstacleStop(Node):

    def __init__(self):
        super().__init__('obstacle_stop')

        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.status_pub = self.create_publisher(String, '/robot_status', 10)

        self.running = False

        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.BEST_EFFORT

        self.create_subscription(LaserScan, '/scan', self.scan_callback, qos)
        self.create_subscription(Bool, '/robot_run', self.control_callback, 10)

        self.get_logger().info("Obstacle Stop Started")

    def scan_callback(self, msg):
        twist = Twist()

        if not self.running:
            self.publish_status("STOPPED")
            self.cmd_pub.publish(twist)
            return

        distance = self.get_front_distance(msg)

        if distance is None:
            return

        if distance < 0.15:
            twist.linear.x = 0.0
            self.publish_status("OBSTACLE DETECTED")
        else:
            twist.linear.x = 0.1
            self.publish_status("RUNNING")

        self.cmd_pub.publish(twist)

    def get_front_distance(self, msg):
        front_ranges = msg.ranges[0:20] + msg.ranges[-20:]
        valid = [r for r in front_ranges if 0.05 < r < 3.5]

        if not valid:
            return None

        return min(valid)

    def control_callback(self, msg):
        self.running = msg.data
        self.publish_status("RUNNING" if self.running else "STOPPED")

    def publish_status(self, text):
        msg = String()
        msg.data = text
        self.status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleStop()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()