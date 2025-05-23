# Face Recognition Session Manager

## Description
This is a Flask-based web application that uses face recognition technology to manage user sessions. Users can sign up by registering their face encoding, sign in using face recognition, and the system automatically logs out users based on face detection. The app tracks user sessions, daily activity, and provides detailed session reports.

## Features
- User signup with face encoding registration
- User signin using face recognition
- Automatic logout based on face recognition
- Session tracking with login/logout times and status
- Daily activity calculation and reporting
- Detailed user activity views by date
- Web interface with multiple pages for session and activity management

## Technologies Used
- Python 3
- Flask web framework
- OpenCV for image processing
- face_recognition library for face encoding and comparison
- SQLite for database storage
- HTML templates for frontend rendering

## Setup and Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd Face_recognition_session_manager
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install required Python packages:
   ```
   pip install flask opencv-python face_recognition numpy
   ```

4. Ensure you have SQLite installed (usually pre-installed on most systems).

## Running the Application
Run the Flask app with:
```
python app.py
```
The app will start in debug mode and be accessible at `http://127.0.0.1:5000/`.

## Usage Overview
- **Signup:** Register a new user by submitting a username and a face image. The face encoding is stored in the database.
- **Signin:** Authenticate by submitting a face image. If recognized, the user is logged in and session starts.  
  URL: `/signin`
- **Autologout:** The system can automatically log out users by detecting their face and updating session status.  
  URL: `/autologout`
- **Sessions Page:** View all user sessions with login/logout times and status.  
  URL: `/sessions`
- **Daily Activity:** View aggregated daily active time per user.  
  URL: `/daily-activity`
- **User Activity:** View detailed session logs and activity for individual users by date.
- **Logout:** Log out the current user and end the session.  
  URL: `/logout`

## Database Schema Overview
- **users:** Stores user information including username, face encoding, login/logout times, and status.
- **daily_activity:** Stores daily total active seconds per user.
- **session_details:** Stores individual session records with login/logout times and duration.

## License
This project is provided as-is without any warranty. Feel free to use and modify it as needed.
