import os
from database import execute_query


def create_demo_data():
    # Student name -> roll number mapping
    students_data = [
        ("Tripti", "124102052"),
        ("Pallavi", "124102053"),
        ("Raj", "124102058"),
        ("Rahul", "124102062"),
        ("Sarbjeet", "124102064"),
    ]

    # 1. Insert teacher
    execute_query(
        "INSERT OR IGNORE INTO teachers (name, email, password) VALUES ('Demo Teacher', 'teacher@nitkkr.ac.in', 'teacher123')",
        commit=True,
    )
    teacher = execute_query(
        "SELECT teacher_id FROM teachers WHERE email='teacher@nitkkr.ac.in'", fetch=True
    )
    t_id = teacher["teacher_id"] if teacher else 1

    # 2. Insert subjects (with initial total_classes = 39)
    execute_query(
        "INSERT OR IGNORE INTO subjects (subject_name, teacher_id, total_classes) VALUES ('Scripting Language', %s, 39)",
        (t_id,),
        commit=True,
    )
    execute_query(
        "INSERT OR IGNORE INTO subjects (subject_name, teacher_id, total_classes) VALUES ('Database Management System', %s, 39)",
        (t_id,),
        commit=True,
    )

    # 3. Create students and their image datasets
    for name, roll in students_data:
        # Insert student to DB
        execute_query(
            "INSERT OR IGNORE INTO students (name, roll_no, branch, year) VALUES (%s, %s, 'CSE', 3)",
            (name, roll),
            commit=True,
        )

        # Create dataset directory (named by roll_no)
        dir_path = f"dataset/{roll}"
        os.makedirs(dir_path, exist_ok=True)

        readme_path = os.path.join(dir_path, "README.txt")
        if not os.path.exists(readme_path):
            with open(readme_path, "w") as f:
                f.write(
                    f"Place 1-3 clear photos showing the face of {name} (Roll: {roll}) here as .jpg files.\n"
                )

    print("Demo Data Seeded successfully!")
    print("\nStudents added:")
    for name, roll in students_data:
        print(f"  {roll} - {name}")
    print("\nSubjects: Scripting Language, Database Management System")
    print("Teacher login: teacher@nitkkr.ac.in / teacher123")
    print("\nIMPORTANT:")
    print(
        "To make the Face Recognition work, you MUST place real face images in the 'dataset' subfolders."
    )
    print(
        "Once images are placed, go to the Admin portal and click 'Train Model'."
    )


if __name__ == "__main__":
    create_demo_data()
