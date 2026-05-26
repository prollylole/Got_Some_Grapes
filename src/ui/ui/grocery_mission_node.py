#!/usr/bin/env python3

import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor

from std_msgs.msg import Bool, String
from perception_interfaces.srv import DetectColour


class GroceryMissionNode(Node):
    def __init__(self):
        super().__init__('grocery_mission_node')

        self.object_to_colour = {
            'apple': 'red',
            'bottle': 'blue',
            'cup': 'green',
            'book': 'yellow',
        }

        self.grocery_list = []
        self.current_index = 0
        self.check_in_progress = False

        self.detect_client = self.create_client(DetectColour, '/detect_colour')

        # GUI input topics
        self.create_subscription(
            String,
            '/selected_objects',
            self.selected_objects_callback,
            10
        )

        self.create_subscription(
            Bool,
            '/continue',
            self.continue_callback,
            10
        )

        # GUI output topics
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

        self.get_logger().info('Grocery mission node started.')
        self.get_logger().info('Waiting for grocery list on /selected_objects.')
        self.get_logger().info('Each /continue=True checks the next item only.')

    def selected_objects_callback(self, msg):
        new_list = [
            item.strip().lower()
            for item in msg.data.split(',')
            if item.strip()
        ]

        # If the grocery list changes, restart the manual mission sequence.
        if new_list != self.grocery_list:
            self.grocery_list = new_list
            self.current_index = 0

            self.publish_status(
                f'Grocery list updated: {", ".join(self.grocery_list) if self.grocery_list else "empty"}. '
                'Mission progress reset.'
            )

    def continue_callback(self, msg):
        if not msg.data:
            return

        if self.check_in_progress:
            self.get_logger().warn(
                'Item check already in progress. Ignoring duplicate continue signal.'
            )
            return

        check_thread = threading.Thread(target=self.check_next_item)
        check_thread.daemon = True
        check_thread.start()

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

    def publish_out_of_stock(self, item_name):
        msg = String()
        msg.data = item_name
        self.out_of_stock_pub.publish(msg)

    def call_colour_service(self, expected_colour):
        if not self.detect_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('Service /detect_colour is not available.')
            return None

        request = DetectColour.Request()
        request.expected_colour = expected_colour

        future = self.detect_client.call_async(request)

        start_time = time.time()
        timeout_sec = 35.0

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

    def check_next_item(self):
        self.check_in_progress = True

        try:
            if not self.grocery_list:
                self.publish_status('No grocery list found. Please select an item first.')
                self.publish_item_availability(False)
                return

            if self.current_index >= len(self.grocery_list):
                self.publish_status('All grocery list items have already been checked.')
                self.publish_item_availability(True)
                return

            object_name = self.grocery_list[self.current_index]
            expected_colour = self.object_to_colour.get(object_name)

            if expected_colour is None:
                self.publish_status(
                    f'Unknown item "{object_name}". No colour mapping found. Please update object_to_colour.'
                )
                self.publish_item_availability(False)
                return

            self.publish_status(
                f'Checking item {self.current_index + 1}/{len(self.grocery_list)}: '
                f'{object_name} using colour {expected_colour}.'
            )

            response = self.call_colour_service(expected_colour)

            # Service did not return at all. This is not the same as the item being missing.
            # Do not add to out-of-stock and do not move to the next item.
            if response is None:
                self.publish_status(
                    f'Could not check {object_name}. Perception service did not respond. Please retry.'
                )
                self.publish_item_availability(False)
                return

            self.get_logger().info(
                f'{object_name}: success={response.success}, '
                f'colour_present={response.colour_present}, '
                f'missing_flag={response.missing_flag}, '
                f'position={response.position}, '
                f'detection_count={response.detection_count}, '
                f'status="{response.status}"'
            )

            # A failed service response usually means camera/service/busy/request error.
            # This is not the same as a real out-of-stock result.
            # Do not add to out-of-stock and do not move to the next item.
            if not response.success:
                self.publish_status(
                    f'Perception error while checking {object_name}: {response.status}. Please retry.'
                )
                self.publish_item_availability(False)
                return

            # If the service ran successfully, then colour_present/missing_flag is a genuine detection result.
            item_missing = response.missing_flag or not response.colour_present

            if item_missing:
                self.publish_item_availability(False)
                self.publish_out_of_stock(object_name)
                self.publish_status(
                    f'{object_name} is not available. Added to out-of-stock list.'
                )
            else:
                self.publish_item_availability(True)
                self.publish_status(
                    f'{object_name} is available.'
                )

            self.current_index += 1

            if self.current_index < len(self.grocery_list):
                next_item = self.grocery_list[self.current_index]
                self.publish_status(
                    f'Next item is {next_item}. Move the robot to that area, then press Continue again.'
                )
            else:
                self.publish_status('Finished checking all grocery list items.')

        finally:
            self.publish_continue_false()
            self.check_in_progress = False


def main(args=None):
    rclpy.init(args=args)

    node = GroceryMissionNode()
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