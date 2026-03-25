# streamlit_traffic_dashboard_gtts.py

import streamlit as st
import cv2
from ultralytics import YOLO
from datetime import datetime
import requests
import pandas as pd
from gtts import gTTS
import tempfile
import time
import os

# ==========================================================
# STREAMLIT CONFIG
# ==========================================================
st.set_page_config(page_title="Traffic Sign Context-Aware System", layout="wide")
st.title("🚦 Context-Aware Traffic Sign Detection Dashboard")

# ==========================================================
# YOLO MODEL
# ==========================================================
st.sidebar.header("Model Settings")
model_path = st.sidebar.text_input("YOLOv8 Model Path", "best.pt")

try:
    model = YOLO(model_path)
except:
    st.error("Model not found. Please check model path.")
    st.stop()

# ==========================================================
# WEATHER API
# ==========================================================
st.sidebar.header("Weather Settings")

OPENWEATHER_API_KEY = st.sidebar.text_input("OpenWeather API Key", "")
LAT = float(st.sidebar.text_input("Latitude", "12.9716"))
LON = float(st.sidebar.text_input("Longitude", "77.5946"))

def get_weather(lat, lon):

    if OPENWEATHER_API_KEY == "":
        return None, "Clear"

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        data = requests.get(url).json()

        temp = data["main"]["temp"]
        condition = data["weather"][0]["main"]

        return temp, condition

    except:
        return None, "Clear"

# ==========================================================
# ALERT ENGINE (gTTS)
# ==========================================================
def speak_alert(message):

    try:
        tts = gTTS(text=message, lang="en")

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)

        st.audio(tmp.name)

    except Exception as e:
        st.warning(f"Audio error: {e}")

# ==========================================================
# TRAFFIC SIGN ACTIONS
# ==========================================================
TRAFFIC_ACTIONS = {

    "stop": "STOP VEHICLE",
    "yield": "SLOW DOWN",
    "speed_limit_50": "MAINTAIN SPEED",
    "no_entry": "DO NOT ENTER",
    "turn_left": "TURN LEFT",
    "turn_right": "TURN RIGHT",
    "pedestrian_crossing": "WATCH FOR PEDESTRIANS"
}

# ==========================================================
# RISK ASSESSMENT
# ==========================================================
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

    if weather in ["Rain", "Snow", "Fog"]:
        base_risk += 0.1

    if hour < 6 or hour > 20:
        base_risk += 0.1

    return min(base_risk, 1.0)

# ==========================================================
# CAMERA SETTINGS
# ==========================================================
st.sidebar.header("Camera Settings")

start_camera = st.sidebar.button("Start Camera")
stop_camera = st.sidebar.button("Stop Camera")

FRAME_WINDOW = st.image([])

# ==========================================================
# DATA LOG
# ==========================================================
log_df = pd.DataFrame(columns=["Time","Sign","Action","Risk","Weather","Hour"])

# ==========================================================
# CAMERA LOOP
# ==========================================================
if start_camera:

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        st.error("Camera not detected")
        st.stop()

    last_alert = ""

    while cap.isOpened():

        ret, frame = cap.read()

        if not ret:
            st.error("Cannot read camera frame")
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # ==============================
        # STEP 1: SIGN DETECTION
        # ==============================
        results = model.predict(frame_rgb, verbose=False)[0]

        detected_signs = []
        actions = []
        risks = []

        temp, weather = get_weather(LAT, LON)
        hour = datetime.now().hour

        for box in results.boxes:

            cls_id = int(box.cls[0])
            label = results.names[cls_id]
            confidence = round(box.conf[0].item(),2)

            x1,y1,x2,y2 = map(int,box.xyxy[0])

            cv2.rectangle(frame_rgb,(x1,y1),(x2,y2),(0,255,0),2)

            cv2.putText(frame_rgb,
                        f"{label} {confidence}",
                        (x1,y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0,255,0),
                        2)

            # ==============================
            # STEP 2: RISK
            # ==============================
            risk = risk_score(label,weather,hour)

            action = TRAFFIC_ACTIONS.get(label,"MONITOR")

            detected_signs.append(label)
            actions.append(action)
            risks.append(risk)

            # ==============================
            # STEP 3: VOICE ALERT
            # ==============================
            alert_msg = f"{label} detected. {action}"

            if alert_msg != last_alert:
                speak_alert(alert_msg)
                last_alert = alert_msg

            # ==============================
            # STEP 4: LOGGING
            # ==============================
            log_df.loc[len(log_df)] = [
                datetime.now(),
                label,
                action,
                risk,
                weather,
                hour
            ]

        # ==============================
        # STEP 5: DASHBOARD UPDATE
        # ==============================
        FRAME_WINDOW.image(frame_rgb,channels="RGB")

        st.sidebar.subheader("Detected Signs")
        st.sidebar.write(detected_signs if detected_signs else "None")

        st.sidebar.subheader("Recommended Actions")
        st.sidebar.write(actions if actions else "-")

        st.sidebar.subheader("Risk Scores")
        st.sidebar.write([round(r,2) for r in risks] if risks else "-")

        st.sidebar.subheader("Weather / Time")
        st.sidebar.write(f"Weather: {weather}")
        st.sidebar.write(f"Hour: {hour}")
        st.sidebar.write(f"Temperature: {temp}")

        time.sleep(0.1)

        if stop_camera:
            break

    cap.release()

# ==========================================================
# DOWNLOAD LOG
# ==========================================================
if not log_df.empty:

    st.subheader("Detection Log")

    st.dataframe(log_df)

    csv = log_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download CSV",
        csv,
        "traffic_detection_log.csv",
        "text/csv"
    )