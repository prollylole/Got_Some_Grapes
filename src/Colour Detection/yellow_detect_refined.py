import cv2
import numpy as np

# Open laptop webcam
cap = cv2.VideoCapture(1)

# Check if webcam opened properly
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

while True:
    # Read one frame
    ret, frame = cap.read()

    if not ret:
        print("Error: Could not read frame.")
        break

    # Convert frame from BGR to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Define yellow colour range in HSV
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([35, 255, 255])

    # Create yellow mask
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # Count yellow pixels
    yellow_pixel_count = cv2.countNonZero(mask)

    # Boolean detection flag
    yellow_detected = yellow_pixel_count > 1000

    # Default text
    detection_text = "Yellow Detected: FALSE"
    position_text = "Position: NONE"

    if yellow_detected:
        detection_text = "Yellow Detected: TRUE"

        # Find contours in the yellow mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) > 0:
            # Choose the largest yellow contour
            largest_contour = max(contours, key=cv2.contourArea)

            # Get moments of the contour to find centroid
            M = cv2.moments(largest_contour)

            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])

                # Draw centroid on frame
                cv2.circle(frame, (cx, cy), 8, (0, 0, 255), -1)

                # Draw contour on frame
                cv2.drawContours(frame, [largest_contour], -1, (255, 0, 0), 2)

                # Get frame width
                frame_width = frame.shape[1]

                # Decide left / centre / right
                if cx < frame_width / 3:
                    position_text = "Position: LEFT"
                elif cx < 2 * frame_width / 3:
                    position_text = "Position: CENTRE"
                else:
                    position_text = "Position: RIGHT"

    # Draw text on frame
    cv2.putText(frame, detection_text, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.putText(frame, position_text, (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    # Show windows
    cv2.imshow("Webcam Feed", frame)
    cv2.imshow("Yellow Mask", mask)

    # Press q to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
cap.release()
cv2.destroyAllWindows()