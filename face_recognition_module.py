import face_recognition
import cv2
import os
import json
import numpy as np

def encode_faces(dataset_path):
    """
    Scans the dataset directory. Returns a dictionary mapping student_names to their face encodings.
    The directory structure should be: dataset/student_name/image.jpg
    Returns: { "student_name": encoding_list_or_numpy_array }
    """
    known_encodings = {}
    
    # Check if dataset path exists
    if not os.path.exists(dataset_path):
        print(f"Dataset path {dataset_path} does not exist.")
        return known_encodings
        
    for student_name in os.listdir(dataset_path):
        student_dir = os.path.join(dataset_path, student_name)
        
        # Skip if it's not a directory
        if not os.path.isdir(student_dir):
            continue
            
        student_encodings = []
        for image_name in os.listdir(student_dir):
            if image_name.endswith(('.jpg', '.jpeg', '.png')):
                image_path = os.path.join(student_dir, image_name)
                
                try:
                    # Load image
                    image = face_recognition.load_image_file(image_path)
                    
                    # Convert to RGB (OpenCV uses BGR, but face_recognition load_image_file uses RGB)
                    
                    # Find encodings
                    encodings = face_recognition.face_encodings(image)
                    
                    if len(encodings) > 0:
                        student_encodings.append(encodings[0])
                    else:
                        print(f"Warning: No face found in {image_path}")
                except Exception as e:
                    print(f"Error processing {image_path}: {e}")
                    
        if student_encodings:
            # We average the encodings if there are multiple images for better accuracy
            avg_encoding = np.mean(student_encodings, axis=0)
            known_encodings[student_name] = avg_encoding.tolist()
            print(f"Generated encoding for {student_name}")
            
    return known_encodings

def recognize_faces(image_path, known_student_names, known_encodings_list, tolerance=0.5):
    """
    Detects faces in an uploaded group photo and matches them against known encodings.
    
    Args:
        image_path (str): Path to the uploaded group photo.
        known_student_names (list): List of student names (or IDs) corresponding to the encodings.
        known_encodings_list (list): List of known face encodings (numpy arrays).
        tolerance (float): How much distance between faces to consider it a match. Lower is more strict.
        
    Returns:
        recognized_students (list): List of student names identified in the photo.
        annotated_image_path (str): Relative path to the image with bounding boxes.
    """
    try:
        # Load the uploaded image
        group_image = face_recognition.load_image_file(image_path)
        
        # Find all face locations and encodings in the group image
        face_locations = face_recognition.face_locations(group_image)
        face_encodings = face_recognition.face_encodings(group_image, face_locations)
        
        # We also want to keep an annotated image to show the teacher
        # Convert RGB to BGR for OpenCV
        annotated_image = cv2.cvtColor(group_image, cv2.COLOR_RGB2BGR)
        
        recognized_students = []
        
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(known_encodings_list, face_encoding, tolerance=tolerance)
            name = "Unknown"
            
            # Use the known face with the smallest distance to the new face
            face_distances = face_recognition.face_distance(known_encodings_list, face_encoding)
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_student_names[best_match_index]
                    if name not in recognized_students:
                        recognized_students.append(name)
            
            # Draw a box around the face
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(annotated_image, (left, top), (right, bottom), color, 2)
            
            # Draw a label with a name below the face
            cv2.rectangle(annotated_image, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(annotated_image, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)
            
        # Save the annotated image
        output_filename = "annotated_" + os.path.basename(image_path)
        output_path = os.path.join(os.path.dirname(image_path), output_filename)
        cv2.imwrite(output_path, annotated_image)
        
        return recognized_students, output_filename
        
    except Exception as e:
        print(f"Error in recognize_faces: {e}")
        return [], None
