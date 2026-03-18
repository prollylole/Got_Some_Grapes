import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist

class ObstacleStop(Node):

    def __init__(self):
        super().__init__('obstacle_stop')

        self.publisher = self.create_publisher(Twist, 'cmd_vel', 10)

        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.BEST_EFFORT

        self.scan_sub = self.create_subscription(
        LaserScan,
        '/scan',
        self.scan_callback,
        qos)

        self.get_logger().info("Obstacle Stop Started")

    def scan_callback(self, msg):

        twist = Twist()

        front = msg.ranges[0]

        if front < 1:
            twist.linear.x = 0.0
            self.get_logger().info("STOP")
        else:
            twist.linear.x = 0.1
            self.get_logger().info("MOVE")

        self.publisher.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleStop()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()