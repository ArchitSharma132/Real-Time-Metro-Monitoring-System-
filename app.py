import os
import random
import requests
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, redirect, url_for
from flask_cors import CORS
from sqlalchemy import create_engine, text, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# --- Absolute Path Setup ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# --- App Initialization ---
app = Flask(__name__)
app.secret_key = 'a-very-secret-and-random-key-for-sessions'
CORS(app, supports_credentials=True)

# --- Database Setup ---
DB_URL = f"sqlite:///{os.path.join(BASE_DIR, 'metro.db')}"
engine = create_engine(DB_URL)
Base = declarative_base()

class User(UserMixin, Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# --- Login Manager ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'serve_login_page'

@login_manager.user_loader
def load_user(user_id):
    return session.get(User, int(user_id))

# --- ROUTES ---

@app.route('/')
def serve_login_page():
    if not session.query(User).filter_by(username='admin').first():
        default_user = User(username='admin', password='password')
        session.add(default_user)
        session.commit()
    return send_from_directory(BASE_DIR, 'login.html')

@app.route('/dashboard')
@login_required
def serve_dashboard():
    return send_from_directory(BASE_DIR, 'sih-2prjct.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = session.query(User).filter_by(username=data.get('username')).first()
    if user and user.password == data.get('password'):
        login_user(user)
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('serve_login_page'))
    
@app.route('/api/current_user')
@login_required
def get_current_user_api():
    return jsonify({"is_logged_in": True, "username": current_user.username})

# --- ALL DATA API ROUTES ---

@app.route("/api/status")
@login_required
def get_system_status():
    status = {"backend_status": "OK", "database_status": "Error", "database_details": "N/A"}
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT count(*) FROM stops")).scalar_one()
            status["database_status"] = "OK"
            status["database_details"] = f"Connected and found {result} stops."
    except Exception as e:
        status["database_details"] = f"Could not connect. Error: {e}"
    return jsonify(status)

@app.route("/api/live")
@login_required
def get_live_stats():
    stats = {"currentDemand": 1350, "activeTrains": 20, "avgWaitTime": 2.5, "systemEfficiency": 95.8}
    return jsonify(stats)

@app.route("/api/schedule/suggested")
@login_required
def get_suggested_schedule():
    schedule = [
        {"time": "10:10", "status": "AI Suggested"},
        {"time": "10:18", "status": "AI Suggested"},
        {"time": "10:25", "status": "AI Suggested"},
        {"time": "10:32", "status": "AI Suggested"},
        {"time": "10:40", "status": "AI Suggested"},
    ]
    return jsonify(schedule)

@app.route("/api/schedule/current")
@login_required
def get_current_schedule():
    schedule = [
        {"time": "10:12", "status": "Confirmed"},
        {"time": "10:20", "status": "Confirmed"},
        {"time": "10:28", "status": "Manual Override"},
        {"time": "10:36", "status": "Confirmed"},
        {"time": "10:44", "status": "Confirmed"},
    ]
    return jsonify(schedule)
@app.route("/api/analytics/historical_demand")
@login_required
def get_historical_demand():
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT strftime('%H:00', arrival_time) as hour, COUNT(trip_id) as demand FROM stop_times WHERE arrival_time IS NOT NULL GROUP BY hour ORDER BY hour;")).fetchall()
            labels = [row._mapping['hour'] for row in rows]
            actual = [row._mapping['demand'] for row in rows]
            predicted = [d + random.randint(-15, 15) for d in actual]
        return jsonify({"labels": labels, "actual": actual, "predicted": predicted})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/simulation/initial_state")
@login_required
def get_simulation_state():
    try:
        station_types = {"Aluva": "hub", "Edapally": "hub", "JLN Stadium": "hub"}
        current_hour = datetime.now().hour
        multiplier = 1.5 if 7 <= current_hour < 10 or 16 <= current_hour < 20 else 0.8
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT stop_name FROM stops LIMIT 12;")).fetchall()
            response_data = []
            for row in rows:
                name = row._mapping['stop_name']
                base_demand = 150 if station_types.get(name) == "hub" else 80
                predicted = int(base_demand * multiplier) + random.randint(-20, 20)
                actual = predicted + random.randint(-30, 30)
                response_data.append({"station_name": name, "actual_passengers": max(20, actual), "predicted_passengers": max(25, predicted)})
        return jsonify(response_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/location_forecast")
@login_required
def get_location_forecast():
    forecast = [
        {"name": "Aluva", "lat": 10.1068, "lon": 76.3533, "predicted_demand": 155},
        {"name": "Pulinchodu", "lat": 10.096, "lon": 76.347, "predicted_demand": 95}, # Corrected this line
        {"name": "Companypady", "lat": 10.087, "lon": 76.342, "predicted_demand": 75},
        {"name": "Muttom", "lat": 10.0736, "lon": 76.3421, "predicted_demand": 80},
        {"name": "Cusat", "lat": 10.0468, "lon": 76.3283, "predicted_demand": 210},
        {"name": "Edapally", "lat": 10.0267, "lon": 76.3116, "predicted_demand": 250},
        {"name": "JLN Stadium", "lat": 9.9984, "lon": 76.3073, "predicted_demand": 180},
        {"name": "MG Road", "lat": 9.9701, "lon": 76.2847, "predicted_demand": 280},
        {"name": "Vyttila", "lat": 9.9678, "lon": 76.3216, "predicted_demand": 120},
    ]
    return jsonify(forecast)

@app.route("/api/chat", methods=['POST'])
@login_required
def chat_proxy():
    # --- This key is now defined at the top of the file ---
    GEMINI_API_KEY = ""
    GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    if "YOUR_GEMINI_API_KEY" in GEMINI_API_KEY or not GEMINI_API_KEY:
        return jsonify({"error": "Server is missing the Gemini API Key."}), 500

    user_prompt = request.json.get('prompt')
    system_context = request.json.get('context')
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": f"{system_context}\n\nUser Query: \"{user_prompt}\""}]}]}
    
    try:
        # We use the requests library that we imported
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        error_details = e.response.json() if e.response else str(e)
    return jsonify({"error": "Failed to communicate with the AI service.", "details": error_details}), 500
    
if __name__ == "__main__":

    app.run(debug=True, port=3001)
