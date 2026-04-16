from rclpy.node import Node
from std_msgs.msg import Bool, String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from PyQt6.QtGui import QImage, QPixmap


class StaffNode(Node):
    """
    ROS2 node for staff GUI control.

    Handles publishing control commands, mode changes, and subscribing to
    robot status, out-of-stock items, and camera images.
    """

    def __init__(self, ui):
        super().__init__('staff_gui')

        self.ui = ui

        # Publishers
        self.control_pub = self.create_publisher(Bool, '/robot_run', 10)
        self.mode_pub = self.create_publisher(String, '/mode', 10)

        # Subscribers
        self.create_subscription(Bool, '/robot_run', self.robot_run_callback, 10)
        self.create_subscription(String, '/out_of_stock', self.stock_callback, 10)
        self.create_subscription(String, '/robot_status', self.status_callback, 10)

        self.bridge = CvBridge()

        self.create_subscription(
            Image,
            '/image',
            self.image_callback,
            10
        )

    def start_robot(self):
        """Publish command to start the robot."""
        msg = Bool()
        msg.data = True
        self.control_pub.publish(msg)
        self.update_run_buttons(True)

    def stop_robot(self):
        """Publish command to stop the robot."""
        msg = Bool()
        msg.data = False
        self.control_pub.publish(msg)
        self.update_run_buttons(False)

    def robot_run_callback(self, msg):
        """Callback for robot run status updates."""
        self.update_run_buttons(msg.data)

    def update_run_buttons(self, running: bool):
        """Update the GUI run buttons based on running state."""
        self.ui.start_btn.setEnabled(not running)
        self.ui.stop_btn.setEnabled(running)

    def stock_callback(self, item):
        """Add an item to the out-of-stock list."""
        if not item:
            return

        self.ui.add_stock_item_signal.emit(item)

    def status_callback(self, msg):
        """Callback for robot status updates."""
        self.ui.status.setText(f"Status: {msg.data}")

    def set_mode(self, mode):
        """Set the robot operation mode."""
        self.mode = mode

        msg = String()
        msg.data = mode
        self.mode_pub.publish(msg)

        if mode == "normal":
            self.ui.normal_btn.setChecked(True)
            self.ui.upsell_btn.setChecked(False)
        else:
            self.ui.normal_btn.setChecked(False)
            self.ui.upsell_btn.setChecked(True)

    def image_callback(self, msg):
        """Callback for camera image updates."""
        cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)

        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w

        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)

        self.ui.camera_feed.setPixmap(pixmap.scaled(
            self.ui.camera_feed.width(),
            self.ui.camera_feed.height()))