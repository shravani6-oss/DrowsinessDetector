import os
import cv2
import time
import threading
import numpy as np
from flask import Flask, render_template, Response, jsonify
import facemeshdetect as fmt

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='/static')

# ====== GLOBAL STATE ======
camera = None
is_detecting = False
global_frame = None
status_lock = threading.Lock()

# Output state variables
current_status = "IDLE"
state_reason = "System initialized"
fps_value = 0
current_ear = 0.0
current_mar = 0.0
alertness_score = 100.0
drowsy_duration = 0.0

# Internal Tracking Logic
LEFT_EYE = [33, 160, 158, 133, 153, 144]
# Inner mouth: left corner 78, right corner 308, top lip 13, bottom lip 14
MOUTH = [78, 308, 13, 14] 

closed_frames = 0
eyes_open_frames = 0
last_yawn_time = 0
yawn_cooldown = 4.0 # seconds
drowsy_start_time = 0

# Initialize MediaPipe wrapper
detector = fmt.faceMeshDetection()

def eye_aspect_ratio(eye):
    """Calculates Eye Aspect Ratio to detect blinks/drowsiness"""
    A = np.linalg.norm(np.array(eye[1]) - np.array(eye[5]))
    B = np.linalg.norm(np.array(eye[2]) - np.array(eye[4]))
    C = np.linalg.norm(np.array(eye[0]) - np.array(eye[3]))
    ear = (A + B) / (2.0 * C) if C != 0 else 0
    return ear

def mouth_aspect_ratio(mouth):
    """Calculates Mouth Aspect Ratio to detect yawning"""
    width = np.linalg.norm(np.array(mouth[0]) - np.array(mouth[1]))
    height = np.linalg.norm(np.array(mouth[2]) - np.array(mouth[3]))
    return height / width if width != 0 else 0

def detection_loop():
    """Background thread function for handling the webcam and CV processing"""
    global camera, is_detecting, global_frame
    global current_status, fps_value, current_ear, current_mar
    global alertness_score, drowsy_duration, state_reason
    global closed_frames, eyes_open_frames, last_yawn_time, drowsy_start_time

    camera = cv2.VideoCapture(0)
    previous_time = 0

    while is_detecting:
        if not camera.isOpened():
            time.sleep(0.1)
            continue
            
        success, frame = camera.read()
        if not success:
            time.sleep(0.1)
            continue
            
        # Flip frame horizontally for easier viewing mirroring
        frame = cv2.flip(frame, 1)

        # Process frame
        frame, faces = detector.findfacemeshes(frame, draw_landmark=False)
        
        # Local state
        frame_status = "ACTIVE"
        frame_reason = "Driver behavior nominal"
        score_adj = 0.0
        ear = 0.0
        mar = 0.0
        is_yawning = False

        if faces:
            face = faces[0]
            try:
                current_time_loop = time.time()
                
                # Calculate EAR for left eye
                left_eye = [face[i] for i in LEFT_EYE]
                ear = eye_aspect_ratio(left_eye)
                
                # Calculate MAR
                mouth_pts = [face[i] for i in MOUTH]
                mar = mouth_aspect_ratio(mouth_pts)
                
                # Draw landmarks
                for point in left_eye:
                    cv2.circle(frame, point, 2, (0, 255, 0), -1)
                for point in mouth_pts:
                    cv2.circle(frame, point, 2, (0, 255, 255), -1)

                cv2.putText(frame, f'EAR: {round(ear,2)}', (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(frame, f'MAR: {round(mar,2)}', (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                # Yawning Logic
                if mar > 0.5 and (current_time_loop - last_yawn_time) > yawn_cooldown:
                    is_yawning = True
                    last_yawn_time = current_time_loop
                
                if (current_time_loop - last_yawn_time) < 2.0: # active yawn indicator
                    frame_reason = "Yawning detected"
                    cv2.putText(frame, "YAWN DETECTED", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)

                # Drowsiness Logic (EAR)
                if ear < 0.22: # Tweak: Dropped from 0.25 to 0.22 to account for natural variations
                    if closed_frames == 0:
                        drowsy_start_time = current_time_loop
                    closed_frames += 1
                    eyes_open_frames = 0
                    drowsy_sec = current_time_loop - drowsy_start_time
                    
                    if drowsy_sec > 0.5:
                        frame_reason = "EAR below threshold"
                        score_adj = -0.3 # Penalize sustained closure
                    else:
                        score_adj = 0.0 # Normal blink, don't penalize yet
                else:
                    eyes_open_frames += 1
                    if eyes_open_frames > 3: # Tweak: Fast recovery (was 15) to prevent double-blink stacking
                        closed_frames = 0
                        drowsy_sec = 0.0
                    else:
                        drowsy_sec = current_time_loop - drowsy_start_time if closed_frames > 0 else 0.0
                    score_adj = 0.3 # Faster recovery
                
                if is_yawning or (current_time_loop - last_yawn_time) < 2.0:
                    score_adj = -0.5
                
                if drowsy_sec > 1.5:
                    frame_status = "WARNING"
                    frame_reason = "Prolonged eye closure"
                    score_adj = -1.0
                if drowsy_sec > 3.0:
                    frame_status = "CRITICAL"
                    frame_reason = "Critical fatigue detected"
                    score_adj = -2.0
                    cv2.putText(frame, "DROWSY ALERT!", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            except Exception as e:
                print(f"Error processing face: {e}")

        else:
             # No face found
             frame_reason = "Tracking lost / No face detected"
             drowsy_sec = 0.0
             score_adj = -0.05 # Tweak: Severely reduced penalty for simply moving out of frame

        # Update FPS
        current_time_now = time.time()
        fps = 1 / (current_time_now - previous_time) if (current_time_now - previous_time) > 0 else 0
        previous_time = current_time_now
        
        # Update Alertness Score
        alertness_val = alertness_score + score_adj
        alertness_val = max(0.0, min(100.0, alertness_val))
        
        # Override status based on strict score limits
        if alertness_val <= 40:
            frame_status = "CRITICAL"
            frame_reason = "Alertness score critically low"
            cv2.putText(frame, "CRITICAL ALERTNESS!", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
        elif alertness_val <= 70 and frame_status == "ACTIVE":
            frame_status = "WARNING"
            if frame_reason == "Driver behavior nominal":
                frame_reason = "Driver alertness dropping"

        # Safely update global state which API reads from
        with status_lock:
            current_status = frame_status
            state_reason = frame_reason
            fps_value = int(fps)
            current_ear = ear
            current_mar = mar
            drowsy_duration = drowsy_sec if drowsy_sec > 0 else 0.0
            alertness_score = alertness_val
            
            # Encode frame to JPEG so it can be pushed to browser
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                global_frame = buffer.tobytes()

    # Thread exits gracefully
    if camera:
        camera.release()
        camera = None

def generate_frames():
    """Generator for streaming MJPEG bytes"""
    global global_frame, is_detecting
    while is_detecting:
        with status_lock:
            frame = global_frame
            
        if frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.03) # Cap stream at ~30 FPS
        else:
            time.sleep(0.1)

# ====== ROUTES ======

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Route serving the multipart video feed"""
    if not is_detecting:
        return Response(status=204) # No Content
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_detection', methods=['POST'])
def start_detection():
    global is_detecting, current_status, score_adj, alertness_score, state_reason
    global closed_frames, eyes_open_frames, drowsy_duration, last_yawn_time
    if not is_detecting:
        is_detecting = True
        current_status = "ACTIVE"
        state_reason = "System tracking initialized"
        alertness_score = 100.0
        closed_frames = 0
        eyes_open_frames = 0
        drowsy_duration = 0.0
        last_yawn_time = 0.0
        # Spool up thread
        threading.Thread(target=detection_loop, daemon=True).start()
    return jsonify({"success": True, "message": "System active."})

@app.route('/stop_detection', methods=['POST'])
def stop_detection():
    global is_detecting, current_status, global_frame, closed_frames, eyes_open_frames, drowsy_duration, state_reason
    with status_lock:
        is_detecting = False
        current_status = "IDLE"
        state_reason = "System offline"
        global_frame = None
        # Reset trackers
        closed_frames = 0
        eyes_open_frames = 0
        drowsy_duration = 0.0
    return jsonify({"success": True, "message": "System halted."})

@app.route('/reset', methods=['POST'])
@app.route('/reset/', methods=['POST'])
@app.route('/openenv/reset', methods=['POST'])
@app.route('/openenv/reset/', methods=['POST'])
def reset():
    global is_detecting, current_status, global_frame, closed_frames, eyes_open_frames, drowsy_duration, state_reason
    global alertness_score, last_yawn_time, fps_value, current_ear, current_mar, drowsy_start_time
    with status_lock:
        is_detecting = False
        current_status = "IDLE"
        state_reason = "System initialized"
        global_frame = None
        closed_frames = 0
        eyes_open_frames = 0
        drowsy_duration = 0.0
        alertness_score = 100.0
        last_yawn_time = 0
        fps_value = 0
        current_ear = 0.0
        current_mar = 0.0
        drowsy_start_time = 0
    return jsonify({"success": True, "status": "ok", "message": "System reset ok"}), 200

@app.route('/status')
def get_status():
    """Returns real-time system status in JSON format"""
    with status_lock:
        return jsonify({
            "status": current_status,
            "reason": state_reason,
            "fps": fps_value,
            "ear": round(current_ear, 3),
            "mar": round(current_mar, 3),
            "score": round(alertness_score, 1),
            "drowsy_duration": round(drowsy_duration, 1)
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))
    app.run(debug=True, threaded=True, host='0.0.0.0', port=port)

