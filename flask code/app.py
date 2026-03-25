from flask import Flask, render_template, Response
import cv2
from ultralytics import YOLO
import requests
import pandas as pd
from datetime import datetime
from gtts import gTTS
import google.generativeai as genai
import os
import time

app = Flask(__name__)

# ================================
# API KEYS
# ================================

GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
OPENWEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"

LAT = 12.9716
LON = 77.5946

# ================================
# GEMINI SETUP
# ================================

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.5-flash")

# ================================
# YOLO MODEL
# ================================

model = YOLO("best.pt")

# ================================
# DATA LOG
# ================================

log_data = []

# ================================
# WEATHER FUNCTION
# ================================

def get_weather():

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={OPENWEATHER_API_KEY}&units=metric"

        data = requests.get(url).json()

        temp = data["main"]["temp"]
        weather = data["weather"][0]["main"]

        return temp, weather

    except:
        return None, "Clear"

# ================================
# SPEED ESTIMATION
# ================================

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

# ================================
# GEMINI AI ANALYSIS
# ================================

def gemini_risk(sign, weather, hour, speed):

    prompt = f"""
    Traffic Sign: {sign}
    Weather: {weather}
    Time: {hour}
    Vehicle Speed: {speed}

    Determine Risk Level and Driver Action.
    """

    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except:
        return "AI decision unavailable"

# ================================
# VOICE ALERT
# ================================

def speak_alert(message):

    path = "static/alerts/alert.mp3"

    tts = gTTS(message)
    tts.save(path)

    return path

# ================================
# VIDEO STREAM
# ================================

def generate_frames():

    cap = cv2.VideoCapture(0)

    while True:

        success, frame = cap.read()

        if not success:
            break

        results = model(frame)[0]

        temp, weather = get_weather()
        hour = datetime.now().hour

        for box in results.boxes:

            cls = int(box.cls[0])
            label = results.names[cls]

            x1,y1,x2,y2 = map(int, box.xyxy[0])

            cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
            cv2.putText(frame,label,(x1,y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,(0,255,0),2)

            speed = estimate_speed(x1)

            decision = gemini_risk(label, weather, hour, speed)

            speak_alert(f"{label} detected")

            log_data.append({
                "time":datetime.now(),
                "sign":label,
                "weather":weather,
                "speed":speed,
                "decision":decision
            })

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# ================================
# ROUTES
# ================================

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/dashboard')
def dashboard():
    return render_template("dashboard.html", logs=log_data)

# ================================

if __name__ == "__main__":
    app.run(debug=True)