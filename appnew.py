# streamlit_traffic_dashboard.py
import streamlit as st
import cv2
from ultralytics import YOLO
import numpy as np
import pyttsx3
from datetime import datetime
import requests
import pandas as pd
import tempfile
import time

# ==========================================================
# STREAMLIT DASHBOARD CONFIG
# ==========================================================
st.set_page_config(
    page_title="Traffic Sign Context-Aware System",
    layout="wide",
)

st.title("🚦 Context-Aware Traffic Sign Detection Dashboard")

# ==========================================================
# INITIALIZE YOLO MODEL
# ==========================================================
st.sidebar.header("Model Settings")
model_path = st.sidebar.text_input("YOLOv8 Model Path", "best.pt")
model = YOLO(model_path)

# ==========================================================
# INITIALIZE SPEECH ENGINE
# ==========================================================
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

last_alert_time = 0
alert_cooldown = 3

def speak_alert(message):
    global last_alert_time
    current_time = time.time()
    if current_time - last_alert_time > alert_cooldown:
        engine.say(message)
        engine.runAndWait()
        last_alert_time = current_time

# ==========================================================
# WEATHER API SETUP
# ==========================================================
OPENWEATHER_API_KEY = st.sidebar.text_input("OpenWeather API Key", "")
LAT, LON = st.sidebar.text_input("Latitude", "12.9716"), st.sidebar.text_input("Longitude", "77.5946")

def get_weather(lat, lon):
    if OPENWEATHER_API_KEY:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        try:
            data = requests.get(url).json()
            temp = data['main']['temp']
            condition = data['weather'][0]['main']
            return temp, condition
        except:
            return None, None
    else:
        return None, None

# ==========================================================
# RISK ENGINE / ML DECISION
# ==========================================================
TRAFFIC_ACTIONS = {
    "stop": "STOP",
    "yield": "SLOW DOWN",
    "speed_limit_50": "MAINTAIN SPEED",
    "no_entry": "DO NOT ENTER",
    "turn_left": "TURN LEFT",
    "turn_right": "TURN RIGHT",
    "pedestrian_crossing": "CAUTION: PEDESTRIANS"
}

def risk_score(sign_label, weather, hour):
    base_risk = {
        "stop": 0.9,
        "yield": 0.7,
        "speed_limit_50": 0.5,
        "no_entry": 0.95,
        "turn_left": 0.5,
        "turn_right": 0.5,
        "pedestrian_crossing": 0.8
    }.get(sign_label, 0.4)
    if weather in ["Rain", "Snow"]:
        base_risk += 0.1
    if hour < 6 or hour > 20:
        base_risk += 0.1
    return min(base_risk, 1.0)

# ==========================================================
# STREAMLIT VIDEO CAPTURE
# ==========================================================
st.sidebar.header("Camera Settings")
start_camera = st.sidebar.button("Start Camera")
FRAME_WINDOW = st.image([])  # Placeholder for video

# Log Data
log_df = pd.DataFrame(columns=["Time", "Sign", "Action", "Risk", "Weather", "Hour"])

if start_camera:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        st.error("Unable to open camera")
    else:
        while True:
            ret, frame = cap.read()
            if not ret:
                st.error("Cannot read frame")
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # ========== STEP 1: TRAFFIC SIGN DETECTION ==========
            results = model.predict(frame_rgb, verbose=False)[0]

            detected_signs = []
            actions = []
            risks = []

            temp, weather = get_weather(LAT, LON)
            current_hour = datetime.now().hour

            for box in results.boxes:
                cls_id = int(box.cls[0])
                label = results.names[cls_id]
                confidence = round(box.conf[0].item(), 2)

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame_rgb, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame_rgb, f"{label} {confidence}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # ========== STEP 2: RISK ASSESSMENT ==========
                risk = risk_score(label, weather, current_hour)
                action = TRAFFIC_ACTIONS.get(label, "MONITOR")

                detected_signs.append(label)
                actions.append(action)
                risks.append(risk)

                speak_alert(f"{label} detected. {action}")

                # Log the data
                log_df.loc[len(log_df)] = [datetime.now(), label, action, risk, weather, current_hour]

            # ========== STEP 3: UPDATE DASHBOARD ==========
            FRAME_WINDOW.image(frame_rgb, channels="RGB")

            st.sidebar.subheader("Detected Signs")
            st.sidebar.write(detected_signs if detected_signs else "No signs detected")

            st.sidebar.subheader("Recommended Actions")
            st.sidebar.write(actions if actions else "-")

            st.sidebar.subheader("Risk Scores")
            st.sidebar.write([round(r, 2) for r in risks] if risks else "-")

            st.sidebar.subheader("Weather / Time")
            st.sidebar.write(f"Weather: {weather}, Hour: {current_hour}, Temp: {temp}")

            # Small delay to simulate frame rate
            time.sleep(0.1)

# ========== STEP 4: DOWNLOAD LOG ==========
if not log_df.empty:
    st.subheader("Logged Detection Data")
    st.dataframe(log_df)
    csv = log_df.to_csv(index=False).encode('utf-8')
    st.download_button(label="Download CSV Log", data=csv, file_name="traffic_log.csv", mime="text/csv")