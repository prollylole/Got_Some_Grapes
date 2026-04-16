import sys
import rclpy
from threading import Thread

from PyQt6.QtWidgets import QApplication

from ui.staff_ui import StaffGUI
from ui.staff_node import StaffNode


def main(args=None):
    rclpy.init(args=args)

    app = QApplication(sys.argv)

    gui = StaffGUI()
    gui.show()

    node = StaffNode(gui)
    gui.node = node

    gui.start_btn.clicked.connect(node.start_robot)
    gui.stop_btn.clicked.connect(node.stop_robot)

    gui.normal_btn.clicked.connect(lambda: node.set_mode("normal"))
    gui.upsell_btn.clicked.connect(lambda: node.set_mode("upsell"))

    Thread(target=rclpy.spin, args=(node,), daemon=True).start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()