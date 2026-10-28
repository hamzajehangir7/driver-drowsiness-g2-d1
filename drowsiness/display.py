"""Drawing: landmarks on the face, a status panel and a live EAR/MAR graph."""
from collections import deque

import cv2
import numpy as np

from . import config
from .eye import LEFT_EYE, RIGHT_EYE

GREEN = (80, 200, 80)
RED = (60, 60, 230)
ORANGE = (0, 165, 255)
YELLOW = (0, 220, 220)
WHITE = (240, 240, 240)
GREY = (150, 150, 150)
CYAN = (230, 200, 60)
BG = (30, 30, 30)

PANEL_W = 300
GRAPH_H = 150

# BGR colours for ALERT / WARNING / DROWSY (always shown with the level's name)
LEVEL_COLORS = {0: (92, 125, 47), 1: (59, 162, 233), 2: (51, 59, 184)}
LEVEL_TEXT = {0: "ALERT", 1: "WARNING - take a break", 2: "DROWSY - WAKE UP!"}

# Outlines for drawing (MediaPipe Face Mesh indices)
LEFT_EYE_OUTLINE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_EYE_OUTLINE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
INNER_LIPS = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]


class Display:
    def __init__(self):
        self.history = deque()   # (t, ear, mar) for the graph
        self.show_mesh = False

    def render(self, frame, t, fps, face, eye, mh, calib, eye_threshold,
               temporal=None, decision=None, hold=None, muted=False):
        h, w = frame.shape[:2]
        view = frame.copy()

        if face.found:
            self._draw_face(view, face, eye, mh)
            self.history.append((t, eye.ear, mh.mar))
        while self.history and t - self.history[0][0] > config.GRAPH_SECONDS:
            self.history.popleft()

        if not calib.done:
            self._draw_calibration(view, calib.progress(t), face.found)
        elif temporal is not None and decision is not None:
            self._draw_banner(view, t, temporal, decision)

        panel = self._panel(h, fps, face, eye, mh, calib)
        panel2 = self._panel2(h, temporal, decision, hold, muted)
        top = np.hstack([view, panel, panel2])
        graph = self._graph(top.shape[1], t, eye_threshold)
        return np.vstack([top, graph])

    # ---------------- level banner ----------------
    def _draw_banner(self, img, t, ts, d):
        h, w = img.shape[:2]
        if not ts.driver_visible:
            color, text = (90, 90, 90), "DRIVER NOT VISIBLE"
        else:
            color, text = LEVEL_COLORS[d.level], LEVEL_TEXT[d.level]
        cv2.rectangle(img, (0, 0), (w, 46), color, -1)
        txt_col = (20, 20, 20) if d.level == 1 and ts.driver_visible else WHITE
        cv2.putText(img, text, (14, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.85, txt_col, 2)
        if d.level == 2 and ts.driver_visible and int(t * 3) % 2 == 0:
            cv2.rectangle(img, (0, 0), (w - 1, h - 1), LEVEL_COLORS[2], 12)   # flashing border

    # ---------------- face overlay ----------------
    def _draw_face(self, img, face, eye, mh):
        lm = face.landmarks.astype(np.int32)
        x1, y1, x2, y2 = face.bbox
        cv2.rectangle(img, (x1, y1), (x2, y2), GREEN, 2)
        cv2.putText(img, "FACE", (x1, max(y1 - 8, 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 1)

        if self.show_mesh:
            for p in lm:
                cv2.circle(img, tuple(p), 1, GREY, -1)

        eye_col = RED if eye.closed else GREEN
        for outline in (LEFT_EYE_OUTLINE, RIGHT_EYE_OUTLINE):
            cv2.polylines(img, [lm[outline]], True, eye_col, 1, cv2.LINE_AA)
        for idx in LEFT_EYE + RIGHT_EYE:          # the 6 EAR points per eye
            cv2.circle(img, tuple(lm[idx]), 2, YELLOW, -1)

        mouth_col = RED if mh.yawning else (ORANGE if mh.mouth_open else GREEN)
        cv2.polylines(img, [lm[INNER_LIPS]], True, mouth_col, 1, cv2.LINE_AA)

        # Arrow from the nose showing where the head points
        nose = lm[1]
        dx = int(np.clip(mh.yaw, -60, 60) * 2)
        dy = int(np.clip(mh.pitch_change, -60, 60) * 2)
        cv2.arrowedLine(img, tuple(nose), (int(nose[0] + dx), int(nose[1] + dy)),
                        RED if mh.head_down else CYAN, 2, tipLength=0.3)

    def _draw_calibration(self, img, progress, face_found):
        h, w = img.shape[:2]
        overlay = img.copy()
        cv2.rectangle(overlay, (0, h - 70), (w, h), BG, -1)
        cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)
        msg = ("CALIBRATING: look at the camera, eyes open, mouth closed"
               if face_found else "CALIBRATING: no face found - face the camera")
        cv2.putText(img, msg, (10, h - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, YELLOW, 1)
        cv2.rectangle(img, (10, h - 30), (w - 10, h - 15), GREY, 1)
        cv2.rectangle(img, (10, h - 30), (10 + int((w - 20) * progress), h - 15), YELLOW, -1)

    # ---------------- status panel ----------------
    def _panel(self, h, fps, face, eye, mh, calib):
        p = np.full((h, PANEL_W, 3), BG, dtype=np.uint8)
        y = [28]

        def line(label, value="", color=WHITE, big=False):
            scale = 0.65 if big else 0.5
            cv2.putText(p, label, (12, y[0]), cv2.FONT_HERSHEY_SIMPLEX, scale, GREY if value else color, 1)
            if value:
                cv2.putText(p, value, (140, y[0]), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2 if big else 1)
            y[0] += 28 if big else 20

        def header(text):
            y[0] += 6
            cv2.putText(p, text, (12, y[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, CYAN, 1)
            cv2.line(p, (12, y[0] + 5), (PANEL_W - 12, y[0] + 5), (70, 70, 70), 1)
            y[0] += 24

        line("FPS", f"{fps:4.1f}", WHITE)
        line("Calibration", "done" if calib.done else "in progress", GREEN if calib.done else YELLOW)

        header("SG-1  FACE")
        line("Face", "DETECTED" if face.found else "NOT FOUND", GREEN if face.found else RED, big=True)

        header("SG-2  EYES")
        if face.found:
            line("Eyes", "CLOSED" if eye.closed else "OPEN", RED if eye.closed else GREEN, big=True)
            line("EAR (L / R)", f"{eye.ear_left:.2f} / {eye.ear_right:.2f}")
            line("EAR avg / thr", f"{eye.ear:.2f} / {eye.closed_threshold:.2f}")
            line("Closed for", f"{eye.closed_duration:.2f} s", RED if eye.closed_duration > config.BLINK_MAX_SEC else WHITE)
        else:
            line("Eyes", "--", GREY, big=True)
        line("Blinks", str(eye.blink_count), YELLOW if eye.blink_event else WHITE)
        line("Long closures", str(eye.long_closure_count), ORANGE if eye.long_closure_count else WHITE)
        line("Last closure", f"{eye.last_closure_duration:.2f} s")

        header("SG-3  MOUTH / HEAD")
        if face.found:
            if mh.yawning:
                mouth, col = "YAWNING", RED
            elif mh.mouth_open:
                mouth, col = "OPEN", ORANGE
            else:
                mouth, col = "CLOSED", GREEN
            line("Mouth", mouth, col, big=True)
            line("MAR", f"{mh.mar:.2f}")
            line("Head P/Y/R", " ".join(f"{round(a):+d}" for a in (mh.pitch_change, mh.yaw, mh.roll)))
            line("Head", "DOWN" if mh.head_down else "OK", RED if mh.head_down else GREEN)
        else:
            line("Mouth", "--", GREY, big=True)
        line("Yawns", str(mh.yawn_count), YELLOW if mh.yawn_event else WHITE)

        cv2.putText(p, "q quit | c recalibrate | r reset | m mesh", (12, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, GREY, 1)
        return p

    # ---------------- SG-4 / SG-5 panel ----------------
    def _panel2(self, h, ts, d, hold, muted):
        p = np.full((h, PANEL_W, 3), (38, 34, 30), dtype=np.uint8)
        y = [28]

        def line(label, value="", color=WHITE, big=False):
            scale = 0.65 if big else 0.5
            cv2.putText(p, label, (12, y[0]), cv2.FONT_HERSHEY_SIMPLEX, scale, GREY if value else color, 1)
            if value:
                cv2.putText(p, value, (150, y[0]), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 2 if big else 1)
            y[0] += 28 if big else 20

        def header(text):
            cv2.putText(p, text, (12, y[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, CYAN, 1)
            cv2.line(p, (12, y[0] + 5), (PANEL_W - 12, y[0] + 5), (70, 70, 70), 1)
            y[0] += 24

        header("SG-4  TEMPORAL")
        if ts is None:
            line("Waiting for calibration", "", GREY)
        else:
            if ts.warmed_up:
                line("Window", f"{config.PERCLOS_WINDOW_SEC:.0f} s", WHITE)
            else:
                line("Warm-up", f"{ts.elapsed:.0f} / {config.PERCLOS_WARMUP_SEC:.0f} s", YELLOW)
            perc_col = RED if ts.warmed_up and ts.perclos >= config.PERCLOS_THRESHOLD else WHITE
            line("PERCLOS", f"{ts.perclos * 100:.1f} %", perc_col, big=True)
            line("Eye >=80% shut", "YES" if ts.p80_closed else "no", ORANGE if ts.p80_closed else WHITE)
            if ts.blink_baseline is None:
                line("Blink baseline", f"learning {ts.baseline_progress * 100:.0f}%", YELLOW)
            else:
                line("Blink baseline", f"{ts.blink_baseline * 1000:.0f} ms")
            line("Mean blink (60s)", f"{ts.mean_blink_duration * 1000:.0f} ms  n={ts.blinks_in_window}")
            line("Slow blinks", "YES" if ts.slow_blinks else "no", RED if ts.slow_blinks else WHITE)
            line("Microsleeps 60s", f"{ts.microsleeps_60s}  (total {ts.total_microsleeps})",
                 RED if ts.microsleep_active or ts.microsleeps_60s else WHITE)
            line("Yawns (3 min)", str(ts.yawns_180s), ORANGE if ts.yawns_180s >= config.YAWN_COUNT_THRESHOLD else WHITE)
            line("Nods (60 s)", str(ts.nods_60s), ORANGE if ts.nods_60s else WHITE)

        y[0] += 6
        header("SG-5  DECISION")
        if d is not None:
            line("Score", f"{d.score} points", WHITE)
            cv2.rectangle(p, (12, y[0] - 4), (PANEL_W - 12, y[0] + 44), LEVEL_COLORS[d.level], -1)
            txt_col = (20, 20, 20) if d.level == 1 else WHITE
            cv2.putText(p, d.name, (24, y[0] + 32), cv2.FONT_HERSHEY_SIMPLEX, 1.0, txt_col, 2)
            y[0] += 66
            if "MICROSLEEP" in d.reasons:
                line("  MICROSLEEP -> DROWSY", "", RED)
            for k, v in d.points.items():
                line(f"  {k}", f"+{v}", ORANGE)
            if hold is not None:
                line("Lowering in", f"{hold:.0f} s", GREY)
        else:
            line("--", "", GREY)

        cv2.putText(p, f"s sound: {'OFF' if muted else 'on'}", (12, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, GREY, 1)
        return p

    # ---------------- live graph ----------------
    def _graph(self, width, t, eye_threshold):
        g = np.full((GRAPH_H, width, 3), (20, 20, 20), dtype=np.uint8)
        top, bottom, left, right = 20, GRAPH_H - 10, 50, width - 10
        y_max = 1.0  # both EAR and MAR plotted on 0..1

        def to_xy(tt, v):
            x = right - (t - tt) / config.GRAPH_SECONDS * (right - left)
            y = bottom - min(v, y_max) / y_max * (bottom - top)
            return int(x), int(y)

        for v, label in ((0.0, "0"), (0.5, "0.5"), (1.0, "1.0")):
            _, yy = to_xy(t, v)
            cv2.line(g, (left, yy), (right, yy), (50, 50, 50), 1)
            cv2.putText(g, label, (8, yy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.38, GREY, 1)

        for v, col in ((eye_threshold, GREEN), (config.MAR_YAWN, ORANGE)):
            _, yy = to_xy(t, v)
            for x in range(left, right, 12):
                cv2.line(g, (x, yy), (x + 6, yy), col, 1)

        if len(self.history) > 1:
            ear_pts = np.array([to_xy(tt, e) for tt, e, _ in self.history], np.int32)
            mar_pts = np.array([to_xy(tt, m) for tt, _, m in self.history], np.int32)
            cv2.polylines(g, [mar_pts], False, ORANGE, 1, cv2.LINE_AA)
            cv2.polylines(g, [ear_pts], False, GREEN, 2, cv2.LINE_AA)

        cv2.putText(g, f"EAR (green, dashed = closed threshold)   MAR (orange, dashed = yawn level)"
                       f"   last {config.GRAPH_SECONDS:.0f} s",
                    (left, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, WHITE, 1)
        return g
