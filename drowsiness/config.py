"""All tunable settings in one place.

Times are in seconds (not frames) so the same values work on a fast laptop
and on a slower Raspberry Pi.
"""

# ---------------- Camera ----------------
CAMERA_SOURCE = "auto"    # "auto" = first real camera; or a number; or a video file path
CAMERA_NAME = ""          # e.g. "USB HD UVC WebCam" to force a camera by (part of) its name
CAMERA_SKIP_WORDS = ("virtual", "phone link", "obs", "droidcam", "iriun")  # never auto-pick these
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
MIRROR = True             # flip the image horizontally (feels natural on a webcam)

# ---------------- SG-1 Face / Landmarks ----------------
MIN_DETECTION_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5

# ---------------- Calibration ----------------
# At start-up the driver looks at the camera normally (eyes open, mouth closed)
# for this long. Their personal "normal" EAR / MAR / head angle is measured.
CALIBRATION_SECONDS = 3.0

# ---------------- SG-2 Eye / Blink ----------------
EAR_DEFAULT_CLOSED = 0.20   # used until calibration finishes
EAR_CLOSED_RATIO = 0.70     # eyes "closed" when EAR < 70% of the person's open-eye EAR
EAR_HYSTERESIS = 1.10       # must rise 10% above the closed threshold to count as open again
BLINK_MIN_SEC = 0.05        # shorter closures are treated as noise
BLINK_MAX_SEC = 0.50        # longer closures are "long closures" (not a normal blink)

# ---------------- SG-3 Mouth / Yawn ----------------
MAR_OPEN = 0.35             # mouth counts as "open" (talking, etc.)
MAR_YAWN = 0.60             # mouth wide open, possible yawn
YAWN_MIN_SEC = 1.5          # wide open at least this long = yawn

# ---------------- SG-3 Head pose ----------------
HEAD_DOWN_DEG = 20.0        # head pitched down this much more than baseline = "head down"

# ---------------- SG-4 Temporal analysis ----------------
# Sources for each value are listed in REFERENCES.md.
PERCLOS_WINDOW_SEC = 60.0        # PERCLOS is defined per minute (Wierwille et al., 1994)
PERCLOS_WARMUP_SEC = 60.0        # no PERCLOS verdict until this much data exists
PERCLOS_CLOSED_OPENNESS = 0.20   # "closed" for PERCLOS = eye opening <= 20%, i.e. >= 80% closed (P80)
PERCLOS_THRESHOLD = 0.12         # >= 12% closure = drowsy (AAA Foundation, after Wierwille 1994)
MICROSLEEP_SEC = 1.0             # eyes closed >= 1 s = microsleep (Hertig-Godeschalk et al., 2020)
BLINK_BASELINE_SEC = 120.0       # personal blink-duration baseline from the first 2 minutes (design choice)
BLINK_BASELINE_MIN_BLINKS = 5
SLOW_BLINK_FACTOR = 1.5          # slow blinks = mean duration >= 1.5 x baseline (design choice; Ingre 2006)
SLOW_BLINK_MIN_BLINKS = 3        # need at least this many blinks in the window to judge
YAWN_WINDOW_SEC = 180.0          # 2+ yawns in 3 minutes (design choice; Provine 1987)
YAWN_COUNT_THRESHOLD = 2
NOD_MIN_SEC = 1.0                # head down >= 1 s counts as a nod (design choice)
NOD_WINDOW_SEC = 60.0
FACE_LOST_SEC = 2.0              # no face for this long = "driver not visible"

# ---------------- SG-5 Decision (three levels) ----------------
POINTS_PERCLOS = 2               # strong signs
POINTS_SLOW_BLINKS = 2
POINTS_YAWNS = 1                 # supporting signs
POINTS_NODS = 1
WARNING_SCORE = 2                # 0-1 ALERT, 2-3 WARNING, 4+ DROWSY
DROWSY_SCORE = 4
LEVEL_DOWN_HOLD_SEC = 10.0       # level rises at once, falls only after 10 s at the lower level

# ---------------- Display ----------------
GRAPH_SECONDS = 10.0        # how much history the live EAR/MAR graph shows
