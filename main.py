import cv2
import time
import numpy as np
import facemeshdetect as fmt
import winsound  # for alarm (Windows)

cap = cv2.VideoCapture(0)
detector = fmt.faceMeshDetection()

previous_time = 0

# Eye landmark indices (MediaPipe)
LEFT_EYE = [33, 160, 158, 133, 153, 144]

# Fatigue variables
blink_count = 0
closed_frames = 0
fatigue_score = 0

# Drowsiness alert
counter = 0
ALARM_ON = False

def eye_aspect_ratio(eye):
    A = np.linalg.norm(np.array(eye[1]) - np.array(eye[5]))
    B = np.linalg.norm(np.array(eye[2]) - np.array(eye[4]))
    C = np.linalg.norm(np.array(eye[0]) - np.array(eye[3]))
    ear = (A + B) / (2.0 * C)
    return ear

while True:
    success, frame = cap.read()
    if not success:
        break

    frame, faces = detector.findfacemeshes(frame)

    if faces:
        face = faces[0]

        # Get left eye points
        left_eye = [face[i] for i in LEFT_EYE]

        # Calculate EAR
        ear = eye_aspect_ratio(left_eye)

        # Draw eye points
        for point in left_eye:
            cv2.circle(frame, point, 2, (0, 255, 0), -1)

        # ================= FATIGUE LOGIC =================
        if ear < 0.25:
            closed_frames += 1
            counter += 1
        else:
            if closed_frames > 2:
                blink_count += 1
            closed_frames = 0
            counter = 0
            ALARM_ON = False

        # Fatigue Score (0–100)
        fatigue_score = min(100, (closed_frames * 2 + blink_count * 1.5))

        # ================= DISPLAY =================
        cv2.putText(frame, f'EAR: {round(ear,2)}', (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        cv2.putText(frame, f'Fatigue: {int(fatigue_score)}%', (30, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # Fatigue levels
        if fatigue_score > 70:
            cv2.putText(frame, "HIGH FATIGUE!", (50, 200),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        elif fatigue_score > 40:
            cv2.putText(frame, "MEDIUM FATIGUE", (50, 200),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        # ================= DROWSINESS ALERT =================
        if counter > 15:
            cv2.putText(frame, "DROWSY ALERT!", (50, 250),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            if not ALARM_ON:
                winsound.Beep(1000, 500)
                ALARM_ON = True

    # ================= FPS =================
    current_time = time.time()
    fps = 1 / (current_time - previous_time)
    previous_time = current_time

    cv2.putText(frame, f'FPS: {int(fps)}', (10, 300),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)

    cv2.imshow("Driver Drowsiness Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()