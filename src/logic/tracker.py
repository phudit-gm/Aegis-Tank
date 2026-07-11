"""ตัวติดตาม — Kalman filter (constant velocity) ทำตำแหน่งเป้าให้นิ่ง + ประมาณความเร็ว

ตัดสินใจ 2026-07-01: เลือก Kalman แทน centroid ธรรมดา (ปิด TODO ใน SPEC.md §4)
เหตุผล: centroid เฉยๆ ไม่กรอง noise ของตำแหน่งที่ detector รายงาน และไม่ทำนายทิศทาง
เป้าที่กำลังเคลื่อนที่ — จำเป็นสำหรับ PID ที่ต้องการ error ที่นิ่งพอจะไม่สั่นป้อมปืน
(เหตุผลเต็มอยู่ใน overview.md หัวข้อ "ทำไมต้อง Kalman filter")
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
        """เดินทำนายตำแหน่งไปข้างหน้า dt วินาที (เรียกทุกเฟรม แม้เฟรมนั้นไม่มี measurement)."""
        if not self._initialized:
            return None
        F, Q = self._transition_matrices(dt)
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q
        return self.position

    def update(self, x_meas: float, y_meas: float):
        """ผสาน measurement ใหม่เข้ากับ state — เรียกเมื่อ detector เจอเป้าในเฟรมนี้."""
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
