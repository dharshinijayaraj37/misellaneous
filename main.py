import cv2
import numpy as np
from ultralytics import YOLO
import pyttsx3
import time
import os

# ==========================================================
# TEXT TO SPEECH ENGINE SETUP
# ==========================================================
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

last_alert_time = 0
alert_cooldown = 3  # seconds between repeated alerts

def speak_alert(message):
    global last_alert_time
    current_time = time.time()
    if current_time - last_alert_time > alert_cooldown:
        engine.say(message)
        engine.runAndWait()
        last_alert_time = current_time

# ==========================================================
# YOLOv8 TRAFFIC SIGN MODEL
# ==========================================================
model = YOLO("best.pt")  # replace with your trained traffic sign model

# ==========================================================
# CREATE OUTPUT DIRECTORY FOR DATA COLLECTION
# ==========================================================
save_frames = True
output_dir = "traffic_sign_data"
if save_frames and not os.path.exists(output_dir):
    os.makedirs(output_dir)

# ==========================================================
# OPEN CAMERA
# ==========================================================
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Unable to open camera.")
    exit()

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Video writer to save output video
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter("traffic_output.mp4", fourcc, 30, (width, height))

frame_count = 0

# ==========================================================
# TRAFFIC SIGN ALERT MAPPING
# ==========================================================
# Map detected traffic sign labels to alert messages / decisions
TRAFFIC_ALERTS = {
    "stop": "Stop the vehicle!",
    "yield": "Yield to other vehicles.",
    "speed_limit_50": "Limit speed to 50 km/h.",
    "no_entry": "Do not enter!",
    "turn_left": "Prepare to turn left.",
    "turn_right": "Prepare to turn right.",
    "pedestrian_crossing": "Watch out for pedestrians!"
}

# ==========================================================
# MAIN LOOP
# ==========================================================
while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Unable to read frame from camera.")
        break

    # YOLOv8 prediction
    results = model.predict(frame, verbose=False)[0]

    alerts = set()  # store alerts for current frame

    # Draw detected boxes
    for box in results.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls_id = int(box.cls[0])
        label = results.names[cls_id]
        confidence = round(box.conf[0].item(), 2)

        # Draw bounding box and label
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"{label} {confidence}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Prepare alerts
        if label in TRAFFIC_ALERTS:
            alerts.add(TRAFFIC_ALERTS[label])

        # Save frame for data collection
        if save_frames:
            frame_filename = os.path.join(output_dir, f"{label}_{frame_count}.jpg")
            cv2.imwrite(frame_filename, frame)
            frame_count += 1

    # Show alerts on frame
    y_offset = 30
    for alert in alerts:
        cv2.putText(frame, f"ALERT: {alert}", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        speak_alert(alert)
        y_offset += 40

    # Display the frame
    cv2.imshow("Traffic Sign Detection", frame)

    # Save video
    out.write(frame)

    # Exit on 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ==========================================================
# CLEANUP
# ==========================================================
cap.release()
out.release()
cv2.destroyAllWindows()