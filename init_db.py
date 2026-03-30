import sqlite3

def init_database():
    try:
        conn = sqlite3.connect("main.db")
        cursor = conn.cursor()

        # Enable foreign key support
        cursor.execute("PRAGMA foreign_keys = ON;")

        print("Creating admins table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        print("Creating students table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_no TEXT UNIQUE NOT NULL,
            branch TEXT NOT NULL,
            year INTEGER NOT NULL,
            face_encoding TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        print("Creating teachers table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        print("Creating subjects table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            teacher_id INTEGER,
            FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE SET NULL
        )
        """)

        print("Creating attendance table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            subject_id INTEGER,
            date DATE NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
            UNIQUE(student_id, subject_id, date)
        )
        """)

        # Insert demo admin
        cursor.execute("""
        INSERT OR IGNORE INTO admins (username, password)
        VALUES ('admin', 'admin123')
        """)

        conn.commit()
        print("Database initialization successful!")

    except Exception as err:
        print(f"Error initializing database: {err}")

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    init_database()