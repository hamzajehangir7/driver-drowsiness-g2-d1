# SG-3 — Yawn & Facial-Cue Analysis

**Members:** Shaheer Asghar, Tayyaba Naveed

## Purpose
Mouth Aspect Ratio (MAR) from the inner-lip landmarks, yawn detection (mouth wide open for a minimum time), and head pose (pitch/yaw/roll via `solvePnP`) for nod detection.

## I/O (V1)
- **Input:** `landmarks (N,2)` px, `t`, frame width and height; calibrated baseline pitch via `set_baseline()`.
- **Output:** `MouthHeadState` (mar, yawning, yawn_event, yawn_count, pitch/yaw/roll, pitch_change, head_down, head_down_duration) — see `docs/INTERFACES_V1.md`.

## Parameters (`config.py`)
`MAR_OPEN = 0.35`, `MAR_YAWN = 0.60`, `YAWN_MIN_SEC = 1.5`, `HEAD_DOWN_DEG = 20`.

## Status
- ✅ Week 4 baseline is working in the pipeline (5 yawns detected in the recorded session).
- ⏳ **Week 5 left:** compare ≥ 2 configurations (MAR_YAWN 0.5/0.6/0.7 × YAWN_MIN_SEC 1.0/1.5) on yawn and non-yawn clips (talking, laughing). Report false positives and negatives, and add a sample sequence.

## Limitations
Talking or laughing with a wide mouth can trigger a yawn; a hand covering the mouth hides yawns.
