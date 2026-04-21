
import sys
import cv2
import numpy as np
import json
import time
import datetime
import requests
from liveness_mobilenet import check_liveness

last_alert_time = 0
ALERT_COOLDOWN = 5  # seconds
def send_alert_api(name, category, timestamp):
    url = "https://httpbin.org/post"  # demo API endpoint

    payload = {
        "person_name": name,
        "category": category,
        "time": timestamp,
        "location": "Camera-1"
    }

    try:
        response = requests.post(url, json=payload, timeout=3)
        print("API Alert Sent:", response.status_code)
    except Exception as e:
        print("API Alert Failed:", e)
# Load Haar Cascade
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
model = cv2.face.LBPHFaceRecognizer_create()
model.read("lbph_model.yml")
label_map = np.load("label_map.npy", allow_pickle=True).item()
with open("persons.json", "r") as f:
    persons = json.load(f)
# Convert persons list to dict for easy lookup
person_info = {}
for p in persons:
    person_info[p["person_id"]] = p
if len(sys.argv) > 1:
    VIDEO_SOURCE = sys.argv[1]   # video file from FastAPI
else:
    VIDEO_SOURCE = 0            # fallback to webcam
print("VIDEO SOURCE:", VIDEO_SOURCE)
cap = cv2.VideoCapture(VIDEO_SOURCE)

if not cap.isOpened():
    print("Error: Cannot open video source")
    exit()


while True:
    ret, frame = cap.read()
    if not ret:
        break
        print("Processing frame...")
    frame = cv2.convertScaleAbs(frame, alpha=1.2, beta=30)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=4,
        minSize=(50, 50)
    )

    print("Faces found:", len(faces))

    for (x, y, w, h) in faces:
        face = gray[y:y + h, x:x + w]
        face = cv2.resize(face, (200, 200))

        # ✅ STEP 1: Liveness check
        is_live = check_liveness(face)

        if not is_live:
            text = "Unknown"
            color = (0, 165, 255)

        else:
            # ✅ STEP 2: Recognition
            label, confidence = model.predict(face)
            print("Confidence:", confidence)

            if label in label_map and confidence < 70:
                folder_name = label_map[label]
                person_id = int(folder_name.split("_")[0])
                name = folder_name.split("_")[1]
                category = person_info[person_id]["category"]

                # -------- ALERT GENERATION --------
                alert_text = ""

                if category in ["crime", "criminal"]:
                    alert_text = "ALERT: Criminal detected"
                    print("🚨 ALERT: Criminal detected!")
                elif category == "missing":
                    alert_text = "ALERT: Missing person detected"
                    print("⚠️ ALERT: Missing person detected!")

                # -------- ON-SCREEN ALERT --------
                current_time = time.time()
                if alert_text and (current_time - last_alert_time > ALERT_COOLDOWN):
                    last_alert_time = current_time
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")

                    cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), (0, 0, 0), -1)
                    cv2.putText(frame, f"{alert_text} | {timestamp}",
                                (10, 28),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7, (0, 0, 255), 2)

                    # -------- LOG FILE --------
                    with open("alerts_log.txt", "a") as f:
                        f.write(f"{timestamp} - {name} - {category}\n")
                    import sqlite3

                    conn = sqlite3.connect("surveillance.db")
                    cur = conn.cursor()

                    cur.execute(
                        "INSERT INTO alerts (person_name, category, timestamp) VALUES (?, ?, ?)",
                        (name, category, timestamp)
                    )

                    conn.commit()
                    conn.close()


                    send_alert_api(name, category, timestamp)
                text = f"{name} ({category})"
                color = (0, 0, 255) if category in ["crime", "criminal"] else (0, 255, 0)
            else:
                text = "Unknown"
                color = (255, 255, 0)

        # ✅ DRAW ONLY ONCE
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        cv2.putText(frame, text, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    # ✅ 🚨 THIS WAS MISSING — VERY IMPORTANT
    cv2.imshow("Haar + LBPH Face Recognition", frame)

    if cv2.waitKey(30) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
