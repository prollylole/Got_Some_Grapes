import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped
from std_msgs.msg import String, Bool
from nav_msgs.msg import OccupancyGrid

class GuiNode(Node):
    def __init__(self):
        super().__init__('gui_node')
        self.get_logger().info('GUI node started')
        
        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.customer_active_list_pub = self.create_publisher(String, '/customer/active_list', 10)
        self.store_sales_status_pub = self.create_publisher(Bool, '/store/sales_status', 10)
        
        # Subscriptions
        self.gui_status_sub = self.create_subscription(String, '/gui/status', self.gui_status_callback, 10)
        self.map_sub = self.create_subscription(OccupancyGrid, '/map', self.map_callback, 10)
        self.inventory_status_sub = self.create_subscription(Bool, '/inventory_status', self.inventory_status_callback, 10)
        self.amcl_pose_sub = self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.amcl_pose_callback, 10)
        
    def gui_status_callback(self, msg):
        pass

    def map_callback(self, msg):
        pass

    def inventory_status_callback(self, msg):
        pass

    def amcl_pose_callback(self, msg):
        pass


def main(args=None):
    rclpy.init(args=args)
    node = GuiNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
