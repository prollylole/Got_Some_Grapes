import cv2
import numpy as np

# =========================
# SETTINGS
# =========================

CAMERA_INDEX = 1                 # Your laptop webcam
EXPECTED_COLOUR = "green"       # Change to: "yellow", "green", "blue", "red"
PIXEL_THRESHOLD = 1000           # Minimum mask pixels needed to count as detected
MISSING_FRAME_THRESHOLD = 15     # Number of consecutive missing frames before raising flag


# =========================
# COLOUR RANGES IN HSV
# OpenCV HSV:
# H: 0-179, S: 0-255, V: 0-255
# =========================

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


# =========================
# FUNCTION: CREATE MASK
# =========================

def create_colour_mask(hsv_frame, colour_name):
    """
    Create a binary mask for the requested colour.

    Parameters:
        hsv_frame: image in HSV format
        colour_name: string, e.g. 'yellow'

    Returns:
        mask: binary image where white = detected colour
    """
    ranges = COLOUR_RANGES[colour_name]

    # Start with an empty mask
    mask = np.zeros(hsv_frame.shape[:2], dtype=np.uint8)

    # Combine all ranges for that colour
    for lower, upper in ranges:
        partial_mask = cv2.inRange(hsv_frame, lower, upper)
        mask = cv2.bitwise_or(mask, partial_mask)

    return mask


# =========================
# FUNCTION: DETECT COLOUR
# =========================

def detect_colour(frame, expected_colour, pixel_threshold):
    """
    Detect the expected colour in the frame.

    Parameters:
        frame: original BGR webcam image
        expected_colour: target colour string
        pixel_threshold: minimum number of mask pixels needed

    Returns:
        result: dictionary containing detection info
    """
    # Convert original frame to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Create colour mask
    mask = create_colour_mask(hsv, expected_colour)

    # Count number of white pixels in mask
    pixel_count = cv2.countNonZero(mask)

    # Basic detection decision
    colour_detected = pixel_count > pixel_threshold

    # Default return values
    largest_contour = None
    centroid = None

    # Only look for contours if enough colour exists
    if colour_detected:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) > 0:
            largest_contour = max(contours, key=cv2.contourArea)

            # Calculate centroid of largest contour
            M = cv2.moments(largest_contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                centroid = (cx, cy)

    return {
        "mask": mask,
        "pixel_count": pixel_count,
        "detected": colour_detected,
        "largest_contour": largest_contour,
        "centroid": centroid
    }


# =========================
# MAIN PROGRAM
# =========================

def main():
    # Open webcam
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Counter for consecutive missing frames
    missing_frame_count = 0

    # Final missing flag
    missing_flag = False

    print(f"Running detection for expected colour: {EXPECTED_COLOUR}")
    print("Press q to quit.")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Error: Could not read frame.")
            break

        # Run detection
        result = detect_colour(frame, EXPECTED_COLOUR, PIXEL_THRESHOLD)

        mask = result["mask"]
        colour_detected = result["detected"]
        largest_contour = result["largest_contour"]
        centroid = result["centroid"]
        pixel_count = result["pixel_count"]

        # -------------------------
        # MISSING FLAG LOGIC
        # -------------------------
        if colour_detected:
            missing_frame_count = 0
            missing_flag = False
        else:
            missing_frame_count += 1

            if missing_frame_count >= MISSING_FRAME_THRESHOLD:
                missing_flag = True

        # -------------------------
        # DRAW VISUAL FEEDBACK
        # -------------------------

        # Draw largest contour if it exists
        if largest_contour is not None:
            cv2.drawContours(frame, [largest_contour], -1, (255, 0, 0), 2)

        # Draw centroid if it exists
        if centroid is not None:
            cx, cy = centroid
            cv2.circle(frame, (cx, cy), 8, (0, 0, 255), -1)

            # Optional left/centre/right display
            frame_width = frame.shape[1]
            if cx < frame_width / 3:
                position_text = "Position: LEFT"
            elif cx < 2 * frame_width / 3:
                position_text = "Position: CENTRE"
            else:
                position_text = "Position: RIGHT"

            cv2.putText(frame, position_text, (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

        # Detection text
        detection_text = f"{EXPECTED_COLOUR.upper()} detected: {colour_detected}"
        cv2.putText(frame, detection_text, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Pixel count text
        pixel_text = f"Pixel count: {pixel_count}"
        cv2.putText(frame, pixel_text, (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # Missing flag text
        missing_text = f"Missing flag: {missing_flag}"
        cv2.putText(frame, missing_text, (20, 160),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # Missing frame counter
        counter_text = f"Missing frames: {missing_frame_count}"
        cv2.putText(frame, counter_text, (20, 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

        # Show windows
        cv2.imshow("Webcam Feed", frame)
        cv2.imshow(f"{EXPECTED_COLOUR.capitalize()} Mask", mask)

        # Press q to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()