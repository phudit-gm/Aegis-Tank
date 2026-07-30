# Hardware tests — real board required

These are **manual** tests. They need a real ESP32-WROOM powered on and reachable over WiFi, so they
are never collected by `pytest` (the files here deliberately match neither `test_*.py` nor `*_test.py`).
The automated unit tests live one level up in `tests/`.

## `drive_console.py` — TRACK drive console

Sends `TRACK:` commands over UDP and nothing else. No camera, no YOLO, no tracker, no PID — so a
motor-polarity problem cannot be confused with a detection problem. TURRET, TILT and FIRE are
deliberately not implemented here.

```
python tests/hardware/drive_console.py --host 192.168.1.42
```

| Key | Action |
|---|---|
| `W` / `S` | `FORWARD` / `BACKWARD` |
| `A` / `D` | `TURN_LEFT` / `TURN_RIGHT` — skid turn, one track stops |
| `Q` / `E` | `PIVOT_LEFT` / `PIVOT_RIGHT` — both tracks, opposite directions |
| `+` / `-` | speed ±10 (0-255) |
| `SPACE` | `STOP` |
| `F` | fail-safe probe — stops transmitting for 1.5s *without* sending STOP |
| `ESC` | quit (sends `TRACK:STOP:0` three times) |

**Keys latch.** A direction keeps being re-sent until you press another direction or SPACE. Releasing
the key does *not* stop the tank — `msvcrt` reports key presses, not releases. Keep a finger on SPACE.

**Why it transmits continuously:** the firmware stops all motors 500ms after the last command
(`FAILSAFE_TIMEOUT_MS` in `firmware/esp32_wroom/src/main.cpp`). One packet gives a twitch, not motion.
The console re-sends at 20Hz by default, matching `config/settings.yaml motor_controller.send_rate_hz`.

## Pre-flight checklist

- [ ] `firmware/esp32_wroom/include/secrets.h` holds real `WIFI_SSID` / `WIFI_PASS`
- [ ] Firmware flashed — `pio run -t upload -e esp32wroom` in `firmware/esp32_wroom` (COM5)
- [ ] Board IP read from the serial boot log, passed via `--host`
      (`config/settings.yaml` still holds the RFC 5737 placeholder `192.0.2.11`)
- [ ] **FIRE / GPIO27 disconnected** — no reason to have a spring-release armed during a drive test
- [ ] L298Ns on their own battery with a common ground to the ESP32, **not** USB power
      (see `hardware/pin_map.md`)
- [ ] Stage 2 onward: tank up on blocks, wheels clear of the bench

## Staged procedure

**Stage 1 — bench, no motors.** ESP32 on USB only, L298Ns unpowered. Watch the serial monitor while
driving the console. Confirms: WiFi + UDP path works, every key produces the matching `[TRACK] ...`
line, malformed input is rejected. Press `F` and confirm `[SAFE STATE] track stop / turret stop /
tilt stop / fire off` appears within 500ms — the fail-safe proven before anything can move.

**Stage 2 — motors on blocks.** L298Ns on battery, wheels off the ground. Confirms:
- Each of the 7 directions turns the right tracks the right way. `forward=true → INA HIGH` in
  `driveChannel()` is an assumption; a reversed motor makes `FORWARD` drive one track backward and
  turns `PIVOT_*` into a skid.
- The PWM deadband — walk the speed down with `-` until the tracks stall. Below that value the board
  is drawing current and not moving.

**Stage 3 — on the ground.** Confirms skid vs pivot behave differently in practice, and that STOP
coasts rather than brakes (`speed==0` drives both IN pins LOW — the tank rolls on).

## Feed the results back

- Measured deadband → raise `config/settings.yaml control.body_turn_speed` above it (currently `120`,
  an untested guess).
- Motor wired backwards → fix the wiring, or flip the `forward` argument at the call site in
  `handleTrack()` (`firmware/esp32_wroom/src/main.cpp`). Prefer fixing the wiring.
- Record the board's real IP somewhere durable — a DHCP reservation on the router is the real fix.
