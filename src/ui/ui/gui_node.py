import sys
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, String

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QGridLayout, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QMenu 


class GUI(QWidget):

    def __init__(self):
        super().__init__()
        self.node = None  

        self.setWindowTitle("TurtleBot Control GUI")

        self.setFixedSize(800,300)

        # Status labels
        self.status = QLabel("Status: STOPPED")
        self.lidar = QLabel("Closest Distance: --")
        self.direction = QLabel("Obstacle Direction: --")

        # Object buttons
        self.obj1 = QPushButton("Apple")
        self.obj2 = QPushButton("Bottle")
        self.obj3 = QPushButton("Cup")
        self.obj4 = QPushButton("Book")

        self.obj1.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.obj2.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.obj3.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.obj4.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.obj1.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, "apple", self.obj1))
        self.obj2.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, "bottle", self.obj2))
        self.obj3.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, "cup", self.obj3))
        self.obj4.customContextMenuRequested.connect(lambda pos: self.show_context_menu(pos, "book", self.obj4))

        # Start/Stop buttons
        self.start_btn = QPushButton("START")
        self.stop_btn = QPushButton("STOP")
        self.continue_btn = QPushButton("Next Item")

        self.start_btn.setObjectName("start_btn")
        self.stop_btn.setObjectName("stop_btn")
        self.continue_btn.setObjectName("continue_btn")

        main_layout = QGridLayout()

        # LEFT PANEL (robot info)
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.status)
        left_layout.addWidget(self.lidar)
        left_layout.addWidget(self.direction)

        # RIGHT PANEL (object selection)
        right_layout = QGridLayout()
        self.obj_label = QLabel("Pick the objects you want: ")

        right_layout.addWidget(self.obj_label, 0, 0, 1, 2)
        right_layout.addWidget(self.obj1, 1, 0)
        right_layout.addWidget(self.obj2, 1, 1)
        right_layout.addWidget(self.obj3, 2, 0)
        right_layout.addWidget(self.obj4, 2, 1)

        # Add to grid
        main_layout.addLayout(left_layout, 0, 0)
        main_layout.addLayout(right_layout, 0, 1)

        # Bottom buttons span full width
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.start_btn)
        bottom_layout.addWidget(self.continue_btn)
        bottom_layout.addWidget(self.stop_btn)

        # ---------------- GUI Cart Section ----------------
        self.cart_frame = QWidget()  # frame to hold the whole cart
        self.cart_layout = QVBoxLayout()  # layout inside the big rectangle
        self.cart_layout.setSpacing(5)

        # Label inside the big rectangle
        self.cart_label = QLabel("Current Cart")
        self.cart_label.setStyleSheet("font-size:14px; font-weight:bold; background: none; border: none; padding: 0; margin: 0;")
        self.cart_layout.addWidget(self.cart_label)

        # Layout for items
        self.cart_items_layout = QVBoxLayout()
        self.cart_items_layout.setSpacing(0)
        self.cart_layout.addLayout(self.cart_items_layout)

        self.cart_frame.setLayout(self.cart_layout)
        self.cart_frame.setFixedWidth(150)
        self.cart_frame.setStyleSheet("""
            border: 1px solid #888;
            border-radius: 5px;
            padding: 5px;
        """)

        # Add the cart frame to main container
        self.cart_container = QVBoxLayout()
        self.cart_container.addWidget(self.cart_frame)

        container = QVBoxLayout()
        container.addLayout(main_layout)
        container.addLayout(self.cart_container)
        container.addStretch()  # pushes buttons DOWN
        container.addLayout(bottom_layout)

        self.setLayout(container)

        self.setStyleSheet("""
        QWidget {
            background-color: #1e1e2f;
            color: white;
            font-size: 14px;
        }

        QLabel {
            font-size: 16px;
            padding: 5px;
        }

        QPushButton {
            background-color: #3a86ff;
            border-radius: 8px;
            padding: 8px;
            font-weight: bold;
        }

        QPushButton:hover {
            background-color: #265df2;
        }

        QPushButton:pressed {
            background-color: #1d4ed8;
        }

        QPushButton:disabled {
            background-color: #555;
            color: #aaa;
        }

        #start_btn {
            background-color: #06d6a0;
        }

        #stop_btn {
            background-color: #ef476f;
        }
        
        #start_btn:pressed {
            background-color: #04b383;
        }

        #stop_btn:pressed {
            background-color: #d63a5f;
        }
                           
        #continue_btn {
            background-color: #ffd166;
            color: black;
        }

        #continue_btn:pressed {
            background-color: #e6b800;
        }
        """)

    def show_context_menu(self, pos, obj_name, button):
        if not self.node:
            return

        # Only allow removing if already selected
        if obj_name not in self.node.selected_objects:
            return

        menu = QMenu(self)

        remove_action = menu.addAction("Remove")

        action = menu.exec(button.mapToGlobal(pos))

        if action == remove_action:
            self.node.remove_object(obj_name, button)

class GuiNode(Node):

    def __init__(self, ui):
        super().__init__('robot_gui')

        self.ui = ui

        # Publishers
        self.control_pub = self.create_publisher(Bool, '/robot_run', 10)
        self.object_pub = self.create_publisher(String, '/selected_objects', 10)
        self.continue_pub = self.create_publisher(Bool, '/continue', 10)

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
        self.ui.start_btn.setEnabled(False)
        self.ui.stop_btn.setEnabled(True)

    def stop_robot(self):
        self.publish_control(False)
        self.ui.start_btn.setEnabled(True)
        self.ui.stop_btn.setEnabled(False)

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
        self.update_cart_display()

        msg = String()
        msg.data = ",".join(self.selected_objects)
        self.object_pub.publish(msg)

        # UI update
        button.setText(f"{obj_name} ✓")
        button.setStyleSheet("background-color: gray;")

    def remove_object(self, obj_name, button):
        if obj_name not in self.selected_objects:
            return  # only remove if exists

        self.selected_objects.remove(obj_name)
        self.update_cart_display()

        msg = String()
        msg.data = ",".join(self.selected_objects)
        self.object_pub.publish(msg)

        # UI reset
        button.setText(obj_name.capitalize())
        button.setStyleSheet("background-color: #3a86ff;")

    def update_cart_display(self):
        # Clear old items
        while self.ui.cart_items_layout.count():
            item = self.ui.cart_items_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Empty case
        if not self.selected_objects:
            label = QLabel("(empty)")
            label.setStyleSheet("font-size:15px; background: none; border: none; padding: 0; margin: 0;")
            self.ui.cart_items_layout.addWidget(label)
            return

        # Add each selected object as a simple label
        for obj in self.selected_objects:
            label = QLabel(obj.capitalize())
            label.setStyleSheet("font-size:15px; background: none; border: none; padding: 0; margin: 0;")
            self.ui.cart_items_layout.addWidget(label)
            
    def continue_robot(self):
        msg = Bool()
        msg.data = True   # or toggle if you want
        self.continue_pub.publish(msg)
    

def main(args=None):
    rclpy.init(args=args)

    app = QApplication(sys.argv)
    gui = GUI()
    gui.show()

    node = GuiNode(gui)
    gui.node = node 

    # Buttons
    gui.start_btn.clicked.connect(node.start_robot)
    gui.stop_btn.clicked.connect(node.stop_robot)
    gui.continue_btn.clicked.connect(node.continue_robot)

    gui.obj1.clicked.connect(lambda: node.choose_object("apple", gui.obj1))
    gui.obj2.clicked.connect(lambda: node.choose_object("bottle", gui.obj2))
    gui.obj3.clicked.connect(lambda: node.choose_object("cup", gui.obj3))
    gui.obj4.clicked.connect(lambda: node.choose_object("book", gui.obj4))

    # ROS thread
    from threading import Thread
    Thread(target=rclpy.spin, args=(node,), daemon=True).start()

    sys.exit(app.exec())