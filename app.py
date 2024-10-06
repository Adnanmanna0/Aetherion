from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import sqlite3
import bcrypt
import re
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_keyf'  # Change this to a secure secret key in production

# Database initialization
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, email TEXT UNIQUE NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_locations (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS recommendations (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, location_id INTEGER NOT NULL, plants TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (id), FOREIGN KEY (location_id) REFERENCES user_locations (id))''')
    
    conn.commit()
    conn.close()

# Database helper functions
def get_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def close_db(conn):
    if conn is not None:
        conn.close()

# User model functions
def create_user(username, password, email):
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Check if username already exists
        c.execute("SELECT 1 FROM users WHERE username=?", (username,))
        if c.fetchone() is not None:
            return False, "Username already exists"
        
        # Check if email already exists
        c.execute("SELECT 1 FROM users WHERE email=?", (email,))
        if c.fetchone() is not None:
            return False, "Email already registered"
        
        # Hash password and insert user
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        c.execute("""INSERT INTO users (username, password, email, created_at) VALUES (?, ?, ?, ?)""", (username, hashed_password, email, datetime.now()))
        conn.commit()
        return True, "User created successfully"
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"
    finally:
        close_db(conn)

def verify_user(username, password):
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username=?", (username,))
        user = c.fetchone()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return True, user['id']
        return False, None
    except sqlite3.Error as e:
        return False, None
    finally:
        close_db(conn)

def save_location(user_id, latitude, longitude):
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""INSERT INTO user_locations (user_id, latitude, longitude) VALUES (?, ?, ?)""", (user_id, latitude, longitude))
        conn.commit()
        return c.lastrowid
    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        return None
    finally:
        close_db(conn)

def save_recommendation(user_id, location_id, plants):
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        plants_json = json.dumps(plants)
        c.execute("""INSERT INTO recommendations (user_id, location_id, plants) VALUES (?, ?, ?)""", (user_id, location_id, plants_json))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        return False
    finally:
        close_db(conn)

def get_user_recommendations(user_id):
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""SELECT ul.latitude, ul.longitude, r.plants FROM user_locations ul JOIN recommendations r ON ul.id = r.location_id WHERE ul.user_id = ? ORDER BY r.created_at DESC""", (user_id,))
        return c.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        return []
    finally:
        close_db(conn)

# Validation functions
def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

def validate_email(email):
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_regex, email):
        return True, "Email is valid"
    return False, "Invalid email format"

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Your plant recommendation model function (placeholder)
def get_plant_recommendations(latitude, longitude):
    # This is where you'd integrate your actual plant recommendation model
    # For now, returning dummy data
    return [
        {"name": "Tomatoes", "confidence": 0.9},
        {"name": "Lettuce", "confidence": 0.8},
        {"name": "Carrots", "confidence": 0.7}
    ]

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login.html')
        
        success, user_id = verify_user(username, password)
        if success:
            session['user_id'] = user_id
            session['username'] = username
            flash('Logged in successfully', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip()
        
        # Validate input
        if not username or not password or not email:
            flash('All fields are required', 'error')
            return render_template('signup.html')
        
        # Validate password
        password_valid, password_message = validate_password(password)
        if not password_valid:
            flash(password_message, 'error')
            return render_template('signup.html')
        
        # Validate email
        email_valid, email_message = validate_email(email)
        if not email_valid:
            flash(email_message, 'error')
            return render_template('signup.html')
        
        # Create user
        success, message = create_user(username, password, email)
        if success:
            flash('Account created successfully. Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
    
    return render_template('signup.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    recommendations = get_user_recommendations(user_id)
    return render_template('dashboard.html', recommendations=recommendations)

@app.route('/location', methods=['GET', 'POST'])
@login_required
def location_select():
    if request.method == 'POST':
        try:
            latitude = float(request.form['latitude'])
            longitude = float(request.form['longitude'])
            
            # Validate coordinates
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                flash('Invalid coordinates. Please try again.', 'error')
                return render_template('location.html')
            
            location_id = save_location(session['user_id'], latitude, longitude)
            if location_id:
                return redirect(url_for('get_recommendations', location_id=location_id))
            else:
                flash('Error saving location. Please try again.', 'error')
        except ValueError:
            flash('Please enter valid numbers for latitude and longitude.', 'error')
    
    return render_template('location.html')

@app.route('/recommendations/<int:location_id>')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)