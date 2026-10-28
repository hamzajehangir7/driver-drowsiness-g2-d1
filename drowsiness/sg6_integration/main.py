"""Driver Drowsiness Monitoring - full pipeline (SG-1 to SG-5).

Run from the project folder:
    python run.py                          # webcam
    python run.py --quick                  # shorter warm-up/baseline, for quick testing
    python run.py --source video.mp4       # a video file
    python run.py --log data/session1.csv  # also save per-frame features and decisions
"""
import argparse
import csv
import os
import time

import cv2

from .. import config
from ..calibration import Calibrator
from ..sg1_face_landmarks.landmarks import FaceLandmarkDetector
from ..sg2_eye_blink.eye import EyeAnalyzer
from ..sg3_yawn_head.mouth_head import MouthHeadAnalyzer
from ..sg4_temporal.temporal import TemporalAnalyzer
from ..sg5_decision.alert import Alarm
from ..sg5_decision.decision import DecisionEngine
from .capture import Camera, list_cameras
from .display import Display

WINDOW = "Driver Drowsiness Monitoring - G2-D1"

CSV_COLUMNS = [
    "t", "face_found",
    "ear_left", "ear_right", "ear", "eye_closed_threshold", "eyes_closed", "closed_duration",
    "blink_event", "blink_count", "long_closure_count",
    "mar", "mouth_open", "yawning", "yawn_event", "yawn_count",
    "pitch", "yaw", "roll", "pitch_change", "head_down",
    "perclos", "p80_closed", "blink_baseline", "mean_blink_duration", "slow_blinks",
    "microsleep_active", "microsleeps_60s", "yawns_180s", "nods_60s",
    "score", "raw_level", "level",
]


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(config.CAMERA_SOURCE),
                    help="'auto' (laptop webcam), a camera index (see --list-cameras) or a video file path")
    ap.add_argument("--list-cameras", action="store_true", help="print camera names/indexes and exit")
    ap.add_argument("--log", default=None, help="save per-frame features and decisions to this CSV file")
    ap.add_argument("--no-mirror", action="store_true", help="don't flip the webcam image")
    ap.add_argument("--quick", action="store_true",
                    help="testing mode: 20 s PERCLOS warm-up and 30 s blink baseline instead of 60 s / 120 s")
    ap.add_argument("--mute", action="store_true", help="start with the alarm sound off")
    return ap.parse_args()


def main():
    args = parse_args()
    if args.list_cameras:
        for i, name in enumerate(list_cameras()):
            print(f"{i}: {name}")
        return
    if args.quick:
        config.PERCLOS_WARMUP_SEC = 20.0
        config.BLINK_BASELINE_SEC = 30.0
        print("Quick test mode: 20 s warm-up, 30 s blink baseline")

    cam = Camera(args.source, mirror=config.MIRROR and not args.no_mirror)
    detector = FaceLandmarkDetector()
    eyes = EyeAnalyzer()
    mouth_head = MouthHeadAnalyzer()
    calib = Calibrator()
    display = Display()
    alarm = Alarm()
    alarm.muted = args.mute
    temporal, decision = None, None
    print(f"Landmark backend: {detector.backend}")

    log_file, writer = None, None
    if args.log:
        os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
        log_file = open(args.log, "w", newline="")
        writer = csv.writer(log_file)
        writer.writerow(CSV_COLUMNS)
        print(f"Logging to {args.log}")

    fps, last = 0.0, time.time()
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    try:
        while True:
            t, frame = cam.read()
            if frame is None:
                break
            h, w = frame.shape[:2]

            # ---- SG-1: face + landmarks ----
            face = detector.process(frame, t)

            if face.found:
                # ---- SG-2: eyes / blinks ----
                eye = eyes.update(face.landmarks, t)
                # ---- SG-3: mouth / yawn / head ----
                mh = mouth_head.update(face.landmarks, t, w, h)

                if not calib.done and calib.add(t, eye.ear, mh.pitch):
                    eyes.set_baseline(calib.baseline_ear)
                    mouth_head.set_baseline(calib.baseline_pitch)
                    temporal = TemporalAnalyzer(calib.baseline_ear)
                    decision = DecisionEngine()
                    print(f"Calibrated: open-eye EAR = {calib.baseline_ear:.3f}, "
                          f"closed threshold = {eyes.state.closed_threshold:.3f}, "
                          f"baseline pitch = {calib.baseline_pitch:.1f} deg")
            else:
                eyes.face_lost()
                mouth_head.face_lost()
            eye, mh = eyes.state, mouth_head.state

            # ---- SG-4: temporal analysis, SG-5: decision + alarm ----
            ts = ds = None
            if temporal is not None:
                ts = temporal.update(t, face.found, eye, mh)
                ds = decision.update(t, ts)
                alarm.update(ds)
                if ds.level_raised:
                    print(f"[{t:7.1f} s] level -> {ds.name}  ({', '.join(ds.reasons) or 'no reason'})")

            if writer and calib.done:
                writer.writerow(_row(t, face.found, eye, mh, ts, ds))

            now = time.time()
            fps = 0.9 * fps + 0.1 * (1.0 / max(now - last, 1e-6)) if fps else 1.0 / max(now - last, 1e-6)
            last = now

            hold = decision.hold_remaining(t) if decision else None
            out = display.render(frame, t, fps, face, eye, mh, calib, eye.closed_threshold,
                                 ts, ds, hold, alarm.muted)
            cv2.imshow(WINDOW, out)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):          # q or Esc
                break
            if key == ord("c"):                # recalibrate (restarts SG-4 too)
                calib.reset()
                temporal, decision = None, None
            if key == ord("r"):                # reset counters and SG-4 history
                eyes = EyeAnalyzer()
                mouth_head = MouthHeadAnalyzer()
                if calib.done:
                    eyes.set_baseline(calib.baseline_ear)
                    mouth_head.set_baseline(calib.baseline_pitch)
                    temporal = TemporalAnalyzer(calib.baseline_ear)
                    decision = DecisionEngine()
            if key == ord("m"):                # toggle full face mesh
                display.show_mesh = not display.show_mesh
            if key == ord("s"):                # sound on/off
                alarm.muted = not alarm.muted
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break                          # window closed with the X button
    finally:
        cam.release()
        detector.close()
        cv2.destroyAllWindows()
        if log_file:
            log_file.close()

    print(f"Blinks: {eyes.state.blink_count}, long closures: {eyes.state.long_closure_count}, "
          f"yawns: {mouth_head.state.yawn_count}")
    if temporal is not None:
        s = temporal.state
        base = f"{s.blink_baseline * 1000:.0f} ms" if s.blink_baseline else "not learned"
        print(f"SG-4: last PERCLOS {s.perclos * 100:.1f}%, blink baseline {base}, "
              f"microsleeps {s.total_microsleeps}, nods {s.total_nods}; final level {decision.state.name}")


def _row(t, found, eye, mh, ts, ds):
    row = [f"{t:.3f}", int(found)]
    if found:
        row += [
            f"{eye.ear_left:.4f}", f"{eye.ear_right:.4f}", f"{eye.ear:.4f}", f"{eye.closed_threshold:.4f}",
            int(eye.closed), f"{eye.closed_duration:.3f}",
            int(eye.blink_event), eye.blink_count, eye.long_closure_count,
            f"{mh.mar:.4f}", int(mh.mouth_open), int(mh.yawning), int(mh.yawn_event), mh.yawn_count,
            f"{mh.pitch:.2f}", f"{mh.yaw:.2f}", f"{mh.roll:.2f}", f"{mh.pitch_change:.2f}", int(mh.head_down),
        ]
    else:
        row += [""] * 19
    if ts is not None:
        row += [
            f"{ts.perclos:.4f}", int(ts.p80_closed),
            f"{ts.blink_baseline:.3f}" if ts.blink_baseline else "", f"{ts.mean_blink_duration:.3f}",
            int(ts.slow_blinks), int(ts.microsleep_active), ts.microsleeps_60s, ts.yawns_180s, ts.nods_60s,
            ds.score, ds.raw_level, ds.level,
        ]
    else:
        row += [""] * 12
    return row


if __name__ == "__main__":
    main()
