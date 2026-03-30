# Smart Attendance System using Face Recognition

This is a complete Smart Attendance System built with Flask, MySQL, Bootstrap, OpenCV, and the `face_recognition` library.
It is customized to run on a local environment, specifically tailored with setup scripts for macOS.

## System Requirements
- Python 3.9+ 
- MySQL Server (must be running on `localhost:3306`)
- `cmake` (required for dlib/face_recognition on macOS. Can be installed via `brew install cmake`)

## Important: Add Demo Target Faces!
Before the AI can recognize students, you **MUST** provide sample images for it to learn.
1. Go to `attendance_system/dataset/`
2. You will see folders named `Raj`, `Rahul`, `Sarbjeet`, `Tripti`, and `Pallavi`.
3. Inside each folder, place 1-3 clear face photos of that specific person (e.g., `attendance_system/dataset/Raj/raj_face.jpg`).

## How To Run Locally (macOS M1/M2/M3)

### Step 1: Automated Setup
Open your terminal, navigate to the `attendance_system` folder, and run:
```bash
chmod +x setup_mac.sh
./setup_mac.sh
```
This will install `cmake` via Homebrew, create a python virtual environment, and install all required libraries.

### Step 2: Initialize Database
```bash
# Activate the environment
source venv/bin/activate

# Create tables and insert demo students
python3 init_db.py

# Seed demo data and create dataset folders
python3 seed_demo_data.py
```
*(Make sure your local MySQL server is running before executing the DB scripts. If your MySQL root password is not blank, edit `config.py` first).*

### Step 3: Start the Backend Server
```bash
python3 app.py
```
The server will start at `http://127.0.0.0:5000`

### Step 4: System Usage Workflow
1. Go to **Admin Login** (`username: admin`, `password: admin123`).
2. Click **Train Model** (Ensure you have placed the face images in the dataset folders first!).
3. Go to **Teacher Login** (`email: teacher@nit.edu`, `password: teacher123`).
4. Select a Subject, upload a Classroom Group Photo containing the demo students.
5. The system will detect faces, match them to the trained database, and mark attendance!
