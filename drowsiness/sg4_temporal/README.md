# SG-4 — Temporal Behaviour Analysis

**Members:** Rija Shah, Muhammad Hamza Jehangir

## Purpose
A single frame cannot say a driver is drowsy. SG-4 turns per-frame cues from SG-2 (eye state, blinks) and SG-3 (yawns, head
pose) into evidence measured over time: **PERCLOS** (P80, time-weighted), **personal blink-duration baseline and slow
blinks**, **microsleeps**, **yawns in 3 min** and **head nods in 60 s**. SG-5 makes the drowsiness decision from these.

Hierarchy kept: visual cue (SG-2/3) → temporal evidence (**SG-4**) → decision (SG-5) → alert.

## Files
| File | What |
|---|---|
| `temporal.py` | `TemporalAnalyzer` / `TemporalState` — the module used in the live pipeline |
| `mock_cues.py` | standardized cue streams: replay a logged CSV, or a scripted synthetic session with ground truth; `CueStateBuilder` rebuilds SG-2/SG-3 states so SG-4 runs **without camera or upstream modules** |
| `experiments/run_week5_experiment.py` | Week 5 comparison of temporal configurations |
| `results/week5_results.md`, `.json` | generated results (versioned) |

## Interface (V1, frozen)
- **Input** per frame: `update(t, face_found, eye: EyeState, mh: MouthHeadState)` — fields used: `ear, closed, closed_duration, closed_threshold, closure_event, last_closure_duration, last_closure_min_ear` and `yawn_event, head_down, head_down_duration`.
- **Output** to SG-5: `TemporalState` — full schema in [`docs/INTERFACES_V1.md`](../../docs/INTERFACES_V1.md#sg-4--sg-5--temporalstate-sg4_temporaltemporalpy).
- Parameters live in `drowsiness/config.py` (section *SG-4 Temporal analysis*); all windows are in seconds so the module is frame-rate independent (laptop vs Jetson).

## Run
```powershell
python run.py --quick                                              # live pipeline
python -m drowsiness.sg4_temporal.experiments.run_week5_experiment # Week 5 experiment, no camera
```

## Test data
1. **Synthetic cue stream** (`mock_cues.synthetic_stream(seed=0)`): 480 s at 30 fps. 0–240 s alert (blinks ~0.15 s every 2.5–5.5 s, plus three 0.55 s long-but-normal blinks as false-alarm bait); 240–480 s drowsy (blinks ~0.35 s, 0.6–0.9 s long closures every 15 s, **4 microsleeps** of 1.2–2.0 s, 3 yawns, 2 nods). Ground truth is known, so delay and false alarms can be measured.
2. **Recorded session** `data/test_session.csv`: 505 s real webcam log (features only, no images), no drowsiness labels — used for stability/behaviour comparison only.

Both streams are fed through identical SG-4 + SG-5 code under each configuration (same test data, fair comparison).

## Week 5 experiment — temporal window / persistence study
| Config | PERCLOS window / warm-up | Microsleep | Slow-blink factor | Blink baseline |
|---|---|---|---|---|
| C0 baseline (Week 4) | 60 s / 60 s | ≥ 1.0 s | 1.5× | 120 s |
| C1 short window | 30 s / 30 s | ≥ 1.0 s | 1.5× | 60 s |
| C2 sensitive | 30 s / 30 s | ≥ 0.5 s | 1.3× | 60 s |
| C3 conservative | 90 s / 90 s | ≥ 1.5 s | 1.8× | 120 s |

### A. Synthetic stream (ground truth)
| Config | False WARNING+ time (alert phase) | False microsleeps | WARNING delay | DROWSY delay | Microsleeps detected | Microsleep latency | Level changes |
|---|---|---|---|---|---|---|---|
| C0 | 0.0 % | 0 | 11.5 s | 38.7 s | 4/4 | 1.0 s | 2 |
| **C1** | **0.0 %** | **0** | **8.7 s** | **23.5 s** | **4/4** | **1.0 s** | **2** |
| C2 | 45.7 % | 3 | 0.0 s* | 0.0 s* | 4/4 | 0.5 s | 5 |
| C3 | 0.0 % | 0 | 35.3 s | 53.4 s | 2/4 | 1.5 s | 2 |

\* C2 was already (falsely) in DROWSY when the drowsy phase began.

### B. Recorded session (no labels)
| Config | First WARNING | ALERT / WARNING / DROWSY time | Microsleeps | PERCLOS flag toggles | Level changes |
|---|---|---|---|---|---|
| C0 | 31.6 s | 35 / 2 / 64 % | 9 | 7 | 7 |
| C1 | 31.6 s | 48 / 8 / 44 % | 9 | 11 | 8 |
| C2 | 21.9 s | 38 / 7 / 55 % | 14 | 11 | 9 |
| C3 | 32.1 s | 20 / 0 / 80 % | 9 | 7 | 5 |

## Analysis
- **Stability vs. detection delay trade-off is clear.** Shortening the window (C0 → C1) cut the DROWSY delay from 38.7 s to 23.5 s with no extra false alarms on the synthetic stream. Lengthening it (C3) made the delay 53 s and **missed 2 of 4 microsleeps** (1.2–1.5 s closures fall below a 1.5 s rule).
- **A 0.5 s microsleep rule (C2) is not usable:** normal long blinks (0.55 s) became microsleeps, so 45.7 % of the alert phase was flagged, and 14 vs 9 microsleeps were counted on the real session.
- **The cost of C1** is a noisier PERCLOS flag on the real session (11 vs 7 toggles): a 30 s window reacts to short bursts of eye closure. SG-5's 10 s hold-down keeps the shown level steady (8 vs 7 level changes).
- In the real session, the face is lost 45 % of the time. Frames without a face are excluded from PERCLOS, so PERCLOS can be computed over a much shorter effective window. This is a known limitation.

## Week 6 decision
Adopt **C1 (30 s PERCLOS window, 1.0 s microsleep, 1.5× slow blink, 60 s baseline)** as the candidate configuration and
compare it with C0 in Week 6 quantitatively, on labelled drowsy/alert clips (e.g. NTHU-DDD or our own labelled recordings).
Also test a minimum-face-coverage rule for PERCLOS. `config.py` keeps C0 as the default until the Week 6 comparison confirms the change.

## Limitations
- The synthetic stream is scripted. It shows behaviour under known events but is not a substitute for labelled real data.
- The recorded session has no ground-truth labels.
- Thresholds come partly from the literature (PERCLOS 12 %, microsleep 1 s) and are partly design choices.

## Contribution
Both members designed the configurations. Mock cue stream and replay harness: Hamza. Analysis and Week 6 decision: Rija and Hamza.
*(Edit this line to reflect the actual split before the review.)*
