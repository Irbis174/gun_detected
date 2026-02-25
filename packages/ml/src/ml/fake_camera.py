import threading
import time

import cv2
import numpy as np


class FakeCameraStream:
    def __init__(self, fps: float = 10.0, width: int = 640, height: int = 360):
        self.fps = fps
        self.width = width
        self.height = height

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

        self._latest_jpeg = None
        self._latest_ts = None
        self._counter = 0

    def start(self):
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1.0)

    def latest(self):
        with self._lock:
            return self._latest_jpeg, self._latest_ts
        
    def _run(self):
        delay = 1.0 / max(self.fps, 0.1)

        while not self._stop.is_set():
            self._counter += 1
            ts = time.time()
            
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            cv2.putText(frame, f'frame #{self._counter}', (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.putText(frame, f'ts={ts:.3f}', (20, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 200), 2)

            # 3) кодируем в JPEG
            ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ok:
                jpg = buf.tobytes()

                # 4) атомарно обновляем "последний кадр"
                with self._lock:
                    self._latest_jpeg = jpg
                    self._latest_ts = ts

            time.sleep(delay)