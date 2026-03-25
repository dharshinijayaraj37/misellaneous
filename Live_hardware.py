import cv2
import numpy as np
import time
import threading
from ultralytics import YOLO
import socket

# ===== UDP Setup =====
UDP_PORT = 4210
BROADCAST_IP = "255.255.255.255"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
print("UDP Broadcast Sender Ready")

# ===== YOLO Model =====
model = YOLO("best.pt")

# Class-to-command mapping
class_commands = {
    'Parking-Sign': 'a', 'Pedestrian_Crossing': 'b', 'Round-About': 'c',
    'Warning': 'd', 'bump': 'e', 'do_not_enter': 'f', 'do_not_u_turn': 'g',
    'no_parking': 'h', 'no_waiting': 'i', 'speed_limit_100': 'j',
    'speed_limit_120': 'k', 'speed_limit_20': 'l', 'speed_limit_30': 'm',
    'speed_limit_40': 'n', 'speed_limit_50': 'o', 'speed_limit_60': 'p',
    'speed_limit_70': 'q', 'speed_limit_80': 'r', 'speed_limit_90': 's',
    'stop': 't'
}

sending = False

# Function to send command via UDP
def send_command(command):
    global sending
    if not sending:
        sending = True
        sock.sendto(command.encode(), (BROADCAST_IP, UDP_PORT))
        print(f"Sent UDP command: {command}")
        time.sleep(5)  # Prevent sending too frequently
        sending = False

# Initialize camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Unable to open camera.")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Unable to read frame from camera.")
        break

    results = model.predict(frame)

    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        label = results[0].names[int(box.cls[0])]
        confidence = round(box.conf[0].item(), 2)

        # Draw bounding box and label
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"{label} {confidence:.2f}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Send UDP command for detected label
        if label in class_commands and not sending:
            threading.Thread(target=send_command, args=(class_commands[label],)).start()
            break  # Only send one command per frame

    cv2.imshow("Traffic Sign Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
sock.close()
