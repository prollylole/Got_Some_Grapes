from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout,
    QHBoxLayout, QMenu
)
from PyQt6.QtWidgets import QComboBox

class StaffGUI(QWidget):
    add_stock_item_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.node = None
        self.mode = "normal"

        self.setWindowTitle("Staff Control Panel")
        self.setFixedSize(700, 500)

        # ---------------- STATUS ----------------
        self.status = QLabel("Status: STOPPED")

        # ---------------- MODE BUTTONS ----------------
        self.mode_label = QLabel("Mode")

        self.normal_btn = QPushButton("Normal")
        self.upsell_btn = QPushButton("Upsell")

        self.normal_btn.setObjectName("mode_btn")
        self.upsell_btn.setObjectName("mode_btn")

        self.normal_btn.setCheckable(True)
        self.upsell_btn.setCheckable(True)
        self.normal_btn.setChecked(True)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(self.normal_btn)
        mode_layout.addWidget(self.upsell_btn)

        # ---------------- CAMERA SECTION ----------------
        self.camera_frame = QWidget()
        self.camera_layout = QVBoxLayout()
        self.camera_layout.setSpacing(5)

        self.camera_label = QLabel("Robot Camera Feed")
        self.camera_label.setStyleSheet(
            "font-size:14px; font-weight:bold; background: none; "
            "border: none; padding: 0; margin: 0;"
        )

        self.camera_feed = QLabel("No camera feed")
        self.camera_feed.setFixedHeight(200)

        self.camera_layout.addWidget(self.camera_label)
        self.camera_layout.addWidget(self.camera_feed)

        self.camera_frame.setLayout(self.camera_layout)
        self.camera_frame.setStyleSheet("""
            border: 1px solid #888;
            border-radius: 5px;
            padding: 5px;
        """)

        # ---------------- OUT OF STOCK LIST (LIKE CART) ----------------
        self.stock_frame = QWidget()
        self.stock_layout = QVBoxLayout()
        self.stock_layout.setSpacing(5)

        self.stock_label = QLabel("Out of Stock List")
        self.stock_label.setStyleSheet(
            "font-size:14px; font-weight:bold; background: none; "
            "border: none; padding: 0; margin: 0;"
        )
        self.stock_layout.addWidget(self.stock_label)

        self.stock_items_layout = QVBoxLayout()
        self.stock_items_layout.setSpacing(0)
        self.stock_items_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.stock_layout.addLayout(self.stock_items_layout)
        self.stock_layout.addStretch()

        self.stock_frame.setLayout(self.stock_layout)
        self.stock_frame.setFixedWidth(200)
        self.stock_frame.setStyleSheet("""
            border: 1px solid #888;
            border-radius: 5px;
            padding: 5px;
        """)

        #dropdown for upsell products
        self.upsell_label = QLabel("Select Promotion Item")
        self.upsell_label.setVisible(False)  # hidden by default

        self.upsell_dropdown = QComboBox()
        self.upsell_dropdown.addItems(["apple", "bottle", "cup", "book"])
        self.upsell_dropdown.setVisible(False)  # hidden by default

        # ---------------- TOP SECTION ----------------
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.camera_frame)
        top_layout.addWidget(self.stock_frame)

        # ---------------- START/STOP BUTTONS ----------------
        self.start_btn = QPushButton("START")
        self.stop_btn = QPushButton("STOP")

        self.start_btn.setObjectName("start_btn")
        self.stop_btn.setObjectName("stop_btn")

        self.stop_btn.setEnabled(False)

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)

        # ---------------- MAIN LAYOUT ----------------
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.mode_label)
        main_layout.addLayout(mode_layout)
        main_layout.addWidget(self.upsell_label)
        main_layout.addWidget(self.upsell_dropdown)
        main_layout.addWidget(self.status)
        main_layout.addLayout(top_layout)
        main_layout.addStretch()
        main_layout.addLayout(control_layout)

        self.setLayout(main_layout)

        # ---------------- CONNECT SIGNAL ----------------
        self.add_stock_item_signal.connect(self.add_stock_item)

        # ---------------- GLOBAL STYLING ----------------
        self.setStyleSheet("""
        QWidget {
            background-color: #1e1e2f;
            color: white;
            font-size: 14px;
        }

        QLabel {
            font-size: 15px;
            padding: 4px;
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

        #start_btn:disabled {
            background-color: #035f47;
            color: #888;
        }

        #stop_btn:disabled {
            background-color: #7a1f35;
            color: #888;
        }

        #mode_btn {
            background-color: #444;
        }

        #mode_btn:checked {
            background-color: #ffd166;
            color: black;
        }
        """)

    # ---------------- OUT OF STOCK DISPLAY ----------------
    def add_stock_item(self, item):
        button = QPushButton(item.capitalize())
        button.setObjectName("stock_item")
        button.setFlat(True)

        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        button.customContextMenuRequested.connect(
            lambda pos, btn=button: self.show_stock_item_menu(pos, btn)
        )

        button.setStyleSheet(
            "font-size:15px; background: none; border: none; "
            "padding: 0; margin: 0; text-align: left;"
        )

        self.stock_items_layout.addWidget(button)

    def show_stock_item_menu(self, pos, button):
        menu = QMenu(self)
        stocked_action = menu.addAction("Stocked")

        action = menu.exec(button.mapToGlobal(pos))

        if action == stocked_action:
            self.stock_items_layout.removeWidget(button)
            button.deleteLater()

    # ---------------- RUN BUTTON UPDATE ----------------
    def update_run_buttons(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def update_mode_ui(self, mode):
        if mode == "upsell":
            self.upsell_dropdown.setVisible(True)
            self.upsell_label.setVisible(True)
        else:
            self.upsell_dropdown.setVisible(False)
            self.upsell_label.setVisible(False)