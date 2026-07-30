"""Aimer — converts pixel error -> degree error (SPEC.md §2), then runs it through PID to get (direction, speed) motor commands for this cycle

No absolute angle anymore (real hardware has no angle sensor — see decisions.md) —
PID works on per-cycle pixel error (visual servoing), then output effort is converted directly to direction+speed.

Sign convention:
  pan  error > 0  -> target is right of image center -> command TURRET RIGHT
  tilt error > 0  -> target is below image center (larger y pixel) -> command TILT DOWN
  tilt error < 0  -> target is above image center -> no up-tilt command possible -> command STOP (let the return spring work)
"""

from collections import namedtuple

AimCommand = namedtuple("AimCommand", ["pan_direction", "pan_speed", "tilt_direction", "tilt_speed", "pan_error_deg"])


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
    """Formula per SPEC.md §2: degrees = (pixel_error / frame_width_px) x horizontal_FOV_degrees"""
    return (pixel_error / frame_dimension_px) * fov_degrees


class Aimer:
    def __init__(self, frame_width: int, frame_height: int, horizontal_fov_deg: float,
                 pid_pan_gains: dict, pid_tilt_gains: dict, vertical_fov_deg: float = None,
                 max_speed: int = 255):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.horizontal_fov_deg = horizontal_fov_deg
        # TODO: vertical FOV not yet calibrated for real — estimated from frame ratio times horizontal FOV
        self.vertical_fov_deg = vertical_fov_deg or (horizontal_fov_deg * frame_height / frame_width)
        self.max_speed = max_speed

        self.pid_pan = PID(**pid_pan_gains)
        self.pid_tilt = PID(**pid_tilt_gains)

    def reset(self):
        self.pid_pan.reset()
        self.pid_tilt.reset()

    def pixel_error(self, target_x: float, target_y: float):
        center_x = self.frame_width / 2
        center_y = self.frame_height / 2
        return target_x - center_x, target_y - center_y

    def is_on_target(self, target_x: float, target_y: float, tolerance_px: float) -> bool:
        ex, ey = self.pixel_error(target_x, target_y)
        return (ex ** 2 + ey ** 2) ** 0.5 <= tolerance_px

    def _effort_to_speed(self, effort: float) -> int:
        return int(round(min(abs(effort), self.max_speed)))

    def compute(self, target_x: float, target_y: float, dt: float) -> AimCommand:
        """Returns an AimCommand (direction+speed motor command for this cycle, per protocol_contract.yaml v1.2)"""
        error_x_px, error_y_px = self.pixel_error(target_x, target_y)

        pan_error_deg = pixel_error_to_degrees(error_x_px, self.frame_width, self.horizontal_fov_deg)
        tilt_error_deg = pixel_error_to_degrees(error_y_px, self.frame_height, self.vertical_fov_deg)

        pan_effort = self.pid_pan.step(pan_error_deg, dt)
        tilt_effort = self.pid_tilt.step(tilt_error_deg, dt)

        pan_speed = self._effort_to_speed(pan_effort)
        pan_direction = "STOP" if pan_speed == 0 else ("RIGHT" if pan_effort > 0 else "LEFT")

        if tilt_effort <= 0:
            # error direction is upward -> no up-tilt motor command possible (SPEC.md §2) -> STOP and let the return spring work
            tilt_direction, tilt_speed = "STOP", 0
        else:
            tilt_speed = self._effort_to_speed(tilt_effort)
            tilt_direction = "STOP" if tilt_speed == 0 else "DOWN"

        return AimCommand(pan_direction, pan_speed, tilt_direction, tilt_speed, pan_error_deg)
