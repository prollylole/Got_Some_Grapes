import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image, CameraInfo, LaserScan
from rclpy.qos import QoSProfile, ReliabilityPolicy

class ArucoNode(Node):
    def __init__(self):
        super().__init__('aruco_node')
        self.get_logger().info('ArUco node started')
        
        # Publishers
        self.item_detected_pub = self.create_publisher(Bool, '/item_detected', 10)
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # QoS Profile for Sensor Data
        qos_sensor = QoSProfile(depth=10)
        qos_sensor.reliability = ReliabilityPolicy.BEST_EFFORT
        
        # Subscriptions
        self.image_sub = self.create_subscription(Image, '/camera/image_raw', self.image_callback, qos_sensor)
        self.camera_info_sub = self.create_subscription(CameraInfo, '/camera/camera_info', self.camera_info_callback, qos_sensor)
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_callback, qos_sensor)
        
    def image_callback(self, msg):
        pass

    def camera_info_callback(self, msg):
        pass

    def scan_callback(self, msg):
        pass

def main(args=None):
    rclpy.init(args=args)
    node = ArucoNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
