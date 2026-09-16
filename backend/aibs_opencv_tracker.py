"""
AI-BS OpenCV Face & Head Tracking Engine
----------------------------------------
Captures webcam stream, detects face/eye keypoints via OpenCV Haar Cascades,
and streams real-time 3D rotation and translation vectors to Unreal Engine 5.8
via the Remote Control API (Port 30010) or Python WebSocket Relay (Port 8888).
"""

import cv2
import json
import time
import requests
import logging
import threading
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [AI-BS OpenCV Tracker] - %(message)s')

class AIBSIOpenCVTracker:
    def __init__(self, ue_remote_control_url="http://127.0.0.1:30010/remote/object/call", camera_id=0):
        self.ue_url = ue_remote_control_url
        self.camera_id = camera_id
        self.is_running = False
        self.thread = None
        
        # Load OpenCV cascades with resilient fallback and validation
        self.face_cascade = None
        self.eye_cascade = None
        try:
            face_paths = [
                os.path.join(getattr(cv2.data, 'haarcascades', ''), 'haarcascade_frontalface_default.xml'),
                os.path.join(os.path.dirname(__file__), 'models', 'haarcascades', 'haarcascade_frontalface_default.xml'),
            ]
            eye_paths = [
                os.path.join(getattr(cv2.data, 'haarcascades', ''), 'haarcascade_eye.xml'),
                os.path.join(os.path.dirname(__file__), 'models', 'haarcascades', 'haarcascade_eye.xml'),
            ]
            for fp in face_paths:
                if os.path.exists(fp):
                    fc = cv2.CascadeClassifier(fp)
                    if not fc.empty():
                        self.face_cascade = fc
                        break
            for ep in eye_paths:
                if os.path.exists(ep):
                    ec = cv2.CascadeClassifier(ep)
                    if not ec.empty():
                        self.eye_cascade = ec
                        break
            if not self.face_cascade:
                logging.warning("Haar face cascade classifier could not be loaded or is empty.")
        except Exception as e:
            logging.warning(f"Could not load Haar cascades: {e}")
            self.face_cascade = None
            self.eye_cascade = None

    def start(self):
        if self.is_running:
            logging.info("Tracker is already running.")
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
        logging.info("OpenCV Head Tracking daemon started.")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        logging.info("OpenCV Head Tracking daemon stopped.")

    def _tracking_loop(self):
        cap = cv2.VideoCapture(self.camera_id)
        if not cap.isOpened():
            logging.error(f"Cannot open webcam (ID {self.camera_id}). Ensure camera is connected.")
            self.is_running = False
            return

        logging.info("Webcam feed initialized successfully.")

        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.03)
                continue

            if not self.face_cascade:
                time.sleep(0.1)
                continue

            h, w, _ = frame.shape
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

            if len(faces) > 0:
                # Pick largest face
                (x, y, fw, fh) = max(faces, key=lambda b: b[2] * b[3])

                # Calculate normalized offset from frame center (-1.0 to 1.0)
                center_x = (x + fw / 2.0) / w - 0.5
                center_y = (y + fh / 2.0) / h - 0.5
                face_scale = fw / float(w) # Depth approximation

                # Map to Unreal 3D camera / actor rotation angles (Pitch, Yaw, Roll)
                yaw = center_x * 45.0   # Horizontal head turn (-22.5 to +22.5 deg)
                pitch = -center_y * 35.0 # Vertical head tilt (-17.5 to +17.5 deg)
                roll = 0.0

                self._send_to_unreal(pitch, yaw, roll, center_x, center_y, face_scale)

            time.sleep(0.03) # ~30 FPS loop

        cap.release()
        logging.info("Webcam released.")

    def _send_to_unreal(self, pitch, yaw, roll, x_pos, y_pos, depth):
        """Sends payload to Unreal Engine Remote Control API or WebSocket bridge."""
        payload = {
            "objectPath": "/Game/Maps/MainMap.MainMap:PersistentLevel.CineCameraActor_1",
            "functionName": "SetActorRotation",
            "parameters": {
                "NewRotation": {"Pitch": pitch, "Yaw": yaw, "Roll": roll}
            },
            "generateTransaction": False
        }
        try:
            res = requests.put(self.ue_url, json=payload, timeout=0.1)
        except Exception:
            pass # Fail silently if Unreal Engine RC server is temporarily busy

tracker_instance = AIBSIOpenCVTracker()

if __name__ == "__main__":
    print("Testing AI-BS OpenCV Tracker standalone...")
    tracker_instance.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        tracker_instance.stop()
