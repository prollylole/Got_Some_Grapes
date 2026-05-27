import cv2
from rclpy.node import Node
from std_msgs.msg import Bool, String, Float64
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge
from PyQt6.QtGui import QImage, QPixmap
import numpy as np

from nav_msgs.msg import OccupancyGrid, Path
from geometry_msgs.msg import PoseStamped
from PyQt6.QtGui import QImage, QPixmap

from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped

class StaffNode(Node):
    def __init__(self, ui):
        super().__init__('staff_gui')

        self.ui = ui
        self.bridge = CvBridge()

        self.map_data = None
        self.path_data = None
        self.robot_pose = None
        self.goal_pose = None

        # Publishers
        self.control_pub = self.create_publisher(Bool, '/robot_run', 10)
        self.mode_pub = self.create_publisher(String, '/mode', 10)
        self.upsell_pub = self.create_publisher(String, '/upsell_product', 10)

        # Subscribers
        self.create_subscription(Bool, '/robot_run', self.robot_run_callback, 10)
        self.create_subscription(String, '/out_of_stock', self.stock_callback, 10)
        self.create_subscription(String, '/robot_status', self.status_callback, 10)
        self.create_subscription(CompressedImage, '/camera/image_raw/compressed', self.image_callback, 10)

        # add telemtry
        self.create_subscription(Float64, '/mission_progress', self.progress_callback, 10)
        self.create_subscription(String, '/mission_distance', self.distance_callback, 10)
        self.create_subscription(String, '/active_route', self.route_callback, 10)

        self.create_subscription(OccupancyGrid, '/map', self.map_callback, 10)
        self.create_subscription(Path, '/plan', self.path_callback, 10)
        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.robot_pose_callback, 10)
        self.create_subscription(PoseStamped, '/goal_pose', self.goal_callback, 10)

    # ---------------- CONTROL ----------------
    def start_robot(self):
        msg = Bool()
        msg.data = True
        self.control_pub.publish(msg)
        self.ui.update_run_buttons(True)

    def stop_robot(self):
        msg = Bool()
        msg.data = False
        self.control_pub.publish(msg)
        self.ui.update_run_buttons(False)

    def robot_run_callback(self, msg):
        self.ui.update_run_buttons(msg.data)

    # ---------------- STATUS ----------------
    def status_callback(self, msg):
        self.ui.status.setText(f"Status: {msg.data}")
        if msg.data == "Mission completed! Heading to the checkout now.":
            self.ui.reset_upsell_signal.emit()

    # ---------------- TELEMETRY ----------------
    def progress_callback(self, msg):
        self.ui.update_progress_signal.emit(int(msg.data))
        
    def distance_callback(self, msg):
        self.ui.update_distance_signal.emit(f"Distance Travelled: {msg.data}")
        
    def route_callback(self, msg):
        self.ui.update_route_signal.emit(f"Active Route: {msg.data}")

    # ---------------- MODE ----------------
    def set_mode(self, mode):
        msg = String()
        msg.data = mode
        self.mode_pub.publish(msg)

        # Update UI
        self.ui.update_mode_ui(mode)

        if mode == "normal":
            self.ui.normal_btn.setChecked(True)
            self.ui.upsell_btn.setChecked(False)
        else:
            self.ui.normal_btn.setChecked(False)
            self.ui.upsell_btn.setChecked(True)

    # ---------------- OUT OF STOCK ----------------
    def stock_callback(self, msg):
        item = msg.data.strip()

        if item:
            self.ui.add_stock_item_signal.emit(item)

    # ---------------- CAMERA ----------------
    def image_callback(self, msg):
        np_arr = np.frombuffer(msg.data, np.uint8)
        cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)

        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w

        qt_image = QImage(
            rgb_image.data,
            w,
            h,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )

        pixmap = QPixmap.fromImage(qt_image)

        self.ui.camera_feed.setPixmap(pixmap.scaled(
            self.ui.camera_feed.width(),
            self.ui.camera_feed.height()
        ))

    def publish_upsell_product(self, product):
        if product == "Please select Upsell Item":
            return  # Do not publish if no valid product is selected
        
        msg = String()
        msg.data = product
        self.upsell_pub.publish(msg)

    def robot_pose_callback(self, msg):
        self.robot_pose = msg
        self.draw_map()

    def goal_callback(self, msg):
        self.goal_pose = msg
        self.draw_map()

    def map_callback(self, msg):
        self.map_data = msg
        self.draw_map()

    def path_callback(self, msg):
        self.path_data = msg
        self.draw_map()

    def world_to_pixel(self, x, y, origin, resolution, width, height):
        px = int(round((x - origin.x) / resolution))
        py = int(round((y - origin.y) / resolution))

        return px, py

    def draw_map(self):
        if self.map_data is None:
            return

        width = self.map_data.info.width
        height = self.map_data.info.height

        data = np.array(self.map_data.data, dtype=np.int8).reshape((height, width))

        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[data == -1] = [100, 100, 100]
        img[data == 0] = [255, 255, 255]
        img[data > 50] = [0, 0, 0]

        resolution = self.map_data.info.resolution
        origin = self.map_data.info.origin.position

        if self.path_data is not None and self.path_data.poses:
            path_points = []
            for pose_stamped in self.path_data.poses:
                x = pose_stamped.pose.position.x
                y = pose_stamped.pose.position.y
                px, py = self.world_to_pixel(x, y, origin, resolution, width, height)

                if 0 <= px < width and 0 <= py < height:
                    path_points.append((px, py))

            if len(path_points) > 1:
                cv2.polylines(img, [np.array(path_points, dtype=np.int32)], False, (0, 0, 255), 2)
            else:
                for point in path_points:
                    cv2.circle(img, point, 2, (0, 0, 255), -1)

        if self.robot_pose is not None:
            x = self.robot_pose.pose.pose.position.x
            y = self.robot_pose.pose.pose.position.y
            px, py = self.world_to_pixel(x, y, origin, resolution, width, height)
            if 0 <= px < width and 0 <= py < height:
                cv2.circle(img, (px, py), 3, (0, 255, 0), -1)
                cv2.circle(img, (px, py), 5, (255, 255, 255), 1)

        if self.goal_pose is not None:
            x = self.goal_pose.pose.position.x
            y = self.goal_pose.pose.position.y
            px, py = self.world_to_pixel(x, y, origin, resolution, width, height)
            if 0 <= px < width and 0 <= py < height:
                cv2.circle(img, (px, py), 6, (255, 0, 0), -1)
                cv2.circle(img, (px, py), 8, (255, 255, 255), 1)

        # rotate 90 degrees
        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        img = cv2.flip(img, 1)
        # zoom out slightly by drawing the resized map on a smaller centered canvas
        display_w, display_h = 420, 200
        zoom = 1
        small_w = int(display_w * zoom)
        small_h = int(display_h * zoom)
        small = cv2.resize(img, (small_w, small_h), interpolation=cv2.INTER_NEAREST)

        canvas = np.zeros((display_h, display_w, 3), dtype=np.uint8)
        x0 = (display_w - small_w) // 2
        y0 = (display_h - small_h) // 2
        canvas[y0:y0 + small_h, x0:x0 + small_w] = small

        img = canvas

        h, w, ch = img.shape
        bytes_per_line = ch * w
        qt_img = QImage(img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.ui.map_label.setPixmap(QPixmap.fromImage(qt_img))