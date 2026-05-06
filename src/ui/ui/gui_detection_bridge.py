#!/usr/bin/env python3

import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor

from std_msgs.msg import Bool, String
from perception_interfaces.srv import DetectColour


class GuiDetectionBridge(Node):
    def __init__(self):
        super().__init__('gui_detection_bridge')

        self.object_to_colour = {
            'apple': 'red',
            'bottle': 'blue',
            'cup': 'green',
            'book': 'yellow',
        }

        self.selected_objects = []
        self.check_in_progress = False

        self.detect_client = self.create_client(DetectColour, '/detect_colour')

        self.create_subscription(
            String,
            '/selected_objects',
            self.selected_objects_callback,
            10
        )

        self.create_subscription(
            Bool,
            '/trigger_scan',
            self.trigger_scan_callback,
            10
        )

        self.item_availability_pub = self.create_publisher(
            Bool,
            '/item_availability',
            10
        )

        self.out_of_stock_pub = self.create_publisher(
            String,
            '/out_of_stock',
            10
        )

        self.robot_status_pub = self.create_publisher(
            String,
            '/robot_status',
            10
        )

        self.continue_pub = self.create_publisher(
            Bool,
            '/continue',
            10
        )

        self.get_logger().info('GUI detection bridge started.')
        self.get_logger().info('Listening to /selected_objects and /trigger_scan.')
        self.get_logger().info('Calling service /detect_colour.')

    def selected_objects_callback(self, msg):
        self.selected_objects = [
            item.strip().lower()
            for item in msg.data.split(',')
            if item.strip()
        ]

        self.get_logger().info(
            f'Selected objects received: {self.selected_objects}'
        )

    def trigger_scan_callback(self, msg):
        if not msg.data:
            return

        if self.check_in_progress:
            self.get_logger().warn(
                'Detection already in progress. Ignoring duplicate trigger signal.'
            )
            return

        detection_thread = threading.Thread(target=self.run_detection_sequence)
        detection_thread.daemon = True
        detection_thread.start()

    def publish_status(self, text):
        msg = String()
        msg.data = text
        self.robot_status_pub.publish(msg)
        self.get_logger().info(text)

    def publish_continue_false(self):
        msg = Bool()
        msg.data = False
        self.continue_pub.publish(msg)

    def publish_item_availability(self, available):
        msg = Bool()
        msg.data = available
        self.item_availability_pub.publish(msg)

    def publish_out_of_stock(self, missing_items):
        msg = String()
        msg.data = ','.join(missing_items)
        self.out_of_stock_pub.publish(msg)

    def call_colour_service(self, expected_colour):
        if not self.detect_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('Service /detect_colour is not available.')
            return None

        request = DetectColour.Request()
        request.expected_colour = expected_colour

        future = self.detect_client.call_async(request)

        start_time = time.time()
        timeout_sec = 15.0

        while rclpy.ok() and not future.done():
            elapsed = time.time() - start_time

            if elapsed > timeout_sec:
                self.get_logger().error(
                    f'Timeout while waiting for /detect_colour response for {expected_colour}.'
                )
                return None

            time.sleep(0.1)

        if future.result() is None:
            self.get_logger().error(
                f'/detect_colour returned no result for {expected_colour}.'
            )
            return None

        return future.result()

    def run_detection_sequence(self):
        self.check_in_progress = True

        try:
            if not self.selected_objects:
                self.publish_status('No selected objects to check.')
                self.publish_item_availability(False)
                return

            self.publish_status(
                f'Checking selected objects: {", ".join(self.selected_objects)}'
            )

            missing_items = []

            for object_name in self.selected_objects:
                expected_colour = self.object_to_colour.get(object_name)

                if expected_colour is None:
                    self.publish_status(
                        f'Unknown object "{object_name}". No colour mapping found.'
                    )
                    missing_items.append(object_name)
                    continue

                self.publish_status(
                    f'Checking {object_name} using expected colour {expected_colour}.'
                )

                response = self.call_colour_service(expected_colour)

                if response is None:
                    self.publish_status(
                        f'Could not check {object_name}. Marking as unavailable.'
                    )
                    missing_items.append(object_name)
                    continue

                self.get_logger().info(
                    f'{object_name}: success={response.success}, '
                    f'colour_present={response.colour_present}, '
                    f'missing_flag={response.missing_flag}, '
                    f'position={response.position}, '
                    f'detection_count={response.detection_count}, '
                    f'status="{response.status}"'
                )

                if not response.success:
                    missing_items.append(object_name)
                elif response.missing_flag:
                    missing_items.append(object_name)
                elif not response.colour_present:
                    missing_items.append(object_name)

            if missing_items:
                self.publish_item_availability(False)
                self.publish_out_of_stock(missing_items)
                self.publish_status(
                    f'Missing items: {", ".join(missing_items)}'
                )
            else:
                self.publish_item_availability(True)
                self.publish_status('All selected items are available.')

        finally:
            self.publish_continue_false()
            self.check_in_progress = False


def main(args=None):
    rclpy.init(args=args)

    node = GuiDetectionBridge()
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()