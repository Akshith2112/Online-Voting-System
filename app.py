import streamlit as st
import sqlite3
import hashlib
import re
from datetime import datetime
import pandas as pd
import shutil
import cv2
import face_recognition
import numpy as np
import os
import time
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(page_title="Online Voting System", page_icon="🗳️", layout="wide")

# Create directory for face encodings
ENCODINGS_DIR = "face_encodings"
if not os.path.exists(ENCODINGS_DIR):
    os.makedirs(ENCODINGS_DIR)

# Custom CSS for dark theme and centered buttons
st.markdown("""
    <style>
        body {
            background: linear-gradient(135deg, #1a1a1a, #2d2d2d);
            color: #ffffff;
            font-family: Arial, sans-serif;
        }
        h1, h2, p, .stMarkdown {
            color: #ffffff;
        }
        .main-header {
            font-size: 48px;
            font-weight: bold;
            color: #00aaff;
            text-align: center;
            padding: 20px 0;
        }
        .subheader {
            font-size: 24px;
            color: #cccccc;
            text-align: center;
            margin-bottom: 40px;
        }
        .cta-button {
            background-color: #00aaff;
            color: #ffffff;
            border-radius: 8px;
            padding: 12px 30px;
            font-size: 18px;
            text-align: center;
            display: block;
            margin: 10px auto;
            transition: all 0.3s ease;
            text-decoration: none;
            width: 200px;
        }
        .cta-button:hover {
            background-color: #0088cc;
            transform: scale(1.05);
        }
        .button-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 300px;
        }
        .form-section {
            background-color: #2a2a2a;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            margin: 20px auto;
            max-width: 600px;
        }
        .stButton>button {
            background-color: #00aaff;
            color: #ffffff;
            border-radius: 5px;
            padding: 10px 20px;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #0088cc;
            transform: scale(1.05);
        }
        .stTextInput>div>input, .stSelectbox>div>select {
            border: 1px solid #00aaff;
            border-radius: 5px;
            background-color: #2a2a2a;
            color: #ffffff;
        }
        .stForm {
            background-color: #2a2a2a;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.5);
        }
        .stTabs {
            background-color: #1a1a1a;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.5);
        }
        .stMetric {
            background-color: #2a2a2a;
            padding: 10px;
            border-radius: 5px;
        }
        .security-text {
            font-size: 14px;
            color: #999;
            text-align: center;
            margin-top: 20px;
            padding-bottom: 20px;
        }
        .webcam-container {
            text-align: center;
            margin: 20px 0;
        }
        .countdown {
            font-size: 18px;
            color: #00aaff;
            text-align: center;
            margin-top: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# Database setup
def init_db():
    conn = sqlite3.connect('election.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE,
                 password TEXT,
                 full_name TEXT,
                 gender TEXT,
                 has_voted BOOLEAN,
                 face_encoding_path TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS candidates (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT UNIQUE,
                 description TEXT,
                 votes INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS votes (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 candidate_id INTEGER,
                 timestamp TEXT,
                 FOREIGN KEY(user_id) REFERENCES users(id),
                 FOREIGN KEY(candidate_id) REFERENCES candidates(id))''')
    conn.commit()
    conn.close()

# Password hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Validate inputs
def is_valid_username(username):
    return re.match(r'^[a-zA-Z0-9]{3,20}$', username) is not None or \
           re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', username) is not None or \
           re.match(r'^\+?\d{10,15}$', username) is not None

def is_valid_password(password):
    return len(password) >= 6

# Check if username exists
def is_user_registered(username):
    conn = sqlite3.connect('election.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

# Capture face for registration (auto-capture within 5 seconds)
def capture_face():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Could not access webcam.")
        st.error("Could not access webcam.")
        return None
    
    st.info("Position your face in the frame. Face will be captured automatically within 5 seconds.")
    frame_placeholder = st.empty()
    countdown_placeholder = st.empty()
    start_time = time.time()
    
    while time.time() - start_time < 5:
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to capture image from webcam.")
            st.error("Failed to capture image.")
            cap.release()
            return None
        
        # Resize frame for faster processing
        frame = cv2.resize(frame, (640, 480))
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(frame_rgb, model="small")
        
        # Update countdown
        remaining_time = 5 - (time.time() - start_time)
        countdown_placeholder.markdown(f'<div class="countdown">Time remaining: {remaining_time:.1f} seconds</div>', unsafe_allow_html=True)
        
        # Display frame
        frame_placeholder.image(frame_rgb, channels="RGB")
        
        if len(face_locations) == 1:
            logger.info("Single face detected and captured automatically.")
            cap.release()
            return frame_rgb
        elif len(face_locations) > 1:
            logger.warning("Multiple faces detected.")
            st.warning("Multiple faces detected. Please ensure only one face is in the frame.")
        # Continue loop until timeout or face detected
        
    logger.error("No face detected within 5 seconds.")
    st.error("No face detected within 5 seconds. Please try again.")
    cap.release()
    return None

# Verify face for login (real-time detection and comparison)
def verify_face(username, stored_encoding):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Could not access webcam.")
        st.error("Could not access webcam.")
        return False, "Could not access webcam."
    
    st.info("Position your face in the frame. Verifying in real-time...")
    frame_placeholder = st.empty()
    status_placeholder = st.empty()
    start_time = time.time()
    timeout = 30  # Timeout after 30 seconds
    
    while time.time() - start_time < timeout:
        ret, frame = cap.read()
        if not ret:
            logger.error("Failed to capture image from webcam.")
            cap.release()
            return False, "Failed to capture image."
        
        # Resize frame for faster processing
        frame = cv2.resize(frame, (640, 480))
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(frame_rgb, model="small")
        
        # Display frame
        frame_placeholder.image(frame_rgb, channels="RGB")
        
        if len(face_locations) == 1:
            # Get live encoding
            encodings = face_recognition.face_encodings(frame_rgb, known_face_locations=face_locations)
            if len(encodings) == 0:
                status_placeholder.warning("No face encoding generated. Please adjust position.")
                continue
            
            live_encoding = encodings[0]
            # Compare with stored encoding
            matches = face_recognition.compare_faces([stored_encoding], live_encoding, tolerance=0.4)
            if matches[0]:
                logger.info(f"Face verification successful for user {username}.")
                cap.release()
                return True, "Face verification successful!"
            else:
                status_placeholder.error("Face does not match the registered face. Try again.")
        elif len(face_locations) > 1:
            status_placeholder.warning("Multiple faces detected. Please ensure only one face is in the frame.")
        else:
            status_placeholder.warning("No face detected. Please position your face in the frame.")
        
        # Small delay to prevent excessive CPU usage
        time.sleep(0.1)
    
    logger.error("Face verification timed out.")
    cap.release()
    return False, "Face verification timed out after 30 seconds."

# Get face encoding from image
def get_face_encoding(image):
    try:
        # Convert Streamlit's RGB to BGR for face_recognition
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        encodings = face_recognition.face_encodings(image_bgr)
        if len(encodings) == 0:
            logger.warning("No face detected in the image.")
            return None, "No face detected in the image. Please try again."
        if len(encodings) > 1:
            logger.warning("Multiple faces detected.")
            return None, "Multiple faces detected. Please ensure only one face is in the frame."
        logger.info("Face encoding generated successfully.")
        return encodings[0], None
    except Exception as e:
        logger.error(f"Error processing face: {str(e)}")
        return None, f"Error processing face: {str(e)}"

# Register user with face recognition
def register_user(username, password, full_name, gender, face_image):
    if not is_valid_username(username):
        return False, "Invalid username, email, or mobile number format."
    if not is_valid_password(password):
        return False, "Password must be at least 6 characters."
    if not full_name.strip():
        return False, "Full name is required."
    if face_image is None:
        return False, "No face image provided."
    
    # Get face encoding
    encoding, error = get_face_encoding(face_image)
    if encoding is None:
        return False, error
    
    # Save encoding as .npy
    encoding_path = os.path.join(ENCODINGS_DIR, f"{username}.npy")
    try:
        np.save(encoding_path, encoding)
        logger.info(f"Face encoding saved to {encoding_path}, size: {os.path.getsize(encoding_path)} bytes.")
    except Exception as e:
        logger.error(f"Failed to save face encoding to {encoding_path}: {str(e)}")
        return False, f"Failed to save face encoding: {str(e)}"
    
    conn = sqlite3.connect('election.db')
    c = conn.cursor()
    try:
        hashed_password = hash_password(password)
        c.execute('''INSERT INTO users (username, password, full_name, gender, has_voted, face_encoding_path)
                     VALUES (?, ?, ?, ?, ?, ?)''', 
                  (username, hashed_password, full_name, gender, False, encoding_path))
        conn.commit()
        # Verify insertion
        c.execute("SELECT face_encoding_path FROM users WHERE username = ?", (username,))
        stored_path = c.fetchone()
        if stored_path and os.path.exists(stored_path[0]):
            logger.info(f"Face encoding path saved for user {username}: {stored_path[0]}")
            return True, "Face successfully captured! Please go to login page."
        else:
            logger.error(f"Failed to save face encoding path for user {username}.")
            return False, "Failed to save face encoding path."
    except sqlite3.IntegrityError:
        logger.error(f"Username {username} already exists.")
        return False, "Username already exists."
    except Exception as e:
        logger.error(f"Database error during registration: {str(e)}")
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()

# Login user with face recognition
def login_user(username, password):
    conn = sqlite3.connect('election.db')
    c = conn.cursor()
    hashed_password = hash_password(password)
    c.execute("SELECT id, has_voted, face_encoding_path FROM users WHERE username = ? AND password = ?",
              (username, hashed_password))
    user = c.fetchone()
    if not user:
        logger.error(f"Invalid credentials for username {username}.")
        conn.close()
        return False, None, None, "Invalid username or password."
    
    user_id, has_voted, encoding_path = user
    if not encoding_path or not os.path.exists(encoding_path):
        logger.error(f"No face encoding file found for user {username} at {encoding_path}.")
        conn.close()
        return False, None, None, "No face encoding found for this user."
    
    # Load stored encoding
    try:
        stored_encoding = np.load(encoding_path)
        logger.info(f"Loaded face encoding for user {username} from {encoding_path}.")
    except Exception as e:
        logger.error(f"Error loading face encoding for user {username}: {str(e)}")
        conn.close()
        return False, None, None, f"Error loading face encoding: {str(e)}"
    
    conn.close()
    # Verify face in real-time
    success, message = verify_face(username, stored_encoding)
    if success:
        return True, user_id, has_voted, "Successfully verified!"
    return False, None, None, message

# Cast vote
def cast_vote(user_id, candidate_id):
    if user_id == 0:  # Admin user_id
        logger.error("Admin cannot vote.")
        return False, "Admin accounts cannot vote."
    
    if not user_id:
        logger.error("Invalid user_id: None or empty.")
        return False, "Invalid user ID."
    
    conn = sqlite3.connect('election.db')
    c = conn.cursor()
    try:
        # Verify user exists
        c.execute("SELECT has_voted FROM users WHERE id = ?", (user_id,))
        user_result = c.fetchone()
        if user_result is None:
            logger.error(f"No user found with user_id {user_id}.")
            return False, "User not found."
        if user_result[0]:
            logger.info(f"User {user_id} has already voted.")
            return False, "You have already voted."
        
        # Verify candidate exists
        c.execute("SELECT id FROM candidates WHERE id = ?", (candidate_id,))
        candidate_result = c.fetchone()
        if candidate_result is None:
            logger.error(f"No candidate found with candidate_id {candidate_id}.")
            return False, "Candidate not found."
        
        # Update vote records
        c.execute("UPDATE users SET has_voted = ? WHERE id = ?", (True, user_id))
        c.execute("UPDATE candidates SET votes = votes + 1 WHERE id = ?", (candidate_id,))
        c.execute("INSERT INTO votes (user_id, candidate_id, timestamp) VALUES (?, ?, ?)",
                  (user_id, candidate_id, datetime.now().isoformat()))
        conn.commit()
        
        # Verify update
        c.execute("SELECT votes FROM candidates WHERE id = ?", (candidate_id,))
        updated_votes = c.fetchone()[0]
        logger.info(f"Vote cast successfully by user {user_id} for candidate {candidate_id}. New vote count: {updated_votes}.")
        
        get_results.clear()  # Clear results cache
        get_candidates.clear()  # Clear candidates cache
        return True, "Vote cast successfully!"
    except Exception as e:
        logger.error(f"Error casting vote for user {user_id}, candidate {candidate_id}: {str(e)}")
        conn.rollback()
        return False, f"Error casting vote: {str(e)}"
    finally:
        conn.close()

# Add candidate
def add_candidate(name, description):
    if not name.strip():
        logger.error("Candidate name cannot be empty.")
        return False, "Candidate name cannot be empty."
    
    conn = sqlite3.connect('election.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO candidates (name, description, votes) VALUES (?, ?, ?)", 
                  (name.strip(), description.strip() if description else None, 0))
        conn.commit()
        logger.info(f"Candidate {name} added successfully to database.")
        get_candidates.clear()
        get_results.clear()
        return True, "Candidate added successfully!"
    except sqlite3.IntegrityError:
        logger.error(f"Candidate {name} already exists in database.")
        return False, "Candidate already exists."
    except Exception as e:
        logger.error(f"Database error while adding candidate {name}: {str(e)}")
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()

# Reset votes with backup
def reset_votes():
    try:
        shutil.copy('election.db', f'election_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
    except Exception as e:
        return False, f"Backup failed: {str(e)}"
    
    conn = sqlite3.connect('election.db')
    c = conn.cursor()
    c.execute("UPDATE candidates SET votes = 0")
    c.execute("UPDATE users SET has_voted = 0")
    c.execute("DELETE FROM votes")
    conn.commit()
    conn.close()
    get_results.clear()
    get_candidates.clear()
    return True, "All votes reset successfully!"

# Update user profile
def update_user_profile(user_id, username, full_name, gender):
    conn = sqlite3.connect('election.db')
    c = conn.cursor()
    try:
        if not is_valid_username(username):
            return False, "Invalid username format."
        c.execute('''UPDATE users SET username = ?, full_name = ?, gender = ? WHERE id = ?''', 
                  (username, full_name, gender, user_id))
        conn.commit()
        return True, "Profile updated successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    except Exception as e:
        return False, f"Error: {str(e)}"
    finally:
        conn.close()

# Get user profile
def get_user_profile(user_id):
    conn = sqlite3.connect('election.db')
    c = conn.cursor()
    c.execute("SELECT username, full_name, gender, has_voted FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

# Get candidates (cached)
@st.cache_data
def get_candidates():
    conn = sqlite3.connect('election.db')
    c = conn.cursor()
    c.execute("SELECT id, name, description, votes FROM candidates")
    candidates = c.fetchall()
    conn.close()
    logger.info(f"Fetched {len(candidates)} candidates from database.")
    return candidates

# Get results (cached)
@st.cache_data
def get_results():
    candidates = get_candidates()
    total_votes = sum(candidate[3] for candidate in candidates)
    results = [(c[1], c[3], (c[3] / total_votes * 100) if total_votes > 0 else 0) for c in candidates]
    logger.info(f"Fetched results: {len(results)} candidates, {total_votes} total votes.")
    return results, total_votes

# Admin authentication
def is_admin(username, password):
    return username == "admin" and password == "admin123"

# Check voting deadline
def is_voting_open():
    deadline = datetime(2025, 12, 31, 23, 59, 59)
    return datetime.now() <= deadline

# Streamlit app
def main():
    # Initialize session state
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
        st.session_state.has_voted = False
        st.session_state.username = None
        st.session_state.is_admin = False
        st.session_state.page = "welcome"
        st.session_state.register_data = None
        st.session_state.login_data = None

    # Initialize database
    init_db()

    # Welcome screen
    if st.session_state.page == "welcome" and st.session_state.user_id is None:
        with st.container():
            st.markdown('<div class="main-header">Your Vote. Secure. Simple. Online.</div>', unsafe_allow_html=True)
            st.markdown('<div class="subheader">Cast your vote with secure facial recognition.</div>', unsafe_allow_html=True)
            with st.container():
                st.markdown('<div class="button-container">', unsafe_allow_html=True)
                st.button("Register", key="register_btn", help="Create a new account", on_click=lambda: st.session_state.update(page="register"))
                st.button("Login", key="login_btn", help="Log in to your account", on_click=lambda: st.session_state.update(page="login"))
                st.button("Login as Admin", key="admin_login_btn", help="Log in as administrator", on_click=lambda: st.session_state.update(page="admin_login"))
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div class="security-text">Your information, including face data, is protected with encryption.</div>', unsafe_allow_html=True)

    # Registration page
    elif st.session_state.page == "register" and st.session_state.user_id is None:
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.subheader("Register")
        with st.form("register_form"):
            full_name = st.text_input("Full Name", placeholder="Enter full name")
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
            submit = st.form_submit_button("Next: Capture Face")
            if submit:
                if not full_name.strip() or not username or not password:
                    st.error("All fields are required.")
                elif not is_valid_username(username):
                    st.error("Invalid username format.")
                elif not is_valid_password(password):
                    st.error("Password must be at least 6 characters.")
                else:
                    st.session_state.register_data = {
                        "full_name": full_name,
                        "username": username,
                        "password": password,
                        "gender": gender
                    }
                    st.session_state.page = "capture_face_register"
                    st.rerun()
        if st.button("Back to Welcome"):
            st.session_state.page = "welcome"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Face capture for registration
    elif st.session_state.page == "capture_face_register" and st.session_state.user_id is None:
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.subheader("Capture Your Face")
        face_image = capture_face()
        if face_image is not None:
            success, message = register_user(
                st.session_state.register_data["username"],
                st.session_state.register_data["password"],
                st.session_state.register_data["full_name"],
                st.session_state.register_data["gender"],
                face_image
            )
            if success:
                st.session_state.register_data = None
                st.success(message)
                time.sleep(2)
                st.session_state.page = "welcome"
                st.rerun()
            else:
                st.error(message)
        if st.button("Back to Register"):
            st.session_state.page = "register"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Login page
    elif st.session_state.page == "login" and st.session_state.user_id is None:
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submit = st.form_submit_button("Next: Verify Face")
            if submit:
                if not username or not password:
                    st.error("Username and password are required.")
                elif not is_user_registered(username):
                    st.error("Username not found. Please register first.")
                    st.session_state.page = "register"
                    st.rerun()
                else:
                    st.session_state.login_data = {
                        "username": username,
                        "password": password
                    }
                    st.session_state.page = "capture_face_login"
                    st.rerun()
        if st.button("Back to Welcome"):
            st.session_state.page = "welcome"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Admin login page
    elif st.session_state.page == "admin_login" and st.session_state.user_id is None:
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.subheader("Admin Login")
        with st.form("admin_login_form"):
            username = st.text_input("Username", placeholder="Enter admin username")
            password = st.text_input("Password", type="password", placeholder="Enter admin password")
            submit = st.form_submit_button("Login")
            if submit:
                if is_admin(username, password):
                    st.session_state.user_id = 0
                    st.session_state.username = username
                    st.session_state.is_admin = True
                    st.session_state.has_voted = False
                    st.session_state.page = "dashboard"
                    st.success("Logged in as admin!")
                    st.rerun()
                else:
                    st.error("Invalid admin credentials.")
        if st.button("Back to Welcome"):
            st.session_state.page = "welcome"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Face verification for login
    elif st.session_state.page == "capture_face_login" and st.session_state.user_id is None:
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.subheader("Verify Your Face")
        success, user_id, has_voted, message = login_user(
            st.session_state.login_data["username"],
            st.session_state.login_data["password"]
        )
        if success:
            st.success(message)
            time.sleep(2)
            st.session_state.user_id = user_id
            st.session_state.has_voted = has_voted
            st.session_state.username = st.session_state.login_data["username"]
            st.session_state.is_admin = is_admin(st.session_state.login_data["username"], st.session_state.login_data["password"])
            st.session_state.login_data = None
            st.session_state.page = "dashboard"
            st.rerun()
        else:
            st.error(message)
        if st.button("Back to Login"):
            st.session_state.page = "login"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Main app for logged-in users
    if st.session_state.user_id is not None:
        st.session_state.page = "dashboard"
        st.markdown('<div class="main-header">Online Voting System</div>', unsafe_allow_html=True)
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            st.markdown(f"**Logged in as: {st.session_state.username}** {'(Admin)' if st.session_state.is_admin else ''}")
        with col2:
            st.write("")

        tabs = st.tabs(["Home", "Vote", "Profile", "Admin"] if st.session_state.is_admin else ["Home", "Vote", "Profile"])

        # Home tab
        with tabs[0]:
            st.header("Welcome to the Voting System")
            st.markdown("""
            Navigate using the tabs above to:
            - **Vote**: Cast your vote for a candidate.
            - **Profile**: Manage your account details.
            """)
            if st.session_state.is_admin:
                st.markdown("- **Admin**: Add candidates, view results, and reset votes.")
            deadline = datetime(2025, 12, 31, 23, 59, 59)
            st.info(f"Voting is open until {deadline.strftime('%B %d, %Y, %I:%M %p')}.")

        # Vote tab
        with tabs[1]:
            st.header("Cast Your Vote")
            if st.session_state.is_admin:
                st.error("Admin accounts cannot vote. Use a regular user account to vote.")
            elif not is_voting_open():
                st.error("Voting has closed.")
            elif st.session_state.has_voted:
                st.warning("You have already voted.")
            else:
                candidates = get_candidates()
                if not candidates:
                    st.warning("No candidates available. Please contact the admin.")
                else:
                    st.subheader("Candidates")
                    for candidate in candidates:
                        with st.expander(f"{candidate[1]}"):
                            st.write(candidate[2] or "No description provided.")
                    selected_candidate = st.selectbox("Choose a candidate", [c[1] for c in candidates], key="vote_select")
                    confirm = st.checkbox("I confirm my vote for the selected candidate")
                    if st.button("Submit Vote", disabled=not confirm):
                        try:
                            candidate_id = next(c[0] for c in candidates if c[1] == selected_candidate)
                            logger.info(f"Submitting vote for user {st.session_state.user_id}, candidate {candidate_id}")
                            success, message = cast_vote(st.session_state.user_id, candidate_id)
                            if success:
                                st.session_state.has_voted = True
                                st.success(message)
                                st.balloons()
                                st.rerun()  # Refresh to update UI
                            else:
                                st.error(message)
                        except StopIteration:
                            st.error("Selected candidate not found.")
                            logger.error(f"Selected candidate {selected_candidate} not found in candidates list.")

        # Profile tab
        with tabs[2]:
            st.header("User Profile")
            if not st.session_state.is_admin:
                user = get_user_profile(st.session_state.user_id)
                if user:
                    st.write(f"**Username**: {user[0]}")
                    st.write(f"**Full Name**: {user[1] or 'Not set'}")
                    st.write(f"**Gender**: {user[2] or 'Not set'}")
                    st.write(f"**Voting Status**: {'Voted' if user[3] else 'Not Voted'}")
                
                st.subheader("Edit Profile")
                with st.form("edit_profile"):
                    edit_username = st.text_input("Username", value=user[0] or '')
                    edit_full_name = st.text_input("Full Name", value=user[1] or '')
                    edit_gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"], 
                                             index=["Male", "Female", "Other", "Prefer not to say"].index(user[2]) if user[2] else 0)
                    if st.form_submit_button("Update Profile"):
                        success, message = update_user_profile(st.session_state.user_id, edit_username, edit_full_name, edit_gender)
                        if success:
                            st.session_state.username = edit_username
                            st.success(message)
                        else:
                            st.error(message)
            else:
                st.info("Admin account does not have a user profile.")

            if st.button("Logout"):
                st.session_state.user_id = None
                st.session_state.has_voted = False
                st.session_state.username = None
                st.session_state.is_admin = False
                st.session_state.page = "welcome"
                st.session_state.register_data = None
                st.session_state.login_data = None
                st.success("Logged out successfully.")
                st.rerun()

        # Admin tab
        if st.session_state.is_admin:
            with tabs[3]:
                st.header("Admin Panel")
                st.subheader("Add Candidate")
                with st.form("add_candidate"):
                    new_candidate = st.text_input("Candidate Name", placeholder="Enter candidate name")
                    description = st.text_area("Candidate Description", placeholder="Enter candidate description")
                    if st.form_submit_button("Add Candidate"):
                        success, message = add_candidate(new_candidate, description)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                
                st.subheader("Reset All Votes")
                with st.form("reset_votes_form"):
                    confirm_reset = st.text_input("Type 'CONFIRM' to reset all votes")
                    if st.form_submit_button("Reset Votes"):
                        if confirm_reset == "CONFIRM":
                            success, message = reset_votes()
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                        else:
                            st.error("Please type 'CONFIRM' to proceed.")
                
                st.subheader("Current Candidates")
                candidates = get_candidates()
                if not candidates:
                    st.info("No candidates added yet.")
                else:
                    for _, name, desc, votes in candidates:
                        st.write(f"**{name}**: {votes} votes")
                        st.write(f"_{desc or 'No description provided.'}_")
                
                st.subheader("Election Results")
                results, total_votes = get_results()
                if not candidates:
                    st.warning("No candidates available to display results.")
                elif total_votes == 0:
                    st.info("No votes cast yet.")
                else:
                    st.markdown("**Current Vote Tallies**")
                    for name, votes, percentage in results:
                        st.metric(label=name, value=f"{votes} votes", delta=f"{percentage:.2f}%")
                    st.write(f"**Total votes cast**: {total_votes}")
                    df = pd.DataFrame(results, columns=["Candidate", "Votes", "Percentage"])
                    st.bar_chart(df.set_index("Candidate")["Votes"])

if __name__ == "__main__":
    main()