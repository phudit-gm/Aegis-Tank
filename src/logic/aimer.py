"""ตัวเล็ง — แปลง error พิกเซล -> องศา (SPEC.md §2) แล้วผ่าน PID ให้ได้มุมสั่งหันนุ่มนวล (SPEC.md §3.1)

Sign convention (ตาม config/protocol_contract.yaml):
  pan  : -180=ซ้ายสุด, 0=กลาง, +180=ขวาสุด  -> เป้าอยู่ขวาของกลางภาพ = pan error เป็นบวก
  tilt : -90=ลง, 0=ระดับ, +90=ขึ้น          -> เป้าอยู่เหนือกลางภาพ (y พิกเซลน้อยกว่า) = tilt error เป็นบวก
"""


class PID:
    def __init__(self, kp: float, ki: float, kd: float):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self._integral = 0.0
        self._prev_error = None

    def reset(self):
        self._integral = 0.0
        self._prev_error = None

    def step(self, error: float, dt: float) -> float:
        self._integral += error * dt
        derivative = 0.0 if self._prev_error is None or dt <= 0 else (error - self._prev_error) / dt
        self._prev_error = error
        return self.kp * error + self.ki * self._integral + self.kd * derivative


def pixel_error_to_degrees(pixel_error: float, frame_dimension_px: int, fov_degrees: float) -> float:
    """สูตรตาม SPEC.md §2: องศา = (pixel_error / frame_width_px) x horizontal_FOV_degrees"""
    return (pixel_error / frame_dimension_px) * fov_degrees


class Aimer:
    def __init__(self, frame_width: int, frame_height: int, horizontal_fov_deg: float,
                 pid_pan_gains: dict, pid_tilt_gains: dict, vertical_fov_deg: float = None):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.horizontal_fov_deg = horizontal_fov_deg
        # TODO: ยังไม่ calibrate vertical FOV จริง — ประมาณจากสัดส่วนเฟรมคูณ horizontal FOV
        self.vertical_fov_deg = vertical_fov_deg or (horizontal_fov_deg * frame_height / frame_width)

        self.pid_pan = PID(**pid_pan_gains)
        self.pid_tilt = PID(**pid_tilt_gains)

        self.current_pan = 0.0
        self.current_tilt = 0.0

    def reset(self):
        self.pid_pan.reset()
        self.pid_tilt.reset()
        self.current_pan = 0.0
        self.current_tilt = 0.0

    def pixel_error(self, target_x: float, target_y: float):
        center_x = self.frame_width / 2
        center_y = self.frame_height / 2
        return target_x - center_x, target_y - center_y

    def is_on_target(self, target_x: float, target_y: float, tolerance_px: float) -> bool:
        ex, ey = self.pixel_error(target_x, target_y)
        return (ex ** 2 + ey ** 2) ** 0.5 <= tolerance_px

    def compute(self, target_x: float, target_y: float, dt: float):
        """คืนค่า (pan_angle, tilt_angle) องศาสะสมที่ควรสั่งหันตอนนี้ (absolute, clamp แล้ว)"""
        error_x_px, error_y_px = self.pixel_error(target_x, target_y)

        pan_error_deg = pixel_error_to_degrees(error_x_px, self.frame_width, self.horizontal_fov_deg)
        tilt_error_deg = pixel_error_to_degrees(error_y_px, self.frame_height, self.vertical_fov_deg)

        pan_delta = self.pid_pan.step(pan_error_deg, dt)
        tilt_delta = self.pid_tilt.step(-tilt_error_deg, dt)  # y พิกเซลมากขึ้น = ลงต่ำ -> กลับเครื่องหมายให้ + คือขึ้น

        self.current_pan = max(-180.0, min(180.0, self.current_pan + pan_delta))
        self.current_tilt = max(-90.0, min(90.0, self.current_tilt + tilt_delta))

        return self.current_pan, self.current_tilt
