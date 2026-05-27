from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout,
    QHBoxLayout, QMenu, QProgressBar
)
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QSizePolicy


class StaffGUI(QWidget):
    add_stock_item_signal = pyqtSignal(str)
    update_progress_signal = pyqtSignal(int)
    update_distance_signal = pyqtSignal(str)
    update_route_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.node = None
        self.mode = "normal"

        self.out_of_stock_items = set()

        self.setWindowTitle("Staff Control Panel")
        self.setFixedSize(700, 705)

        # ---------------- STATUS ----------------
        self.status = QLabel("Status: STOPPED")

        # ---------------- TELEMETRY LABELS ----------------
        self.route_lbl = QLabel("Active Route: --")
        self.distance_lbl = QLabel("Progress Bar: ")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.update_progress_signal.connect(self.progress_bar.setValue)
        # self.update_distance_signal.connect(self.distance_lbl.setText)
        self.update_route_signal.connect(self.route_lbl.setText)

        # ---------------- MODE BUTTONS ----------------
        self.mode_label = QLabel("Please Select the Mode")

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
        self.camera_feed = QLabel("No camera feed")
        self.camera_feed.setFixedSize(450, 180)

        self.camera_feed.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.camera_feed.setStyleSheet("""
            border: 2px solid #888;
            background-color: black;
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
        self.stock_frame.setFixedWidth(180)
        self.stock_frame.setFixedHeight(200)

        self.stock_frame.setStyleSheet("""
            border: 1px solid #888;
            border-radius: 5px;
            padding: 5px;
        """)

        #map label
        self.map_label = QLabel()
        self.map_label.setFixedSize(450, 180)
        self.map_label.setStyleSheet("""
            border: 2px solid #888;
            background-color: black;
        """)
        self.map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_label.setText("Nav2 Map View")

        #dropdown for upsell products
        self.upsell_label = QLabel("Select Promotion Item")
        self.upsell_label.setVisible(False)  # hidden by default

        self.upsell_dropdown = QComboBox()
        self.upsell_dropdown.addItem("Please select Upsell Item")
        self.upsell_dropdown.addItems(["apple", "bottle", "cup", "book", "banana", "blueberry"])
        self.upsell_dropdown.setVisible(False)  # hidden by default
        self.upsell_dropdown.setCurrentIndex(0)

        # ---------------- TOP SECTION ----------------
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.camera_feed, Qt.AlignmentFlag.AlignLeft)
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
        main_layout.addWidget(self.route_lbl) 
        main_layout.addWidget(self.distance_lbl)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(top_layout)
        # main_layout.addStretch()
        main_layout.addWidget(self.map_label, alignment=Qt.AlignmentFlag.AlignLeft)
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
        item = item.lower().strip()

        # Do not add duplicates
        if item in self.out_of_stock_items:
            return

        # Track currently displayed items
        self.out_of_stock_items.add(item)

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

            self.out_of_stock_items.discard(button.text().lower().strip())

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