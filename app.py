import os
import sqlite3
import cv2
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from geopy.geocoders import Nominatim
from ultralytics import YOLO

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_this'  # Required for login security

# --- CONFIGURATION ---
# 1. Load AI Model
try:
    model = YOLO('best.pt')
    print("✅ AI Model Loaded")
except:
    print("⚠ 'best.pt' not found. Using 'yolov8n.pt' for testing.")
    model = YOLO('yolov8n.pt')

# 2. Setup Geocoder (Converts Lat/Long -> Address)
geolocator = Nominatim(user_agent="smart_city_app_v1")

# 3. Setup Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('smart_city.db')
    c = conn.cursor()
    # Create Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  role TEXT,    -- 'citizen' or 'mayor'
                  region TEXT)  -- e.g., 'Chennai' (only for mayors)
              ''')
    # Create Reports Table
    c.execute('''CREATE TABLE IF NOT EXISTS reports
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  image_path TEXT,
                  annotated_path TEXT,
                  hazard_type TEXT,
                  latitude TEXT,
                  longitude TEXT,
                  address TEXT,
                  assigned_to TEXT,
                  status TEXT)
              ''')
    conn.commit()
    conn.close()

# --- USER CLASS ---
class User(UserMixin):
    def __init__(self, id, username, role, region):
        self.id = id
        self.username = username
        self.role = role
        self.region = region

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('smart_city.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    u = c.fetchone()
    conn.close()
    if u:
        return User(id=u[0], username=u[1], role=u[3], region=u[4])
    return None

# --- ROUTES ---

@app.route('/')
def home():
    if current_user.is_authenticated:
        if current_user.role == 'mayor':
            return redirect(url_for('mayor_dashboard'))
        return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))

# AUTHENTICATION ROUTES
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        region = request.form.get('region', 'General')

        try:
            conn = sqlite3.connect('smart_city.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password, role, region) VALUES (?, ?, ?, ?)",
                      (username, password, role, region))
            conn.commit()
            conn.close()
            flash("Account created! Please login.", "success")
            return redirect(url_for('login'))
        except:
            flash("Username already exists.", "danger")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('smart_city.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            login_user(User(id=user[0], username=user[1], role=user[3], region=user[4]))
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials.", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# CITIZEN ROUTES - (FIXED FOR FILE PATHS)
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def user_dashboard():
    if request.method == 'POST':
        file = request.files['file']
        lat = request.form['lat']
        lon = request.form['lon']

        if file:
            # --- FIX STARTS HERE: ABSOLUTE PATHS ---
            
            # 1. Get the Absolute Path (C:\Users\...\static\uploads)
            basedir = os.path.abspath(os.path.dirname(__file__))
            upload_folder = os.path.join(basedir, 'static', 'uploads')
            
            # Create folder if it doesn't exist
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            # 2. Save Original Image using Absolute Path
            filename = file.filename
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)

            # 3. AI Detection (Pass the Absolute Path to YOLO)
            results = model(filepath)
            
            # Get Class Name
            try:
                class_id = int(results[0].boxes.cls[0])
                hazard = results[0].names[class_id]
            except:
                hazard = "Unknown Hazard"

            # 4. Save Annotated Image using Absolute Path
            annotated_filename = "detected_" + filename
            annotated_path_abs = os.path.join(upload_folder, annotated_filename)
            cv2.imwrite(annotated_path_abs, results[0].plot())

            # 5. Prepare Database Paths (These must be RELATIVE for HTML to see them)
            # Convert back to "static/uploads/image.jpg"
            db_image_path = f"static/uploads/{filename}"
            db_annotated_path = f"static/uploads/{annotated_filename}"

            # --- FIX ENDS HERE ---

            # 6. Get Address from GPS
            try:
                location_info = geolocator.reverse(f"{lat}, {lon}")
                address = location_info.address
                city = location_info.raw['address'].get('city', 'Unknown')
            except:
                address = "GPS Location Found (Address Unavailable)"
                city = "General"

            # 7. Assign to Mayor
            assigned_to = f"{city} Mayor"

            # 8. Save to DB (Using the relative paths for HTML)
            conn = sqlite3.connect('smart_city.db')
            c = conn.cursor()
            c.execute("""INSERT INTO reports (user_id, image_path, annotated_path, hazard_type, latitude, longitude, address, assigned_to, status)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (current_user.id, db_image_path, db_annotated_path, hazard, lat, lon, address, assigned_to, "Pending"))
            conn.commit()
            conn.close()
            flash("Report Submitted Successfully!", "success")

    # Load User History
    conn = sqlite3.connect('smart_city.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM reports WHERE user_id = ? ORDER BY id DESC", (current_user.id,))
    reports = c.fetchall()
    conn.close()
    return render_template('user_dashboard.html', reports=reports, user=current_user)

# MAYOR ROUTES
@app.route('/admin')
@login_required
def mayor_dashboard():
    if current_user.role != 'mayor':
        return "Access Denied"
    
    conn = sqlite3.connect('smart_city.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Filter reports by Mayor's Region (e.g., "Chennai" matches "Chennai, TN")
    c.execute("SELECT * FROM reports WHERE address LIKE ? ORDER BY id DESC", (f'%{current_user.region}%',))
    reports = c.fetchall()
    conn.close()
    return render_template('mayor_dashboard.html', reports=reports, user=current_user)

@app.route('/resolve/<int:id>')
@login_required
def resolve_issue(id):
    if current_user.role == 'mayor':
        conn = sqlite3.connect('smart_city.db')
        c = conn.cursor()
        c.execute("UPDATE reports SET status = 'Resolved' WHERE id = ?", (id,))
        conn.commit()
        conn.close()
    return redirect(url_for('mayor_dashboard'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)