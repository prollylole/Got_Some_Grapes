import math
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, String

from PyQt6.QtWidgets import QLabel


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
        self.ui.lidar.setText(f"Closest Distance: {distance:.2f} m")

        if distance > 1:
            self.ui.direction.setText("No obstacle")
            return

        direction = self.get_direction(angle)
        self.ui.direction.setText(f"Obstacle Direction: {direction}")

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
        if obj_name in self.selected_objects:
            return

        self.selected_objects.append(obj_name)
        self.update_cart_display()

        msg = String()
        msg.data = ",".join(self.selected_objects)
        self.object_pub.publish(msg)

        button.setText(f"{obj_name} ✓")
        button.setStyleSheet("background-color: gray;")

    def remove_object(self, obj_name, button):
        if obj_name not in self.selected_objects:
            return

        self.selected_objects.remove(obj_name)
        self.update_cart_display()

        msg = String()
        msg.data = ",".join(self.selected_objects)
        self.object_pub.publish(msg)

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
            label = QLabel(obj.capitalize())
            label.setStyleSheet(
                "font-size:15px; background: none; border: none; "
                "padding: 0; margin: 0;"
            )
            self.ui.cart_items_layout.addWidget(label)

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