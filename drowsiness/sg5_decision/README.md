# SG-5 — Drowsiness Decision & Alert Logic

**Members:** Eman Rana, Fahad Naseer, Syed Muhammad Dawar Raza Zaidi

## Purpose
Fuse SG-4 temporal evidence into three levels — ALERT / WARNING / DROWSY — and drive the alarm.

| Evidence | Points |
|---|---|
| Microsleep in the last 60 s | DROWSY at once |
| PERCLOS ≥ 12 % | +2 |
| Slow blinks (≥ 1.5 × baseline) | +2 |
| ≥ 2 yawns in 3 min | +1 |
| Head nod in the last 60 s | +1 |

0–1 ALERT, 2–3 WARNING, 4+ DROWSY. The level rises at once and falls only after 10 s at the lower level.

## I/O (V1)
- **Input:** `TemporalState` from SG-4.
- **Output:** `DecisionState(level, raw_level, score, points, reasons, level_raised)`. `alert.py` is kept separate from the decision logic (laptop beeps now, GPIO buzzer later).

## Mock input
Run SG-4 + SG-5 without a camera: `python -m drowsiness.sg4_temporal.experiments.run_week5_experiment` (uses `mock_cues.py`).

## Status
- ✅ Week 4 baseline is working in the pipeline.
- ⏳ **Week 5 left:** compare ≥ 2 decision rules (current weighted score vs. weighted score with a 5 s/15 s hold, or a state machine). Report false and missed alerts and alert latency on the mock streams, and select a preliminary rule.
