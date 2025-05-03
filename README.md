Online Voting System 🗳️
A secure, user-friendly web application for conducting online elections with facial recognition authentication, built using Streamlit. This system ensures a seamless voting experience with robust security features, including face verification and encrypted data storage.

✨ Features

Secure User Authentication: Register and log in with a username, password, and facial recognition powered by the face_recognition library.
Real-Time Facial Recognition: Uses OpenCV and face_recognition for capturing and verifying faces via webcam.
Voting Mechanism: Cast votes for candidates with safeguards to prevent multiple votes. Voting is open until December 31, 2025.
Admin Dashboard: Manage candidates, reset votes, and view real-time election results with vote counts and visualizations.
Data Management: Stores user data, candidate details, and votes in an SQLite database (election.db).
Modern UI: Dark-themed, responsive interface with custom CSS for an intuitive experience.
Security: Passwords are hashed with SHA-256, and face encodings are securely stored as .npy files.


📋 Prerequisites

Python: Version 3.8 or higher
Webcam: Required for facial recognition
Dependencies: Listed in requirements.txt (see Installation)


🚀 Installation

Clone the Repository:
git clone https://github.com/your-username/online-voting-system.git
cd online-voting-system


Set Up a Virtual Environment (recommended):
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install Dependencies:
pip install -r requirements.txt


Run the Application:
streamlit run app.py

Open the provided URL (usually http://localhost:8501) in your browser.



📦 Dependencies
The project relies on the following Python packages, listed in requirements.txt:
streamlit
opencv-python
face_recognition
numpy
pandas

To create the requirements.txt file:
echo -e "streamlit\nopencv-python\nface_recognition\nnumpy\npandas" > requirements.txt


🖥️ Usage

Launch the App: Run streamlit run app.py and access it via the local URL.
Register: Create an account by entering your username, password, full name, gender, and capturing your face.
Log In: Use your credentials and verify your identity with facial recognition.
Vote: Select a candidate and confirm your vote (available until the deadline).
Admin Access: Log in with admin credentials (username: admin, password: admin123) to:
Add candidates
Reset all votes
View election results with charts




🗄️ Database Structure
The SQLite database (election.db) includes three tables:

users: Stores user information (username, hashed password, full name, gender, voting status, face encoding path).
candidates: Stores candidate details (name, description, vote count).
votes: Records votes with user ID, candidate ID, and timestamp.


🔒 Security

Password Hashing: Passwords are hashed using SHA-256 for secure storage.
Face Encodings: Stored as .npy files in the face_encodings directory, excluded from version control.
Vote Integrity: Ensures one vote per user and enforces a voting deadline.
Data Protection: Database backups are created before vote resets.


⚠️ Limitations

Requires a webcam for facial recognition.
Admin credentials are hardcoded (admin/admin123) for simplicity; consider securing them in production.
Facial recognition performance may vary based on lighting, camera quality, or face positioning.


🛠️ Contributing
We welcome contributions! To contribute:

Fork the repository.
Create a new branch (git checkout -b feature/your-feature).
Make your changes and commit (git commit -m "Add your feature").
Push to your branch (git push origin feature/your-feature).
Open a pull request.


📜 License
This project is licensed under the MIT License.

📬 Contact
For questions or issues, please:

Open an issue on GitHub.
Contact [your-email@example.com].


🌟 Acknowledgments

Streamlit for the web framework.
face_recognition for facial recognition capabilities.
OpenCV for image processing.
SQLite for lightweight database management.

