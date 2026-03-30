import mysql.connector
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

def init_database():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        print(f"Creating database {DB_NAME} if not exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        cursor.execute(f"USE {DB_NAME}")
        
        print("Creating admins table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        print("Creating students table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            roll_no VARCHAR(50) UNIQUE NOT NULL,
            branch VARCHAR(100) NOT NULL,
            year INT NOT NULL,
            face_encoding LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        print("Creating teachers table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            teacher_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        print("Creating subjects table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id INT AUTO_INCREMENT PRIMARY KEY,
            subject_name VARCHAR(100) NOT NULL,
            teacher_id INT,
            FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE SET NULL
        )
        """)
        
        print("Creating attendance table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            subject_id INT,
            date DATE NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
            UNIQUE KEY unique_attendance (student_id, subject_id, date)
        )
        """)
        
        # Insert demo admin
        try:
            cursor.execute("INSERT IGNORE INTO admins (username, password) VALUES ('admin', 'admin123')")
        except:
            pass
            
        conn.commit()
        print("Database initialization successful!")
        
    except mysql.connector.Error as err:
        print(f"Error initializing database: {err}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals() and conn.is_connected(): conn.close()

if __name__ == "__main__":
    init_database()
