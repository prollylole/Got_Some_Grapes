import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry, OccupancyGrid
from sensor_msgs.msg import LaserScan
from rclpy.qos import QoSProfile, ReliabilityPolicy

class SlamNode(Node):
    def __init__(self):
        super().__init__('slam_node')
        self.get_logger().info('SLAM node started')
        
        # Publishers
        self.map_pub = self.create_publisher(OccupancyGrid, '/map', 10)
        
        # QoS Profile for Sensor Data
        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.BEST_EFFORT
        
        # Subscriptions
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, qos)
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, qos)
        
    def odom_callback(self, msg):
        pass

    def scan_callback(self, msg):
        pass

def main(args=None):
    rclpy.init(args=args)
    node = SlamNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()