import socket
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.main import Orchestrator


def make_settings(motor_host, motor_port):
    return {
        "camera": {
            "stream_url": "http://127.0.0.1:1/stream",  # not actually connected in this test (FrameReceiver connects lazily)
            "frame_width": 320,
            "frame_height": 240,
            "horizontal_fov_deg": 60.0,
        },
        "motor_controller": {"host": motor_host, "port": motor_port, "send_rate_hz": 20},
        "detection": {"target_class": "person", "conf_threshold": 0.5, "model_path": "models/yolov8n.pt"},
        "tracking": {"algorithm": "kalman", "process_noise": 1.0, "measurement_noise": 10.0},
        "aiming": {
            "aim_tolerance_px": 15,
            "pid_pan": {"kp": 1.0, "ki": 0.0, "kd": 0.0},
            "pid_tilt": {"kp": 1.0, "ki": 0.0, "kd": 0.0},
        },
        "control": {
            "body_turn_threshold_deg": 45,
            "body_turn_speed": 120,
            "fire_burst_ms": 500,
            "scan_sweep_limit_deg": 60,
            "scan_step_deg_per_sec": 30,
            "scan_speed": 120,
        },
        "loop": {"frequency_hz": 20},
    }


class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.settimeout(1.0)
        host, port = self.listener.getsockname()
        self.orchestrator = Orchestrator(make_settings(host, port))

    def tearDown(self):
        self.orchestrator.close()
        self.listener.close()

    def _recv_all(self, n):
        msgs = []
        for _ in range(n):
            data, _ = self.listener.recvfrom(1024)
            msgs.append(data.decode("utf-8"))
        return msgs

    def test_target_at_center_stops_body_and_holds_fire(self):
        detection = SimpleNamespace(x=160, y=120)  # exact center of a 320x240 frame
        self.orchestrator._on_target_found(detection, dt=0.05)
        msgs = self._recv_all(4)  # turret, tilt, track, fire
        self.assertTrue(any(m.startswith("TURRET:STOP:") for m in msgs))
        self.assertTrue(any(m.startswith("TILT:STOP:") for m in msgs))
        self.assertIn("TRACK:STOP:0", msgs)
        self.assertTrue(any(m.startswith("FIRE:ON:") for m in msgs))

    def test_target_off_target_holds_fire_off(self):
        detection = SimpleNamespace(x=280, y=120)  # far from center beyond tolerance
        self.orchestrator._on_target_found(detection, dt=0.05)
        msgs = self._recv_all(4)
        self.assertTrue(any(m.startswith("FIRE:OFF:") for m in msgs))

    def test_target_lost_stops_and_scans(self):
        self.orchestrator._on_target_lost(dt=0.1)
        msgs = self._recv_all(4)  # fire off, track stop, turret, tilt
        self.assertIn("FIRE:OFF:0", msgs)
        self.assertIn("TRACK:STOP:0", msgs)
        self.assertTrue(any(m.startswith("TILT:STOP:") for m in msgs))

    def test_steer_body_pivots_when_off_center(self):
        # aim-assist uses pivot-turn, not skid-turn (decisions.md 2026-07-13)
        self.orchestrator._steer_body(60)
        self.assertEqual(self._recv_all(1)[0], "TRACK:PIVOT_RIGHT:120")

        self.orchestrator._steer_body(-60)
        self.assertEqual(self._recv_all(1)[0], "TRACK:PIVOT_LEFT:120")


if __name__ == "__main__":
    unittest.main()
