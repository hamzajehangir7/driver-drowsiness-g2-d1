"""Measures the person's normal open-eye EAR and head angle at start-up."""
import numpy as np

from . import config


class Calibrator:
    def __init__(self, seconds=config.CALIBRATION_SECONDS):
        self.seconds = seconds
        self.reset()

    def reset(self):
        self.done = False
        self._start = None
        self._ears, self._pitches = [], []
        self.baseline_ear = None
        self.baseline_pitch = None

    def progress(self, t):
        if self.done:
            return 1.0
        if self._start is None:
            return 0.0
        return min((t - self._start) / self.seconds, 1.0)

    def add(self, t, ear, pitch):
        """Feed one frame (only while the face is visible). Returns True when finished."""
        if self.done:
            return True
        if self._start is None:
            self._start = t
        self._ears.append(ear)
        self._pitches.append(pitch)
        if t - self._start >= self.seconds and len(self._ears) >= 10:
            # Median ignores the odd blink during calibration.
            self.baseline_ear = float(np.median(self._ears))
            self.baseline_pitch = float(np.median(self._pitches))
            self.done = True
        return self.done
