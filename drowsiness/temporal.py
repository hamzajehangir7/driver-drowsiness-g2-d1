"""SG-4: Temporal analysis.

Turns the per-frame outputs of SG-2 / SG-3 into evidence measured over time:
PERCLOS, blink duration vs. a personal baseline, microsleeps, yawns and nods.
Every window is in seconds of real time, so it works at any frame rate.
"""
from collections import deque
from dataclasses import dataclass

import numpy as np

from . import config


@dataclass
class TemporalState:
    elapsed: float = 0.0              # seconds since temporal analysis started
    warmed_up: bool = False           # enough data for a PERCLOS verdict
    perclos: float = 0.0              # fraction 0..1 of the last 60 s with eyes >= 80% closed
    p80_closed: bool = False          # eyes >= 80% closed in this frame
    closed_ear: float = 0.0           # estimated fully-closed EAR (from blinks)
    blink_baseline: float = None      # personal mean blink duration (s), None until learned
    baseline_progress: float = 0.0    # 0..1 while the baseline is being learned
    mean_blink_duration: float = 0.0  # mean blink duration in the last 60 s
    blinks_in_window: int = 0
    slow_blinks: bool = False
    microsleep_active: bool = False   # eyes closed >= 1 s right now
    microsleeps_60s: int = 0
    total_microsleeps: int = 0
    yawns_180s: int = 0
    nods_60s: int = 0
    total_nods: int = 0
    driver_visible: bool = True


class TemporalAnalyzer:
    def __init__(self, open_ear):
        self.open_ear = open_ear
        self.state = TemporalState()
        self._start = None
        self._last_t = None
        self._last_face_t = None
        self._frames = deque()        # (t, dt, p80_closed) for frames with a face
        self._blinks = deque()        # (t, duration)
        self._baseline_durations = []
        self._closed_minima = deque(maxlen=15)
        self._microsleeps = deque()   # t
        self._yawns = deque()         # t
        self._nods = deque()          # t
        self._microsleep_counted = False
        self._nod_counted = False

    def update(self, t, face_found, eye, mh):
        s = self.state
        if self._start is None:
            self._start = t
            self._last_face_t = t
        dt = 0.0 if self._last_t is None else min(t - self._last_t, 0.2)
        self._last_t = t
        s.elapsed = t - self._start

        if face_found:
            self._last_face_t = t
            self._update_eyes(t, dt, eye)
            self._update_head_mouth(t, mh)
        else:
            s.microsleep_active = False
            self._microsleep_counted = False
            self._nod_counted = False
        s.driver_visible = (t - self._last_face_t) < config.FACE_LOST_SEC

        self._trim(t)
        self._compute(t)
        return s

    # ---------------- per-frame bookkeeping ----------------
    def _update_eyes(self, t, dt, eye):
        s = self.state
        # Closed-eye EAR, learned from the lowest EAR reached in real blinks.
        if eye.closure_event:
            self._closed_minima.append(eye.last_closure_min_ear)
        if len(self._closed_minima) >= 3:
            closed = float(np.median(self._closed_minima))
        else:
            closed = self.open_ear * 0.3     # starting guess until 3 blinks are seen
        s.closed_ear = min(closed, eye.closed_threshold)

        # P80: eye opening <= 20% of the range between closed and open EAR.
        span = max(self.open_ear - s.closed_ear, 1e-6)
        openness = (eye.ear - s.closed_ear) / span
        s.p80_closed = openness <= config.PERCLOS_CLOSED_OPENNESS
        self._frames.append((t, dt, s.p80_closed))

        # Blink durations (closures shorter than a microsleep).
        if eye.closure_event and eye.last_closure_duration < config.MICROSLEEP_SEC:
            self._blinks.append((t, eye.last_closure_duration))
            if s.blink_baseline is None:
                self._baseline_durations.append(eye.last_closure_duration)

        # Microsleep: one count per closure that reaches 1 s.
        s.microsleep_active = eye.closed and eye.closed_duration >= config.MICROSLEEP_SEC
        if s.microsleep_active and not self._microsleep_counted:
            self._microsleeps.append(t)
            s.total_microsleeps += 1
            self._microsleep_counted = True
        if not eye.closed:
            self._microsleep_counted = False

    def _update_head_mouth(self, t, mh):
        s = self.state
        if mh.yawn_event:
            self._yawns.append(t)
        if mh.head_down and mh.head_down_duration >= config.NOD_MIN_SEC and not self._nod_counted:
            self._nods.append(t)
            s.total_nods += 1
            self._nod_counted = True
        if not mh.head_down:
            self._nod_counted = False

    def _trim(self, t):
        for q, window in ((self._frames, config.PERCLOS_WINDOW_SEC),
                          (self._blinks, config.PERCLOS_WINDOW_SEC),
                          (self._microsleeps, config.PERCLOS_WINDOW_SEC),
                          (self._nods, config.NOD_WINDOW_SEC),
                          (self._yawns, config.YAWN_WINDOW_SEC)):
            while q and t - (q[0][0] if isinstance(q[0], tuple) else q[0]) > window:
                q.popleft()

    # ---------------- features ----------------
    def _compute(self, t):
        s = self.state

        # PERCLOS, weighted by time so uneven frame rates don't bias it.
        total = sum(dt for _, dt, _ in self._frames)
        closed = sum(dt for _, dt, c in self._frames if c)
        s.perclos = closed / total if total > 0 else 0.0
        s.warmed_up = s.elapsed >= config.PERCLOS_WARMUP_SEC

        # Personal blink-duration baseline (driver assumed alert at the start).
        if s.blink_baseline is None:
            n = len(self._baseline_durations)
            s.baseline_progress = min(s.elapsed / config.BLINK_BASELINE_SEC,
                                      n / config.BLINK_BASELINE_MIN_BLINKS)
            if s.elapsed >= config.BLINK_BASELINE_SEC and n >= config.BLINK_BASELINE_MIN_BLINKS:
                s.blink_baseline = float(np.median(self._baseline_durations))
                s.baseline_progress = 1.0

        durations = [d for _, d in self._blinks]
        s.blinks_in_window = len(durations)
        s.mean_blink_duration = float(np.mean(durations)) if durations else 0.0
        s.slow_blinks = (s.blink_baseline is not None
                         and s.blinks_in_window >= config.SLOW_BLINK_MIN_BLINKS
                         and s.mean_blink_duration >= config.SLOW_BLINK_FACTOR * s.blink_baseline)

        s.microsleeps_60s = len(self._microsleeps)
        s.yawns_180s = len(self._yawns)
        s.nods_60s = len(self._nods)
