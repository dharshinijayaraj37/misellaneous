import streamlit as st
import cv2
from ultralytics import YOLO
import requests
import pandas as pd
from datetime import datetime
from gtts import gTTS
import tempfile
import time
import google.generativeai as genai
import plotly.express as px

# ======================================================
# API KEYS (INLINE)
# ======================================================

GEMINI_API_KEY = "AIzaSyB7PICa_ls2ovFKP-3H2ZDK3dDxQ6wlQcw"
OPENWEATHER_API_KEY = "587eb73cbf6e07c4f2de5cca079b5ed5"

# Location
LAT = 12.9716
LON = 77.5946

# ======================================================
# GEMINI AI CONFIG
# ======================================================

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.5-flash")

# ======================================================
# STREAMLIT CONFIG
# ======================================================

st.set_page_config(page_title="AI Traffic Safety System", layout="wide")
st.title("🚦 AI Context-Aware Traffic Sign Detection System")

# ======================================================
# YOLO MODEL
# ======================================================

st.sidebar.header("Model Settings")
model_path = st.sidebar.text_input("YOLO Model Path", "best.pt")

try:
    yolo_model = YOLO(model_path)
except:
    st.error("YOLO model not found")
    st.stop()

# ======================================================
# WEATHER FUNCTION
# ======================================================

def get_weather():

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={OPENWEATHER_API_KEY}&units=metric"

        data = requests.get(url).json()

        temp = data["main"]["temp"]
        weather = data["weather"][0]["main"]

        return temp, weather

    except:
        return None, "Clear"

# ======================================================
# SPEED ESTIMATION
# ======================================================

prev_x = None
prev_time = None

def estimate_speed(x):

    global prev_x, prev_time

    current_time = time.time()

    if prev_x is None:
        prev_x = x
        prev_time = current_time
        return 0

    distance = abs(x - prev_x)
    time_diff = current_time - prev_time

    speed = distance / time_diff

    prev_x = x
    prev_time = current_time

    return round(speed * 0.1, 2)

# ======================================================
# GEMINI AI RISK ANALYSIS
# ======================================================

def gemini_risk(sign, weather, hour, speed):

    prompt = f"""
    You are an intelligent road safety AI.

    Traffic Sign: {sign}
    Weather: {weather}
    Time of Day: {hour}
    Vehicle Speed: {speed}

    Analyze the situation and return:

    Risk Level (Low/Medium/High)
    Recommended Driver Action
    """

    try:
        response = gemini_model.generate_content(prompt)
        return response.text

    except:
        return "AI decision unavailable"

# ======================================================
# VOICE ALERT
# ======================================================

def speak_alert(text):

    try:
        tts = gTTS(text=text)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")

        tts.save(tmp.name)

        st.audio(tmp.name)

    except:
        pass

# ======================================================
# CAMERA SETTINGS
# ======================================================

st.sidebar.header("Camera")

start_camera = st.sidebar.button("Start Camera")
stop_camera = st.sidebar.button("Stop Camera")

frame_display = st.image([])

# ======================================================
# DATA LOG
# ======================================================

log_df = pd.DataFrame(columns=[
    "Time","Sign","Weather","Speed","AI Decision"
])

# ======================================================
# CAMERA LOOP
# ======================================================

if start_camera:

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        st.error("Camera not detected")
        st.stop()

    last_alert = ""

    while cap.isOpened():

        ret, frame = cap.read()

        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = yolo_model.predict(frame_rgb, verbose=False)[0]

        temp, weather = get_weather()
        hour = datetime.now().hour

        for box in results.boxes:

            cls = int(box.cls[0])
            label = results.names[cls]

            x1,y1,x2,y2 = map(int, box.xyxy[0])

            cv2.rectangle(frame_rgb,(x1,y1),(x2,y2),(0,255,0),2)

            cv2.putText(frame_rgb,label,(x1,y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,(0,255,0),2)

            # SPEED ESTIMATION
            speed = estimate_speed(x1)

            # GEMINI AI DECISION
            decision = gemini_risk(label, weather, hour, speed)

            st.sidebar.subheader("Gemini AI Decision")
            st.sidebar.write(decision)

            # VOICE ALERT
            alert_msg = f"{label} detected"

            if alert_msg != last_alert:

                speak_alert(alert_msg)

                last_alert = alert_msg

            # LOG DATA
            log_df.loc[len(log_df)] = [
                datetime.now(),
                label,
                weather,
                speed,
                decision
            ]

        frame_display.image(frame_rgb, channels="RGB")

        st.sidebar.subheader("Environment")

        st.sidebar.write(f"Weather: {weather}")
        st.sidebar.write(f"Temperature: {temp}")
        st.sidebar.write(f"Hour: {hour}")

        time.sleep(0.1)

        if stop_camera:
            break

    cap.release()

# ======================================================
# DASHBOARD ANALYTICS
# ======================================================

if not log_df.empty:

    st.subheader("Detection Log")

    st.dataframe(log_df)

    # TRAFFIC SIGN FREQUENCY
    st.subheader("Traffic Sign Frequency")

    sign_counts = log_df["Sign"].value_counts()

    fig = px.bar(sign_counts,
                 x=sign_counts.index,
                 y=sign_counts.values,
                 labels={"x":"Sign","y":"Count"})

    st.plotly_chart(fig)

    # SPEED TIMELINE
    st.subheader("Speed Timeline")

    fig2 = px.line(log_df,
                   x="Time",
                   y="Speed")

    st.plotly_chart(fig2)

    # DOWNLOAD CSV
    csv = log_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Log",
        csv,
        "traffic_log.csv",
        "text/csv"
    )