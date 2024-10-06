from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import requests
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure secret key in production

# Simulated plant database and recommendation function
plant_database = [
    {"name": "Sunflower", "description": "Tall annual with large yellow flowers"},
    {"name": "Tomato", "description": "Popular vegetable/fruit plant"},
    {"name": "Lavender", "description": "Fragrant herb with purple flowers"},
    {"name": "Basil", "description": "Aromatic herb used in cooking"},
    {"name": "Rose", "description": "Classic flowering shrub"},
]

def recommend_plants(latitude, longitude):
    # This is a dummy function. Replace with your actual recommendation logic.
    return random.sample(plant_database, 3)

def get_plant_image(plant_name):
    url = f"https://pixabay.com/api/?key=2b10itQ9lIJq3gulBGOljmPyWO&q={plant_name}+plant&image_type=photo&per_page=3"
    try:
        response = requests.get(url)
        data = response.json()
        if data['hits'] and len(data['hits']) > 0:
            return data['hits'][0]['webformatURL']
    except Exception as e:
        print(f"Error fetching image for {plant_name}: {str(e)}")
    return "https://via.placeholder.com/200x200?text=No+Image"

def init_db():
    conn = sqlite3.connect('plants.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_locations 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  latitude REAL NOT NULL, 
                  longitude REAL NOT NULL, 
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('plants.db')
    conn.row_factory = sqlite3.Row
    return conn

def close_db(conn):
    if conn is not None:
        conn.close()

def save_location(latitude, longitude):
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO user_locations (latitude, longitude) VALUES (?, ?)", (latitude, longitude))
        conn.commit()
        return c.lastrowid
    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        return None
    finally:
        close_db(conn)

@app.route('/')
def home():
    return redirect(url_for('location_select'))

@app.route('/location', methods=['GET', 'POST'])
def location_select():
    if request.method == 'POST':
        try:
            latitude = float(request.form['latitude'])
            longitude = float(request.form['longitude'])

            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                flash('Invalid coordinates. Please try again.', 'error')
                return render_template('location_map.html')

            location_id = save_location(latitude, longitude)
            if location_id:
                return redirect(url_for('get_recommendations', location_id=location_id))
            else:
                flash('Error saving location. Please try again.', 'error')
        except ValueError:
            flash('Please enter valid numbers for latitude and longitude.', 'error')

    return render_template('location_map.html')

@app.route('/recommendations/<int:location_id>')
def get_recommendations(location_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT latitude, longitude FROM user_locations WHERE id = ?", (location_id,))
    location = c.fetchone()
    close_db(conn)

    if location:
        latitude, longitude = location['latitude'], location['longitude']
        recommendations = recommend_plants(latitude, longitude)
        
        formatted_recommendations = []
        for rec in recommendations:
            plant_name = rec["name"]
            formatted_rec = {
                "name": plant_name,
                "description": rec["description"],
                "image": get_plant_image(plant_name),
                "score": random.uniform(0.5, 1.0)  # Dummy score
            }
            formatted_recommendations.append(formatted_rec)
        
        return render_template('recommendations.html', recommendations=formatted_recommendations, latitude=latitude, longitude=longitude)
    else:
        flash('Location not found.', 'error')
        return redirect(url_for('location_select'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)