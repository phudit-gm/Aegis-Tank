"""ตัวคุมหลัก (orchestrator) — วน main loop ตาม AGENTS.md:
รับภาพ -> ตรวจจับ+ติดตาม -> ถ้าเจอเป้า: เล็ง+หันตัวรถ+ยิง / ถ้าไม่เจอ: กวาดหาเป้า -> รอ dt คงที่ -> วนใหม่

รันด้วย: python -m src.main
ต้องมี ESP32-CAM และ ESP32-WROOM ต่ออยู่จริงตาม config/settings.yaml (motor_controller.host ต้องไม่ใช่ null)
"""

import time

from src.actuators.command_sender import CommandSender
from src.logic.aimer import Aimer
from src.logic.tracker import KalmanTracker2D
from src.utils.config import load_settings
from src.vision.detector import Detector
from src.vision.frame_receiver import FrameReceiver


class ScanPattern:
    """กวาดป้อมซ้าย-ขวาระหว่างไม่เจอเป้า (AGENTS.md main loop ข้อ 4)

    ไม่มีเซนเซอร์วัดมุม — ใช้มุมเสมือน (dead-reckoning โดยประมาณจาก step_deg_per_sec)
    แค่กำหนดจังหวะสลับทิศ ไม่ใช่ตำแหน่งจริง
    """

    def __init__(self, limit_deg: float, step_deg_per_sec: float, speed: int):
        self.limit_deg = limit_deg
        self.step_deg_per_sec = step_deg_per_sec
        self.speed = speed
        self._virtual_angle = 0.0
        self._direction = "RIGHT"

    def reset(self):
        self._virtual_angle = 0.0
        self._direction = "RIGHT"

    def step(self, dt: float):
        sign = 1 if self._direction == "RIGHT" else -1
        self._virtual_angle += sign * self.step_deg_per_sec * dt
        if self._virtual_angle >= self.limit_deg:
            self._virtual_angle = self.limit_deg
            self._direction = "LEFT"
        elif self._virtual_angle <= -self.limit_deg:
            self._virtual_angle = -self.limit_deg
            self._direction = "RIGHT"
        return self._direction, self.speed


class Orchestrator:
    def __init__(self, settings: dict):
        cam = settings["camera"]
        self.frame_receiver = FrameReceiver(cam["stream_url"])

        det = settings["detection"]
        self.detector = Detector(det["model_path"], det["target_class"], det["conf_threshold"])

        trk = settings["tracking"]
        self.tracker = KalmanTracker2D(trk["process_noise"], trk["measurement_noise"])

        aim = settings["aiming"]
        self.aimer = Aimer(
            frame_width=cam["frame_width"], frame_height=cam["frame_height"],
            horizontal_fov_deg=cam["horizontal_fov_deg"],
            pid_pan_gains=aim["pid_pan"], pid_tilt_gains=aim["pid_tilt"],
        )
        self.aim_tolerance_px = aim["aim_tolerance_px"]

        mc = settings["motor_controller"]
        self.command_sender = CommandSender(mc["host"], mc["port"])

        ctrl = settings.get("control", {})
        self.body_turn_threshold_deg = ctrl.get("body_turn_threshold_deg", 45)
        self.body_turn_speed = ctrl.get("body_turn_speed", 120)
        self.fire_burst_ms = ctrl.get("fire_burst_ms", 500)
        self.scan = ScanPattern(
            ctrl.get("scan_sweep_limit_deg", 60),
            ctrl.get("scan_step_deg_per_sec", 30),
            ctrl.get("scan_speed", 120),
        )

        self.dt = 1.0 / settings["loop"]["frequency_hz"]

    def _steer_body(self, pan_error_deg: float):
        """เป้าเบี่ยงจากกลางภาพเกิน threshold -> หันตัวรถทั้งคันช่วยป้อม (AGENTS.md main loop ข้อ 3)

        ใช้ pivot-turn (ล้อสองข้างสวนทางกัน) ไม่ใช่ skid-turn — เพราะเป็นสถานการณ์ aim-assist
        (ตั้งป้อม/พื้นที่แคบ) ต้องการความแม่นยำ ไม่อยากให้ตำแหน่งรถเลื่อนมากเท่า skid (decisions.md)
        """
        if pan_error_deg > self.body_turn_threshold_deg:
            self.command_sender.track("PIVOT_RIGHT", self.body_turn_speed)
        elif pan_error_deg < -self.body_turn_threshold_deg:
            self.command_sender.track("PIVOT_LEFT", self.body_turn_speed)
        else:
            self.command_sender.track("STOP", 0)

    def _on_target_found(self, detection, dt: float):
        self.tracker.update(detection.x, detection.y)
        smooth_x, smooth_y = self.tracker.position

        aim = self.aimer.compute(smooth_x, smooth_y, dt)
        self.command_sender.turret(aim.pan_direction, aim.pan_speed)
        self.command_sender.tilt(aim.tilt_direction, aim.tilt_speed)
        self._steer_body(aim.pan_error_deg)

        if self.aimer.is_on_target(smooth_x, smooth_y, self.aim_tolerance_px):
            self.command_sender.fire("ON", self.fire_burst_ms)
        else:
            self.command_sender.fire("OFF", 0)

    def _on_target_lost(self, dt: float):
        self.tracker.reset()
        self.aimer.reset()
        self.command_sender.fire("OFF", 0)
        self.command_sender.track("STOP", 0)
        scan_direction, scan_speed = self.scan.step(dt)
        self.command_sender.turret(scan_direction, scan_speed)
        self.command_sender.tilt("STOP", 0)

    def run(self):
        print("Aegis-Tank orchestrator starting...")
        for frame in self.frame_receiver.frames():
            loop_start = time.time()

            detection = self.detector.detect(frame)
            if detection is not None:
                self._on_target_found(detection, self.dt)
            else:
                self._on_target_lost(self.dt)

            elapsed = time.time() - loop_start
            sleep_time = self.dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def close(self):
        self.frame_receiver.close()
        self.command_sender.close()


def main():
    settings = load_settings()
    orchestrator = Orchestrator(settings)
    try:
        orchestrator.run()
    except KeyboardInterrupt:
        print("Stopped by user")
    finally:
        orchestrator.close()


if __name__ == "__main__":
    main()
