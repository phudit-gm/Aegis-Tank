"""Frame receiver — connects to the MJPEG stream from the ESP32-CAM and pulls out frames one at a time (BGR numpy array)."""

import cv2
import numpy as np
import requests

JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"


class FrameReceiver:
    def __init__(self, stream_url: str, timeout: float = 5.0):
        self.stream_url = stream_url
        self.timeout = timeout
        self._resp = None
        self._buffer = b""

    def connect(self):
        self._resp = requests.get(self.stream_url, stream=True, timeout=self.timeout)
        self._resp.raise_for_status()
        self._buffer = b""

    def close(self):
        if self._resp is not None:
            self._resp.close()
            self._resp = None

    def frames(self):
        """Generator that yields BGR frames (numpy array) continuously until the stream drops.

        Reconnection is not handled here — the caller (main loop) decides how to retry when the stream drops.
        """
        if self._resp is None:
            self.connect()

        for chunk in self._resp.iter_content(chunk_size=4096):
            if not chunk:
                continue
            self._buffer += chunk

            while True:
                start = self._buffer.find(JPEG_SOI)
                end = self._buffer.find(JPEG_EOI)
                if start == -1 or end == -1 or end < start:
                    if start > 0:
                        self._buffer = self._buffer[start:]
                    break
                jpg_bytes = self._buffer[start:end + 2]
                self._buffer = self._buffer[end + 2:]
                frame = cv2.imdecode(np.frombuffer(jpg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    yield frame
