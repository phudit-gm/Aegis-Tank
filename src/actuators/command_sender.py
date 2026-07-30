"""Board commander — assembles commands per config/protocol_contract.yaml (v1.2, direction+speed) and sends via UDP to the ESP32-WROOM.

The clamp here is the "PC-side clamp before sending" layer per SPEC.md §1 — the receiving ESP32
must clamp again itself (authoritative) because UDP may be corrupted or come from another source.
"""

import socket

TRACK_DIRECTIONS = {
    "FORWARD", "BACKWARD", "STOP",
    "TURN_LEFT", "TURN_RIGHT",  # skid-turn — one side stops, other side drives
    "PIVOT_LEFT", "PIVOT_RIGHT",  # pivot-turn — both sides opposite directions (used during aim-assist)
}
TURRET_DIRECTIONS = {"LEFT", "RIGHT", "STOP"}
TILT_DIRECTIONS = {"DOWN", "STOP"}


class CommandSender:
    def __init__(self, host: str, port: int):
        if not host:
            raise ValueError(
                "CommandSender requires the ESP32-WROOM host — "
                "config/settings.yaml -> motor_controller.host is still null (no real board connected yet)"
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
            raise ValueError(f"direction must be one of {TRACK_DIRECTIONS}, got {direction!r}")
        speed = self._clamp(int(speed), 0, 255)
        self._send(f"TRACK:{direction}:{speed}")

    def turret(self, direction: str, speed: int):
        if direction not in TURRET_DIRECTIONS:
            raise ValueError(f"direction must be one of {TURRET_DIRECTIONS}, got {direction!r}")
        speed = self._clamp(int(speed), 0, 255)
        self._send(f"TURRET:{direction}:{speed}")

    def tilt(self, direction: str, speed: int):
        if direction not in TILT_DIRECTIONS:
            raise ValueError(f"direction must be one of {TILT_DIRECTIONS}, got {direction!r}")
        speed = self._clamp(int(speed), 0, 255)
        self._send(f"TILT:{direction}:{speed}")

    def fire(self, state: str, duration_ms: int = 0):
        if state not in ("ON", "OFF"):
            raise ValueError(f"state must be ON or OFF, got {state!r}")
        duration_ms = self._clamp(int(duration_ms), 0, 32767)
        self._send(f"FIRE:{state}:{duration_ms}")
