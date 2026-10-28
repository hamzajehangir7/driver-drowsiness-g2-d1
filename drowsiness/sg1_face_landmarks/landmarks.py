"""SG-1: Face detection and facial landmarks using MediaPipe Face Mesh.

Gives 468+ (x, y) points per face. Supports both MediaPipe APIs:
  - the classic `mp.solutions.face_mesh` (older versions)
  - the newer Tasks `FaceLandmarker` (needs a small model file, auto-downloaded)
"""
import os
import urllib.request
from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np

from .. import config

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
             "face_landmarker/float16/1/face_landmarker.task")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "face_landmarker.task")


@dataclass
class FaceResult:
    found: bool
    landmarks: np.ndarray = None   # (N, 2) pixel coordinates
    bbox: tuple = None             # (x1, y1, x2, y2) in pixels


class FaceLandmarkDetector:
    def __init__(self):
        self._use_solutions = hasattr(mp, "solutions") and hasattr(mp.solutions, "face_mesh")
        if self._use_solutions:
            self._mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            )
        else:
            from mediapipe.tasks import python as mp_tasks
            from mediapipe.tasks.python import vision

            _ensure_model()
            options = vision.FaceLandmarkerOptions(
                base_options=mp_tasks.BaseOptions(model_asset_path=MODEL_PATH),
                running_mode=vision.RunningMode.VIDEO,
                num_faces=1,
                min_face_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_face_presence_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            )
            self._landmarker = vision.FaceLandmarker.create_from_options(options)
            self._last_ms = -1

    @property
    def backend(self):
        return "mediapipe.solutions" if self._use_solutions else "mediapipe.tasks"

    def process(self, frame_bgr, t):
        """Find the face in one frame. t = timestamp in seconds."""
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        if self._use_solutions:
            res = self._mesh.process(rgb)
            if not res.multi_face_landmarks:
                return FaceResult(found=False)
            pts = res.multi_face_landmarks[0].landmark
        else:
            ms = max(int(t * 1000), self._last_ms + 1)  # must strictly increase
            self._last_ms = ms
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = self._landmarker.detect_for_video(image, ms)
            if not res.face_landmarks:
                return FaceResult(found=False)
            pts = res.face_landmarks[0]

        lm = np.array([(p.x * w, p.y * h) for p in pts], dtype=np.float32)
        x1, y1 = lm.min(axis=0)
        x2, y2 = lm.max(axis=0)
        bbox = (int(max(x1, 0)), int(max(y1, 0)), int(min(x2, w - 1)), int(min(y2, h - 1)))
        return FaceResult(found=True, landmarks=lm, bbox=bbox)

    def close(self):
        if self._use_solutions:
            self._mesh.close()
        else:
            self._landmarker.close()


def _ensure_model():
    if os.path.exists(MODEL_PATH):
        return
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    print(f"Downloading face landmark model to {MODEL_PATH} ...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
