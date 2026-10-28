# Frozen V1 module interfaces — G2-D1 Driver Drowsiness

Pipeline: `Camera → SG-1 Face/Landmarks → SG-2 Eye cues + SG-3 Yawn/Head cues → SG-4 Temporal indicators → SG-5 Decision → Alert`

These are the objects passed between modules in `drowsiness/sg6_integration/main.py`. **Do not rename or
remove a field without agreement from the dependent sub-group.** Adding new fields is allowed. Every time is in seconds of
real time (video clock for files), never frame counts.

## Camera → SG-1
`Camera.read() -> (t: float seconds, frame: np.ndarray BGR uint8 HxWx3)`, `(None, None)` at end of stream.

## SG-1 → SG-2 / SG-3 — `FaceResult` (`sg1_face_landmarks/landmarks.py`)
| Field | Type | Meaning |
|---|---|---|
| `found` | bool | a face was found in this frame |
| `landmarks` | `np.ndarray (N, 2) float32` | MediaPipe Face Mesh points in **pixels**, N = 468 (478 with iris refinement) |
| `bbox` | `(x1, y1, x2, y2)` int | face box in pixels, clipped to the frame |

## SG-2 → SG-4 — `EyeState` (`sg2_eye_blink/eye.py`)
| Field | Type | Meaning |
|---|---|---|
| `ear_left`, `ear_right`, `ear` | float | eye aspect ratio per eye and the mean |
| `closed` | bool | eyes closed now (with hysteresis) |
| `closed_threshold` | float | EAR below which the eye counts as closed (0.70 × calibrated open EAR) |
| `closed_duration` | float s | length of the current closure (0 when open) |
| `blink_count`, `long_closure_count` | int | running counters |
| `blink_event` | bool | True on the frame a 0.05–0.50 s blink ends |
| `closure_event` | bool | True on the frame **any** closure ≥ 0.05 s ends |
| `last_closure_duration` | float s | duration of the closure that just ended |
| `last_closure_min_ear` | float | lowest EAR reached during that closure |

## SG-3 → SG-4 — `MouthHeadState` (`sg3_yawn_head/mouth_head.py`)
| Field | Type | Meaning |
|---|---|---|
| `mar` | float | mouth aspect ratio |
| `mouth_open`, `yawning` | bool | MAR > 0.35; wide open ≥ 1.5 s |
| `yawn_event` | bool | True on the frame a yawn is first confirmed |
| `yawn_count` | int | running counter |
| `pitch`, `yaw`, `roll` | float deg | head pose (pitch > 0 = looking down) |
| `pitch_change` | float deg | pitch relative to calibrated baseline |
| `head_down` | bool | `pitch_change > 20°` |
| `head_down_duration` | float s | length of the current head-down period |

## SG-4 → SG-5 — `TemporalState` (`sg4_temporal/temporal.py`)
Call: `TemporalAnalyzer(open_ear).update(t, face_found, eye_state, mouth_head_state) -> TemporalState`

| Field | Type | Meaning |
|---|---|---|
| `elapsed` | float s | time since temporal analysis started |
| `warmed_up` | bool | enough history for a PERCLOS verdict |
| `perclos` | float 0..1 | share of the last `PERCLOS_WINDOW_SEC` with eyes ≥ 80 % closed (P80, time-weighted) |
| `p80_closed` | bool | this frame counts as P80-closed |
| `closed_ear` | float | learned fully-closed EAR |
| `blink_baseline` | float s or None | personal median blink duration, None until learned |
| `baseline_progress` | float 0..1 | progress while learning the baseline |
| `mean_blink_duration`, `blinks_in_window` | float s, int | blinks in the last window |
| `slow_blinks` | bool | mean blink ≥ `SLOW_BLINK_FACTOR` × baseline |
| `microsleep_active` | bool | eyes closed ≥ `MICROSLEEP_SEC` right now |
| `microsleeps_60s`, `total_microsleeps` | int | counts |
| `yawns_180s` | int | yawns in the last 3 min |
| `nods_60s`, `total_nods` | int | head nods (head down ≥ 1 s) |
| `driver_visible` | bool | face seen in the last 2 s |

SG-4 can be driven without a camera from a standardized cue stream — see `drowsiness/sg4_temporal/mock_cues.py`.

## SG-5 → Alert — `DecisionState` (`sg5_decision/decision.py`)
| Field | Type | Meaning |
|---|---|---|
| `level` | int | 0 ALERT, 1 WARNING, 2 DROWSY (with 10 s hold when falling) |
| `raw_level` | int | level from this frame's evidence only |
| `score`, `points` | int, dict | evidence points (PERCLOS 2, slow blinks 2, yawns 1, nods 1) |
| `reasons` | list[str] | human-readable reasons, `"MICROSLEEP"` first if present |
| `level_raised` | bool | True on the frame the level goes up |

## Log format (`python run.py --log file.csv`)
One row per frame after calibration; columns listed in `CSV_COLUMNS` in `sg6_integration/main.py`. This CSV is also the
standardized cue-stream format consumed by `sg4_temporal/mock_cues.load_csv_stream()`.
