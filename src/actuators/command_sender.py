"""ตัวสั่งบอร์ด — ประกอบคำสั่งตาม config/protocol_contract.yaml (v1.2, direction+speed) แล้วส่งผ่าน UDP ไป ESP32-WROOM.

Clamp ที่นี่คือชั้น "PC clamp ก่อนส่ง" ตาม SPEC.md §1 — ESP32 ฝั่งรับต้อง clamp ซ้ำเองอีกชั้น (authoritative)
เพราะ UDP อาจ corrupt หรือมาจากแหล่งอื่น
"""

import socket

TRACK_DIRECTIONS = {
    "FORWARD", "BACKWARD", "STOP",
    "TURN_LEFT", "TURN_RIGHT",  # skid-turn — ข้างหนึ่งหยุด อีกข้างขับ
    "PIVOT_LEFT", "PIVOT_RIGHT",  # pivot-turn — สองข้างสวนทางกัน (ใช้ตอน aim-assist)
}
TURRET_DIRECTIONS = {"LEFT", "RIGHT", "STOP"}
TILT_DIRECTIONS = {"DOWN", "STOP"}


class CommandSender:
    def __init__(self, host: str, port: int):
        if not host:
            raise ValueError(
                "CommandSender ต้องการ host ของ ESP32-WROOM — "
                "config/settings.yaml -> motor_controller.host ยังเป็น null (ยังไม่มีบอร์ดต่อจริง)"
            )
        self.host = host
        self.port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def close(self):
        self._sock.close()

    def _send(self, message: str):
        self._sock.sendto(message.encode("utf-8"), (self.host, self.port))

    @staticmethod
    def _clamp(value, lo, hi):
        return max(lo, min(hi, value))

    def track(self, direction: str, speed: int):
        if direction not in TRACK_DIRECTIONS:
            raise ValueError(f"direction ต้องเป็นหนึ่งใน {TRACK_DIRECTIONS}, ได้ {direction!r}")
        speed = self._clamp(int(speed), 0, 255)
        self._send(f"TRACK:{direction}:{speed}")

    def turret(self, direction: str, speed: int):
        if direction not in TURRET_DIRECTIONS:
            raise ValueError(f"direction ต้องเป็นหนึ่งใน {TURRET_DIRECTIONS}, ได้ {direction!r}")
        speed = self._clamp(int(speed), 0, 255)
        self._send(f"TURRET:{direction}:{speed}")

    def tilt(self, direction: str, speed: int):
        if direction not in TILT_DIRECTIONS:
            raise ValueError(f"direction ต้องเป็นหนึ่งใน {TILT_DIRECTIONS}, ได้ {direction!r}")
        speed = self._clamp(int(speed), 0, 255)
        self._send(f"TILT:{direction}:{speed}")

    def fire(self, state: str, duration_ms: int = 0):
        if state not in ("ON", "OFF"):
            raise ValueError(f"state ต้องเป็น ON หรือ OFF, ได้ {state!r}")
        duration_ms = self._clamp(int(duration_ms), 0, 32767)
        self._send(f"FIRE:{state}:{duration_ms}")
