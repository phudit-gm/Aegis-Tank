# Handoff Archive — Closed work / history

> Moved out of `handoff/current-task.md` (2026-07-14) so current-task.md only holds current status + next tasks
> This file holds a history log of closed-out work — no need to read it before starting new work (always read `handoff/current-task.md` first)

---

## ✅ Updated the code to match protocol v1.2 (2026-07-13) — summary of changes

- `src/logic/aimer.py`: `compute()` now returns `AimCommand(pan_direction, pan_speed, tilt_direction, tilt_speed, pan_error_deg)` instead of an absolute angle — no more `current_pan`/`current_tilt` accumulator or the old -180..180/-90..90 clamp; an upward tilt error (effort <= 0) always gets `STOP` (no up-tilt command)
- `src/actuators/command_sender.py`: `turret(direction, speed)`, `tilt(direction, speed)` (validates the `TURRET_DIRECTIONS`/`TILT_DIRECTIONS` enums), `fire(state, duration_ms)` replacing `laser(...)`
- `src/main.py`: `Orchestrator._on_target_found`/`_on_target_lost` call the new methods above, `_steer_body` switched to using `pan_error_deg` (from the current aimer cycle) instead of an accumulated absolute pan angle, `ScanPattern` now returns `(direction, speed)` using a virtual angle (estimated dead-reckoning) only to time direction switches, not a real position
- `firmware/esp32_wroom/src/main.cpp`: `handleTurret`/`handleTilt` now take `(direction, speed)` with enum validation, `handleLaser`→`handleFire`, dispatch checks `"FIRE"` instead of `"LASER"`
- `config/settings.yaml`: `laser_burst_ms`→`fire_burst_ms`, added `control.scan_speed` (turret motor speed while scanning, separate from `scan_step_deg_per_sec` which is now only used for timing)
- `tests/test_aimer.py`, `test_command_sender.py`, `test_orchestrator.py`: rewritten entirely to match the new interface — all pass (`python tests/test_<name>.py -v`)

**Not yet done (next tasks as of then):**
- Flash the updated `firmware/esp32_wroom` and test the real UDP round-trip with the v1.2 format (parse/clamp/fail-safe for TURRET/TILT/FIRE)
- Tune real PID gains (from the old position-PID → velocity/effort-PID) against real hardware

---

## Formerly: most urgent item (closed 2026-07-13) — protocol changed, code hadn't caught up yet (2026-07-01)

Discovered today that the real hardware (converted from a ~20-year-old RC car) has **no angle sensor at all for either pan or tilt** — originally assumed pan/tilt were servos, so it was designed to send an absolute angle (`TURRET:PAN:angle`), which isn't actually possible with a plain DC motor.

**Docs already updated** (`decisions.md`, `SPEC.md`, `config/protocol_contract.yaml`, `AGENTS.md`, `overview/overview.md`, `README.md`, `hardware/pin_map.md`) to match the real hardware:
- `TURRET:direction:speed` (LEFT/RIGHT/STOP) replacing `TURRET:PAN:angle`
- `TILT:direction:speed` (DOWN/STOP only, no UP — tilting up is via the return spring) replacing `TILT:PITCH:angle`
- `LASER` renamed to `FIRE` (the real mechanism is a spring-release driven by a DC motor, not a laser)
- Concept: use the camera as feedback instead of a potentiometer (visual servoing) — send direction+speed every loop cycle ~20Hz instead of an absolute angle

**Code not yet updated to match at that point** (deliberately split into two tasks: docs first, code later — that task is now done, see the section above) — files that needed changes at the time:
- `src/logic/aimer.py` — change output from absolute angle (`current_pan`/`current_tilt` accumulator) to (direction, speed) per axis, remove the old -180..180/-90..90 clamp
- `src/actuators/command_sender.py` — change `turret(angle)`→`turret(direction, speed)`, `tilt(angle)`→`tilt(direction, speed)`, `laser(...)`→`fire(...)`
- `src/main.py` — `Orchestrator._on_target_found`/`_on_target_lost`/`ScanPattern` need to call the new methods above
- `firmware/esp32_wroom/src/main.cpp` — `handleTurret`/`handleTilt`/`handleLaser` need to change signature to accept a direction enum instead of angle, rename handleLaser→handleFire
- `tests/test_aimer.py`, `tests/test_command_sender.py`, `tests/test_orchestrator.py` — need to be rewritten to match the new interface
- `config/settings.yaml` — the key `control.laser_burst_ms` may need renaming to match (`fire_burst_ms`?), review PID gains (meaning changes from position-PID to velocity/effort-PID, needs re-tuning)

---

## Real hardware known so far (2026-07-01)

- **Pan** (left-right): DC motor through L298N#2, no potentiometer/encoder
- **Tilt** (up-down): a single DC motor pushes down one direction only via cam/worm, tilting up = the return spring (passive), no sensor
- **Firing mechanism (FIRE):** a DC motor spins one direction to release the firing spring — tested at 9V with the original RC car's motor, works (unknown how the force compares to the original)
- **Laser rangefinder:** just a future idea, no real hardware yet, not in the protocol currently
- **Boards:** ESP32-CAM on COM4 (CH340), ESP32-WROOM on COM5 (CH9102) — **only one working USB data cable, must swap between boards**
- Both boards currently draw power only from the upload USB cable, no auxiliary power/battery connected yet — **do not connect the L298N for real right now** (waiting on pin map + real PWM driving code + a separate battery — pin map + PWM are now done, see current-task.md)

---

## src/ already written (first round — used the old protocol)

| Role | File | Tested |
|---|---|---|
| Frame receiver | `src/vision/frame_receiver.py` | live-tested with a real camera (`scripts/test_camera_stream.py`) |
| Detector | `src/vision/detector.py` (YOLOv8n) | real inference run, model auto-loads |
| Tracker | `src/logic/tracker.py` (Kalman constant-velocity) | `tests/test_tracker.py` — unaffected by the protocol change |
| Aimer | `src/logic/aimer.py` | ✅ updated to protocol v1.2 (2026-07-13) |
| Board commander | `src/actuators/command_sender.py` | ✅ updated to protocol v1.2 (2026-07-13) |
| Main controller | `src/main.py` (`Orchestrator`) | ✅ updated to protocol v1.2 (2026-07-13) |

Run all unit tests: `python tests/test_<name>.py -v` (pytest not set up yet — using stdlib `unittest`) — all 25 cases pass (2026-07-13)
