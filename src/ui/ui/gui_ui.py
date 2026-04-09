from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout,
    QHBoxLayout, QGridLayout, QMenu
)


class GUI(QWidget):
    def __init__(self):
        super().__init__()

        self.node = None  # will be assigned externally

        self.setWindowTitle("TurtleBot Control GUI")
        self.setFixedSize(800, 300)

        # ---------------- STATUS LABELS ----------------
        self.status = QLabel("Status: STOPPED")
        self.lidar = QLabel("Closest Distance: --")
        self.direction = QLabel("Obstacle Direction: --")

        # ---------------- OBJECT BUTTONS ----------------
        self.obj1 = QPushButton("Apple")
        self.obj2 = QPushButton("Bottle")
        self.obj3 = QPushButton("Cup")
        self.obj4 = QPushButton("Book")

        self.obj1.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.obj2.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.obj3.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.obj4.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.obj1.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, "apple", self.obj1)
        )
        self.obj2.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, "bottle", self.obj2)
        )
        self.obj3.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, "cup", self.obj3)
        )
        self.obj4.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, "book", self.obj4)
        )

        # ---------------- START/STOP BUTTONS ----------------
        self.start_btn = QPushButton("START")
        self.stop_btn = QPushButton("STOP")
        self.continue_btn = QPushButton("Next Item")

        self.start_btn.setObjectName("start_btn")
        self.stop_btn.setObjectName("stop_btn")
        self.continue_btn.setObjectName("continue_btn")

        # ---------------- MAIN LAYOUT ----------------
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

        main_layout.addLayout(left_layout, 0, 0)
        main_layout.addLayout(right_layout, 0, 1)

        # ---------------- BOTTOM BUTTONS ----------------
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.start_btn)
        bottom_layout.addWidget(self.continue_btn)
        bottom_layout.addWidget(self.stop_btn)

        # ---------------- GUI CART SECTION ----------------
        self.cart_frame = QWidget()
        self.cart_layout = QVBoxLayout()
        self.cart_layout.setSpacing(5)

        self.cart_label = QLabel("Current Cart")
        self.cart_label.setStyleSheet(
            "font-size:14px; font-weight:bold; background: none; "
            "border: none; padding: 0; margin: 0;"
        )
        self.cart_layout.addWidget(self.cart_label)

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

        self.cart_container = QVBoxLayout()
        self.cart_container.addWidget(self.cart_frame)

        # ---------------- FINAL CONTAINER ----------------
        container = QVBoxLayout()
        container.addLayout(main_layout)
        container.addLayout(self.cart_container)
        container.addStretch()
        container.addLayout(bottom_layout)

        self.setLayout(container)

        # ---------------- GLOBAL STYLING ----------------
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

    # ---------------- CONTEXT MENU ----------------
    def show_context_menu(self, pos, obj_name, button):
        if not self.node:
            return

        if obj_name not in self.node.selected_objects:
            return

        menu = QMenu(self)
        remove_action = menu.addAction("Remove")

        action = menu.exec(button.mapToGlobal(pos))

        if action == remove_action:
            self.node.remove_object(obj_name, button)