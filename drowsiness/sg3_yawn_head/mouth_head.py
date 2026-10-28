"""SG-3: Mouth opening (MAR), yawn detection and head pose."""
import math
from dataclasses import dataclass

import cv2
import numpy as np

from .. import config

# ---------------- Mouth ----------------
# Inner-lip points from MediaPipe Face Mesh.
MOUTH_CORNERS = (78, 308)                       # left / right inner corners
MOUTH_VERTICAL = [(81, 178), (13, 14), (311, 402)]  # upper / lower lip pairs


def mouth_aspect_ratio(lm):
    """MAR = mean vertical lip gap / horizontal mouth width.

    About 0.0-0.1 closed, 0.3-0.5 talking, above 0.6 for a wide yawn.
    """
    width = np.linalg.norm(lm[MOUTH_CORNERS[0]] - lm[MOUTH_CORNERS[1]])
    if width == 0:
        return 0.0
    gaps = [np.linalg.norm(lm[a] - lm[b]) for a, b in MOUTH_VERTICAL]
    return float(np.mean(gaps) / width)


# ---------------- Head pose ----------------
# Points used for head pose: nose tip, chin, outer eye corners, mouth corners.
POSE_IDS = [1, 152, 33, 263, 61, 291]
# Generic 3D face model in the camera's convention (x right, y down,
# z away from the camera). With no rotation, the face looks straight at the camera.
MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),          # nose tip
    (0.0, 330.0, 65.0),       # chin
    (-225.0, -170.0, 135.0),  # left eye outer corner (image left)
    (225.0, -170.0, 135.0),   # right eye outer corner (image right)
    (-150.0, 150.0, 125.0),   # left mouth corner
    (150.0, 150.0, 125.0),    # right mouth corner
], dtype=np.float64)


def head_pose(lm, frame_w, frame_h):
    """Return (pitch, yaw, roll) in degrees, or None if it can't be solved.

    pitch > 0: looking down     yaw > 0: turned towards image right
    roll  > 0: tilted clockwise in the image
    """
    image_points = lm[POSE_IDS].astype(np.float64)
    focal = frame_w  # rough focal length is fine for angles
    camera_matrix = np.array([[focal, 0, frame_w / 2],
                              [0, focal, frame_h / 2],
                              [0, 0, 1]], dtype=np.float64)
    ok, rvec, _ = cv2.solvePnP(MODEL_POINTS, image_points, camera_matrix,
                               np.zeros((4, 1)), flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        return None
    R, _ = cv2.Rodrigues(rvec)
    forward = -R[:, 2]  # direction the face is pointing (towards the camera at rest)
    pitch = math.degrees(math.asin(float(np.clip(forward[1], -1.0, 1.0))))
    yaw = math.degrees(math.atan2(forward[0], -forward[2]))
    roll = math.degrees(math.atan2(R[1, 0], R[0, 0]))
    return pitch, yaw, roll


# ---------------- State ----------------
@dataclass
class MouthHeadState:
    mar: float = 0.0
    mouth_open: bool = False
    yawning: bool = False          # wide open for at least YAWN_MIN_SEC
    wide_open_duration: float = 0.0
    yawn_count: int = 0
    yawn_event: bool = False       # True only on the frame a yawn is first confirmed
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0
    pitch_change: float = 0.0      # pitch relative to the calibrated baseline
    head_down: bool = False
    head_down_duration: float = 0.0


class MouthHeadAnalyzer:
    def __init__(self):
        self.state = MouthHeadState()
        self.baseline_pitch = 0.0
        self._wide_since = None
        self._yawn_counted = False
        self._down_since = None

    def set_baseline(self, pitch):
        """Camera may be mounted above/below the face, so 'down' is relative."""
        self.baseline_pitch = pitch

    def update(self, lm, t, frame_w, frame_h):
        s = self.state
        s.yawn_event = False

        # --- mouth / yawn ---
        s.mar = mouth_aspect_ratio(lm)
        s.mouth_open = s.mar > config.MAR_OPEN
        if s.mar > config.MAR_YAWN:
            if self._wide_since is None:
                self._wide_since = t
                self._yawn_counted = False
            s.wide_open_duration = t - self._wide_since
            if s.wide_open_duration >= config.YAWN_MIN_SEC and not self._yawn_counted:
                s.yawn_count += 1
                s.yawn_event = True
                self._yawn_counted = True
        else:
            self._wide_since = None
            s.wide_open_duration = 0.0
        s.yawning = self._wide_since is not None and self._yawn_counted

        # --- head pose ---
        pose = head_pose(lm, frame_w, frame_h)
        if pose is not None:
            s.pitch, s.yaw, s.roll = pose
            s.pitch_change = s.pitch - self.baseline_pitch
            s.head_down = s.pitch_change > config.HEAD_DOWN_DEG
            if s.head_down:
                if self._down_since is None:
                    self._down_since = t
                s.head_down_duration = t - self._down_since
            else:
                self._down_since = None
                s.head_down_duration = 0.0
        return s

    def face_lost(self):
        s = self.state
        s.mouth_open = s.yawning = s.head_down = s.yawn_event = False
        s.wide_open_duration = s.head_down_duration = 0.0
        self._wide_since = None
        self._down_since = None
