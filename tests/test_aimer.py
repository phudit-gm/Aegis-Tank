import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.logic.aimer import Aimer, PID, pixel_error_to_degrees


class TestPixelErrorToDegrees(unittest.TestCase):
    def test_center_is_zero(self):
        self.assertEqual(pixel_error_to_degrees(0, 320, 60), 0)

    def test_full_half_frame_equals_half_fov(self):
        self.assertAlmostEqual(pixel_error_to_degrees(160, 320, 60), 30.0)


class TestPID(unittest.TestCase):
    def test_converges_on_simple_feedback_loop(self):
        # ระบบจำลอง: position += pid_output ทุก step, error = setpoint - position
        pid = PID(kp=0.5, ki=0.1, kd=0.05)
        setpoint = 10.0
        position = 0.0
        dt = 0.1
        for _ in range(200):
            error = setpoint - position
            position += pid.step(error, dt) * dt
        self.assertAlmostEqual(position, setpoint, delta=0.5)


class TestAimer(unittest.TestCase):
    def _make_aimer(self):
        return Aimer(
            frame_width=320, frame_height=240, horizontal_fov_deg=60.0,
            pid_pan_gains={"kp": 1.0, "ki": 0.0, "kd": 0.0},
            pid_tilt_gains={"kp": 1.0, "ki": 0.0, "kd": 0.0},
        )

    def test_target_at_center_gives_zero_angles(self):
        aimer = self._make_aimer()
        pan, tilt = aimer.compute(160, 120, dt=0.05)
        self.assertAlmostEqual(pan, 0.0)
        self.assertAlmostEqual(tilt, 0.0)

    def test_target_right_of_center_gives_positive_pan(self):
        aimer = self._make_aimer()
        pan, _ = aimer.compute(280, 120, dt=0.05)
        self.assertGreater(pan, 0.0)

    def test_target_above_center_gives_positive_tilt(self):
        aimer = self._make_aimer()
        _, tilt = aimer.compute(160, 40, dt=0.05)
        self.assertGreater(tilt, 0.0)

    def test_angles_clamped_to_range(self):
        aimer = self._make_aimer()
        for _ in range(50):
            pan, tilt = aimer.compute(320, 0, dt=0.1)
        self.assertLessEqual(pan, 180.0)
        self.assertLessEqual(tilt, 90.0)

    def test_is_on_target(self):
        aimer = self._make_aimer()
        self.assertTrue(aimer.is_on_target(160, 120, tolerance_px=15))
        self.assertFalse(aimer.is_on_target(160, 200, tolerance_px=15))


if __name__ == "__main__":
    unittest.main()
