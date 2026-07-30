import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.logic.tracker import KalmanTracker2D


class TestKalmanTracker2D(unittest.TestCase):
    def test_smooths_noisy_linear_motion(self):
        rng = np.random.default_rng(42)
        dt = 0.05
        true_vx, true_vy = 40.0, -20.0  # px/s
        x0, y0 = 100.0, 100.0

        tracker = KalmanTracker2D(process_noise=1.0, measurement_noise=10.0)

        errors_raw = []
        errors_filtered = []

        for i in range(60):
            t = i * dt
            true_x = x0 + true_vx * t
            true_y = y0 + true_vy * t

            noisy_x = true_x + rng.normal(0, 8)
            noisy_y = true_y + rng.normal(0, 8)

            if i > 0:
                tracker.predict(dt)
            fx, fy = tracker.update(noisy_x, noisy_y)

            if i > 10:  # skip the warm-up period
                errors_raw.append(((noisy_x - true_x) ** 2 + (noisy_y - true_y) ** 2) ** 0.5)
                errors_filtered.append(((fx - true_x) ** 2 + (fy - true_y) ** 2) ** 0.5)

        avg_raw = sum(errors_raw) / len(errors_raw)
        avg_filtered = sum(errors_filtered) / len(errors_filtered)

        self.assertLess(avg_filtered, avg_raw)

    def test_velocity_estimation(self):
        dt = 0.05
        true_vx, true_vy = 40.0, -20.0
        tracker = KalmanTracker2D(process_noise=1.0, measurement_noise=5.0)

        x, y = 0.0, 0.0
        for i in range(80):
            if i > 0:
                tracker.predict(dt)
                x += true_vx * dt
                y += true_vy * dt
            tracker.update(x, y)

        vx, vy = tracker.velocity
        self.assertAlmostEqual(vx, true_vx, delta=5.0)
        self.assertAlmostEqual(vy, true_vy, delta=5.0)

    def test_predict_before_init_returns_none(self):
        tracker = KalmanTracker2D()
        self.assertIsNone(tracker.predict(0.05))


if __name__ == "__main__":
    unittest.main()
