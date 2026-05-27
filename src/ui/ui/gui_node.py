import math
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped

import numpy as np
import cv2

from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, String, Float64

from PyQt6.QtWidgets import QLabel

from nav_msgs.msg import OccupancyGrid, Path
from geometry_msgs.msg import PoseStamped
from PyQt6.QtGui import QImage, QPixmap


class GuiNode(Node):
    def __init__(self, ui):
        super().__init__('robot_gui')

        self.ui = ui

        # Publishers
        self.control_pub = self.create_publisher(Bool, '/robot_run', 10)
        self.object_pub = self.create_publisher(String, '/selected_objects', 10)
        self.continue_pub = self.create_publisher(Bool, '/continue', 10)
        self.mode_pub = self.create_publisher(String, '/mode', 10)

        self.mode = "normal"
        self.continue_state = False
        self.ui.continue_btn.setEnabled(False) 

        self.map_data = None
        self.path_data = None
        self.robot_pose = None
        self.goal_pose = None

        # State
        self.selected_objects = []

        # QoS
        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.BEST_EFFORT

        # Subscribers
        self.create_subscription(Bool, '/robot_run', self.robot_run_callback, 10)
        self.create_subscription(LaserScan, '/scan', self.scan_callback, qos)
        self.create_subscription(String, '/robot_status', self.status_callback, 10)
        self.create_subscription(Bool, '/continue', self.continue_callback, 10)
        self.create_subscription(Bool, '/item_availability', self.availability_callback,10)

        # adding telemetry data
        self.create_subscription(Float64, '/mission_progress', self.progress_callback, 10)
        self.create_subscription(String, '/mission_distance', self.distance_callback, 10)
        self.create_subscription(String, '/active_route', self.route_callback, 10)

        self.create_subscription(OccupancyGrid, '/map', self.map_callback, 10)
        self.create_subscription(Path, '/plan', self.path_callback, 10)
        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.robot_pose_callback, 10)
        self.create_subscription(PoseStamped, '/goal_pose', self.goal_callback, 10)

    # ---------------- CONTROL ----------------
    def start_robot(self):
        self.publish_control(True)
        self.update_run_buttons(True)

    def stop_robot(self):
        self.publish_control(False)
        self.update_run_buttons(False)

    def robot_run_callback(self, msg):
        self.update_run_buttons(msg.data)

    def update_run_buttons(self, running: bool):
        self.ui.start_btn.setEnabled(not running)
        self.ui.stop_btn.setEnabled(running)

    def publish_control(self, state):
        msg = Bool()
        msg.data = state
        self.control_pub.publish(msg)

    # ---------------- STATUS ----------------
    def status_callback(self, msg):
        self.ui.status.setText(f"Status: {msg.data}")
        if "Mission complete" in msg.data:
            self.clear_cart()

    # ---------------- TELEMETRY ----------------
    def progress_callback(self, msg):
        self.ui.update_progress_signal.emit(int(msg.data))
        
    def distance_callback(self, msg):
        self.ui.update_distance_signal.emit(f"Distance Travelled: {msg.data}")
        
    def route_callback(self, msg):
        self.ui.update_route_signal.emit(f"Active Route: {msg.data}")

    # ---------------- SCAN PROCESSING ----------------
    def scan_callback(self, msg):
        closest, angle = self.get_closest_obstacle(msg)

        if closest is None:
            return

        self.update_lidar_display(closest, angle)

    def get_closest_obstacle(self, msg):
        valid = [r for r in msg.ranges if 0.05 < r < 10.0]

        if not valid:
            return None, None

        closest = min(valid)
        index = msg.ranges.index(closest)

        angle = math.degrees(msg.angle_min + index * msg.angle_increment)

        if angle < 0:
            angle += 360

        return closest, angle

    def update_lidar_display(self, distance, angle):
        self.ui.lidar.setText(f"Closest Obstacle Distance: {distance:.2f} m")

        if distance > 1:
            self.ui.direction.setText("No obstacle")
            return

        direction = self.get_direction(angle)
        self.ui.direction.setText(f"Closest Obstacle Direction: {direction}")

    def get_direction(self, angle):
        if 0 <= angle <= 45 or 315 < angle <= 360:
            return "FRONT"
        elif 45 < angle <= 135:
            return "LEFT"
        elif 135 < angle <= 225:
            return "BACK"
        elif 225 < angle <= 315:
            return "RIGHT"
        return "UNKNOWN"

    # ---------------- OBJECT SELECTION ----------------
    def choose_object(self, obj_name, button):
        # ensure we don't add the exact same object twice
        if obj_name in self.selected_objects:
            return
        
        self.selected_objects.append(obj_name)
        self.update_cart_display()

        msg = String()
        msg.data = ",".join(self.selected_objects)
        self.object_pub.publish(msg)

        button.setText(f"{obj_name} ✓")
        button.setStyleSheet("background-color: gray;")

    def remove_object(self, target_obj, button):
        if target_obj not in self.selected_objects:
            return

        self.selected_objects.remove(target_obj)
        self.update_cart_display()

        msg = String()
        msg.data = ",".join(self.selected_objects)
        self.object_pub.publish(msg)

        obj_name = target_obj.split(':')[0]
        button.setText(obj_name.capitalize())
        button.setStyleSheet("background-color: #3a86ff;")

    def update_cart_display(self):
        while self.ui.cart_items_layout.count():
            item = self.ui.cart_items_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.selected_objects:
            label = QLabel("(empty)")
            label.setStyleSheet(
                "font-size:15px; background: none; border: none; "
                "padding: 0; margin: 0;"
            )
            self.ui.cart_items_layout.addWidget(label)
            return

        for obj in self.selected_objects:
            display_name = obj.capitalize()
                
            label = QLabel(display_name)
            label.setStyleSheet(
                "font-size:15px; background: none; border: none; "
                "padding: 0; margin: 0;"
            )
            self.ui.cart_items_layout.addWidget(label)

    def clear_cart(self):
        self.selected_objects.clear()
        self.update_cart_display()

        buttons = [
            ("apple", self.ui.obj1),
            ("bottle", self.ui.obj2),
            ("cup", self.ui.obj3),
            ("book", self.ui.obj4),
            ("banana", self.ui.obj5),
            ("blueberry", self.ui.obj6)
        ]

        for name, btn in buttons:
            btn.setText(name.capitalize())
            btn.setStyleSheet("background-color: #3a86ff;")

    # ---------------- CONTINUE BUTTON ----------------
    def continue_callback(self, msg):
        self.continue_state = msg.data

        if self.continue_state:   # True = busy
            self.ui.continue_btn.setEnabled(False)
        else:                     # False = ready
            self.ui.continue_btn.setEnabled(True)

    def continue_robot(self):
        self.ui.availability.setText("Item Status: Please wait...")
        if self.continue_state:
            return

        msg = Bool()
        msg.data = True
        self.continue_pub.publish(msg)

        # disable immediately
        self.continue_state = True
        self.ui.continue_btn.setEnabled(False)

    def publish_mode(self, mode):
        self.mode = mode

        msg = String()
        msg.data = mode
        self.mode_pub.publish(msg)

        self.get_logger().info(f"Mode: {mode}")

    def availability_callback(self, msg):

        if msg.data == True:
            self.ui.availability.setText("Item Status: Item available")

        elif msg.data == False:
            self.ui.availability.setText("Item Status: Not available")

        else:
            self.ui.availability.setText("Item Status: Please wait...")

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
                cv2.circle(img, (px, py), 3, (255, 0, 0), -1)
                cv2.circle(img, (px, py), 5, (255, 255, 255), 1)

        # rotate 90 degrees
        # img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
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