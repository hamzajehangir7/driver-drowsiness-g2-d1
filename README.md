# Driver Drowsiness Monitoring â€” G2-D1 (CS-477 Computer Vision, SEECS CV Face-Off 2026)

Real-time driver drowsiness monitor. A webcam (or video file) is analysed frame by frame for eye closure, blinks, yawns
and head nods. These cues are turned into temporal evidence (PERCLOS, slow blinks, microsleeps) and a three-level
decision (**ALERT â†’ WARNING â†’ DROWSY**) with an audible alarm. Target hardware: laptop now, NVIDIA Jetson Orin Nano 8GB later.

```
Camera â†’ SG-1 Face/Landmarks â†’ SG-2 Eye/Blink â”€â”
                             â†’ SG-3 Yawn/Head â”€â”´â†’ SG-4 Temporal analysis â†’ SG-5 Decision â†’ Alert
```

## Repository structure

| Path | Owner | Contents |
|---|---|---|
| `drowsiness/sg1_face_landmarks/` | SG-1 Face/Landmarks | MediaPipe Face Mesh detector (`landmarks.py`) |
| `drowsiness/sg2_eye_blink/` | SG-2 Eye/Blink | EAR, eye state, blink detection (`eye.py`) |
| `drowsiness/sg3_yawn_head/` | SG-3 Yawn/Facial cues | MAR, yawn detection, head pose (`mouth_head.py`) |
| `drowsiness/sg4_temporal/` | **SG-4 Temporal analysis** | PERCLOS, blink baseline, microsleeps (`temporal.py`), mock cue streams, Week 5 experiment + results |
| `drowsiness/sg5_decision/` | SG-5 Drowsiness decision | Evidence scoring and levels (`decision.py`), alarm (`alert.py`) |
| `drowsiness/sg6_integration/` | SG-6 Embedded/Integration | Pipeline entry point (`main.py`), camera input, display, integration log |
| `drowsiness/config.py`, `drowsiness/calibration.py` | shared | all tunable parameters; start-up calibration |
| `docs/` | shared | V1 interfaces, setup, contribution workflow, meeting notes, status reports |
| `data/` | shared | recorded test session (features only, no images) |
| `models/` | shared | MediaPipe `face_landmarker.task` (auto-downloaded if missing) |
| `tools/` | shared | camera diagnostics |

Each sub-group folder has its own `README.md` with purpose, I/O, run commands, test data and limitations.

## Setup

Python 3.10â€“3.13.

```powershell
git clone https://github.com/hamzajehangir7/driver-drowsiness-g2-d1.git
cd driver-drowsiness-g2-d1
python -m venv .venv
.\.venv\Scripts\activate          # Linux/Jetson: source .venv/bin/activate
pip install -r requirements.txt
```

Tested on Windows 11, Python 3.13, opencv-python 5.0.0, mediapipe 0.10/1.1.0, numpy 2.5.

## Run

```powershell
python run.py                          # webcam (first real camera)
python run.py --quick                  # shorter warm-up/baseline for quick tests
python run.py --source video.mp4       # a video file
python run.py --log data/session.csv   # also save per-frame features and decisions
python run.py --list-cameras           # list camera indexes
```

Keys: `q`/Esc quit Â· `c` recalibrate Â· `r` reset counters Â· `m` face mesh Â· `s` sound on/off.
Look at the camera normally for the first 3 s (calibration).

### Week 5 experiment (no camera needed)

```powershell
python -m drowsiness.sg4_temporal.experiments.run_week5_experiment
```

Writes `drowsiness/sg4_temporal/results/week5_results.md` and `.json`.

## Interfaces

The frozen V1 input/output of every module is documented in [`docs/INTERFACES_V1.md`](docs/INTERFACES_V1.md).

## Week 5 status

| Sub-group | Baseline (Week 4) | Week 5 experiment | Status |
|---|---|---|---|
| SG-1 Face/Landmarks | âœ… working in pipeline | â³ detector-configuration comparison not done yet | see board |
| SG-2 Eye/Blink | âœ… working in pipeline | â³ threshold comparison not done yet | see board |
| SG-3 Yawn/Head | âœ… working in pipeline | â³ yawn-threshold comparison not done yet | see board |
| **SG-4 Temporal** | âœ… working in pipeline | âœ… 4 temporal configurations compared, Week 6 config selected | [results](drowsiness/sg4_temporal/README.md) |
| SG-5 Decision | âœ… working in pipeline | â³ decision-rule comparison not done yet | see board |
| SG-6 Integration | âœ… runs on laptop | â³ Jetson run not done yet | see board |

Task tracking: GitHub Project board **"G2-D1 Driver Drowsiness â€” Week Planning"** (linked from the repository's *Projects* tab).

## Team G2-D1

| Sub-group | Members |
|---|---|
| SG-1 Face/Landmarks | Muhammad Hassan, Abdul Wahid |
| SG-2 Eye/Blink | Anss Ahmad, Abdul Sammi Khan |
| SG-3 Yawn/Facial cues | Shaheer Asghar, Tayyaba Naveed |
| SG-4 Temporal analysis | Rija Shah, Muhammad Hamza Jehangir |
| SG-5 Drowsiness decision | Eman Rana, Fahad Naseer, Syed Muhammad Dawar Raza Zaidi |

## Known limitations

- Thresholds are partly literature-based and partly design choices (sources are noted next to each value in `drowsiness/config.py`); none are yet validated on a labelled drowsiness dataset.
- Face is lost when the driver turns far away or the lighting is poor (55 % face-found rate in the recorded session).
- Single face only; spectacles/sunglasses not yet evaluated.
- Not yet run on Jetson; alarm is laptop beeps only (GPIO buzzer planned).
