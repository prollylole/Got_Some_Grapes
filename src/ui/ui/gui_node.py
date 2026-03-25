import sys
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, String

from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout


class GUI(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("TurtleBot Control GUI")

        # Status labels
        self.status = QLabel("Status: STOPPED")
        self.lidar = QLabel("Closest Distance: --")
        self.direction = QLabel("Obstacle Direction: --")

        # Object buttons
        self.obj1 = QPushButton("Apple")
        self.obj2 = QPushButton("Bottle")
        self.obj3 = QPushButton("Cup")
        self.obj4 = QPushButton("Book")

        # Start/Stop buttons
        self.start_btn = QPushButton("START")
        self.stop_btn = QPushButton("STOP")

        # LEFT PANEL (robot info)
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.status)
        left_layout.addWidget(self.lidar)
        left_layout.addWidget(self.direction)

        # RIGHT PANEL (object selection - TOP RIGHT ✅)
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Select Objects"))
        right_layout.addWidget(self.obj1)
        right_layout.addWidget(self.obj2)
        right_layout.addWidget(self.obj3)
        right_layout.addWidget(self.obj4)

        # TOP SECTION
        top_layout = QHBoxLayout()
        top_layout.addLayout(left_layout)
        top_layout.addLayout(right_layout)

        # BOTTOM SECTION (START/STOP)
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.start_btn)
        bottom_layout.addWidget(self.stop_btn)

        # MAIN LAYOUT
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

class GuiNode(Node):

    def __init__(self, ui):
        super().__init__('robot_gui')

        self.ui = ui

        # Publishers
        self.control_pub = self.create_publisher(Bool, '/robot_run', 10)
        self.object_pub = self.create_publisher(String, '/selected_objects', 10)

        # State
        self.selected_objects = []

        # QoS
        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.BEST_EFFORT

        # Subscribers
        self.create_subscription(LaserScan, '/scan', self.scan_callback, qos)
        self.create_subscription(String, '/robot_status', self.status_callback, 10)

    # ---------------- CONTROL ----------------
    def start_robot(self):
        self.publish_control(True)

    def stop_robot(self):
        self.publish_control(False)

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

        # normalize angle to 0–360
        if angle < 0:
            angle += 360

        return closest, angle

    def update_lidar_display(self, distance, angle):
        self.ui.lidar.setText(f"Closest Distance: {distance:.2f} m")

        if distance > 0.25:
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

        msg = String()
        msg.data = ",".join(self.selected_objects)
        self.object_pub.publish(msg)

        # UI update
        button.setText(f"{obj_name} ✓")
        button.setEnabled(False)
    

def main(args=None):
    rclpy.init(args=args)

    app = QApplication(sys.argv)
    gui = GUI()
    gui.show()

    node = GuiNode(gui)

    # Buttons
    gui.start_btn.clicked.connect(node.start_robot)
    gui.stop_btn.clicked.connect(node.stop_robot)

    gui.obj1.clicked.connect(lambda: node.choose_object("apple", gui.obj1))
    gui.obj2.clicked.connect(lambda: node.choose_object("bottle", gui.obj2))
    gui.obj3.clicked.connect(lambda: node.choose_object("cup", gui.obj3))
    gui.obj4.clicked.connect(lambda: node.choose_object("book", gui.obj4))

    # ROS thread
    from threading import Thread
    Thread(target=rclpy.spin, args=(node,), daemon=True).start()

    sys.exit(app.exec())