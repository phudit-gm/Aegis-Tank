"""ตัวคุมหลัก (orchestrator) — วน main loop ตาม AGENTS.md:
รับภาพ -> ตรวจจับ+ติดตาม -> ถ้าเจอเป้า: เล็ง+หันตัวรถ+ยิงเลเซอร์ / ถ้าไม่เจอ: กวาดหาเป้า -> รอ dt คงที่ -> วนใหม่

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
    """กวาดป้อมซ้าย-ขวาระหว่างไม่เจอเป้า (AGENTS.md main loop ข้อ 4)"""

    def __init__(self, limit_deg: float, step_deg_per_sec: float):
        self.limit_deg = limit_deg
        self.step_deg_per_sec = step_deg_per_sec
        self.angle = 0.0
        self.direction = 1

    def step(self, dt: float) -> float:
        self.angle += self.direction * self.step_deg_per_sec * dt
        if self.angle >= self.limit_deg:
            self.angle = self.limit_deg
            self.direction = -1
        elif self.angle <= -self.limit_deg:
            self.angle = -self.limit_deg
            self.direction = 1
        return self.angle


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
        self.laser_burst_ms = ctrl.get("laser_burst_ms", 500)
        self.scan = ScanPattern(
            ctrl.get("scan_sweep_limit_deg", 60),
            ctrl.get("scan_step_deg_per_sec", 30),
        )

        self.dt = 1.0 / settings["loop"]["frequency_hz"]

    def _steer_body(self, pan_angle: float):
        if pan_angle > self.body_turn_threshold_deg:
            self.command_sender.track("TURN_RIGHT", self.body_turn_speed)
        elif pan_angle < -self.body_turn_threshold_deg:
            self.command_sender.track("TURN_LEFT", self.body_turn_speed)
        else:
            self.command_sender.track("STOP", 0)

    def _on_target_found(self, detection, dt: float):
        self.tracker.update(detection.x, detection.y)
        smooth_x, smooth_y = self.tracker.position

        pan_angle, tilt_angle = self.aimer.compute(smooth_x, smooth_y, dt)
        self.command_sender.turret(pan_angle)
        self.command_sender.tilt(tilt_angle)
        self._steer_body(pan_angle)

        if self.aimer.is_on_target(smooth_x, smooth_y, self.aim_tolerance_px):
            self.command_sender.laser("ON", self.laser_burst_ms)
        else:
            self.command_sender.laser("OFF", 0)

    def _on_target_lost(self, dt: float):
        self.tracker.reset()
        self.aimer.reset()
        self.command_sender.laser("OFF", 0)
        self.command_sender.track("STOP", 0)
        scan_angle = self.scan.step(dt)
        self.command_sender.turret(scan_angle)
        self.command_sender.tilt(0)

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
