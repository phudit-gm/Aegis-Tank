"""Manual drive console — sends TRACK commands over UDP to the ESP32-WROOM, nothing else.

Standalone road test for the drive base: no camera, no YOLO, no tracker, no PID. If the tank
misbehaves here it is the firmware, the wiring or the motors — not the vision stack.

Use: python tests/hardware/drive_console.py --host 192.168.1.42

The firmware fail-safe stops all motors 500ms after the last command
(firmware/esp32_wroom/src/main.cpp FAILSAFE_TIMEOUT_MS), so this re-sends the current command
continuously at ~20Hz. One packet only produces a twitch.

TRACK only by design — this tool cannot move the turret/tilt or arm the FIRE spring-release.
Windows only (uses msvcrt for non-blocking key input).
"""

import argparse
import msvcrt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.actuators.command_sender import CommandSender
from src.utils.config import load_settings

SPEED_STEP = 10
FAILSAFE_PROBE_SEC = 1.5

# key -> TRACK direction per config/protocol_contract.yaml (v1.3)
KEY_DIRECTIONS = {
    "w": "FORWARD",
    "s": "BACKWARD",
    "a": "TURN_LEFT",    # skid — left track stops, right track drives
    "d": "TURN_RIGHT",
    "q": "PIVOT_LEFT",   # pivot — tracks spin opposite directions
    "e": "PIVOT_RIGHT",
    " ": "STOP",
}

# ASCII only — this gets encoded to the terminal, which may not be a UTF-8 codepage
HELP = """
== Aegis-Tank drive console -- TRACK only ==

  W / S    FORWARD / BACKWARD
  A / D    TURN_LEFT / TURN_RIGHT   (skid, one track stops)
  Q / E    PIVOT_LEFT / PIVOT_RIGHT (both tracks, opposite directions)
  + / -    speed +-{step} (0-255)
  SPACE    STOP
  F        fail-safe probe: stop transmitting for {probe}s WITHOUT sending STOP
           -> the board must stop itself, look for [SAFE STATE] in the serial log
  ESC      quit (sends STOP)

NOTE: keys latch. A direction keeps being re-sent until you press another
direction or SPACE. Letting go of the key does NOT stop the tank.
"""


def read_key():
    """Return the last key pressed as a lowercase str, or None if no key is waiting.

    Drains the whole buffer so holding a key down doesn't build up a backlog that
    keeps replaying after release.
    """
    key = None
    while msvcrt.kbhit():
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):  # arrow/function key — swallow the 2-byte sequence
            msvcrt.getch()
            continue
        key = ch.decode("latin-1").lower()
    return key


def main():
    settings = load_settings()
    motor = settings["motor_controller"]

    parser = argparse.ArgumentParser(description="Manual TRACK drive console for the ESP32-WROOM")
    # settings.yaml still holds an RFC 5737 placeholder — the board's real DHCP IP comes from its boot log
    parser.add_argument("--host", default=motor["host"], help="ESP32-WROOM IP (default: settings.yaml)")
    parser.add_argument("--port", type=int, default=motor["port"], help="UDP port (default: settings.yaml)")
    parser.add_argument("--rate", type=float, default=motor["send_rate_hz"],
                        help="resend rate in Hz — must stay above the 500ms fail-safe")
    parser.add_argument("--speed", type=int, default=settings["control"]["body_turn_speed"],
                        help="initial speed 0-255")
    args = parser.parse_args()

    if args.rate <= 2:
        parser.error(f"--rate {args.rate}Hz is slower than the 500ms fail-safe, the board would never move")

    sender = CommandSender(args.host, args.port)
    period = 1.0 / args.rate

    direction = "STOP"
    speed = max(0, min(255, args.speed))
    sent = 0
    quiet_until = 0.0  # fail-safe probe: hold off transmitting until this time

    print(HELP.format(step=SPEED_STEP, probe=FAILSAFE_PROBE_SEC))
    print(f"Target: {args.host}:{args.port} @ {args.rate:g}Hz")
    if args.host.startswith("192.0.2."):
        # UDP never reports an unreachable host, so this would silently do nothing all session
        print("WARNING: that is the RFC 5737 placeholder from settings.yaml, not a real board.\n"
              "         Pass the IP from the board's serial boot log via --host.")
    print()

    try:
        while True:
            tick = time.time()
            key = read_key()

            if key == "\x1b":  # ESC
                break
            elif key in KEY_DIRECTIONS:
                direction = KEY_DIRECTIONS[key]
            elif key in ("+", "="):
                speed = min(255, speed + SPEED_STEP)
            elif key in ("-", "_"):
                speed = max(0, speed - SPEED_STEP)
            elif key == "f":
                quiet_until = tick + FAILSAFE_PROBE_SEC

            if tick < quiet_until:
                remaining = quiet_until - tick
                status = f"[FAILSAFE PROBE] silent for {remaining:4.1f}s more, board should self-stop"
            else:
                sender.track(direction, speed)
                sent += 1
                status = f"TRACK:{direction}:{speed}"

            print(f"\r{status:<70} sent={sent}", end="", flush=True)

            elapsed = time.time() - tick
            if elapsed < period:
                time.sleep(period - elapsed)
    except KeyboardInterrupt:
        pass
    finally:
        # UDP is lossy and a dropped stop leaves the tank driving — send it three times.
        # The 500ms fail-safe is the backstop, not the plan.
        for _ in range(3):
            sender.track("STOP", 0)
            time.sleep(0.02)
        sender.close()
        print(f"\nStopped. Sent {sent} commands + 3x TRACK:STOP:0")


if __name__ == "__main__":
    main()
