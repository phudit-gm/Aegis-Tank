"""Manual smoke test — เช็คว่า FrameReceiver ต่อกล้องจริงติดและถอดเฟรมได้

ใช้: python scripts/test_camera_stream.py
ต้องมี ESP32-CAM เปิดอยู่บนเครือข่ายเดียวกันตาม config/settings.yaml (camera.stream_url)
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config import load_settings
from src.vision.frame_receiver import FrameReceiver


def main():
    settings = load_settings()
    stream_url = settings["camera"]["stream_url"]
    print(f"Connecting to {stream_url} ...")

    receiver = FrameReceiver(stream_url)
    n_frames = 0
    start = time.time()
    target_frames = 30

    try:
        for frame in receiver.frames():
            n_frames += 1
            if n_frames == 1:
                out_path = Path(__file__).resolve().parent / "last_frame.jpg"
                import cv2
                cv2.imwrite(str(out_path), frame)
                print(f"Frame shape: {frame.shape} — saved first frame to {out_path}")
            if n_frames >= target_frames:
                break
    finally:
        receiver.close()

    elapsed = time.time() - start
    fps = n_frames / elapsed if elapsed > 0 else 0
    print(f"Got {n_frames} frames in {elapsed:.2f}s ({fps:.1f} fps)")


if __name__ == "__main__":
    main()
