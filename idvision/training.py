import json
import os

import cv2
import numpy as np

BASE_DIR = "dataset"
CATEGORIES = {
    "missing_persons": "missing",
    "criminals": "criminal",
}

_face_cascade = None


def _cascade():
    global _face_cascade
    if _face_cascade is None:
        _face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
    return _face_cascade


def _parse_folder(folder_name):
    parts = folder_name.split("_", 1)
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), parts[1].strip()
    except ValueError:
        return None


def _extract_faces(img_path):
    img = cv2.imread(img_path)
    if img is None:
        return []
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    detections = _cascade().detectMultiScale(gray, 1.3, 5)
    out = []
    for (x, y, w, h) in detections:
        face = gray[y:y + h, x:x + w]
        out.append(cv2.resize(face, (200, 200)))
    return out


def train():
    """Train LBPH from dataset/ and write lbph_model.yml, label_map.npy, persons.json."""
    faces = []
    labels = []
    label_map = {}
    persons = []
    current_label = 0

    for category_folder, category_value in CATEGORIES.items():
        category_path = os.path.join(BASE_DIR, category_folder)
        if not os.path.isdir(category_path):
            print(f"[train] Skipping missing category dir: {category_path}")
            continue

        for entry in sorted(os.listdir(category_path)):
            person_path = os.path.join(category_path, entry)
            if not os.path.isdir(person_path):
                print(f"[train] Skipping non-folder entry: {person_path}")
                continue

            parsed = _parse_folder(entry)
            if not parsed:
                print(f"[train] Skipping unparseable folder name: {entry!r}")
                continue
            person_id, person_name = parsed

            sample_count = 0
            for img_name in sorted(os.listdir(person_path)):
                for face in _extract_faces(os.path.join(person_path, img_name)):
                    faces.append(face)
                    labels.append(current_label)
                    sample_count += 1

            if sample_count == 0:
                print(f"[train] No faces found in {person_path}; skipping.")
                continue

            label_map[current_label] = {
                "folder": entry,
                "person_id": person_id,
                "name": person_name,
                "category": category_value,
            }
            persons.append({
                "person_id": person_id,
                "name": person_name,
                "category": category_value,
            })
            print(f"[train] Label {current_label}: {entry} ({category_value}, {sample_count} faces)")
            current_label += 1

    if not faces:
        raise SystemExit("[train] No training samples found. Add images to dataset/ first.")

    print(f"[train] Training LBPH on {len(faces)} faces across {current_label} people...")
    model = cv2.face.LBPHFaceRecognizer_create()
    model.train(faces, np.array(labels))

    model.save("lbph_model.yml")
    np.save("label_map.npy", label_map)
    with open("persons.json", "w", encoding="utf-8") as f:
        json.dump(persons, f, indent=2)

    print("[train] Training complete. Saved lbph_model.yml, label_map.npy, persons.json.")
