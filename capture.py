import threading
import time

import mss
import numpy as np
from PIL import Image


class CaptureThread(threading.Thread):
    """Captures a screen region at a fixed FPS and exposes the latest frame."""

    def __init__(self, config):
        super().__init__(daemon=True)
        self.config = config
        self._frame: Image.Image | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._enabled = config.enabled

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def get_frame(self) -> Image.Image | None:
        with self._lock:
            return self._frame

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def update_config(self, config) -> None:
        self.config = config
        self._enabled = config.enabled

    def stop(self) -> None:
        self._stop.set()

    # ------------------------------------------------------------------ #
    # Thread loop                                                          #
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        with mss.mss() as sct:
            while not self._stop.is_set():
                if self._enabled:
                    try:
                        monitor = {
                            "left":   self.config.capture_x,
                            "top":    self.config.capture_y,
                            "width":  max(1, self.config.capture_w),
                            "height": max(1, self.config.capture_h),
                        }
                        shot = sct.grab(monitor)
                        # mss returns BGRA; convert to RGB PIL image
                        img = Image.frombytes(
                            "RGB",
                            (shot.width, shot.height),
                            shot.bgra,
                            "raw",
                            "BGRX",
                        )
                        with self._lock:
                            self._frame = img
                    except Exception:
                        pass

                interval = 1.0 / max(1, self.config.fps)
                self._stop.wait(interval)
