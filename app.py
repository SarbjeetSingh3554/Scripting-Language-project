import os
import json
import math
import numpy as np
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import execute_query

try:
    from face_recognition_module import encode_faces, recognize_faces
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    def encode_faces(*a, **kw): return {}
    def recognize_faces(*a, **kw): return [], None

app = Flask(__name__)
app.secret_key = 'smart_attendance_secret_key'

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads'
DATASET_FOLDER = 'dataset'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =========================
# Auth & Common Routes
# =========================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        identifier = request.form.get('identifier') # Username/Email/RollNo
        password = request.form.get('password')     # For admin/teacher. Students might login by rollno
        
        if role == 'admin':
            admin = execute_query("SELECT * FROM admins WHERE username = %s AND password = %s", (identifier, password), fetch=True)
            if admin:
                session['user_id'] = admin['admin_id']
                session['role'] = 'admin'
                return redirect(url_for('admin_dashboard'))
        elif role == 'teacher':
            teacher = execute_query("SELECT * FROM teachers WHERE email = %s AND password = %s", (identifier, password), fetch=True)
            if teacher:
                session['user_id'] = teacher['teacher_id']
                session['name'] = teacher['name']
                session['role'] = 'teacher'
                return redirect(url_for('teacher_dashboard'))
        elif role == 'student':
            student = execute_query("SELECT * FROM students WHERE roll_no = %s", (identifier,), fetch=True)
            if student:
                session['user_id'] = student['student_id']
                session['name'] = student['name']
                session['roll_no'] = student['roll_no']
                session['role'] = 'student'
                return redirect(url_for('student_dashboard'))
                
        flash("Invalid credentials", "danger")
        
    return render_template('login.html', role=role)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# =========================
# Admin Routes
# =========================
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login', role='admin'))
    
    stats = {}
    stats['students'] = execute_query("SELECT COUNT(*) as count FROM students", fetch=True)['count']
    stats['teachers'] = execute_query("SELECT COUNT(*) as count FROM teachers", fetch=True)['count']
    stats['subjects'] = execute_query("SELECT COUNT(*) as count FROM subjects", fetch=True)['count']
    
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/manage_students', methods=['GET', 'POST'])
def manage_students():
    if session.get('role') != 'admin':
        return redirect(url_for('login', role='admin'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            name = request.form.get('name')
            roll_no = request.form.get('roll_no')
            branch = request.form.get('branch')
            year = request.form.get('year')
            execute_query("INSERT INTO students (name, roll_no, branch, year) VALUES (%s, %s, %s, %s)",
                          (name, roll_no, branch, year), commit=True)
            flash("Student added successfully", "success")
        elif action == 'delete':
            student_id = request.form.get('student_id')
            execute_query("DELETE FROM students WHERE student_id = %s", (student_id,), commit=True)
            flash("Student deleted successfully", "success")
            
    students = execute_query("SELECT * FROM students ORDER BY roll_no ASC", fetchall=True)
    return render_template('admin/manage_students.html', students=students)

@app.route('/admin/manage_teachers', methods=['GET', 'POST'])
def manage_teachers():
    if session.get('role') != 'admin': return redirect(url_for('login', role='admin'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            execute_query("INSERT INTO teachers (name, email, password) VALUES (%s, %s, %s)",
                          (name, email, password), commit=True)
            flash("Teacher added successfully", "success")
        elif action == 'delete':
            teacher_id = request.form.get('teacher_id')
            execute_query("DELETE FROM teachers WHERE teacher_id = %s", (teacher_id,), commit=True)
            flash("Teacher deleted successfully", "success")
            
    teachers = execute_query("SELECT * FROM teachers ORDER BY name ASC", fetchall=True)
    return render_template('admin/manage_teachers.html', teachers=teachers)

@app.route('/admin/train_model', methods=['POST'])
def train_model():
    if session.get('role') != 'admin': return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    # Process the dataset to generate encodings
    try:
        encodings = encode_faces(DATASET_FOLDER)
        
        # Update database with new encodings
        success_count = 0
        for roll_no, encoding in encodings.items():
            # Convert encoding back to JSON string to save in DB
            encoding_json = json.dumps(encoding)
            # Find student by name (folder names are student names)
            student = execute_query("SELECT student_id FROM students WHERE LOWER(name) = %s", (roll_no.lower(),), fetch=True)
            if student:
                execute_query("UPDATE students SET face_encoding = %s WHERE student_id = %s", 
                             (encoding_json, student['student_id']), commit=True)
                success_count += 1
                
        flash(f"Model trained successfully. {success_count} student encodings generated.", "success")
    except Exception as e:
        flash(f"Error training model: {str(e)}", "danger")
        
    return redirect(url_for('admin_dashboard'))

# =========================
# Teacher Routes
# =========================
@app.route('/teacher/dashboard')
def teacher_dashboard():
    if session.get('role') != 'teacher': return redirect(url_for('login', role='teacher'))
    
    teacher_id = session.get('user_id')
    subjects = execute_query("SELECT * FROM subjects WHERE teacher_id = %s", (teacher_id,), fetchall=True)
    
    return render_template('teacher/dashboard.html', subjects=subjects)

@app.route('/teacher/mark_attendance', methods=['GET', 'POST'])
def mark_attendance():
    if session.get('role') != 'teacher': return redirect(url_for('login', role='teacher'))
    
    teacher_id = session.get('user_id')
    subjects = execute_query("SELECT * FROM subjects WHERE teacher_id = %s", (teacher_id,), fetchall=True)
    
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        attendance_date = request.form.get('date')
        
        if 'file' not in request.files:
            flash("No file part", "danger")
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash("No selected file", "danger")
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Fetch all known encodings from DB
            students = execute_query("SELECT student_id, name, roll_no, face_encoding FROM students WHERE face_encoding IS NOT NULL", fetchall=True)
            
            known_encodings = []
            known_student_names = []
            student_mapping = {} # Name to ID
            
            for s in students:
                encoding = json.loads(s['face_encoding'])
                known_encodings.append(np.array(encoding))
                # For display and matching, we can use Name or Roll No
                known_student_names.append(s['name'])
                student_mapping[s['name']] = s['student_id']
                
            # Process image
            recognized_names, annotated_file = recognize_faces(filepath, known_student_names, known_encodings)
            
            # Prepare data for review screen — show by roll_no
            all_students = execute_query("SELECT * FROM students ORDER BY roll_no ASC", fetchall=True)
            
            attendance_status = []
            for student in all_students:
                status = "Present" if student['name'] in recognized_names else "Absent"
                attendance_status.append({
                    'student_id': student['student_id'],
                    'name': student['name'],
                    'roll_no': student['roll_no'],
                    'status': status
                })
                
            return render_template('teacher/review_attendance.html', 
                                   attendance_status=attendance_status,
                                   subject_id=subject_id,
                                   date=attendance_date,
                                   annotated_image=annotated_file)
                                   
    return render_template('teacher/mark_attendance.html', subjects=subjects)

@app.route('/teacher/save_attendance', methods=['POST'])
def save_attendance():
    if session.get('role') != 'teacher': return redirect(url_for('login', role='teacher'))
    
    subject_id = request.form.get('subject_id')
    date = request.form.get('date')
    
    # Process dynamically generated inputs for student statuses
    all_students = execute_query("SELECT student_id FROM students", fetchall=True)
    
    success_count = 0
    for s in all_students:
        s_id = str(s['student_id'])
        status = request.form.get(f"status_{s_id}")
        if status:
            try:
                execute_query(
                    "INSERT OR REPLACE INTO attendance (student_id, subject_id, date, status) VALUES (%s, %s, %s, %s)",
                    (s_id, subject_id, date, status), commit=True
                )
                success_count += 1
            except Exception as e:
                print(f"Error saving attendance for student {s_id}: {e}")
                
    flash(f"Attendance saved successfully for {success_count} students.", "success")
    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher/cancel_class', methods=['POST'])
def cancel_class():
    """When a teacher cancels a class, decrease total_classes for that subject by 1."""
    if session.get('role') != 'teacher': return redirect(url_for('login', role='teacher'))
    
    subject_id = request.form.get('subject_id')
    if subject_id:
        # Decrease total_classes by 1 (minimum 0)
        execute_query(
            "UPDATE subjects SET total_classes = MAX(total_classes - 1, 0) WHERE subject_id = %s",
            (subject_id,), commit=True
        )
        subject = execute_query("SELECT subject_name, total_classes FROM subjects WHERE subject_id = %s", (subject_id,), fetch=True)
        if subject:
            flash(f"Class cancelled for {subject['subject_name']}. Total classes now: {subject['total_classes']}", "success")
    
    return redirect(url_for('teacher_dashboard'))

# =========================
# Student Routes
# =========================
@app.route('/student/dashboard')
def student_dashboard():
    if session.get('role') != 'student': return redirect(url_for('login', role='student'))
    
    student_id = session.get('user_id')
    roll_no = session.get('roll_no', '')
    
    # Fetch all subjects
    all_subjects = execute_query("SELECT * FROM subjects", fetchall=True)
    
    subject_stats = []
    overall_attended = 0
    overall_total = 0
    
    for sub in all_subjects:
        sub_id = sub['subject_id']
        total_classes = sub.get('total_classes', 39) or 39
        
        # Count attended classes for this student in this subject
        attended = execute_query(
            "SELECT COUNT(*) as count FROM attendance WHERE student_id = %s AND subject_id = %s AND status = 'Present'",
            (student_id, sub_id), fetch=True
        )['count']
        
        # Calculate percentage
        percentage = round((attended / total_classes * 100), 1) if total_classes > 0 else 0
        
        # Calculate classes needed to maintain 75%
        # We need: (attended + x) / (total_classes + x) >= 0.75  (if attending future classes)
        # But simpler: how many more classes to attend out of remaining to reach 75%
        # Required attended for 75%: ceil(0.75 * total_classes)
        required_for_75 = math.ceil(0.75 * total_classes)
        classes_needed = max(required_for_75 - attended, 0)
        
        # Remaining classes (total - classes marked so far)
        classes_marked = execute_query(
            "SELECT COUNT(*) as count FROM attendance WHERE student_id = %s AND subject_id = %s",
            (student_id, sub_id), fetch=True
        )['count']
        remaining = max(total_classes - classes_marked, 0)
        
        # Can the student still reach 75%?
        can_reach_75 = (attended + remaining) >= required_for_75
        
        # How many classes can student skip (bunk) and still have 75%
        classes_can_skip = max(remaining - classes_needed, 0) if can_reach_75 else 0
        
        subject_stats.append({
            'subject_name': sub['subject_name'],
            'subject_id': sub_id,
            'total_classes': total_classes,
            'attended': attended,
            'classes_marked': classes_marked,
            'remaining': remaining,
            'percentage': percentage,
            'required_for_75': required_for_75,
            'classes_needed': classes_needed,
            'can_reach_75': can_reach_75,
            'classes_can_skip': classes_can_skip,
        })
        
        overall_attended += attended
        overall_total += total_classes
    
    overall_percentage = round((overall_attended / overall_total * 100), 1) if overall_total > 0 else 0
    
    # Fetch detailed recent attendance
    history = execute_query("""
        SELECT a.date, a.status, s.subject_name 
        FROM attendance a 
        JOIN subjects s ON a.subject_id = s.subject_id 
        WHERE a.student_id = %s 
        ORDER BY a.date DESC LIMIT 15
    """, (student_id,), fetchall=True)
    
    return render_template('student/dashboard.html', 
                           roll_no=roll_no,
                           subject_stats=subject_stats,
                           overall_percentage=overall_percentage,
                           overall_attended=overall_attended,
                           overall_total=overall_total,
                           history=history)

if __name__ == '__main__':
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5000)
