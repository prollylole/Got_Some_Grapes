from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout,
    QHBoxLayout, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal


class StaffGUI(QWidget):
    add_stock_item_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.node = None
        self.mode = "normal"

        self.setWindowTitle("Staff Control Panel")
        self.setFixedSize(700, 450)

        # ---------------- STATUS ----------------
        self.status = QLabel("Status: STOPPED")

        # ---------------- CAMERA ----------------
        self.camera_frame = QWidget()
        self.camera_layout = QVBoxLayout()
        self.camera_layout.setSpacing(5)

        self.camera_label = QLabel("Robot Camera Feed")
        self.camera_label.setStyleSheet(
            "font-size:14px; font-weight:bold; background:none; border:none;"
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

        # Heading inside the rectangle
        self.stock_label = QLabel("Out of Stock List")
        self.stock_label.setStyleSheet(
            "font-size:14px; font-weight:bold; background: none; "
            "border: none; padding: 0; margin: 0 0 8px 0;" "padding: 0;"
        )
        self.stock_layout.addWidget(self.stock_label)

        # Layout for items
        self.stock_items_layout = QVBoxLayout()
        self.stock_items_layout.setSpacing(0)
        self.stock_items_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.stock_layout.addLayout(self.stock_items_layout)

        self.stock_frame.setLayout(self.stock_layout)
        self.stock_frame.setFixedWidth(200)
        self.stock_frame.setStyleSheet("""
            border: 1px solid #888;
            border-radius: 5px;
            padding: 5px;
        """)

        # ---------------- MODE SELECTOR ----------------
        self.mode_label = QLabel("Mode")

        self.normal_btn = QPushButton("Normal")
        self.upsell_btn = QPushButton("Upsell")

        self.normal_btn.setObjectName("mode_btn")
        self.upsell_btn.setObjectName("mode_btn")

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(self.normal_btn)
        mode_layout.addWidget(self.upsell_btn)

        # ---------------- CONTROL BUTTONS ----------------
        self.start_btn = QPushButton("START")
        self.stop_btn = QPushButton("STOP")

        self.start_btn.setObjectName("start_btn")
        self.stop_btn.setObjectName("stop_btn")

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)

        # ---------------- TOP (camera + stock) ----------------
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.camera_frame)
        top_layout.addWidget(self.stock_frame)

        # ---------------- MAIN ----------------
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.mode_label)
        main_layout.addLayout(mode_layout)
        main_layout.addWidget(self.status)
        main_layout.addLayout(top_layout)
        main_layout.addStretch()
        main_layout.addLayout(control_layout)

        self.setLayout(main_layout)

        # ---------------- STYLE ----------------
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

        QPushButton#stock_item {
            background: none;
            border: none;
            color: white;
            text-align: left;
        }

        QPushButton#stock_item:hover {
            background-color: rgba(255,255,255,0.08);
        }

        QPushButton#stock_item:pressed {
            background-color: rgba(255,255,255,0.16);
        }

        #start_btn {
            background-color: #06d6a0;
        }

        #start_btn:pressed {
            background-color: #04b383;
        }

        #start_btn:disabled {
            background-color: #035f47;
            color: #888;
        }

        #stop_btn {
            background-color: #ef476f;
        }

        #stop_btn:pressed {
            background-color: #d63a5f;
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

        # Make mode buttons toggleable
        self.normal_btn.setCheckable(True)
        self.upsell_btn.setCheckable(True)

        self.normal_btn.setChecked(True)
        self.stop_btn.setEnabled(False)

        # connect signal
        self.add_stock_item_signal.connect(self.add_stock_item)

    def update_run_buttons(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def add_stock_item(self, item):
        button = QPushButton(f"• {item.capitalize()}")
        button.setObjectName("stock_item")
        button.setProperty("stock_item", item)
        button.setFlat(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        button.customContextMenuRequested.connect(
            lambda pos, btn=button: self.show_stock_item_menu(pos, btn)
        )
        button.setStyleSheet(
            "font-size: 14px;"
            "color: white;"
            "background: none;"
            "border: none;"
            "text-align: left;"
            "margin: 0;"
            "padding: 4px 6px;"
        )
        self.stock_items_layout.addWidget(button)

    def show_stock_item_menu(self, pos, label):
        menu = QMenu(self)
        stocked_action = menu.addAction("Stocked")
        action = menu.exec(label.mapToGlobal(pos))
        if action == stocked_action:
            self.remove_stock_item(label)

    def remove_stock_item(self, label):
        item = label.property("stock_item")
        if self.node and hasattr(self.node, "logged_items"):
            try:
                self.node.logged_items.remove(item)
            except ValueError:
                pass

        self.stock_items_layout.removeWidget(label)
        label.deleteLater()