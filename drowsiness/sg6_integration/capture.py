"""Camera / video input.

On Windows the camera is chosen by NAME (via DirectShow), so a phone connected
through Phone Link ("Windows Virtual Camera") is never picked by accident.
On the Raspberry Pi later, only this file needs to change (e.g. to Picamera2).
"""
import sys
import time

import cv2

from .. import config


def list_cameras():
    """Camera names in DirectShow order (index = position). Empty if unavailable."""
    if sys.platform != "win32":
        return []
    try:
        from pygrabber.dshow_graph import FilterGraph
        return FilterGraph().get_input_devices()
    except Exception:
        return []


def choose_camera(names):
    """Index of the first real (non-virtual) camera, preferring CAMERA_NAME if set."""
    if config.CAMERA_NAME:
        for i, n in enumerate(names):
            if config.CAMERA_NAME.lower() in n.lower():
                return i
        raise RuntimeError(f"No camera named like '{config.CAMERA_NAME}'. Found: {names}")
    for i, n in enumerate(names):
        if not any(word in n.lower() for word in config.CAMERA_SKIP_WORDS):
            return i
    return 0


class Camera:
    def __init__(self, source=config.CAMERA_SOURCE, width=config.FRAME_WIDTH,
                 height=config.FRAME_HEIGHT, mirror=config.MIRROR):
        source = str(source)
        self.is_file = not (source == "auto" or source.isdigit())
        self.mirror = mirror and not self.is_file

        if self.is_file:
            self.cap = cv2.VideoCapture(source)
            if not self.cap.isOpened():
                raise RuntimeError(f"Could not open video file: {source}")
        else:
            self.cap = self._open_webcam(source, width, height)

        # For video files, use the video's own clock so timing is correct
        # even if processing is slower or faster than real time.
        self.file_fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.frame_index = 0
        self.start_time = time.time()

    @staticmethod
    def _open_webcam(source, width, height):
        names = list_cameras()
        if names:
            # Windows: DirectShow indexes match the names list.
            index = choose_camera(names) if source == "auto" else int(source)
            label = names[index] if index < len(names) else f"camera {index}"
            api = cv2.CAP_DSHOW
        else:
            index = 0 if source == "auto" else int(source)
            label = f"camera {index}"
            api = cv2.CAP_ANY

        cap = cv2.VideoCapture(index, api)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open {label}. Close other apps using it "
                               f"(Teams, Zoom, Camera app) and try again.")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        # Cameras often send a few black frames while starting up.
        deadline = time.time() + 3.0
        while time.time() < deadline:
            ok, frame = cap.read()
            if ok and frame is not None and frame.mean() > 5:
                print(f"Using camera {index}: {label} ({frame.shape[1]}x{frame.shape[0]})")
                return cap
        cap.release()
        raise RuntimeError(f"{label} opened but only gives a black picture. "
                           f"Check the lens cover / camera privacy switch.")

    def read(self):
        """Return (timestamp_seconds, frame_bgr) or (None, None) at the end."""
        ok, frame = self.cap.read()
        if not ok:
            return None, None
        if self.mirror:
            frame = cv2.flip(frame, 1)
        if self.is_file:
            t = self.frame_index / self.file_fps
        else:
            t = time.time() - self.start_time
        self.frame_index += 1
        return t, frame

    def release(self):
        self.cap.release()
