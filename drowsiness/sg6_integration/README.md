# SG-6 — Embedded Deployment & System Integration

## Purpose
Own the pipeline entry point (`main.py`), camera input (`capture.py`), on-screen display (`display.py`), the shared
environment, and the Jetson Orin Nano deployment. Keep `main` stable and check that subgroup branches merge without breaking `docs/INTERFACES_V1.md`.

## Run
`python run.py [--source auto|<index>|video.mp4] [--log file.csv] [--quick] [--mute]`

## Integration log
| Date | Item | Status |
|---|---|---|
| 2026-10-28 | Moved the flat `drowsiness/*.py` modules into the SG-1…SG-6 folders; imports updated; `run.py` entry point unchanged | ✅ merged |
| 2026-10-28 | MediaPipe ≥ 0.10.x has no `mp.solutions`; `landmarks.py` falls back to the Tasks API + model file | ✅ handled |
| 2026-10-28 | Windows camera picked by name (DirectShow) to avoid the Phone Link virtual camera; on Jetson only `capture.py` needs changing | ⚠️ Jetson not tested |

## Status
- ✅ Pipeline runs on a Windows laptop (Python 3.13, OpenCV 5.0, MediaPipe 1.1).
- ⏳ **Week 5 left:** Jetson Orin Nano setup (JetPack, Python env, MediaPipe availability on aarch64). Run SG-1 on the Jetson and report FPS, latency and memory (CPU vs GPU delegate), and complete `docs/SETUP_JETSON.md`.
