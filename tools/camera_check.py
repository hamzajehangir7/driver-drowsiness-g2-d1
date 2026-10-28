r"""Find which camera index / backend works on this PC.

Usage:  .\.venv\Scripts\python.exe tools\camera_check.py
Each attempt runs in its own process with a time limit, so a stuck driver can't hang the test.
"""
import subprocess
import sys

ATTEMPT = r"""
import sys, time, cv2
idx, backend = int(sys.argv[1]), sys.argv[2]
api = {"DSHOW": cv2.CAP_DSHOW, "MSMF": cv2.CAP_MSMF, "ANY": cv2.CAP_ANY}[backend]
t0 = time.time()
cap = cv2.VideoCapture(idx, api)
opened = cap.isOpened()
ok, frame = (cap.read() if opened else (False, None))
for _ in range(5):
    if ok: break
    time.sleep(0.2); ok, frame = cap.read()
print(f"opened={opened} frame_ok={ok} shape={None if frame is None else frame.shape} "
      f"mean={None if frame is None else round(float(frame.mean()), 1)} time={time.time()-t0:.1f}s")
cap.release()
"""


def main():
    print("OpenCV test of camera index x backend (15 s limit each)\n")
    for idx in range(3):
        for backend in ("DSHOW", "MSMF", "ANY"):
            try:
                r = subprocess.run([sys.executable, "-c", ATTEMPT, str(idx), backend],
                                   capture_output=True, text=True, timeout=15)
                out = r.stdout.strip() or ("ERROR: " + r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "no output")
            except subprocess.TimeoutExpired:
                out = "TIMED OUT (driver hung)"
            print(f"index {idx}  {backend:5s}  {out}")


if __name__ == "__main__":
    main()
