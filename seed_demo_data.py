import os
from database import execute_query


def create_demo_data():
    names = ["Raj", "Rahul", "Sarbjeet", "Tripti", "Pallavi"]

    # 1. Insert teacher
    execute_query(
        "INSERT OR IGNORE INTO teachers (name, email, password) VALUES ('Demo Teacher', 'teacher@nit.edu', 'teacher123')",
        commit=True,
    )
    teacher = execute_query(
        "SELECT teacher_id FROM teachers WHERE email='teacher@nit.edu'", fetch=True
    )
    t_id = teacher["teacher_id"] if teacher else 1

    # 2. Insert subjects
    execute_query(
        "INSERT OR IGNORE INTO subjects (subject_name, teacher_id) VALUES ('Machine Learning CS-501', %s)",
        (t_id,),
        commit=True,
    )
    execute_query(
        "INSERT OR IGNORE INTO subjects (subject_name, teacher_id) VALUES ('Computer Networks CS-502', %s)",
        (t_id,),
        commit=True,
    )

    # 3. Create students and their image datasets
    for i, name in enumerate(names):
        roll = f"120150{i+1}"

        # Insert student to DB
        execute_query(
            "INSERT OR IGNORE INTO students (name, roll_no, branch, year) VALUES (%s, %s, 'CSE', 3)",
            (name, roll),
            commit=True,
        )

        # Create dataset directory
        dir_path = f"dataset/{name}"
        os.makedirs(dir_path, exist_ok=True)

        readme_path = os.path.join(dir_path, "README.txt")
        if not os.path.exists(readme_path):
            with open(readme_path, "w") as f:
                f.write(
                    f"Place 1-3 clear photos showing the face of {name} here as .jpg files.\n"
                )

    print("Demo Data Seeded successfully!")
    print("\nIMPORTANT:")
    print(
        "To make the Face Recognition work, you MUST place real face images in the 'dataset' subfolders:"
    )
    print(", ".join(names))
    print(
        "Once images are placed, go to the Admin portal and click 'Train Model'."
    )


if __name__ == "__main__":
    create_demo_data()
