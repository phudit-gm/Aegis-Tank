"""Tracker — Kalman filter (constant velocity) smooths target position + estimates velocity

Decided 2026-07-01: chose Kalman over plain centroid (closes TODO in SPEC.md §4)
Reason: plain centroid doesn't filter noise in the position the detector reports, and doesn't
predict the direction of a moving target — necessary for PID which needs an error signal stable
enough to not make the turret jitter.
(Full reasoning in overview.md, section "Why Kalman filter")
"""

import numpy as np


class KalmanTracker2D:
    def __init__(self, process_noise: float = 1.0, measurement_noise: float = 10.0):
        self.process_noise = process_noise
        self._initialized = False
        self.x = np.zeros((4, 1))          # state: [x, y, vx, vy]
        self.P = np.eye(4) * 500.0

        self.H = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ])
        self.R = np.eye(2) * measurement_noise

    @property
    def initialized(self) -> bool:
        return self._initialized

    def reset(self):
        self._initialized = False
        self.x = np.zeros((4, 1))
        self.P = np.eye(4) * 500.0

    def initialize(self, x: float, y: float):
        self.x = np.array([[x], [y], [0.0], [0.0]])
        self.P = np.eye(4) * 500.0
        self._initialized = True

    def _transition_matrices(self, dt: float):
        F = np.array([
            [1.0, 0.0, dt, 0.0],
            [0.0, 1.0, 0.0, dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        q = self.process_noise
        Q = q * np.array([
            [dt**4 / 4, 0, dt**3 / 2, 0],
            [0, dt**4 / 4, 0, dt**3 / 2],
            [dt**3 / 2, 0, dt**2, 0],
            [0, dt**3 / 2, 0, dt**2],
        ])
        return F, Q

    def predict(self, dt: float):
        """Predicts position forward by dt seconds (called every frame, even if that frame has no measurement)."""
        if not self._initialized:
            return None
        F, Q = self._transition_matrices(dt)
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q
        return self.position

    def update(self, x_meas: float, y_meas: float):
        """Merges a new measurement into the state — called when the detector finds a target in this frame."""
        if not self._initialized:
            self.initialize(x_meas, y_meas)
            return self.position

        z = np.array([[x_meas], [y_meas]])
        innovation = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ innovation
        self.P = (np.eye(4) - K @ self.H) @ self.P
        return self.position

    @property
    def position(self):
        return float(self.x[0, 0]), float(self.x[1, 0])

    @property
    def velocity(self):
        return float(self.x[2, 0]), float(self.x[3, 0])
