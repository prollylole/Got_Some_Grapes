import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped
from nav_msgs.msg import Odometry, OccupancyGrid
from sensor_msgs.msg import LaserScan
from nav2_msgs.action import NavigateThroughPoses
from rclpy.qos import QoSProfile, ReliabilityPolicy

class NavNode(Node):
    def __init__(self):
        super().__init__('nav_node')
        self.get_logger().info('Navigation node started')
        
        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.amcl_pose_pub = self.create_publisher(PoseWithCovarianceStamped, '/amcl_pose', 10)
        
        # QoS Profile for Sensor Data
        qos_sensor = QoSProfile(depth=10)
        qos_sensor.reliability = ReliabilityPolicy.BEST_EFFORT
        
        # Subscriptions
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, qos_sensor)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, qos_sensor)
        self.map_sub = self.create_subscription(OccupancyGrid, '/map', self.map_callback, 10)
        
        # Action Server
        self._action_server = ActionServer(
            self,
            NavigateThroughPoses,
            '/navigate_through_poses',
            self.execute_callback)
            
    def scan_callback(self, msg):
        pass

    def odom_callback(self, msg):
        pass

    def map_callback(self, msg):
        pass

    def execute_callback(self, goal_handle):
        self.get_logger().info('Executing goal...')
        goal_handle.succeed()
        result = NavigateThroughPoses.Result()
        return result

def main(args=None):
    rclpy.init(args=args)
    node = NavNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
