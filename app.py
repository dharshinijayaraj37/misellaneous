import cv2
import numpy as np
import requests
import pyttsx3
from ultralytics import YOLO
from datetime import datetime
import time

# ==========================================================
# VOICE ENGINE
# ==========================================================

engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

last_spoken = ""
last_time = 0


def speak_alert(message):
    global last_spoken, last_time

    if message != "" and (message != last_spoken or time.time() - last_time > 5):
        engine.say(message)
        engine.runAndWait()
        last_spoken = message
        last_time = time.time()


# ==========================================================
# WEATHER API SETTINGS
# ==========================================================

API_KEY = "587eb73cbf6e07c4f2de5cca079b5ed5"
CITY = "Salem"

URL = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"


def get_weather():

    try:
        response = requests.get(URL)
        data = response.json()

        weather = data['weather'][0]['main']
        temp = data['main']['temp']

        return weather, temp

    except:
        return "Unknown", 0


# ==========================================================
# TIME CONTEXT
# ==========================================================

def get_time_context():

    now = datetime.now()

    hour = now.hour
    current_time = now.strftime("%H:%M:%S")

    if 6 <= hour < 18:
        period = "Day"
    else:
        period = "Night"

    return current_time, period


# ==========================================================
# CONTEXT ALERT ENGINE
# ==========================================================

def generate_alert(label, weather, period):

    alert = ""

    if "speed_limit" in label and weather == "Rain":
        alert = "Rain detected. Reduce vehicle speed"

    elif "speed_limit" in label and weather == "Fog":
        alert = "Fog detected. Low visibility"

    elif label == "Pedestrian_Crossing" and period == "Night":
        alert = "Night alert. Watch for pedestrians"

    elif label == "stop":
        alert = "Stop sign detected"

    elif label == "bump":
        alert = "Speed breaker ahead"

    elif label == "Round-About":
        alert = "Roundabout ahead"

    elif label == "do_not_enter":
        alert = "Do not enter zone"

    elif label == "no_parking":
        alert = "No parking area"

    elif label == "no_waiting":
        alert = "No waiting zone"

    elif label == "Parking-Sign":
        alert = "Parking area detected"

    elif label == "do_not_u_turn":
        alert = "U turn prohibited"

    elif label == "Warning":
        alert = "General road warning"

    return alert


# ==========================================================
# LOAD YOLO MODEL
# ==========================================================

model = YOLO("best.pt")


# ==========================================================
# CAMERA SETUP
# ==========================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Unable to open camera.")
    exit()

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))


# ==========================================================
# VIDEO RECORDING
# ==========================================================

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter("output_video.mp4", fourcc, 30, (width, height))


# ==========================================================
# MAIN LOOP
# ==========================================================

while True:

    ret, frame = cap.read()

    if not ret:
        print("Error: Unable to read frame from camera.")
        break

    # ===============================
    # WEATHER DATA
    # ===============================

    weather, temperature = get_weather()

    # ===============================
    # TIME CONTEXT
    # ===============================

    current_time, period = get_time_context()

    # ===============================
    # YOLO DETECTION
    # ===============================

    results = model.predict(frame)

    alert_message = ""

    for box in results[0].boxes:

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        label = results[0].names[int(box.cls[0])]
        confidence = round(box.conf[0].item(), 2)

        # Draw box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)

        cv2.putText(frame,
                    f"{label} {confidence}",
                    (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0,255,0),
                    2)

        # Generate alert
        alert_message = generate_alert(label, weather, period)

        # Speak alert
        speak_alert(alert_message)

        break


    # ===============================
    # DISPLAY WEATHER
    # ===============================

    cv2.putText(frame,
                f"Weather: {weather}",
                (20,40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255,255,0),
                2)

    cv2.putText(frame,
                f"Temp: {temperature} C",
                (20,70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255,255,0),
                2)


    # ===============================
    # DISPLAY TIME
    # ===============================

    cv2.putText(frame,
                f"Time: {current_time}",
                (20,100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255,255,0),
                2)

    cv2.putText(frame,
                f"Period: {period}",
                (20,130),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255,255,0),
                2)


    # ===============================
    # DISPLAY ALERT
    # ===============================

    if alert_message != "":

        cv2.rectangle(frame, (10,160), (650,210), (0,0,0), -1)

        cv2.putText(frame,
                    f"ALERT: {alert_message}",
                    (20,200),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0,0,255),
                    3)


    # Show window
    cv2.imshow("Context Aware Traffic Alert System", frame)

    # Save video
    out.write(frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


# ==========================================================
# RELEASE
# ==========================================================

cap.release()
out.release()
cv2.destroyAllWindows()