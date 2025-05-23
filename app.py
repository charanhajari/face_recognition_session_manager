from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import cv2
from datetime import datetime
import face_recognition
import numpy as np
import base64
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necessary for session management

# Initialize database
def init_db():
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                (user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT,
                 encoding BLOB,
                 time_of_login TEXT,
                 time_of_logout TEXT,
                 status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_activity
                (date TEXT,
                 username TEXT,
                 total_active_seconds INTEGER,
                 PRIMARY KEY (date, username))''')
    c.execute('''CREATE TABLE IF NOT EXISTS session_details
                (session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT,
                 login_time TEXT,
                 logout_time TEXT,
                 duration_seconds INTEGER,
                 date TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_face_encoding(image):
    face_encodings = face_recognition.face_encodings(image)
    return face_encodings[0] if face_encodings else None

@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return render_template('index.html')

@app.route('/home')
def home():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    return redirect(url_for('index'))

def calculate_daily_activity():
    """Calculate and store daily active time for all users"""
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    
    # Get all completed sessions
    c.execute("""SELECT username, login_time, logout_time 
                FROM session_details 
                WHERE login_time IS NOT NULL 
                AND logout_time IS NOT NULL""")
    sessions = c.fetchall()
    
    # Calculate daily totals
    daily_totals = {}
    for username, login, logout in sessions:
        login_date = datetime.strptime(login, '%Y-%m-%d %H:%M:%S.%f').date()
        logout_time = datetime.strptime(logout, '%Y-%m-%d %H:%M:%S.%f')
        login_time = datetime.strptime(login, '%Y-%m-%d %H:%M:%S.%f')
        duration = (logout_time - login_time).total_seconds()
        
        date_str = login_date.isoformat()
        key = (date_str, username)
        daily_totals[key] = daily_totals.get(key, 0) + duration
    
    # Update daily_activity table
    for (date, username), total_seconds in daily_totals.items():
        c.execute("""INSERT OR REPLACE INTO daily_activity 
                    (date, username, total_active_seconds) 
                    VALUES (?, ?, ?)""", 
                    (date, username, int(total_seconds)))
    
    conn.commit()
    conn.close()

@app.route('/sessions')
def sessions():
    """Display all user sessions"""
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    c.execute("SELECT username, time_of_login, time_of_logout, status FROM users")
    sessions = c.fetchall()
    conn.close()
    return render_template('sessions.html', sessions=sessions)

@app.route('/daily-activity')
def daily_activity():
    """Display daily activity summary with date filtering"""
    calculate_daily_activity()
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    c.execute("SELECT date, username, total_active_seconds FROM daily_activity ORDER BY date DESC")
    daily_activity = c.fetchall()
    conn.close()
    return render_template('daily_activity.html', daily_activity=daily_activity)

@app.route('/user-activity/<username>')
def user_activity(username):
    """Display detailed activity for a specific user"""
    selected_date = request.args.get('date')
    conn = sqlite3.connect('faces.db')
    c = conn.cursor()
    
    # Get all sessions for this user (filter by date if provided)
    if selected_date:
        c.execute("""SELECT date, login_time, logout_time, duration_seconds 
                   FROM session_details 
                   WHERE username = ? AND date = ?
                   ORDER BY login_time DESC""", (username, selected_date))
    else:
        c.execute("""SELECT date, login_time, logout_time, duration_seconds 
                   FROM session_details 
                   WHERE username = ? 
                   ORDER BY login_time DESC""", (username,))
    sessions = c.fetchall()
    
    # Get daily totals for this user (filter by date if provided)
    if selected_date:
        c.execute("""SELECT date, total_active_seconds 
                   FROM daily_activity 
                   WHERE username = ? AND date = ?
                   ORDER BY date DESC""", (username, selected_date))
    else:
        c.execute("""SELECT date, total_active_seconds 
                   FROM daily_activity 
                   WHERE username = ? 
                   ORDER BY date DESC""", (username,))
    daily_totals = c.fetchall()
    
    conn.close()
    
    # Group sessions by date
    sessions_by_date = {}
    for date, login, logout, seconds in sessions:
        if date not in sessions_by_date:
            sessions_by_date[date] = []
        sessions_by_date[date].append({
            'login': login,
            'logout': logout,
            'duration': seconds
        })
    
    return render_template('user_activity.html', 
                         username=username,
                         sessions_by_date=sessions_by_date,
                         daily_totals=daily_totals,
                         selected_date=selected_date)

@app.route('/autologout', methods=['POST'])
def autologout():
    data = request.get_json()
    image_data = data['image']
    
    try:
        image = np.frombuffer(base64.b64decode(image_data), dtype=np.uint8)
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
        face_encoding = get_face_encoding(image)
        
        if face_encoding is None:
            return jsonify({'status': 'error', 'message': 'No face detected'})

        conn = sqlite3.connect('faces.db')
        c = conn.cursor()
        c.execute("SELECT username, encoding FROM users")
        users = c.fetchall()
        conn.close()

        for username, encoding in users:
            stored_encoding = np.frombuffer(encoding, dtype=np.float64)
            matches = face_recognition.compare_faces([stored_encoding], face_encoding)
            if matches[0]:
                conn = sqlite3.connect('faces.db')
                c = conn.cursor()
                c.execute("UPDATE users SET time_of_logout = ?, status = 'inactive' WHERE username = ? AND encoding = ?", 
                         (datetime.now(), username, encoding))
                conn.commit()
                conn.close()
                
                # Clear session if logging out current user
                if 'username' in session and session['username'] == username:
                    session.pop('username', None)
                    session.pop('user_id', None)
                
                return jsonify({
                    'status': 'success', 
                    'message': 'Logout successful!',
                    'username': username,
                    'redirect': url_for('index')
                })
        
        return jsonify({'status': 'error', 'message': 'Face not recognized'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/logout', methods=['GET'])
def logout():
    if 'username' in session:
        conn = sqlite3.connect('faces.db')
        c = conn.cursor()
        c.execute("UPDATE users SET time_of_logout = ?, status = 'inactive' WHERE username = ?", 
                 (datetime.now(), session['username']))
        conn.commit()
        conn.close()
        session.pop('username', None)
    return render_template('logout.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data['username']
    image_data = data['image']
    
    image = np.frombuffer(base64.b64decode(image_data), dtype=np.uint8)
    if image_data:  # Check if image_data is not empty
        image = np.frombuffer(base64.b64decode(image_data), dtype=np.uint8)
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    else:
        return jsonify({'status': 'error', 'message': 'No image data received'})
    face_encoding = get_face_encoding(image)
    
    if face_encoding is not None:
        conn = sqlite3.connect('faces.db')
        c = conn.cursor()
        try:
            # Insert new user with face encoding
            c.execute("INSERT INTO users (username, encoding) VALUES (?, ?)", 
                     (username, face_encoding.tobytes()))
            conn.commit()
            response = {'status': 'success', 'message': 'User registered successfully'}
        except Exception as e:
            response = {'status': 'error', 'message': f'Registration failed: {str(e)}'}
        conn.close()
    else:
        response = {'status': 'error', 'message': 'No face detected'}
    
    return jsonify(response)

@app.route('/signin', methods=['POST'])
def signin():
    try:
        data = request.json
        if not data or 'image' not in data:
            return jsonify({'status': 'error', 'message': 'No image data received'})

        image_data = data['image']
        if not image_data:
            return jsonify({'status': 'error', 'message': 'Empty image data'})

        image = np.frombuffer(base64.b64decode(image_data), dtype=np.uint8)
        if image.size == 0:
            return jsonify({'status': 'error', 'message': 'Invalid image data'})

        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
        if image is None:
            return jsonify({'status': 'error', 'message': 'Failed to decode image'})

        face_encoding = get_face_encoding(image)
        if face_encoding is None:
            return jsonify({'status': 'error', 'message': 'No face detected'})

        conn = sqlite3.connect('faces.db')
        c = conn.cursor()
        c.execute("SELECT username, encoding FROM users")
        users = c.fetchall()
        conn.close()

        for username, encoding in users:
            stored_encoding = np.frombuffer(encoding, dtype=np.float64)
            matches = face_recognition.compare_faces([stored_encoding], face_encoding)
            if matches[0]:
                conn = sqlite3.connect('faces.db')
                c = conn.cursor()
                c.execute("SELECT user_id, status FROM users WHERE username = ? AND encoding = ?", 
                         (username, encoding))
                user_data = c.fetchone()
                conn.close()
                
                if user_data and user_data[1] == 'active':
                    return jsonify({'status': 'error', 'message': 'This face is already logged in'})
                
                session['username'] = username
                session['user_id'] = user_data[0]
                conn = sqlite3.connect('faces.db')
                c = conn.cursor()
                c.execute("UPDATE users SET time_of_login = ?, status = ? WHERE user_id = ?", 
                         (datetime.now(), 'active', user_data[0]))
                conn.commit()
                conn.close()
                return jsonify({'status': 'success', 'message': 'Login successful', 'redirect': url_for('index')})
        
        return jsonify({'status': 'error', 'message': 'Face not recognized'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error processing request: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)
