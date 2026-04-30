#!/usr/bin/env python3

import time
import cv2
import numpy as np

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String
from cv_bridge import CvBridge

from rclpy.qos import qos_profile_sensor_data

# =========================================================
# CONFIG
# =========================================================

NUM_FRAMES = 5
FRAME_DELAY = 0.2
PIXEL_THRESHOLD = 1000
REQUIRED_DETECTIONS = 3
SHOW_DEBUG_WINDOWS = True
EXPECTED_COLOUR = "blue"   # change if needed: yellow, green, blue, red


# =========================================================
# HSV COLOUR RANGES
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
    Detect the expected colour in one frame.
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

                # If third left side then left side if not there and is less than right side then middle othewrise has to be right side 
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

        # Basically first one is best one then if next image has more pixels than best one then that's the best one
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


def draw_detection_visuals(frame, detection_result, expected_colour, frame_index=None):
    """
    Draw contour, centroid, and text onto a frame copy.
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

    title_text = f"Expected: {expected_colour.upper()}"
    if frame_index is not None:
        title_text += f" | Frame {frame_index}"

    cv2.putText(
        annotated_frame,
        title_text,
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
# ROS 2 ONE-SHOT BATCH NODE
# =========================================================

class ColourBatchNode(Node):
    def __init__(self):
        super().__init__('colour_batch_node')

        self.expected_colour = EXPECTED_COLOUR
        self.num_frames = NUM_FRAMES
        self.frame_delay = FRAME_DELAY
        self.pixel_threshold = PIXEL_THRESHOLD
        self.required_detections = REQUIRED_DETECTIONS
        self.show_debug_windows = SHOW_DEBUG_WINDOWS

        self.bridge = CvBridge()

        self.frames = []
        self.batch_result = None
        self.batch_ready = False
        self.finished = False
        self.last_capture_time = None

        self.image_sub = self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            qos_profile_sensor_data
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

        # Printing stuff to terminal 
        self.get_logger().info('One-shot Colour Batch Node started.')
        self.get_logger().info('Subscribing to: /image_raw')
        self.get_logger().info(f'Expected colour: {self.expected_colour}') # Don't forget need f to insert values straight to string otehrwise will just print what ever in between apostraphe
        self.get_logger().info(f'Will capture exactly {self.num_frames} frames once.')

    def image_callback(self, msg):
        """
        Capture frames only until we have exactly NUM_FRAMES.
        Then inspect once and stop collecting.
        """
        if self.finished:
            return

        now = time.monotonic()

        if self.last_capture_time is not None:
            if (now - self.last_capture_time) < self.frame_delay:
                return

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'Failed to convert image: {e}')
            return

        self.frames.append(frame.copy())
        self.last_capture_time = now

        self.get_logger().info(f'Captured frame {len(self.frames)}/{self.num_frames}')

        if len(self.frames) < self.num_frames:
            return

        self.batch_result = inspect_frame_batch(
            self.frames,
            self.expected_colour,
            pixel_threshold=self.pixel_threshold,
            required_detections=self.required_detections
        )

        self.batch_ready = True
        self.finished = True

        self.destroy_subscription(self.image_sub)

        missing_flag = self.batch_result["missing_flag"]

        missing_msg = Bool()
        missing_msg.data = missing_flag
        self.missing_flag_pub.publish(missing_msg)

        # This one to publish to topic not terminal
        status_msg = String()
        status_msg.data = (
            f"expected_colour={self.batch_result['expected_colour']}, "
            f"detection_count={self.batch_result['detection_count']}/{self.batch_result['num_frames']}, "
            f"colour_present={self.batch_result['colour_present']}, "
            f"missing_flag={self.batch_result['missing_flag']}"
        )
        self.status_pub.publish(status_msg)

        self.get_logger().info("===== FINAL BATCH RESULT =====")
        self.get_logger().info(status_msg.data)

        for i, result in enumerate(self.batch_result["per_frame_results"]):
            self.get_logger().info(
                f"Frame {i + 1}: "
                f"detected={result['detected']}, "
                f"pixel_count={result['pixel_count']}, "
                f"position={result['position']}"
            )

    def show_batch_debug_results(self):
        """
        Show each saved frame and its corresponding mask one-by-one.
        Press any key for next. Press q to quit early.
        """
        if not self.batch_ready or not self.show_debug_windows:
            return

        for i, frame in enumerate(self.frames):
            result = self.batch_result["per_frame_results"][i]

            annotated_frame = draw_detection_visuals(
                frame,
                result,
                self.expected_colour,
                frame_index=i + 1
            )

            cv2.imshow(f"Frame {i + 1}", annotated_frame)
            cv2.imshow(f"Mask {i + 1}", result["mask"])

            key = cv2.waitKey(0) & 0xFF

            cv2.destroyWindow(f"Frame {i + 1}")
            cv2.destroyWindow(f"Mask {i + 1}")

            if key == ord('q'):
                break

        cv2.destroyAllWindows()


def main(args=None):
    rclpy.init(args=args)
    node = ColourBatchNode()

    try:
        while rclpy.ok() and not node.batch_ready:
            rclpy.spin_once(node, timeout_sec=0.1)

        if node.batch_ready and node.show_debug_windows:
            node.get_logger().info("Showing saved batch frames...")
            node.show_batch_debug_results()

    except KeyboardInterrupt:
        pass

    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()