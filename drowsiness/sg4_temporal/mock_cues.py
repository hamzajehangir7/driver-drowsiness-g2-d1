"""Standardized / mock cue streams for SG-4 (no camera, no SG-1..SG-3 needed).

A cue stream is a list of frames:
    {"t": seconds, "face": bool, "ear": float, "closed": bool,
     "closed_threshold": float, "yawn_event": bool, "head_down": bool}

CueStateBuilder turns those frames into the same EyeState / MouthHeadState
fields that SG-2 / SG-3 hand to TemporalAnalyzer.update() in the live pipeline.
"""
import csv
import random
from dataclasses import dataclass

from .. import config


@dataclass
class MockEye:
    ear: float = 0.0
    closed: bool = False
    closed_duration: float = 0.0
    closed_threshold: float = config.EAR_DEFAULT_CLOSED
    closure_event: bool = False
    last_closure_duration: float = 0.0
    last_closure_min_ear: float = 0.0


@dataclass
class MockMouthHead:
    yawn_event: bool = False
    head_down: bool = False
    head_down_duration: float = 0.0


class CueStateBuilder:
    """Rebuilds SG-2/SG-3 per-frame state (closure events, durations) from frame cues."""

    def __init__(self):
        self.eye = MockEye()
        self.mh = MockMouthHead()
        self._closed_since = None
        self._min_ear = 0.0
        self._down_since = None

    def update(self, f):
        e, m = self.eye, self.mh
        e.closure_event = False
        m.yawn_event = False
        if not f["face"]:
            e.closed, e.closed_duration = False, 0.0
            m.head_down, m.head_down_duration = False, 0.0
            self._closed_since = self._down_since = None
            return e, m

        t = f["t"]
        e.ear, e.closed_threshold = f["ear"], f["closed_threshold"]
        if f["closed"] and not e.closed:
            self._closed_since, self._min_ear = t, f["ear"]
        elif f["closed"]:
            self._min_ear = min(self._min_ear, f["ear"])
        elif e.closed and self._closed_since is not None:
            duration = t - self._closed_since
            if duration >= config.BLINK_MIN_SEC:
                e.closure_event = True
                e.last_closure_duration = duration
                e.last_closure_min_ear = self._min_ear
            self._closed_since = None
        e.closed = f["closed"]
        e.closed_duration = (t - self._closed_since) if e.closed and self._closed_since is not None else 0.0

        m.yawn_event = f["yawn_event"]
        if f["head_down"]:
            if self._down_since is None:
                self._down_since = t
            m.head_down, m.head_down_duration = True, t - self._down_since
        else:
            self._down_since = None
            m.head_down, m.head_down_duration = False, 0.0
        return e, m


def load_csv_stream(path):
    """Cue stream from a CSV written by `python run.py --log ...`."""
    frames = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            face = r["face_found"] == "1"
            frames.append({
                "t": float(r["t"]), "face": face,
                "ear": float(r["ear"]) if face else 0.0,
                "closed": face and r["eyes_closed"] == "1",
                "closed_threshold": float(r["eye_closed_threshold"]) if face else config.EAR_DEFAULT_CLOSED,
                "yawn_event": face and r["yawn_event"] == "1",
                "head_down": face and r["head_down"] == "1",
            })
    return frames


def synthetic_stream(seed=0, fps=30.0, alert_sec=240.0, drowsy_sec=240.0):
    """Scripted session with known ground truth.

    0 .. alert_sec           ALERT: blinks every 2.5-5.5 s lasting ~0.15 s, plus three
                             0.55 s 'long but normal' blinks (false-alarm bait).
    alert_sec .. end         DROWSY: blinks every 2-4 s lasting ~0.35 s, 0.6-0.9 s long
                             closures every ~15 s, 4 microsleeps (1.2-2.0 s),
                             3 yawns and 2 head nods (1.3 s).
    Returns (frames, truth) where truth lists the scripted events.
    """
    rng = random.Random(seed)
    end = alert_sec + drowsy_sec
    open_ear, closed_ear = 0.30, 0.08
    threshold = open_ear * config.EAR_CLOSED_RATIO

    closures = []                                   # (start, duration)
    t = 2.0
    while t < alert_sec:
        closures.append((t, max(0.08, rng.gauss(0.15, 0.03))))
        t += rng.uniform(2.5, 5.5)
    for s in (70.0, 150.0, 210.0):
        closures.append((s, 0.55))
    t = alert_sec + 1.0
    while t < end:
        closures.append((t, max(0.15, rng.gauss(0.35, 0.08))))
        t += rng.uniform(2.0, 4.0)
    t = alert_sec + 8.0
    while t < end:
        closures.append((t, rng.uniform(0.6, 0.9)))
        t += 15.0
    microsleeps = [alert_sec + d for d in (60.0, 120.0, 180.0, 210.0)]
    for s in microsleeps:
        closures.append((s, rng.uniform(1.2, 2.0)))
    yawns = [alert_sec + d for d in (20.0, 90.0, 160.0)]
    nods = [alert_sec + d for d in (110.0, 200.0)]

    frames, n = [], int(end * fps)
    for i in range(n):
        ti = i / fps
        closed = any(s <= ti < s + d for s, d in closures)
        ear = (closed_ear if closed else open_ear) + rng.gauss(0, 0.008)
        frames.append({
            "t": ti, "face": True, "ear": ear, "closed": ear < threshold,
            "closed_threshold": threshold,
            "yawn_event": any(abs(ti - y) < 0.5 / fps for y in yawns),
            "head_down": any(s <= ti < s + 1.3 for s in nods),
        })
    truth = {"drowsy_onset": alert_sec, "microsleeps": microsleeps, "yawns": yawns,
             "nods": nods, "open_ear": open_ear}
    return frames, truth
