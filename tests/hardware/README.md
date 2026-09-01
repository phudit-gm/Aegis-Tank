# Hardware tests — real board required

These are **manual** tests. They need a real ESP32-WROOM powered on and reachable over WiFi, so they
are never collected by `pytest` (the files here deliberately match neither `test_*.py` nor `*_test.py`).
The automated unit tests live one level up in `tests/`.

## `speed_limits.py` — PWM deadband + speed 255 (wheels up)

Guided walkthrough for characterization items 1–2. Holds `TRACK:` over UDP while you watch the
tracks and the PSU; it cannot see motion or read the supply. Does not write `settings.yaml`.

```
python tests/hardware/speed_limits.py --host 192.168.1.129
```

`--start` defaults to `control.body_turn_speed` (120). If a track is already dead at that PWM, rerun
with `--start 180` (or 220). Left track is isolated with `TURN_RIGHT`, right with `TURN_LEFT`.
`--max-only` skips deadband and only records PSU amps at speed 255. On takeoff type the **highest**
amps you see; after it settles type the steady number. Do not type the lowest. The PSU display is
already an average, not a true peak-hold.

## `turret_console.py` — TURRET pan console (one motor)

Sends `TURRET:` only. Wire L298N#2 channel A per `hardware/pin_map.md` (pan-only). Do not connect tilt or FIRE.

```
python tests/hardware/turret_console.py --host 192.168.1.137
```

| Key | Action |
|---|---|
| `A` / `D` (or `J` / `L`) | `LEFT` / `RIGHT` |
| `+` / `-` | speed ±10 (0-255) |
| `M` | speed = 255 |
| `SPACE` | `STOP` |
| `F` | fail-safe probe — silent 1.5s, no STOP packet |
| `ESC` | quit (`TURRET:STOP:0` three times) |

Default speed is `control.scan_speed` (120). Keys latch like the drive console. Serial should show `[TURRET] LEFT speed=...` (or RIGHT). Firmware already implements this — no re-flash needed if v1.4 MIX is already on the board.

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
| `A` / `D` | `PIVOT_LEFT` / `PIVOT_RIGHT` — in-place, tracks opposite |
| `Q` / `E` | curve left / right — `TRACK:MIX` (inner wheel slower, both forward) |
| `+` | speed +10 (0-255) |
| `M` | speed = 255 |
| `SPACE` | `STOP` |
| `F` | fail-safe probe — stops transmitting for 1.5s *without* sending STOP |
| `ESC` | quit (sends `TRACK:STOP:0` three times) |

Q/E need firmware **protocol v1.4** (`handleTrackMix`). Skid `TURN_*` is still on the board; this console no longer maps keys to it (`speed_limits.py` still uses `TURN_*` for deadband). Inner-wheel PWM is `speed * control.curve_inner_ratio` (0.2 — lower = tighter turn). Inner may sit below the measured deadband (~60) so that side crawls or stalls; that is intentional so Q/E actually yaw.

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
