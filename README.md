# Driver Drowsiness Detection System (AI Dashboard)

A real-time, AI-powered Driver Monitoring Engine that evaluates driver drowsiness using computer vision and facial landmarks. This system uses MediaPipe and OpenCV to calculate both the **Eye Aspect Ratio (EAR)** and **Mouth Aspect Ratio (MAR)** to intelligently detect signs of fatigue and yawning. 

The application features a modern, responsive web dashboard built with Flask and Bootstrap 5, complete with live telemetry streaming and "OpenEnv" compatible API endpoints.

## 🌟 Features
* **Real-Time Video Streaming**: Analyzes the camera feed dynamically within your browser.
* **Dual-Metric Detection**:
  * **EAR**: Tracks precise eye closure states to classify normal blinks vs. micro-sleeps.
  * **MAR**: Detects yawning based on mouth coordinate tracking.
* **Smart Alerting System**: Automatically escalates warnings from "Drowsy Alert" to "Critical Fatigue" based on a calculated cumulative Alertness Score.
* **OpenEnv Compatible**: Includes a `POST /reset` route to comply with OpenEnv standardized baseline testing and automated checking.
* **Dashboard Interface**: Provides live FPS tracking, alertness scoring, and an interactive system log with a futuristic dark-mode UI.

## 🚀 Hugging Face Deployment Setup
This project has been configured for easy deployment on Hugging Face Spaces using the Docker SDK:

### Prerequisites (For HF Spaces)
The repository uses a flat file structure so it can easily operate in cloud Docker environments. Ensure all files are uploaded exactly to the root:
* `app.py`
* `facemeshdetect.py`
* `inference.py` (Validation tester)
* `Dockerfile`
* `requirements.txt`
* `index.html`
* `script.js`
* `style.css`

### Local Installation
If running locally, ensure you have Python 3.9+ installed.

1. Install dependencies:
```bash
pip install -r requirements.txt
```
*(Note: Uses `opencv-python-headless` and explicitly caps `numpy < 2.0.0` for Mediapipe stability).*

2. Launch the Flask App:
```bash
python app.py
```
3. Open `http://localhost:7860` in your web browser.

## 🛠️ API Endpoints
* **`GET /`**: Renders the main dashboard interface.
* **`GET /video_feed`**: Streams the annotated MJPEG video feed.
* **`GET /status`**: Returns real-time metrics (EAR, MAR, FPS, and scoring) via JSON.
* **`POST /start_detection`**: Boots up the worker thread to begin tracking metrics.
* **`POST /stop_detection`**: Gracefully spins down the camera allocation.
* **`POST /reset`** or **`/openenv/reset`**: Resets all internal drowsiness trackers, score penalties, and state flags back to initialization status.

## 🧠 Technologies Used
* **Backend**: Python, Flask, OpenCV
* **AI/CV Engine**: Google MediaPipe Solutions (`mp.solutions.face_mesh`)
* **Frontend**: HTML5, Vanilla JavaScript, CSS3, Bootstrap 5
* **Deployment**: Docker (`python:3.9-slim`)
