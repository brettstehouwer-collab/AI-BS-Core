import os
import sys

class AIBSVideoAnalyzer:
    """
    Bridge to OpenCV, Torchvision 3D ConvNets, TensorFlow, and DeepSORT
    for advanced Video Analysis, Action Recognition, and Object Tracking.
    """
    def __init__(self):
        self.device = "cpu"
        try:
            import torch
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            print(f"AIBSVideoAnalyzer Torch initialized on {self.device}")
        except ImportError:
            print("PyTorch not installed.")
            
        try:
            import tensorflow as tf
            print(f"TensorFlow available: {tf.__version__}")
        except ImportError:
            print("TensorFlow not installed.")

    def extract_frames(self, video_path):
        """Uses OpenCV to extract frames from a video."""
        import cv2
        cap = cv2.VideoCapture(video_path)
        frames = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()
        return frames

    def load_action_recognizer(self, model_name="r3d_18"):
        """Loads a 3D ConvNet for action recognition (e.g., R3D_18, MC3_18)"""
        from torchvision import models
        if model_name == "r3d_18":
            model = models.video.r3d_18(pretrained=True)
        elif model_name == "mc3_18":
            model = models.video.mc3_18(pretrained=True)
        else:
            raise ValueError(f"Unknown action recognition model {model_name}")
        model.eval()
        return model.to(self.device)

    def load_tracker(self, max_age=30):
        """Loads DeepSORT for object tracking."""
        from deep_sort_realtime.deepsort_tracker import DeepSort
        tracker = DeepSort(max_age=max_age)
        return tracker

    def recognize_action(self, model, video_tensor):
        """
        video_tensor shape should be (B, C, T, H, W)
        """
        import torch
        with torch.no_grad():
            output = model(video_tensor.to(self.device))
        return output

    def track_objects_in_frame(self, tracker, detections, frame):
        """
        detections format: [[ [x,y,w,h], confidence, class_id ], ...]
        """
        tracks = tracker.update_tracks(detections, frame=frame)
        return tracks

if __name__ == "__main__":
    analyzer = AIBSVideoAnalyzer()
    print("Maximum Video Analysis Capabilities Instantiated.")
