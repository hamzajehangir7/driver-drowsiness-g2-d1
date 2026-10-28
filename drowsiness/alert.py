"""Alarm output. Laptop: beeps. Raspberry Pi later: swap in a GPIO buzzer + LED here."""
import sys
import threading
import time

from .decision import DROWSY, WARNING

try:
    import winsound
except ImportError:          # not Windows
    winsound = None


def _beep(freq, ms):
    if winsound:
        winsound.Beep(freq, ms)
    else:
        sys.stdout.write("\a")
        sys.stdout.flush()
        time.sleep(ms / 1000)


class Alarm:
    def __init__(self):
        self.muted = False
        self._busy = False
        self._last_drowsy_beep = 0.0

    def update(self, decision):
        if self.muted:
            return
        now = time.time()
        if decision.level == WARNING and decision.level_raised:
            self._play([(880, 250), (660, 350)])                 # one chime
        elif decision.level == DROWSY and now - self._last_drowsy_beep > 0.8:
            self._last_drowsy_beep = now
            self._play([(1400, 300)])                             # repeating alarm

    def _play(self, tones):
        if self._busy:
            return
        self._busy = True

        def run():
            try:
                for f, ms in tones:
                    _beep(f, ms)
            finally:
                self._busy = False
        threading.Thread(target=run, daemon=True).start()
