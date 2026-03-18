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

    # Convert the frame from BGR to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Define yellow colour range in HSV
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([35, 255, 255])

    # Create mask for yellow
    mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # Count how many yellow pixels are detected
    yellow_pixel_count = cv2.countNonZero(mask)

    # Set the flag
    yellow_detected = yellow_pixel_count > 1000

    # Show result text on webcam frame
    if yellow_detected:
        text = "Yellow Detected: TRUE"
    else:
        text = "Yellow Detected: FALSE"

    cv2.putText(frame, text, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Show both windows
    cv2.imshow("Webcam Feed", frame)
    cv2.imshow("Yellow Mask", mask)

    # Press q to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
cap.release()
cv2.destroyAllWindows()