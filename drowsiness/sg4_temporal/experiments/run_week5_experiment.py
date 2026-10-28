"""SG-4 Week 5 experiment: compare temporal window / persistence configurations.

Run from the project root:
    python -m drowsiness.sg4_temporal.experiments.run_week5_experiment

Feeds the same cue streams through TemporalAnalyzer (SG-4) and DecisionEngine (SG-5)
under each configuration and writes results to drowsiness/sg4_temporal/results/.
"""
import json
import os
from contextlib import contextmanager

from ... import config
from ...sg5_decision.decision import ALERT, DROWSY, WARNING, DecisionEngine
from ..mock_cues import CueStateBuilder, load_csv_stream, synthetic_stream
from ..temporal import TemporalAnalyzer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RESULTS = os.path.join(ROOT, "drowsiness", "sg4_temporal", "results")
SESSION_CSV = os.path.join(ROOT, "data", "test_session.csv")

CONFIGS = {
    "C0_baseline_W4": dict(PERCLOS_WINDOW_SEC=60.0, PERCLOS_WARMUP_SEC=60.0, MICROSLEEP_SEC=1.0,
                           SLOW_BLINK_FACTOR=1.5, BLINK_BASELINE_SEC=120.0),
    "C1_short_window": dict(PERCLOS_WINDOW_SEC=30.0, PERCLOS_WARMUP_SEC=30.0, MICROSLEEP_SEC=1.0,
                            SLOW_BLINK_FACTOR=1.5, BLINK_BASELINE_SEC=60.0),
    "C2_sensitive": dict(PERCLOS_WINDOW_SEC=30.0, PERCLOS_WARMUP_SEC=30.0, MICROSLEEP_SEC=0.5,
                         SLOW_BLINK_FACTOR=1.3, BLINK_BASELINE_SEC=60.0),
    "C3_conservative": dict(PERCLOS_WINDOW_SEC=90.0, PERCLOS_WARMUP_SEC=90.0, MICROSLEEP_SEC=1.5,
                            SLOW_BLINK_FACTOR=1.8, BLINK_BASELINE_SEC=120.0),
}


@contextmanager
def patched(values):
    old = {k: getattr(config, k) for k in values}
    for k, v in values.items():
        setattr(config, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(config, k, v)


def replay(frames, open_ear):
    """Run SG-4 + SG-5 over a cue stream; return per-frame (t, TemporalState copy fields, level)."""
    builder, temporal, decision = CueStateBuilder(), TemporalAnalyzer(open_ear), DecisionEngine()
    out = []
    for f in frames:
        eye, mh = builder.update(f)
        ts = temporal.update(f["t"], f["face"], eye, mh)
        ds = decision.update(f["t"], ts)
        out.append({
            "t": f["t"], "perclos": ts.perclos, "perclos_flag": ts.warmed_up and ts.perclos >= config.PERCLOS_THRESHOLD,
            "slow_blinks": ts.slow_blinks, "microsleep_active": ts.microsleep_active,
            "total_microsleeps": ts.total_microsleeps, "level": ds.level,
        })
    return out


def toggles(rows, key):
    return sum(1 for a, b in zip(rows, rows[1:]) if a[key] != b[key])


def first_time(rows, cond, after=0.0):
    for r in rows:
        if r["t"] >= after and cond(r):
            return r["t"]
    return None


def time_share(rows, cond, lo=-1.0, hi=1e9):
    sel = [r for r in rows if lo <= r["t"] < hi]
    return sum(1 for r in sel if cond(r)) / len(sel) if sel else 0.0


def fmt(x, unit="s"):
    return "never" if x is None else f"{x:.1f} {unit}"


def evaluate_synthetic(rows, truth):
    onset = truth["drowsy_onset"]
    ms_detect = []
    for m in truth["microsleeps"]:
        hit = first_time(rows, lambda r: r["microsleep_active"], after=m)
        ms_detect.append(hit - m if hit is not None and hit - m < 3.0 else None)
    first_warn = first_time(rows, lambda r: r["level"] >= WARNING, after=onset)
    first_drowsy = first_time(rows, lambda r: r["level"] >= DROWSY, after=onset)
    found = [d for d in ms_detect if d is not None]
    return {
        "false_alarm_time_alert_phase": time_share(rows, lambda r: r["level"] >= WARNING, 0, onset),
        "false_microsleeps_alert_phase": max((r["total_microsleeps"] for r in rows if r["t"] < onset), default=0),
        "warning_delay_s": None if first_warn is None else first_warn - onset,
        "drowsy_delay_s": None if first_drowsy is None else first_drowsy - onset,
        "microsleeps_detected": f"{len(found)}/{len(truth['microsleeps'])}",
        "mean_microsleep_latency_s": sum(found) / len(found) if found else None,
        "drowsy_time_in_drowsy_phase": time_share(rows, lambda r: r["level"] >= DROWSY, onset),
        "perclos_flag_toggles": toggles(rows, "perclos_flag"),
        "level_changes": toggles(rows, "level"),
    }


def evaluate_session(rows):
    return {
        "duration_s": rows[-1]["t"] - rows[0]["t"],
        "first_warning_s": first_time(rows, lambda r: r["level"] >= WARNING),
        "first_drowsy_s": first_time(rows, lambda r: r["level"] >= DROWSY),
        "time_alert": time_share(rows, lambda r: r["level"] == ALERT),
        "time_warning": time_share(rows, lambda r: r["level"] == WARNING),
        "time_drowsy": time_share(rows, lambda r: r["level"] == DROWSY),
        "microsleeps": rows[-1]["total_microsleeps"],
        "max_perclos": max(r["perclos"] for r in rows),
        "perclos_flag_toggles": toggles(rows, "perclos_flag"),
        "level_changes": toggles(rows, "level"),
    }


def main():
    os.makedirs(RESULTS, exist_ok=True)
    synth, truth = synthetic_stream(seed=0)
    session = load_csv_stream(SESSION_CSV) if os.path.exists(SESSION_CSV) else None
    session_open_ear = None
    if session:
        # Same rule as SG-2 calibration: closed threshold = 0.70 x open EAR.
        th = next(f["closed_threshold"] for f in session if f["face"])
        session_open_ear = th / config.EAR_CLOSED_RATIO

    results = {"synthetic": {}, "session": {}}
    for name, values in CONFIGS.items():
        with patched(values):
            results["synthetic"][name] = evaluate_synthetic(replay(synth, truth["open_ear"]), truth)
            if session:
                results["session"][name] = evaluate_session(replay(session, session_open_ear))
        print(f"done {name}")

    with open(os.path.join(RESULTS, "week5_results.json"), "w") as fh:
        json.dump({"configs": CONFIGS, "results": results}, fh, indent=2)

    lines = ["# SG-4 Week 5 results (generated)", "",
             "Generated by `python -m drowsiness.sg4_temporal.experiments.run_week5_experiment`.", "",
             "## Configurations", "",
             "| Config | PERCLOS window / warm-up | Microsleep | Slow-blink factor | Blink baseline |",
             "|---|---|---|---|---|"]
    for n, c in CONFIGS.items():
        lines.append(f"| {n} | {c['PERCLOS_WINDOW_SEC']:.0f} s / {c['PERCLOS_WARMUP_SEC']:.0f} s | "
                     f">= {c['MICROSLEEP_SEC']} s | {c['SLOW_BLINK_FACTOR']} x | {c['BLINK_BASELINE_SEC']:.0f} s |")

    lines += ["", "## A. Synthetic stream with ground truth (alert 0-240 s, drowsy 240-480 s)", "",
              "| Config | False WARNING+ time (alert phase) | False microsleeps (alert) | WARNING delay | "
              "DROWSY delay | Microsleeps detected | Mean microsleep latency | DROWSY share (drowsy phase) | "
              "PERCLOS flag toggles | Level changes |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in results["synthetic"].items():
        lines.append(f"| {n} | {r['false_alarm_time_alert_phase'] * 100:.1f}% | {r['false_microsleeps_alert_phase']} | "
                     f"{fmt(r['warning_delay_s'])} | {fmt(r['drowsy_delay_s'])} | {r['microsleeps_detected']} | "
                     f"{fmt(r['mean_microsleep_latency_s'])} | {r['drowsy_time_in_drowsy_phase'] * 100:.1f}% | "
                     f"{r['perclos_flag_toggles']} | {r['level_changes']} |")

    if session:
        lines += ["", "## B. Recorded webcam session `data/test_session.csv` (no labels)", "",
                  "| Config | First WARNING | First DROWSY | ALERT / WARNING / DROWSY time | Microsleeps | "
                  "Max PERCLOS | PERCLOS flag toggles | Level changes |",
                  "|---|---|---|---|---|---|---|---|"]
        for n, r in results["session"].items():
            lines.append(f"| {n} | {fmt(r['first_warning_s'])} | {fmt(r['first_drowsy_s'])} | "
                         f"{r['time_alert'] * 100:.0f}% / {r['time_warning'] * 100:.0f}% / {r['time_drowsy'] * 100:.0f}% | "
                         f"{r['microsleeps']} | {r['max_perclos'] * 100:.1f}% | {r['perclos_flag_toggles']} | "
                         f"{r['level_changes']} |")

    with open(os.path.join(RESULTS, "week5_results.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
