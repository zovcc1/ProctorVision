import cv2
import threading
import numpy as np
from typing import Optional, Tuple
from backend.config.config_manager import config

class CameraStream:
    def __init__(self):
        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._fps = 0
        self._last_time = 0

    def start(self) -> bool:
        idx = config.get('camera.index', 0)
        res = config.get('camera.resolution', [640, 480])
        buf = config.get('camera.buffer_size', 1)

        self._cap = cv2.VideoCapture(idx)
        if not self._cap.isOpened():
            return False

        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, buf)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, res[0])
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, res[1])

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def _loop(self):
        while self._running and self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret and frame is not None:
                with self._lock:
                    self._frame = frame

    def read_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._frame is not None:
                return self._frame.copy()
        return None

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._cap:
            self._cap.release()
        self._cap = None
        with self._lock:
            self._frame = None

    def is_running(self) -> bool:
        return self._running and self._cap is not None and self._cap.isOpened()
