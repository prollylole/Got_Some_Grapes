import cv2
import numpy as np
import time


# =========================================================
# CONFIG
# =========================================================

CAMERA_INDEX = 1                  # Change if needed on your machine (ROS is probably soem camera topic I'm not sure)
NUM_FRAMES = 5                    # Number of frames to capture for one inspection
FRAME_DELAY = 0.2                 # Delay between captured frames (seconds)
PIXEL_THRESHOLD = 1000            # Minimum mask pixels needed to count as detected
REQUIRED_DETECTIONS = 3           # Example: 3 out of 5 frames must detect the colour

# Turn this on to see each frame's drawings and mask
SHOW_DEBUG_WINDOWS = True


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
# CREATE MASK FOR A GIVEN COLOUR
# =========================================================

def create_colour_mask(hsv_frame, colour_name):
    """
    Create a binary mask for the requested colour.

    Parameters:
        hsv_frame (numpy array): HSV image
        colour_name (str): 'yellow', 'green', 'blue', or 'red'

    Returns:
        mask (numpy array): binary mask where white = detected colour
    """
    if colour_name not in COLOUR_RANGES:
        raise ValueError(f"Unsupported colour: {colour_name}")

    ranges = COLOUR_RANGES[colour_name]

    # Start with an empty mask
    mask = np.zeros(hsv_frame.shape[:2], dtype=np.uint8)

    # Combine all HSV ranges for this colour
    for lower, upper in ranges:
        partial_mask = cv2.inRange(hsv_frame, lower, upper)
        mask = cv2.bitwise_or(mask, partial_mask)

    return mask


# =========================================================
# DETECT EXPECTED COLOUR IN A SINGLE FRAME
# =========================================================

def detect_colour(frame, expected_colour, pixel_threshold=1000):
    """
    Run colour detection on a single frame.

    Parameters:
        frame (numpy array): BGR image
        expected_colour (str): target colour
        pixel_threshold (int): minimum number of white mask pixels

    Returns:
        result (dict): detection result for this frame
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


# =========================================================
# DRAW VISUAL FEEDBACK ON A FRAME
# =========================================================

def draw_detection_visuals(frame, detection_result, expected_colour, frame_index=None):
    """
    Draw contour, centroid, and text onto a copy of the frame.

    Parameters:
        frame (numpy array): original BGR image
        detection_result (dict): output from detect_colour()
        expected_colour (str): target colour
        frame_index (int or None): optional frame number for display

    Returns:
        annotated_frame (numpy array): image with drawings/text
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

    cv2.putText(annotated_frame, title_text, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    cv2.putText(annotated_frame, f"Detected: {detected}", (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.putText(annotated_frame, f"Pixel count: {pixel_count}", (20, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    cv2.putText(annotated_frame, f"Position: {position}", (20, 160),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

    return annotated_frame


# =========================================================
# CAPTURE A SMALL BATCH OF FRAMES FROM A WEBCAM
# =========================================================

def capture_frames_from_webcam(camera_index=0, num_frames=5, delay_between_frames=0.2):
    """
    Capture a small batch of frames from a webcam.

    Parameters:
        camera_index (int): webcam index
        num_frames (int): how many frames to capture
        delay_between_frames (float): delay between captures in seconds

    Returns:
        frames (list): list of BGR frames
    """
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    frames = []

    try:
        for _ in range(num_frames):
            ret, frame = cap.read()
            if not ret:
                raise RuntimeError("Could not read frame from webcam.")
            frames.append(frame)
            time.sleep(delay_between_frames)
    finally:
        cap.release()

    return frames


# =========================================================
# INSPECT A BATCH OF FRAMES
# =========================================================

def inspect_frame_batch(frames, expected_colour, pixel_threshold=1000, required_detections=3):
    """
    Inspect multiple frames and make one final decision.

    Parameters:
        frames (list): list of BGR frames
        expected_colour (str): target colour
        pixel_threshold (int): threshold per frame
        required_detections (int): minimum number of frames that must detect the colour

    Returns:
        batch_result (dict): final inspection result
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


# =========================================================
# EXAMPLE HELPER FOR TEAMMATES / FUTURE ROS USE
# =========================================================

def inspect_expected_colour(expected_colour,
                            frame_source_fn,
                            num_frames=5,
                            pixel_threshold=1000,
                            required_detections=3):
    """
    High-level wrapper that teammates can reuse.

    The frame source is passed in as a function.
    That makes it easier to replace webcam capture with ROS capture later.

    Parameters:
        expected_colour (str): target colour
        frame_source_fn (callable): function that returns a list of frames
        num_frames (int): number of frames to request
        pixel_threshold (int): detection threshold
        required_detections (int): how many frames must detect the colour

    Returns:
        batch_result (dict): final result
    """
    frames = frame_source_fn(num_frames)
    result = inspect_frame_batch(frames,
                                 expected_colour,
                                 pixel_threshold=pixel_threshold,
                                 required_detections=required_detections)
    return result, frames


# =========================================================
# EXAMPLE WEBCAM FRAME SOURCE
# This matches the interface expected by inspect_expected_colour()
# =========================================================

def webcam_frame_source(num_frames):
    ''' Functions currently have place holder value so this sets camera index properly just good practice to make functions resuable'''
    return capture_frames_from_webcam(
        camera_index=CAMERA_INDEX,
        num_frames=num_frames,
        delay_between_frames=FRAME_DELAY
    )


# =========================================================
# MAIN DEMO
# =========================================================

def main():
    expected_colour = "yellow"   # Change this to test: yellow, green, blue, red

    print(f"Starting batch inspection for expected colour: {expected_colour}")
    print(f"Capturing {NUM_FRAMES} frames...")
    print()

    batch_result, frames = inspect_expected_colour(
        expected_colour=expected_colour,
        frame_source_fn=webcam_frame_source,
        num_frames=NUM_FRAMES,
        pixel_threshold=PIXEL_THRESHOLD,
        required_detections=REQUIRED_DETECTIONS
    )

    print("===== FINAL BATCH RESULT =====")
    print(f"Expected colour:   {batch_result['expected_colour']}")
    print(f"Frames checked:    {batch_result['num_frames']}")
    print(f"Detections:        {batch_result['detection_count']}")
    print(f"Required:          {batch_result['required_detections']}")
    print(f"Colour present:    {batch_result['colour_present']}")
    print(f"Missing flag:      {batch_result['missing_flag']}")
    print(f"Best frame index:  {batch_result['best_frame_index']}")
    print()

    for i, frame in enumerate(frames):
        result = batch_result["per_frame_results"][i]
        print(f"Frame {i + 1}: detected={result['detected']}, "
              f"pixel_count={result['pixel_count']}, "
              f"position={result['position']}")

    if SHOW_DEBUG_WINDOWS:
        for i, frame in enumerate(frames):
            result = batch_result["per_frame_results"][i]

            annotated_frame = draw_detection_visuals(
                frame,
                result,
                expected_colour,
                frame_index=i + 1
            )

            cv2.imshow(f"Frame {i + 1}", annotated_frame)
            cv2.imshow(f"Mask {i + 1}", result["mask"])

            key = cv2.waitKey(0)
            if key & 0xFF == ord('q'):
                break

        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()