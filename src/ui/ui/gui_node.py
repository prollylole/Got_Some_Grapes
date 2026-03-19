#ABC
import sys
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, String

from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt


class GuiNode(Node):

    def __init__(self, ui):
        super().__init__('robot_gui')

        self.ui = ui

        self.control_pub = self.create_publisher(Bool, '/robot_run', 10)
        self.object_pub = self.create_publisher(String, '/selected_objects', 10)

        self.selected_objects = []

        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.BEST_EFFORT

        self.scan_sub = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            qos
        )

        self.status_sub = self.create_subscription(
            String,
            '/robot_status',
            self.status_callback,
            10
        )

    def start_robot(self):

        msg = Bool()
        msg.data = True
        self.control_pub.publish(msg)

    def stop_robot(self):

        msg = Bool()
        msg.data = False
        self.control_pub.publish(msg)

    def status_callback(self, msg):

        self.ui.status.setText(f"Status: {msg.data}")

    def scan_callback(self, msg):

        valid_ranges = [r for r in msg.ranges if 0.05 < r < 10.0]
        closest = min(valid_ranges)
        index = msg.ranges.index(closest)

        angle = math.degrees(msg.angle_min + index * msg.angle_increment)

        if closest > 0.25:
            self.ui.lidar.setText(f"Closest Distance: {closest:.2f} m")
            self.ui.direction.setText("No obstacle")
            return

        if 0 <= angle <= 45 or 315 < angle <= 360:  # FRONT
            direction = "FRONT"
        elif 45 < angle <= 135:  # LEFT
            direction = "LEFT"
        elif 135 < angle <= 225:  # BACK
            direction = "BACK"
        elif 225 < angle <= 315:  # RIGHT
            direction = "RIGHT"
        else:
            direction = "BACK"  # Default, for angles above 315° (close to 360°)

        self.ui.lidar.setText(f"Closest Distance: {closest:.2f} m")
        self.ui.direction.setText(f"Obstacle Direction: {direction}")

    def choose_object(self, obj_name, button=None):

        if obj_name in self.selected_objects:
            return

        self.selected_objects.append(obj_name)

        msg = String()
        msg.data = ",".join(self.selected_objects)
        self.object_pub.publish(msg)

        if button:
            button.setText(f"{obj_name} ✓")
            button.setEnabled(False)

    def choose(self, gui, node, obj_name, button):

        node.choose_object(obj_name)

        button.setText(f"{obj_name} ✓")
        button.setEnabled(False)


class GUI(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("TurtleBot Control GUI")

        # status labels
        self.status = QLabel("Status: STOPPED")
        self.lidar = QLabel("Closest Distance: --")
        self.direction = QLabel("Obstacle Direction: --")

        # object buttons
        self.obj1 = QPushButton("Apple")
        self.obj2 = QPushButton("Bottle")
        self.obj3 = QPushButton("Cup")
        self.obj4 = QPushButton("Book")

        # start stop
        self.start_btn = QPushButton("START")
        self.stop_btn = QPushButton("STOP")

        # LEFT PANEL (robot info)
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.status)
        left_layout.addWidget(self.lidar)
        left_layout.addWidget(self.direction)

        # RIGHT PANEL (object selection)
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

        # BOTTOM SECTION
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.start_btn)
        bottom_layout.addWidget(self.stop_btn)

        # MAIN LAYOUT
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

    

def main(args=None):

    rclpy.init(args=args)

    app = QApplication(sys.argv)

    gui = GUI()
    gui.show()

    node = GuiNode(gui)

    gui.start_btn.clicked.connect(node.start_robot)
    gui.stop_btn.clicked.connect(node.stop_robot)

    from threading import Thread
    thread = Thread(target=rclpy.spin, args=(node,), daemon=True)
    thread.start()

    gui.obj1.clicked.connect(lambda: node.choose_object("apple"))
    gui.obj2.clicked.connect(lambda: node.choose_object("bottle"))
    gui.obj3.clicked.connect(lambda: node.choose_object("cup"))
    gui.obj4.clicked.connect(lambda: node.choose_object("book"))

    sys.exit(app.exec())