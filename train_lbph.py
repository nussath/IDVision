import cv2
import os
import numpy as np

BASE_DIR = "dataset"
CATEGORIES = ["missing_persons", "criminals"]

faces = []
labels = []
label_map = {}
current_label = 0

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

for category in CATEGORIES:
    category_path = os.path.join(BASE_DIR, category)

    for person in os.listdir(category_path):
        person_path = os.path.join(category_path, person)

        label_map[current_label] = person

        for img_name in os.listdir(person_path):
            img_path = os.path.join(person_path, img_name)

            img = cv2.imread(img_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            faces_detected = face_cascade.detectMultiScale(gray, 1.3, 5)

            for (x, y, w, h) in faces_detected:
                face = gray[y:y+h, x:x+w]
                face = cv2.resize(face, (200, 200))

                faces.append(face)
                labels.append(current_label)

        current_label += 1

print("Training LBPH model...")
model = cv2.face.LBPHFaceRecognizer_create()
model.train(faces, np.array(labels))

model.save("lbph_model.yml")
np.save("label_map.npy", label_map)

print("Training completed and model saved.")
