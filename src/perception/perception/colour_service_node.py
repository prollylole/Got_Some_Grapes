#!/usr/bin/env python3

import time
import threading

import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String
from cv_bridge import CvBridge

from perception_interfaces.srv import DetectColour


# =========================================================
# HSV COLOUR RANGES
# OpenCV HSV:
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
    if colour_name not in COLOUR_RANGES:
        raise ValueError(f"Unsupported colour: {colour_name}")

    mask = np.zeros(hsv_frame.shape[:2], dtype=np.uint8)

    for lower, upper in COLOUR_RANGES[colour_name]:
        partial_mask = cv2.inRange(hsv_frame, lower, upper)
        mask = cv2.bitwise_or(mask, partial_mask)

    return mask


def detect_colour(frame, expected_colour, pixel_threshold=1000):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = create_colour_mask(hsv, expected_colour)

    pixel_count = cv2.countNonZero(mask)
    detected = pixel_count > pixel_threshold

    largest_contour = None
    centroid = None
    position = "NONE"

    if detected:
        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if contours:
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

    best_position = "NONE"
    if (
        best_frame_index is not None
        and per_frame_results[best_frame_index]["detected"]
    ):
        best_position = per_frame_results[best_frame_index]["position"]

    return {
        "expected_colour": expected_colour,
        "num_frames": len(frames),
        "required_detections": required_detections,
        "detection_count": detection_count,
        "colour_present": colour_present,
        "missing_flag": missing_flag,
        "best_frame_index": best_frame_index,
        "best_position": best_position,
        "per_frame_results": per_frame_results
    }


def draw_detection_visuals(frame, detection_result, expected_colour, frame_index=None):
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
# ROS 2 SERVICE NODE
# =========================================================

class ColourServiceNode(Node):
    def __init__(self):
        super().__init__('colour_service_node')

        # Parameters
        self.declare_parameter('camera_topic', '/camera/image_raw')
        self.declare_parameter('num_frames', 5)
        self.declare_parameter('frame_delay', 0.2)
        self.declare_parameter('pixel_threshold', 1000)
        self.declare_parameter('required_detections', 3)
        self.declare_parameter('capture_timeout_sec', 5.0)
        self.declare_parameter('show_debug_windows', False)

        self.camera_topic = self.get_parameter('camera_topic').get_parameter_value().string_value
        self.num_frames = self.get_parameter('num_frames').get_parameter_value().integer_value
        self.frame_delay = self.get_parameter('frame_delay').get_parameter_value().double_value
        self.pixel_threshold = self.get_parameter('pixel_threshold').get_parameter_value().integer_value
        self.required_detections = self.get_parameter('required_detections').get_parameter_value().integer_value
        self.capture_timeout_sec = self.get_parameter('capture_timeout_sec').get_parameter_value().double_value
        self.show_debug_windows = self.get_parameter('show_debug_windows').get_parameter_value().bool_value

        self.bridge = CvBridge()

        self.callback_group = ReentrantCallbackGroup()

        self.latest_frame = None
        self.latest_frame_seq = 0
        self.frame_lock = threading.Lock()
        self.busy_lock = threading.Lock()

        self.image_sub = self.create_subscription(
            Image,
            self.camera_topic,
            self.image_callback,
            qos_profile_sensor_data,
            callback_group=self.callback_group
        )

        self.detect_service = self.create_service(
            DetectColour,
            '/detect_colour',
            self.handle_detect_colour_request,
            callback_group=self.callback_group
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

        self.get_logger().info('Colour service node started')
        self.get_logger().info(f'Subscribing to: {self.camera_topic}')
        self.get_logger().info('Service available at: /detect_colour')

    def image_callback(self, msg):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'Failed to convert image: {e}')
            return

        with self.frame_lock:
            self.latest_frame = frame.copy()
            self.latest_frame_seq += 1

    def get_latest_frame_snapshot(self):
        with self.frame_lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame_seq, self.latest_frame.copy()

    def collect_batch_frames(self):
        frames = []
        last_seq = -1
        last_capture_time = None
        deadline = time.monotonic() + self.capture_timeout_sec

        while len(frames) < self.num_frames and time.monotonic() < deadline:
            snapshot = self.get_latest_frame_snapshot()

            if snapshot is None:
                time.sleep(0.02)
                continue

            seq, frame = snapshot
            now = time.monotonic()

            is_new_frame = seq != last_seq
            delay_satisfied = (
                last_capture_time is None
                or (now - last_capture_time) >= self.frame_delay
            )

            if is_new_frame and delay_satisfied:
                frames.append(frame)
                last_seq = seq
                last_capture_time = now
                self.get_logger().info(
                    f'Captured frame {len(frames)}/{self.num_frames}'
                )
            else:
                time.sleep(0.02)

        return frames

    def set_error_response(self, response, status):
        response.success = False
        response.colour_present = False
        response.missing_flag = True
        response.position = "NONE"
        response.detection_count = 0
        response.status = status
        return response

    def handle_detect_colour_request(self, request, response):
        expected_colour = request.expected_colour.strip().lower()

        if expected_colour == "":
            return self.set_error_response(response, 'Empty colour request.')

        if expected_colour not in COLOUR_RANGES:
            return self.set_error_response(
                response,
                f'Unsupported colour requested: {expected_colour}'
            )

        acquired = self.busy_lock.acquire(blocking=False)
        if not acquired:
            return self.set_error_response(response, 'Detector is busy.')

        try:
            self.get_logger().info(
                f'Received detect request for colour: {expected_colour}'
            )

            frames = self.collect_batch_frames()

            if len(frames) < self.num_frames:
                return self.set_error_response(
                    response,
                    f'Only captured {len(frames)}/{self.num_frames} frames before timeout.'
                )

            batch_result = inspect_frame_batch(
                frames,
                expected_colour,
                pixel_threshold=self.pixel_threshold,
                required_detections=self.required_detections
            )

            response.success = True
            response.colour_present = batch_result['colour_present']
            response.missing_flag = batch_result['missing_flag']
            response.position = batch_result['best_position']
            response.detection_count = batch_result['detection_count']
            response.status = (
                f"expected_colour={batch_result['expected_colour']}, "
                f"detection_count={batch_result['detection_count']}/{batch_result['num_frames']}, "
                f"colour_present={batch_result['colour_present']}, "
                f"missing_flag={batch_result['missing_flag']}, "
                f"position={batch_result['best_position']}"
            )

            missing_msg = Bool()
            missing_msg.data = response.missing_flag
            self.missing_flag_pub.publish(missing_msg)

            status_msg = String()
            status_msg.data = response.status
            self.status_pub.publish(status_msg)

            self.get_logger().info('===== FINAL BATCH RESULT =====')
            self.get_logger().info(response.status)

            for i, result in enumerate(batch_result['per_frame_results']):
                self.get_logger().info(
                    f"Frame {i + 1}: "
                    f"detected={result['detected']}, "
                    f"pixel_count={result['pixel_count']}, "
                    f"position={result['position']}"
                )

            if self.show_debug_windows:
                self.show_batch_debug_results(
                    frames,
                    batch_result,
                    expected_colour
                )

            return response

        finally:
            self.busy_lock.release()

    def show_batch_debug_results(self, frames, batch_result, expected_colour):
        for i, frame in enumerate(frames):
            result = batch_result['per_frame_results'][i]

            annotated_frame = draw_detection_visuals(
                frame,
                result,
                expected_colour,
                frame_index=i + 1
            )

            cv2.imshow(f'Frame {i + 1}', annotated_frame)
            cv2.imshow(f'Mask {i + 1}', result['mask'])

            key = cv2.waitKey(0) & 0xFF

            cv2.destroyWindow(f'Frame {i + 1}')
            cv2.destroyWindow(f'Mask {i + 1}')

            if key == ord('q'):
                break

        cv2.destroyAllWindows()


def main(args=None):
    rclpy.init(args=args)

    node = ColourServiceNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()