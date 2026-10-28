"""SG-5: Drowsiness decision - three levels from the SG-4 evidence.

    Microsleep in the last 60 s      -> DROWSY at once
    PERCLOS >= 12%                   -> +2   (strong)
    Slow blinks (>= 1.5 x baseline)  -> +2   (strong)
    2+ yawns in 3 min                -> +1   (supporting)
    Head nod in the last 60 s        -> +1   (supporting)
    0-1 ALERT, 2-3 WARNING, 4+ DROWSY
"""
from dataclasses import dataclass, field

from .. import config

ALERT, WARNING, DROWSY = 0, 1, 2
LEVEL_NAMES = {ALERT: "ALERT", WARNING: "WARNING", DROWSY: "DROWSY"}


@dataclass
class DecisionState:
    score: int = 0
    points: dict = field(default_factory=dict)
    raw_level: int = ALERT       # level from this frame's evidence alone
    level: int = ALERT           # level shown (with the 10 s hold when falling)
    reasons: list = field(default_factory=list)
    level_raised: bool = False   # True on the frame the level goes up

    @property
    def name(self):
        return LEVEL_NAMES[self.level]


class DecisionEngine:
    def __init__(self):
        self.state = DecisionState()
        self._lower_since = None

    def update(self, t, ts):
        s = self.state
        points, reasons = {}, []
        if ts.warmed_up and ts.perclos >= config.PERCLOS_THRESHOLD:
            points["PERCLOS"] = config.POINTS_PERCLOS
            reasons.append(f"PERCLOS {ts.perclos * 100:.0f}%")
        if ts.slow_blinks:
            points["Slow blinks"] = config.POINTS_SLOW_BLINKS
            reasons.append("slow blinks")
        if ts.yawns_180s >= config.YAWN_COUNT_THRESHOLD:
            points["Yawns"] = config.POINTS_YAWNS
            reasons.append(f"{ts.yawns_180s} yawns")
        if ts.nods_60s >= 1:
            points["Nods"] = config.POINTS_NODS
            reasons.append("head nod")
        s.points, s.score = points, sum(points.values())

        if ts.microsleep_active or ts.microsleeps_60s > 0:
            raw = DROWSY
            reasons.insert(0, "MICROSLEEP")
        elif s.score >= config.DROWSY_SCORE:
            raw = DROWSY
        elif s.score >= config.WARNING_SCORE:
            raw = WARNING
        else:
            raw = ALERT
        s.raw_level, s.reasons = raw, reasons

        # Rise at once; fall only after LEVEL_DOWN_HOLD_SEC at the lower level.
        s.level_raised = False
        if raw > s.level:
            s.level = raw
            s.level_raised = True
            self._lower_since = None
        elif raw < s.level:
            if self._lower_since is None:
                self._lower_since = t
            elif t - self._lower_since >= config.LEVEL_DOWN_HOLD_SEC:
                s.level = raw
                self._lower_since = None
        else:
            self._lower_since = None
        return s

    def hold_remaining(self, t):
        """Seconds left before the level may drop (for display), or None."""
        if self._lower_since is None:
            return None
        return max(config.LEVEL_DOWN_HOLD_SEC - (t - self._lower_since), 0.0)
