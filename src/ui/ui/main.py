import sys
import rclpy
from threading import Thread

from PyQt6.QtWidgets import QApplication

from ui.gui_ui import GUI
from ui.gui_node import GuiNode


def main(args=None):
    rclpy.init(args=args)

    app = QApplication(sys.argv)

    gui = GUI()
    gui.show()

    node = GuiNode(gui)
    gui.node = node

    # ---------------- BUTTON CONNECTIONS ----------------
    gui.start_btn.clicked.connect(node.start_robot)
    gui.stop_btn.clicked.connect(node.stop_robot)
    gui.continue_btn.clicked.connect(node.continue_robot)

    gui.obj1.clicked.connect(lambda: node.choose_object("apple", gui.obj1))
    gui.obj2.clicked.connect(lambda: node.choose_object("bottle", gui.obj2))
    gui.obj3.clicked.connect(lambda: node.choose_object("cup", gui.obj3))
    gui.obj4.clicked.connect(lambda: node.choose_object("book", gui.obj4))

    # ---------------- ROS SPIN THREAD ----------------
    Thread(target=rclpy.spin, args=(node,), daemon=True).start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()