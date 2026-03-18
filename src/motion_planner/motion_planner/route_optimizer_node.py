import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import String, Bool
from nav2_msgs.action import NavigateThroughPoses

class RouteOptimizerNode(Node):
    def __init__(self):
        super().__init__('route_optimizer_node')
        self.get_logger().info('Route Optimizer node started')
        
        # Publishers
        self.gui_status_pub = self.create_publisher(String, '/gui/status', 10)
        
        # Subscriptions
        self.store_sales_status_sub = self.create_subscription(Bool, '/store/sales_status', self.store_sales_status_callback, 10)
        self.customer_active_list_sub = self.create_subscription(String, '/customer/active_list', self.customer_active_list_callback, 10)
        self.inventory_status_sub = self.create_subscription(Bool, '/inventory_status', self.inventory_status_callback, 10)
        
        # Action Client
        self._action_client = ActionClient(self, NavigateThroughPoses, '/navigate_through_poses')
        
    def store_sales_status_callback(self, msg):
        pass

    def customer_active_list_callback(self, msg):
        pass

    def inventory_status_callback(self, msg):
        pass

    def send_goal(self, poses):
        goal_msg = NavigateThroughPoses.Goal()
        goal_msg.poses = poses
        self._action_client.wait_for_server()
        return self._action_client.send_goal_async(goal_msg)

def main(args=None):
    rclpy.init(args=args)
    node = RouteOptimizerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
