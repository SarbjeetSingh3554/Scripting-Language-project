import os
import json
import math
import shutil
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

def encode_single_student(roll_no):
    """Generate face encoding for a single student from their dataset folder."""
    student_dir = os.path.join(DATASET_FOLDER, roll_no)
    if not os.path.isdir(student_dir):
        return None
    
    try:
        import face_recognition as fr
        student_encodings = []
        for image_name in os.listdir(student_dir):
            if image_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_path = os.path.join(student_dir, image_name)
                try:
                    image = fr.load_image_file(image_path)
                    encodings = fr.face_encodings(image)
                    if len(encodings) > 0:
                        student_encodings.append(encodings[0])
                except Exception as e:
                    print(f"Error processing {image_path}: {e}")
        
        if student_encodings:
            avg_encoding = np.mean(student_encodings, axis=0)
            return avg_encoding.tolist()
    except ImportError:
        pass
    return None

# =========================
# Auth & Common Routes
# =========================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        identifier = request.form.get('identifier')
        password = request.form.get('password')
        
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
    
    # Count students with face data
    stats['trained'] = execute_query("SELECT COUNT(*) as count FROM students WHERE face_encoding IS NOT NULL", fetch=True)['count']
    
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
            
            # Check if roll_no already exists
            existing = execute_query("SELECT student_id FROM students WHERE roll_no = %s", (roll_no,), fetch=True)
            if existing:
                flash(f"Student with roll no {roll_no} already exists!", "danger")
            else:
                # Insert student
                execute_query("INSERT INTO students (name, roll_no, branch, year) VALUES (%s, %s, %s, %s)",
                              (name, roll_no, branch, year), commit=True)
                
                # Handle face photo upload
                photos = request.files.getlist('photos')
                student_dir = os.path.join(DATASET_FOLDER, roll_no)
                os.makedirs(student_dir, exist_ok=True)
                
                photo_count = 0
                for photo in photos:
                    if photo and photo.filename and allowed_file(photo.filename):
                        ext = photo.filename.rsplit('.', 1)[1].lower()
                        photo_filename = f"{roll_no}_face_{photo_count + 1}.{ext}"
                        photo_path = os.path.join(student_dir, photo_filename)
                        photo.save(photo_path)
                        photo_count += 1
                
                # Try to auto-generate face encoding
                if photo_count > 0:
                    encoding = encode_single_student(roll_no)
                    if encoding:
                        student = execute_query("SELECT student_id FROM students WHERE roll_no = %s", (roll_no,), fetch=True)
                        if student:
                            encoding_json = json.dumps(encoding)
                            execute_query("UPDATE students SET face_encoding = %s WHERE student_id = %s",
                                         (encoding_json, student['student_id']), commit=True)
                        flash(f"Student {name} ({roll_no}) added with face data ✅", "success")
                    else:
                        flash(f"Student {name} ({roll_no}) added. Face not detected in photo — retrain model or upload clearer photos.", "warning")
                else:
                    flash(f"Student {name} ({roll_no}) added without photo. Upload face photos and train the model.", "warning")
                    
        elif action == 'delete':
            student_id = request.form.get('student_id')
            # Get student info before deleting
            student = execute_query("SELECT name, roll_no FROM students WHERE student_id = %s", (student_id,), fetch=True)
            if student:
                # Delete attendance records
                execute_query("DELETE FROM attendance WHERE student_id = %s", (student_id,), commit=True)
                # Delete student
                execute_query("DELETE FROM students WHERE student_id = %s", (student_id,), commit=True)
                # Remove dataset folder
                student_dir = os.path.join(DATASET_FOLDER, student['roll_no'])
                if os.path.exists(student_dir):
                    shutil.rmtree(student_dir)
                flash(f"Student {student['name']} ({student['roll_no']}) deleted along with all attendance records.", "success")
            
        elif action == 'upload_photo':
            student_id = request.form.get('student_id')
            student = execute_query("SELECT name, roll_no FROM students WHERE student_id = %s", (student_id,), fetch=True)
            if student:
                photos = request.files.getlist('photos')
                student_dir = os.path.join(DATASET_FOLDER, student['roll_no'])
                os.makedirs(student_dir, exist_ok=True)
                
                # Count existing photos
                existing_count = len([f for f in os.listdir(student_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]) if os.path.exists(student_dir) else 0
                
                photo_count = 0
                for photo in photos:
                    if photo and photo.filename and allowed_file(photo.filename):
                        ext = photo.filename.rsplit('.', 1)[1].lower()
                        photo_filename = f"{student['roll_no']}_face_{existing_count + photo_count + 1}.{ext}"
                        photo_path = os.path.join(student_dir, photo_filename)
                        photo.save(photo_path)
                        photo_count += 1
                
                if photo_count > 0:
                    # Auto re-encode
                    encoding = encode_single_student(student['roll_no'])
                    if encoding:
                        encoding_json = json.dumps(encoding)
                        execute_query("UPDATE students SET face_encoding = %s WHERE student_id = %s",
                                     (encoding_json, student_id), commit=True)
                        flash(f"Photos uploaded and face data updated for {student['name']} ✅", "success")
                    else:
                        flash(f"Photos uploaded but face not detected. Try clearer photos.", "warning")
                else:
                    flash("No valid photos uploaded.", "danger")
            
    students = execute_query("SELECT * FROM students ORDER BY roll_no ASC", fetchall=True)
    
    # Count photos for each student
    for s in students:
        student_dir = os.path.join(DATASET_FOLDER, s['roll_no'])
        if os.path.exists(student_dir):
            s['photo_count'] = len([f for f in os.listdir(student_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        else:
            s['photo_count'] = 0
    
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
            
            # Check if email already exists
            existing = execute_query("SELECT teacher_id FROM teachers WHERE email = %s", (email,), fetch=True)
            if existing:
                flash(f"Teacher with email {email} already exists!", "danger")
            else:
                execute_query("INSERT INTO teachers (name, email, password) VALUES (%s, %s, %s)",
                              (name, email, password), commit=True)
                flash(f"Teacher {name} added successfully", "success")
        elif action == 'delete':
            teacher_id = request.form.get('teacher_id')
            teacher = execute_query("SELECT name FROM teachers WHERE teacher_id = %s", (teacher_id,), fetch=True)
            if teacher:
                # Unassign subjects (set teacher_id to NULL, don't delete subjects)
                execute_query("UPDATE subjects SET teacher_id = NULL WHERE teacher_id = %s", (teacher_id,), commit=True)
                # Delete teacher
                execute_query("DELETE FROM teachers WHERE teacher_id = %s", (teacher_id,), commit=True)
                flash(f"Teacher {teacher['name']} deleted. Their subjects are now unassigned.", "success")
            
    # Fetch teachers with subject count
    teachers = execute_query("""
        SELECT t.*, 
               (SELECT COUNT(*) FROM subjects WHERE teacher_id = t.teacher_id) as subject_count
        FROM teachers t
        ORDER BY t.name ASC
    """, fetchall=True)
    return render_template('admin/manage_teachers.html', teachers=teachers)

@app.route('/admin/manage_subjects', methods=['GET', 'POST'])
def manage_subjects():
    if session.get('role') != 'admin': return redirect(url_for('login', role='admin'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            subject_name = request.form.get('subject_name')
            teacher_id = request.form.get('teacher_id')
            total_classes = request.form.get('total_classes', 39)
            try:
                total_classes = int(total_classes)
            except (ValueError, TypeError):
                total_classes = 39
            if teacher_id == '' or teacher_id is None:
                teacher_id = None
            execute_query(
                "INSERT INTO subjects (subject_name, teacher_id, total_classes) VALUES (%s, %s, %s)",
                (subject_name, teacher_id, total_classes), commit=True
            )
            flash(f"Subject '{subject_name}' added successfully", "success")
        elif action == 'assign':
            subject_id = request.form.get('subject_id')
            teacher_id = request.form.get('teacher_id')
            if teacher_id == '' or teacher_id is None:
                teacher_id = None
            execute_query(
                "UPDATE subjects SET teacher_id = %s WHERE subject_id = %s",
                (teacher_id, subject_id), commit=True
            )
            flash("Subject assignment updated", "success")
        elif action == 'delete':
            subject_id = request.form.get('subject_id')
            # Delete attendance records for this subject first
            execute_query("DELETE FROM attendance WHERE subject_id = %s", (subject_id,), commit=True)
            execute_query("DELETE FROM subjects WHERE subject_id = %s", (subject_id,), commit=True)
            flash("Subject deleted successfully", "success")
    
    subjects = execute_query("""
        SELECT s.*, t.name as teacher_name 
        FROM subjects s 
        LEFT JOIN teachers t ON s.teacher_id = t.teacher_id 
        ORDER BY s.subject_name ASC
    """, fetchall=True)
    teachers = execute_query("SELECT * FROM teachers ORDER BY name ASC", fetchall=True)
    return render_template('admin/manage_subjects.html', subjects=subjects, teachers=teachers)

@app.route('/admin/train_model', methods=['POST'])
def train_model():
    if session.get('role') != 'admin': return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    try:
        # Scan all student folders in dataset (folders named by roll_no)
        success_count = 0
        fail_count = 0
        students = execute_query("SELECT student_id, name, roll_no FROM students", fetchall=True)
        
        for student in students:
            roll_no = student['roll_no']
            encoding = encode_single_student(roll_no)
            if encoding:
                encoding_json = json.dumps(encoding)
                execute_query("UPDATE students SET face_encoding = %s WHERE student_id = %s", 
                             (encoding_json, student['student_id']), commit=True)
                success_count += 1
            else:
                # Check if folder exists but no valid face
                student_dir = os.path.join(DATASET_FOLDER, roll_no)
                if os.path.isdir(student_dir):
                    fail_count += 1
                    
        msg = f"Model trained: {success_count} students encoded."
        if fail_count > 0:
            msg += f" {fail_count} students had photos but no face detected."
        flash(msg, "success" if fail_count == 0 else "warning")
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
            student_mapping = {}
            
            for s in students:
                encoding = json.loads(s['face_encoding'])
                known_encodings.append(np.array(encoding))
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
    if session.get('role') != 'teacher': return redirect(url_for('login', role='teacher'))
    
    teacher_id = session.get('user_id')
    subject_id = request.form.get('subject_id')
    if subject_id:
        subject = execute_query(
            "SELECT * FROM subjects WHERE subject_id = %s AND teacher_id = %s",
            (subject_id, teacher_id), fetch=True
        )
        if subject:
            execute_query(
                "UPDATE subjects SET total_classes = MAX(total_classes - 1, 0) WHERE subject_id = %s",
                (subject_id,), commit=True
            )
            updated = execute_query("SELECT total_classes FROM subjects WHERE subject_id = %s", (subject_id,), fetch=True)
            flash(f"Class cancelled for {subject['subject_name']}. Total classes now: {updated['total_classes']}", "success")
        else:
            flash("You are not authorized to modify this subject.", "danger")
    
    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher/add_extra_class', methods=['POST'])
def add_extra_class():
    if session.get('role') != 'teacher': return redirect(url_for('login', role='teacher'))
    
    teacher_id = session.get('user_id')
    subject_id = request.form.get('subject_id')
    if subject_id:
        subject = execute_query(
            "SELECT * FROM subjects WHERE subject_id = %s AND teacher_id = %s",
            (subject_id, teacher_id), fetch=True
        )
        if subject:
            execute_query(
                "UPDATE subjects SET total_classes = total_classes + 1 WHERE subject_id = %s",
                (subject_id,), commit=True
            )
            updated = execute_query("SELECT total_classes FROM subjects WHERE subject_id = %s", (subject_id,), fetch=True)
            flash(f"Extra class added for {subject['subject_name']}. Total classes now: {updated['total_classes']}", "success")
        else:
            flash("You are not authorized to modify this subject.", "danger")
    
    return redirect(url_for('teacher_dashboard'))

# =========================
# Student Routes
# =========================
@app.route('/student/dashboard')
def student_dashboard():
    if session.get('role') != 'student': return redirect(url_for('login', role='student'))
    
    student_id = session.get('user_id')
    roll_no = session.get('roll_no', '')
    
    all_subjects = execute_query("SELECT * FROM subjects", fetchall=True)
    
    subject_stats = []
    overall_attended = 0
    overall_total = 0
    
    for sub in all_subjects:
        sub_id = sub['subject_id']
        total_classes = sub.get('total_classes', 39) or 39
        
        attended = execute_query(
            "SELECT COUNT(*) as count FROM attendance WHERE student_id = %s AND subject_id = %s AND status = 'Present'",
            (student_id, sub_id), fetch=True
        )['count']
        
        percentage = round((attended / total_classes * 100), 1) if total_classes > 0 else 0
        
        required_for_75 = math.ceil(0.75 * total_classes)
        classes_needed = max(required_for_75 - attended, 0)
        
        classes_marked = execute_query(
            "SELECT COUNT(*) as count FROM attendance WHERE student_id = %s AND subject_id = %s",
            (student_id, sub_id), fetch=True
        )['count']
        remaining = max(total_classes - classes_marked, 0)
        
        can_reach_75 = (attended + remaining) >= required_for_75
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
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(DATASET_FOLDER, exist_ok=True)
    app.run(debug=True, port=5000)
