import cv2
import numpy as np
from ultralytics import YOLO
import pyttsx3
import time
import os
import requests
from datetime import datetime
import csv

# ==============================
# VOICE ALERT SETUP
# ==============================
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

# ==============================
# YOLOv8 MODEL LOAD
# ==============================
model = YOLO("best.pt")  # replace with your trained model

# ==============================
# CAMERA SETUP
# ==============================
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Unable to open camera.")
    exit()

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Video output
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter("traffic_decision_video.mp4", fourcc, 30, (width, height))

# ==============================
# DATA COLLECTION SETUP
# ==============================
save_frames = True
output_dir = "traffic_sign_data"
if save_frames and not os.path.exists(output_dir):
    os.makedirs(output_dir)

csv_file = "traffic_sign_log.csv"
if not os.path.exists(csv_file):
    with open(csv_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Label", "Confidence", "Weather", "TimeOfDay", "Decision"])

# ==============================
# WEATHER CONTEXT
# ==============================
OPENWEATHER_API_KEY = "587eb73cbf6e07c4f2de5cca079b5ed5"  # Replace with your OpenWeatherMap API key
LAT, LON = 12.9716, 77.5946  # Replace with your location

def get_weather_condition():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={OPENWEATHER_API_KEY}&units=metric"
        data = requests.get(url, timeout=2).json()
        return data['weather'][0]['main'].lower()
    except:
        return "unknown"

# ==============================
# TRAFFIC SIGN DECISION MAPPING
# ==============================
TRAFFIC_DECISIONS = {
    "stop": "Stop the vehicle",
    "yield": "Yield to traffic",
    "speed_limit_50": "Limit speed to 50 km/h",
    "no_entry": "Do not enter",
    "turn_left": "Turn left ahead",
    "turn_right": "Turn right ahead",
    "pedestrian_crossing": "Watch for pedestrians"
}

def generate_decision(label, weather, hour):
    decision = TRAFFIC_DECISIONS.get(label, "")
    # Context-aware modifications
    if "rain" in weather or "snow" in weather:
        decision += " | Drive carefully, road slippery"
    if hour < 6 or hour > 18:
        decision += " | Night time, turn on headlights"
    return decision

# ==============================
# MAIN LOOP
# ==============================
frame_count = 0
while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Unable to read frame from camera.")
        break

    # Get current time and weather
    now = datetime.now()
    hour = now.hour
    weather = get_weather_condition()

    # YOLOv8 prediction
    results = model.predict(frame, verbose=False)[0]
    alerts = set()

    for box in results.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls_id = int(box.cls[0])
        label = results.names[cls_id]
        confidence = round(box.conf[0].item(), 2)

        # Draw detection box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"{label} {confidence}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Generate context-aware decision
        decision = generate_decision(label, weather, hour)
        if decision:
            alerts.add(decision)
            speak_alert(decision)

        # Save frames for ML data collection
        if save_frames:
            frame_filename = os.path.join(output_dir, f"{label}_{frame_count}.jpg")
            cv2.imwrite(frame_filename, frame)
            frame_count += 1

        # Log detection and decision
        with open(csv_file, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([now.strftime("%Y-%m-%d %H:%M:%S"), label, confidence, weather, hour, decision])

    # Display alerts on frame
    y_offset = 30
    for alert in alerts:
        cv2.putText(frame, f"DECISION: {alert}", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        y_offset += 40

    # Show frame and save video
    cv2.imshow("Traffic Sign Context-Aware Decisions", frame)
    out.write(frame)

    # Exit on 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ==============================
# CLEANUP
# ==============================
cap.release()
out.release()
cv2.destroyAllWindows()