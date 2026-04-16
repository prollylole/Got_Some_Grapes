#!/usr/bin/env python3

import cv2
import numpy as np

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String
from cv_bridge import CvBridge


# =========================================================
# COLOUR RANGES
# OpenCV HSV ranges:
# H: 0-179, S: 0-255, V: 0-255
# =========================================================

COLOUR_RANGES = {
    "yellow": [
        (np.array([20, 100, 100]), np.array([35, 255, 255]))
    ],
    "green": [
        (np.array([40, 70, 70]), np.array([85, 255, 255]))
    ],
    "blue": [
        (np.array([90, 100, 100]), np.array([130, 255, 255]))
    ],
    "red": [
        (np.array([0, 100, 100]), np.array([10, 255, 255])),
        (np.array([170, 100, 100]), np.array([179, 255, 255]))
    ]
}


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def create_colour_mask(hsv_frame, colour_name):
    """
    Create a binary mask for the requested colour.
    White = detected colour, Black = everything else.
    """
    if colour_name not in COLOUR_RANGES:
        raise ValueError(f"Unsupported colour: {colour_name}")

    ranges = COLOUR_RANGES[colour_name]
    mask = np.zeros(hsv_frame.shape[:2], dtype=np.uint8)

    for lower, upper in ranges:
        partial_mask = cv2.inRange(hsv_frame, lower, upper)
        mask = cv2.bitwise_or(mask, partial_mask)

    return mask


def detect_colour(frame, expected_colour, pixel_threshold=1000):
    """
    Detect the expected colour in one OpenCV frame.

    Returns a dictionary with:
    - detected
    - pixel_count
    - mask
    - largest_contour
    - centroid
    - position
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = create_colour_mask(hsv, expected_colour)

    pixel_count = cv2.countNonZero(mask)
    detected = pixel_count > pixel_threshold

    largest_contour = None
    centroid = None
    position = "NONE"

    if detected:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) > 0:
            largest_contour = max(contours, key=cv2.contourArea)

            M = cv2.moments(largest_contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                centroid = (cx, cy)

                frame_width = frame.shape[1]
                if cx < frame_width / 3:
                    position = "LEFT"
                elif cx < 2 * frame_width / 3:
                    position = "CENTRE"
                else:
                    position = "RIGHT"

    return {
        "detected": detected,
        "pixel_count": pixel_count,
        "mask": mask,
        "largest_contour": largest_contour,
        "centroid": centroid,
        "position": position
    }


def inspect_frame_batch(frames, expected_colour, pixel_threshold=1000, required_detections=3):
    """
    Inspect a batch of frames and make one final decision.
    Example: 3 out of 5 frames must detect the colour.
    """
    if len(frames) == 0:
        raise ValueError("No frames provided for batch inspection.")

    per_frame_results = []
    detection_count = 0

    best_frame_index = None
    best_pixel_count = -1

    for i, frame in enumerate(frames):
        result = detect_colour(frame, expected_colour, pixel_threshold)
        per_frame_results.append(result)

        if result["detected"]:
            detection_count += 1

        if result["pixel_count"] > best_pixel_count:
            best_pixel_count = result["pixel_count"]
            best_frame_index = i

    colour_present = detection_count >= required_detections
    missing_flag = not colour_present

    return {
        "expected_colour": expected_colour,
        "num_frames": len(frames),
        "required_detections": required_detections,
        "detection_count": detection_count,
        "colour_present": colour_present,
        "missing_flag": missing_flag,
        "best_frame_index": best_frame_index,
        "per_frame_results": per_frame_results
    }


def draw_detection_visuals(frame, detection_result, expected_colour):
    """
    Draw contour, centroid, and text onto a frame.
    Useful for optional debugging with imshow.
    """
    annotated_frame = frame.copy()

    detected = detection_result["detected"]
    pixel_count = detection_result["pixel_count"]
    largest_contour = detection_result["largest_contour"]
    centroid = detection_result["centroid"]
    position = detection_result["position"]

    if largest_contour is not None:
        cv2.drawContours(annotated_frame, [largest_contour], -1, (255, 0, 0), 2)

    if centroid is not None:
        cx, cy = centroid
        cv2.circle(annotated_frame, (cx, cy), 8, (0, 0, 255), -1)

    cv2.putText(
        annotated_frame,
        f"Expected: {expected_colour.upper()}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"Detected: {detected}",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    cv2.putText(
        annotated_frame,
        f"Pixel count: {pixel_count}",
        (20, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2
    )

    cv2.putText(
        annotated_frame,
        f"Position: {position}",
        (20, 160),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 0, 0),
        2
    )

    return annotated_frame


# =========================================================
# ROS 2 NODE
# =========================================================

class ColourDetectionNode(Node):
    def __init__(self):
        super().__init__('colour_detection_node')

        # -------- Parameters you can change easily --------
        self.expected_colour = "yellow"     # change later if needed
        self.num_frames = 5
        self.pixel_threshold = 1000
        self.required_detections = 3
        self.show_debug_windows = True     # set True if you want OpenCV windows

        # -------- ROS setup --------
        self.bridge = CvBridge()
        self.frame_buffer = []

        self.image_sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )

        self.missing_flag_pub = self.create_publisher(
            Bool,
            '/colour_detection/missing_flag',
            10
        )

        self.status_pub = self.create_publisher(
            String,
            '/colour_detection/status',
            10
        )

        self.get_logger().info('Colour Detection Node started.')
        self.get_logger().info(f'Subscribing to: /camera/image_raw')
        self.get_logger().info(f'Expected colour: {self.expected_colour}')

    def image_callback(self, msg):
        """
        Called whenever a new image arrives from /camera/image_raw
        """
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'Failed to convert image: {e}')
            return

        # Add new frame to buffer
        self.frame_buffer.append(frame)

        # Keep only the latest self.num_frames frames
        if len(self.frame_buffer) > self.num_frames:
            self.frame_buffer.pop(0)

        # Only inspect once we have enough frames
        if len(self.frame_buffer) < self.num_frames:
            return

        # Run batch inspection
        batch_result = inspect_frame_batch(
            self.frame_buffer,
            self.expected_colour,
            pixel_threshold=self.pixel_threshold,
            required_detections=self.required_detections
        )

        missing_flag = batch_result["missing_flag"]

        # Publish Bool missing flag
        missing_msg = Bool()
        missing_msg.data = missing_flag
        self.missing_flag_pub.publish(missing_msg)

        # Publish human-readable status
        status_msg = String()
        status_msg.data = (
            f"expected_colour={batch_result['expected_colour']}, "
            f"detection_count={batch_result['detection_count']}/{batch_result['num_frames']}, "
            f"colour_present={batch_result['colour_present']}, "
            f"missing_flag={batch_result['missing_flag']}"
        )
        self.status_pub.publish(status_msg)

        self.get_logger().info(status_msg.data)

        # Optional debugging window
        if self.show_debug_windows:
            best_index = batch_result["best_frame_index"]
            best_frame = self.frame_buffer[best_index]
            best_result = batch_result["per_frame_results"][best_index]

            annotated = draw_detection_visuals(
                best_frame,
                best_result,
                self.expected_colour
            )

            cv2.imshow("Colour Detection Debug", annotated)
            cv2.imshow("Colour Mask Debug", best_result["mask"])
            cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = ColourDetectionNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.show_debug_windows:
            cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()