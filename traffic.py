import os
import cv2
import time
import sqlite3
import requests
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, Response, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from ultralytics import YOLO
from gtts import gTTS

# ==========================================================
# APP CONFIGURATION
# ==========================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///traffic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ==========================================================
# DATABASE MODEL
# ==========================================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==========================================================
# GLOBAL VARIABLES & SETTINGS
# ==========================================================
# Default Settings
SETTINGS = {
    'model_path': 'best.pt',
    'api_key': '',
    'lat': 12.9716,
    'lon': 77.5946
}

# Traffic Actions Dictionary
TRAFFIC_ACTIONS = {
    "stop": "STOP VEHICLE",
    "yield": "SLOW DOWN",
    "speed_limit_50": "MAINTAIN SPEED",
    "no_entry": "DO NOT ENTER",
    "turn_left": "TURN LEFT",
    "turn_right": "TURN RIGHT",
    "pedestrian_crossing": "WATCH FOR PEDESTRIANS"
}

# State variables
camera_active = False
latest_alert_text = ""
detection_log = []

# ==========================================================
# HELPER FUNCTIONS
# ==========================================================
def get_weather(lat, lon, api_key):
    if not api_key:
        return None, "Clear"
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        data = requests.get(url).json()
        temp = data["main"]["temp"]
        condition = data["weather"][0]["main"]
        return temp, condition
    except:
        return None, "Clear"

def risk_score(sign_label, weather, hour):
    base_risk = {
        "stop": 0.9, "yield": 0.7, "speed_limit_50": 0.5,
        "no_entry": 0.95, "turn_left": 0.5, "turn_right": 0.5,
        "pedestrian_crossing": 0.8
    }.get(sign_label, 0.4)

    if weather in ["Rain", "Snow", "Fog"]:
        base_risk += 0.1
    if hour < 6 or hour > 20:
        base_risk += 0.1
    
    return min(base_risk, 1.0)

def generate_audio(text):
    try:
        tts = gTTS(text=text, lang="en")
        audio_path = os.path.join('static', 'audio', 'alert.mp3')
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        tts.save(audio_path)
        return audio_path
    except Exception as e:
        print(f"Audio Error: {e}")
        return None

# ==========================================================
# VIDEO STREAMING GENERATOR
# ==========================================================
def gen_frames():
    global camera_active, latest_alert_text, detection_log
    
    # Load Model
    try:
        model = YOLO(SETTINGS['model_path'])
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    cap = cv2.VideoCapture(0)
    
    while camera_active:
        success, frame = cap.read()
        if not success:
            break
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detection
        results = model.predict(frame_rgb, verbose=False)[0]
        
        temp, weather = get_weather(SETTINGS['lat'], SETTINGS['lon'], SETTINGS['api_key'])
        hour = datetime.now().hour
        
        for box in results.boxes:
            cls_id = int(box.cls[0])
            label = results.names[cls_id]
            conf = round(box.conf[0].item(), 2)
            
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            # Draw Box
            cv2.rectangle(frame_rgb, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame_rgb, f"{label} {conf}", (x1, y1-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Logic
            risk = risk_score(label, weather, hour)
            action = TRAFFIC_ACTIONS.get(label, "MONITOR")
            
            # Alert Logic
            alert_msg = f"{label} detected. {action}."
            if alert_msg != latest_alert_text:
                latest_alert_text = alert_msg
                generate_audio(alert_msg)
            
            # Logging
            detection_log.append({
                "time": datetime.now(),
                "sign": label,
                "action": action,
                "risk": risk,
                "weather": weather,
                "hour": hour
            })

        # Encode Frame
        ret, buffer = cv2.imencode('.jpg', frame_rgb)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    cap.release()

# ==========================================================
# ROUTES
# ==========================================================

@app.route('/')
def home():
    return render_template('home.html')

# ----- AUTH -----
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_pw)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            flash('Username already exists')
            
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ----- SETTINGS -----
@app.route('/input', methods=['GET', 'POST'])
@login_required
def input_settings():
    global SETTINGS
    if request.method == 'POST':
        SETTINGS['model_path'] = request.form.get('model_path')
        SETTINGS['api_key'] = request.form.get('api_key')
        SETTINGS['lat'] = float(request.form.get('lat'))
        SETTINGS['lon'] = float(request.form.get('lon'))
        flash('Settings Updated Successfully!')
        return redirect(url_for('dashboard'))
    
    return render_template('input.html', settings=SETTINGS)

# ----- DASHBOARD -----
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user, camera_active=camera_active)

@app.route('/video_feed')
@login_required
def video_feed():
    global camera_active
    camera_active = True
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_camera')
@login_required
def start_camera():
    global camera_active
    camera_active = True
    return redirect(url_for('dashboard'))

@app.route('/stop_camera')
@login_required
def stop_camera():
    global camera_active
    camera_active = False
    return redirect(url_for('dashboard'))

@app.route('/get_status')
@login_required
def get_status():
    # Returns latest detection data to frontend via AJAX
    global latest_alert_text, detection_log
    last_log = detection_log[-1] if detection_log else {
        "sign": "N/A",
        "action": "N/A",
        "risk": "N/A",
        "weather": "N/A"
    }
    return jsonify({
        "alert": latest_alert_text,
        "data": last_log
    })

# ----- RESULTS -----
@app.route('/result')
@login_required
def result():
    global detection_log
    df = pd.DataFrame(detection_log)
    
    # Save to temp CSV for download
    csv_path = os.path.join('static', 'log.csv')
    df.to_csv(csv_path, index=False)
    
    return render_template('result.html', tables=df.head(50).to_html(classes='data', header="true"), csv_link=csv_path)

# ==========================================================
# MAIN
# ==========================================================
if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists('traffic.db'):
            db.create_all()
    app.run(debug=True, threaded=True)