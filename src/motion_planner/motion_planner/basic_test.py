import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, String

class ObstacleStop(Node):

    def __init__(self):
        super().__init__('obstacle_stop')

        self.publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        self.status_pub = self.create_publisher(String, '/robot_status', 10)

        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.BEST_EFFORT

        self.scan_sub = self.create_subscription(
        LaserScan,
        '/scan',
        self.scan_callback,
        qos)

        self.get_logger().info("Obstacle Stop Started")

        self.running = False

        self.control_sub = self.create_subscription(
            Bool,
            '/robot_run',
            self.control_callback,
            10
        )


    def scan_callback(self, msg):

        twist = Twist()
        status = String()

        if not self.running:
            twist.linear.x = 0.0
            status.data = "STOPPED"
            self.status_pub.publish(status)
            self.publisher.publish(twist)
            return

        front_ranges = msg.ranges[0:20] + msg.ranges[-20:]

        # FILTER
        valid = [r for r in front_ranges if 0.05 < r < 3.5]

        if len(valid) == 0:
            return

        front = min(valid)

        if front < 0.15:
            twist.linear.x = 0.0
            status.data = "OBSTACLE DETECTED"
            self.get_logger().info("STOP - Obstacle")
        else:
            twist.linear.x = 0.1
            status.data = "RUNNING"
            self.get_logger().info("MOVE")

        self.publisher.publish(twist)
        self.status_pub.publish(status)

    def control_callback(self, msg):

        self.running = msg.data
        status = String()

        if self.running:
            status.data = "RUNNING"
            self.get_logger().info("Robot STARTED")
        else:
            status.data = "STOPPED"
            self.get_logger().info("Robot STOPPED")

        self.status_pub.publish(status)


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleStop()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()