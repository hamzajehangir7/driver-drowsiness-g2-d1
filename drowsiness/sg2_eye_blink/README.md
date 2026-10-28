# SG-2 — Eye State & Blink Analysis

**Members:** Anss Ahmad, Abdul Sammi Khan

## Purpose
Compute the Eye Aspect Ratio (EAR) for each eye from SG-1 landmarks, decide open/closed with a personal calibrated threshold and hysteresis, and detect blinks and long closures.

## I/O (V1)
- **Input:** `landmarks (N,2)` px + `t`; calibrated open-eye EAR via `set_baseline()`.
- **Output:** `EyeState` (ear, closed, closed_duration, blink/closure events, last closure duration and min EAR) — see `docs/INTERFACES_V1.md`.

## Parameters (`config.py`)
`EAR_CLOSED_RATIO = 0.70`, `EAR_HYSTERESIS = 1.10`, `BLINK_MIN_SEC = 0.05`, `BLINK_MAX_SEC = 0.50`.

## Mock input for SG-4
`drowsiness/sg4_temporal/mock_cues.py` produces EyeState-compatible streams, so SG-4 can run without this module.

## Status
- ✅ Week 4 baseline is working in the pipeline.
- ⏳ **Week 5 left:** compare EAR closed ratios 0.65 / 0.70 / 0.75 (and/or a learned eye-state classifier) on labelled open/closed frames. Report false-open and false-closed counts, including spectacles and low light.

## Limitations
EAR depends on yaw (eye width shrinks when the head turns); not yet evaluated with spectacles.
