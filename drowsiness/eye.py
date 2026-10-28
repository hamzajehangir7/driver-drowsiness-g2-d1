"""SG-2: Eye openness (EAR) and blink detection."""
from dataclasses import dataclass

import numpy as np

from . import config

# MediaPipe Face Mesh indices, ordered p1..p6 for the EAR formula:
#   p1, p4 = eye corners;  p2/p6 and p3/p5 = upper/lower eyelid pairs
LEFT_EYE = [33, 160, 158, 133, 153, 144]     # left side of the image
RIGHT_EYE = [362, 385, 387, 263, 373, 380]   # right side of the image


def eye_aspect_ratio(pts):
    """EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|).

    Roughly 0.25-0.35 when open, drops towards 0 when closed.
    """
    p1, p2, p3, p4, p5, p6 = pts
    vertical = np.linalg.norm(p2 - p6) + np.linalg.norm(p3 - p5)
    horizontal = np.linalg.norm(p1 - p4)
    return float(vertical / (2.0 * horizontal)) if horizontal > 0 else 0.0


@dataclass
class EyeState:
    ear_left: float = 0.0
    ear_right: float = 0.0
    ear: float = 0.0               # average of both eyes
    closed: bool = False
    closed_threshold: float = config.EAR_DEFAULT_CLOSED
    closed_duration: float = 0.0   # how long the eyes have been closed right now (s)
    blink_count: int = 0
    long_closure_count: int = 0    # closures longer than BLINK_MAX_SEC
    blink_event: bool = False      # True only on the frame a blink finishes
    closure_event: bool = False    # True on the frame any closure (blink or longer) finishes
    last_closure_duration: float = 0.0
    last_closure_min_ear: float = 0.0  # lowest EAR during the last closure (= closed-eye EAR)


class EyeAnalyzer:
    def __init__(self):
        self.state = EyeState()
        self.baseline_ear = None
        self._closed_since = None
        self._min_ear = 0.0

    def set_baseline(self, open_ear):
        """Called after calibration with the person's normal open-eye EAR."""
        self.baseline_ear = open_ear
        self.state.closed_threshold = open_ear * config.EAR_CLOSED_RATIO

    def update(self, landmarks, t):
        """landmarks: (N, 2) pixel coordinates. t: timestamp in seconds."""
        s = self.state
        s.blink_event = False
        s.closure_event = False
        s.ear_left = eye_aspect_ratio(landmarks[LEFT_EYE])
        s.ear_right = eye_aspect_ratio(landmarks[RIGHT_EYE])
        s.ear = (s.ear_left + s.ear_right) / 2.0

        # Hysteresis: separate close / re-open thresholds stop flickering.
        if s.closed:
            is_closed = s.ear < s.closed_threshold * config.EAR_HYSTERESIS
        else:
            is_closed = s.ear < s.closed_threshold

        if is_closed and not s.closed:            # eyes just closed
            self._closed_since = t
            self._min_ear = s.ear
        elif is_closed:
            self._min_ear = min(self._min_ear, s.ear)
        elif not is_closed and s.closed:          # eyes just re-opened
            self._finish_closure(t - self._closed_since)
            self._closed_since = None

        s.closed = is_closed
        s.closed_duration = (t - self._closed_since) if s.closed else 0.0
        return s

    def face_lost(self):
        """Reset the closure timer when the face disappears."""
        self.state.closed = False
        self.state.closed_duration = 0.0
        self.state.blink_event = False
        self.state.closure_event = False
        self._closed_since = None

    def _finish_closure(self, duration):
        s = self.state
        s.last_closure_duration = duration
        if duration < config.BLINK_MIN_SEC:
            return                                # noise
        s.closure_event = True
        s.last_closure_min_ear = self._min_ear
        if duration <= config.BLINK_MAX_SEC:
            s.blink_count += 1
            s.blink_event = True
        else:
            s.long_closure_count += 1
