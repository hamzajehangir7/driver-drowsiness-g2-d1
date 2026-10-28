# SG-1 — Driver Face & Landmark Detection

**Members:** Muhammad Hassan, Abdul Wahid

## Purpose
Find the driver's face in each frame and return MediaPipe Face Mesh landmarks for SG-2 (eyes) and SG-3 (mouth/head).

## I/O (V1)
- **Input:** BGR frame + timestamp `t` (s) from `sg6_integration/capture.py`.
- **Output:** `FaceResult(found, landmarks (N,2) px, bbox)` — see `docs/INTERFACES_V1.md`.

## Run
`python run.py` (press `m` to show the full mesh). Settings: `MIN_DETECTION_CONFIDENCE`, `MIN_TRACKING_CONFIDENCE`, `FRAME_WIDTH/HEIGHT` in `drowsiness/config.py`.
The model `models/face_landmarker.task` is downloaded automatically if it is missing. Supports both `mp.solutions` and `mp.tasks`.

## Status
- ✅ Week 4 baseline is working in the pipeline (single face, 640×480).
- ⏳ **Week 5 left:** compare ≥ 2 configurations (confidence 0.3/0.5/0.7, 320 vs 640 input) for face-found rate, landmark jitter and FPS on driver-like clips (pose, low light, spectacles). Record the results in `results/` and recommend a Week 6 configuration.

## Limitations
Face found in only 55 % of frames of the recorded session (turning away, lighting). Single face only.
