"""Manual turret console — sends TURRET commands over UDP, nothing else.

Pan-only road test for L298N#2 channel A (one DC motor). No TRACK, TILT, or FIRE.
If the turret misbehaves here it is firmware, wiring or the motor — not the vision stack.

Use: python tests/hardware/turret_console.py --host 192.168.1.137

Wiring: hardware/pin_map.md (pan-only). Leave TILT pins (GPIO23/25/26) disconnected.

The firmware fail-safe stops all motors 500ms after the last command, so this re-sends
at ~20Hz. Windows only (msvcrt).
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

KEY_MODES = {
    "a": "LEFT",
    "d": "RIGHT",
    "j": "LEFT",
    "l": "RIGHT",
    " ": "STOP",
}

HELP = """
== Aegis-Tank turret console -- TURRET pan only ==

  A / D    LEFT / RIGHT  (J / L also work)
  +        speed +{step} (0-255)
  -        speed -{step}
  M        speed = 255
  SPACE    STOP
  F        fail-safe probe: stop transmitting for {probe}s WITHOUT sending STOP
  ESC      quit (sends TURRET:STOP:0 three times)

NOTE: keys latch. Direction keeps being re-sent until you press the other
direction or SPACE. Letting go of the key does NOT stop the motor.
Leave L298N#2 channel B (tilt) unwired. Do not connect FIRE.
"""


def read_key():
    key = None
    while msvcrt.kbhit():
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            msvcrt.getch()
            continue
        key = ch.decode("latin-1").lower()
    return key


def main():
    settings = load_settings()
    motor = settings["motor_controller"]
    ctrl = settings["control"]

    parser = argparse.ArgumentParser(description="Manual TURRET pan console for the ESP32-WROOM")
    parser.add_argument("--host", default=motor["host"], help="ESP32-WROOM IP (default: settings.yaml)")
    parser.add_argument("--port", type=int, default=motor["port"], help="UDP port (default: settings.yaml)")
    parser.add_argument("--rate", type=float, default=motor["send_rate_hz"],
                        help="resend rate in Hz — must stay above the 500ms fail-safe")
    parser.add_argument("--speed", type=int, default=ctrl["scan_speed"],
                        help="initial speed 0-255 (default: control.scan_speed)")
    args = parser.parse_args()

    if args.rate <= 2:
        parser.error(f"--rate {args.rate}Hz is slower than the 500ms fail-safe, the board would never move")

    sender = CommandSender(args.host, args.port)
    period = 1.0 / args.rate

    mode = "STOP"
    speed = max(0, min(255, args.speed))
    sent = 0
    quiet_until = 0.0

    print(HELP.format(step=SPEED_STEP, probe=FAILSAFE_PROBE_SEC))
    print(f"Target: {args.host}:{args.port} @ {args.rate:g}Hz")
    if args.host.startswith("192.0.2."):
        print("WARNING: that is the RFC 5737 placeholder from settings.yaml, not a real board.\n"
              "         Pass the IP from the board's serial boot log via --host.")
    print()

    try:
        while True:
            tick = time.time()
            key = read_key()

            if key == "\x1b":
                break
            elif key in KEY_MODES:
                mode = KEY_MODES[key]
            elif key in ("+", "="):
                speed = min(255, speed + SPEED_STEP)
            elif key in ("-", "_"):
                speed = max(0, speed - SPEED_STEP)
            elif key == "m":
                speed = 255
            elif key == "f":
                quiet_until = tick + FAILSAFE_PROBE_SEC

            if tick < quiet_until:
                remaining = quiet_until - tick
                status = f"[FAILSAFE PROBE] silent for {remaining:4.1f}s more, board should self-stop"
            else:
                sender.turret(mode, speed)
                status = f"TURRET:{mode}:{speed}"
                sent += 1

            print(f"\r{status:<70} sent={sent}", end="", flush=True)

            elapsed = time.time() - tick
            if elapsed < period:
                time.sleep(period - elapsed)
    except KeyboardInterrupt:
        pass
    finally:
        for _ in range(3):
            sender.turret("STOP", 0)
            time.sleep(0.02)
        sender.close()
        print(f"\nStopped. Sent {sent} commands + 3x TURRET:STOP:0")


if __name__ == "__main__":
    main()
