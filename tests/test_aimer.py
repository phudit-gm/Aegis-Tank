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

    def test_target_at_center_gives_stop(self):
        aimer = self._make_aimer()
        aim = aimer.compute(160, 120, dt=0.05)
        self.assertEqual(aim.pan_direction, "STOP")
        self.assertEqual(aim.pan_speed, 0)
        self.assertEqual(aim.tilt_direction, "STOP")
        self.assertEqual(aim.tilt_speed, 0)

    def test_target_right_of_center_turns_turret_right(self):
        aimer = self._make_aimer()
        aim = aimer.compute(280, 120, dt=0.05)
        self.assertEqual(aim.pan_direction, "RIGHT")
        self.assertGreater(aim.pan_speed, 0)

    def test_target_left_of_center_turns_turret_left(self):
        aimer = self._make_aimer()
        aim = aimer.compute(40, 120, dt=0.05)
        self.assertEqual(aim.pan_direction, "LEFT")
        self.assertGreater(aim.pan_speed, 0)

    def test_target_below_center_tilts_down(self):
        aimer = self._make_aimer()
        aim = aimer.compute(160, 200, dt=0.05)
        self.assertEqual(aim.tilt_direction, "DOWN")
        self.assertGreater(aim.tilt_speed, 0)

    def test_target_above_center_cannot_tilt_up_so_stops(self):
        # ไม่มีคำสั่งมอเตอร์เงยขึ้นได้ (SPEC.md §2) -> ต้อง STOP ไม่ใช่ค่าติดลบ/UP
        aimer = self._make_aimer()
        aim = aimer.compute(160, 40, dt=0.05)
        self.assertEqual(aim.tilt_direction, "STOP")
        self.assertEqual(aim.tilt_speed, 0)

    def test_speed_clamped_to_max(self):
        aimer = self._make_aimer()
        aim = aimer.compute(320, 240, dt=0.1)
        self.assertLessEqual(aim.pan_speed, 255)
        self.assertLessEqual(aim.tilt_speed, 255)

    def test_is_on_target(self):
        aimer = self._make_aimer()
        self.assertTrue(aimer.is_on_target(160, 120, tolerance_px=15))
        self.assertFalse(aimer.is_on_target(160, 200, tolerance_px=15))


if __name__ == "__main__":
    unittest.main()
