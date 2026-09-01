"""Guided TRACK speed limits — PWM deadband (min) then 255 (max), wheels off the ground.

The board has no wheel sensor and the bench PSU is not on the network, so this script holds
a command over UDP and asks you to look at the tracks / PSU. It does not change settings.yaml.

Use: python tests/hardware/speed_limits.py --host 192.168.1.129

Stage 2 only (blocks). Do not run this on the ground.
Windows-friendly (same CommandSender path as drive_console.py). No extra dependencies.
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.actuators.command_sender import CommandSender
from src.utils.config import load_settings

SPEED_STEP = 10
MAX_SPEED = 255

# Skid turns isolate one track (firmware handleTrack):
#   TURN_RIGHT -> left drives, right coast
#   TURN_LEFT  -> right drives, left coast
DEADBAND_SIDES = (
    ("LEFT", "TURN_RIGHT"),
    ("RIGHT", "TURN_LEFT"),
)

MAX_SPEED_MODES = ("FORWARD", "PIVOT_LEFT", "PIVOT_RIGHT")

PREFLIGHT = """
== Aegis-Tank speed limits (deadband + 255) ==

WHEELS OFF THE GROUND. PSU current limit 3A. No USB + VIN together.
FIRE / GPIO27 disconnected. You watch the tracks; the script only holds UDP.

  1) Deadband (MIN): walk PWM down until the track STOPS. You are looking at
     motion vs no-motion. Record = last value that still moved.
  2) Max is NOT another hunt. 255 is already the protocol ceiling (8-bit PWM).
     You do not keep going until something "maxes out". You hold 255 and watch:
       - did the wheel spin clearly faster than at 120?
       - PSU amps JUMP on the first takeoff from rest, then the settled value
       - did the PSU flip to C.C. (current-limit)? if yes, STOP
       - noise / grinding / smoke — STOP
     Wheels-up cannot give m/s or km/h (no encoder). That is a later ground test.

Ctrl+C aborts and sends STOP.
"""


class DriveHold:
    """Keep the fail-safe happy while the main thread waits for you to type."""

    def __init__(self, sender: CommandSender, rate_hz: float):
        self._sender = sender
        self._period = 1.0 / rate_hz
        self._lock = threading.Lock()
        self.direction = "STOP"
        self.speed = 0
        self._run = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def set(self, direction: str, speed: int) -> None:
        with self._lock:
            self.direction = direction
            self.speed = speed

    def coast(self) -> None:
        self.set("STOP", 0)

    def _loop(self) -> None:
        while self._run:
            with self._lock:
                direction, speed = self.direction, self.speed
            self._sender.track(direction, speed)
            time.sleep(self._period)

    def close(self) -> None:
        self._run = False
        self._thread.join(timeout=1.5)
        for _ in range(3):
            self._sender.track("STOP", 0)
            time.sleep(0.02)


def ask(prompt: str) -> str:
    return input(prompt).strip()


def ask_yes_no(prompt: str) -> bool:
    while True:
        raw = ask(prompt + " [y/n] ").lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  type y or n")


def ask_amps(prompt: str) -> str:
    raw = ask(prompt + " (amps, or Enter to skip): ")
    return raw if raw else "(not recorded)"


def deadband_one_side(hold: DriveHold, side: str, command: str, start: int) -> int | None:
    print(f"\n-- deadband {side} track ({command}, other track coasts) --")
    print("  look at THAT track only")
    hold.set(command, start)
    time.sleep(0.4)
    if not ask_yes_no(f"  {side} moving at speed {start}?"):
        hold.coast()
        print(f"  not moving at {start} — rerun with --start higher (try 180 or 220)")
        return None

    last_moving = start
    speed = start - SPEED_STEP
    while speed >= SPEED_STEP:
        hold.set(command, speed)
        time.sleep(0.4)
        if ask_yes_no(f"  {side} STILL moving at speed {speed}?"):
            last_moving = speed
            speed -= SPEED_STEP
            continue
        hold.coast()
        print(f"  {side} deadband = {last_moving} (last PWM that still moved)")
        return last_moving

    hold.coast()
    print(f"  {side} still moving at {SPEED_STEP} — deadband <= {SPEED_STEP}")
    return SPEED_STEP


def max_speed_one_mode(hold: DriveHold, direction: str) -> str:
    print(f"\n-- max PWM {direction} @ {MAX_SPEED} (from rest) --")
    print("  this is the ceiling, not a search. compare spin to the 120 you already know.")
    print("  PSU amps: type the HIGHEST number you see on takeoff, then the number it settles at.")
    print("  Do not type the lowest. The display is already an average, not a true peak-hold.")
    print("  C.C. / smoke = abort.")
    hold.coast()
    time.sleep(0.8)
    input("  Enter = slam to 255 now  ")
    hold.set(direction, MAX_SPEED)
    peak = ask_amps("  HIGHEST amps you saw on takeoff")
    run = ask_amps("  amps after it settles (steady)")
    hold.coast()
    time.sleep(0.3)
    return f"peak={peak}  running={run}"


def print_summary(deadband: dict[str, int | None], max_rows: dict[str, str]) -> None:
    print("\n========== copy into handoff/current-task.md ==========")
    print("PWM deadband (wheels up, step=10):")
    for side, value in deadband.items():
        print(f"  {side:5}  {value if value is not None else 'NOT MEASURED'}")
    measured = [v for v in deadband.values() if isinstance(v, int)]
    if measured:
        print(f"  body_turn_speed must stay ABOVE {max(measured)} (do not edit yaml until the session ends)")
    print(f"Current @ speed {MAX_SPEED} (wheels up, PSU display):")
    for mode, row in max_rows.items():
        print(f"  {mode:12}  {row}")
    print("=======================================================\n")


def main() -> None:
    settings = load_settings()
    motor = settings["motor_controller"]

    parser = argparse.ArgumentParser(description="TRACK PWM deadband + speed 255, wheels up")
    parser.add_argument("--host", default=motor["host"], help="ESP32-WROOM IP")
    parser.add_argument("--port", type=int, default=motor["port"])
    parser.add_argument("--rate", type=float, default=motor["send_rate_hz"],
                        help="resend Hz — must stay above the 500ms fail-safe")
    parser.add_argument("--start", type=int, default=settings["control"]["body_turn_speed"],
                        help="deadband sweep start (default: body_turn_speed, currently 120)")
    parser.add_argument("--max-only", action="store_true",
                        help="skip deadband; only record PSU amps at speed 255")
    args = parser.parse_args()

    if args.rate <= 2:
        parser.error(f"--rate {args.rate}Hz is slower than the 500ms fail-safe")
    start = max(SPEED_STEP, min(MAX_SPEED, args.start))

    print(PREFLIGHT)
    extra = "  max-only" if args.max_only else f"  deadband start={start}"
    print(f"Target: {args.host}:{args.port} @ {args.rate:g}Hz{extra}")
    if args.host.startswith("192.0.2."):
        print("WARNING: RFC 5737 placeholder from settings.yaml — pass the real board IP via --host.")
        return
    if not ask_yes_no("Wheels are OFF the ground and PSU limit is 3A?"):
        print("Aborted.")
        return

    sender = CommandSender(args.host, args.port)
    hold = DriveHold(sender, args.rate)
    deadband: dict[str, int | None] = {}
    max_rows: dict[str, str] = {}
    try:
        if args.max_only:
            print("Skipping deadband (--max-only). Last measured: LEFT/RIGHT = 60.")
        else:
            for side, command in DEADBAND_SIDES:
                deadband[side] = deadband_one_side(hold, side, command, start)

        if args.max_only or ask_yes_no("\nStill on blocks? Continue to speed 255?"):
            for direction in MAX_SPEED_MODES:
                max_rows[direction] = max_speed_one_mode(hold, direction)
        else:
            print("Skipped max-speed block.")
    except KeyboardInterrupt:
        print("\nAborted.")
    finally:
        hold.close()
        sender.close()

    print_summary(deadband, max_rows)


if __name__ == "__main__":
    main()
