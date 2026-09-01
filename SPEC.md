# Aegis-Tank — SPEC.md

> Command protocol format + pixel→degree conversion principles
> **All real values (IP, port, PWM, PID, threshold, FOV) are still pending, to be set when writing code / wiring up for real**

---

## 1. Command Protocol

The PC sends commands to the ESP32-WROOM board over WiFi as a message in the form:

```
TYPE:FIELD2:FIELD3
```

- **Default: 3 parts** separated by `:` — TURRET / TILT / FIRE and all TRACK directions except `MIX`
- **Exception (v1.4):** `TRACK:MIX:left:right` is 4 parts (signed PWM per wheel, -255..255)
- encoded as UTF-8 bytes
- ESP32 parses by splitting on `:` → checks token count (3, or 4 when TRACK MIX) → looks at TYPE to dispatch → checks the value range

### Planned command types (TYPE)

> **Revised 2026-07-01:** originally assumed pan/tilt were servos and sent an absolute angle — the real hardware is a plain DC motor with **no angle sensor at all** (no potentiometer/encoder). Changed to send direction+speed every loop cycle like `TRACK` instead (see `decisions.md` for the full reasoning)

| TYPE | FIELD2 | FIELD3 | Meaning |
|---|---|---|---|
| `TRACK` | direction (`FORWARD`/`BACKWARD`/`STOP`/`TURN_LEFT`/`TURN_RIGHT`/`PIVOT_LEFT`/`PIVOT_RIGHT`) or `MIX` | speed 0-255, or when `MIX`: two signed PWM fields `left:right` each -255..255 | Commands the tracked wheels — `TURN_*` = skid-turn (one side stops), `PIVOT_*` = both sides opposite (aim-assist), `MIX` = independent left/right PWM (`TRACK:MIX:120:60`) |
| `TURRET` | direction (`LEFT`/`RIGHT`/`STOP`) | speed 0-255 | Rotates the turret left/right (DC motor via L298N#2 — no angle feedback) |
| `TILT` | direction (`DOWN`/`STOP` only — **no `UP`**) | speed 0-255 | Pushes the barrel down (single DC motor pushing one direction only) — tilting up comes from the return spring, no motor command |
| `FIRE` | `ON`/`OFF` | duration in ms | Commands the firing mechanism (a DC motor spins one direction to release the firing spring — **not a laser**) |

> Why pan/tilt don't use an absolute angle: there's no real angle sensor, so computing "go to angle X" directly isn't possible — the camera (feedback every frame, ~20Hz) is used instead of a potentiometer, sending short direction+speed commands every cycle, letting the next frame's result correct the error further (visual servoing)

### Clamp principle (two layers)

- **PC clamp before sending** — prevents out-of-range values from being sent
- **ESP32 re-clamps (authoritative)** — the hardware-protection gate must be as close to the hardware as possible; out-of-range value → log + safe state
- UDP may be corrupted or come from another source; the ESP32 must not trust the value it receives directly

### Fail-safe

- The ESP32 stops the motors + returns to safe state if no command is received for longer than the timeout period (timeout value still pending)
- Safe state = stopped / turret centered / barrel level / laser off
- UDP does not guarantee delivery — without a fail-safe, a lost packet would leave the vehicle running unattended, which is dangerous

---

## 2. Pixel → degree error → direction+speed conversion principle

> **Revised 2026-07-01:** the computed degree value is no longer an "absolute commanded turn angle" (no actuator can accept an absolute angle) — it is used only as an **error signal fed into PID**, whose output becomes the direction+speed motor command for this cycle instead

The PC computes error from the target's position in the image, converts it to degrees (an easier-to-understand/easier-to-tune unit than raw pixels), then feeds it into PID.

**Principle:**
- Target at image center → error = 0 → PID output ≈ 0 → command `STOP`
- Target left/right of center → pixel error exists → converted via the camera's FOV into a degree error → PID → direction+speed motor command for this cycle → next frame the camera sees the new result and loops to correct the error further (visual servoing)

**Pixel→degree error conversion formula (conceptual, unchanged):**
```
degree error = (pixel_error / frame_width_px) × horizontal_FOV_degrees
```

**Tilt limitation:** if the error says "tilt up" is needed (upward error direction) — no motor command can do that; the only option is `STOP` and letting the spring return on its own (slower and less precise than the `DOWN` direction)

> Real FOV and real resolution values — **still pending, to be set once the camera is connected for real and calibrated**

---

## 3. Closed decisions (don't relitigate without a new reason)

> See full reasoning and trade-offs in `decisions.md`

1. ~~Send degrees, not PWM~~ — **revised 2026-07-01, see item 9** (the original assumption was wrong: assumed pan/tilt were servos)
2. **The ESP32 converts commands → PWM** (the PC doesn't know the real PWM value — still true, just that the PC now sends direction+speed instead of degrees)
3. **Commands are 3 parts except `TRACK:MIX:left:right` (v1.4, 4 parts)** — other TRACK directions stay 3 parts so `_steer_body` and `speed_limits.py` do not change
4. **Two-layer clamp, ESP32 authoritative**
5. **Use ESP32 instead of Raspberry Pi**
6. **UDP (one-way) + fail-safe timeout**
7. **ESP32-CAM connects to home WiFi as a client (no self-hosted AP)**
8. **Tracking algorithm = Kalman filter (constant-velocity)**, not plain centroid
9. **Pan/Tilt send direction+speed every loop cycle (visual servoing via camera)**, not an absolute angle — because the real hardware has no angle sensor (see `decisions.md`)
10. **Renamed the `LASER` command to `FIRE`** — the real mechanism is a spring-release driven by a DC motor, not a laser diode
11. **`TRACK` separates skid-turn (`TURN_LEFT`/`TURN_RIGHT`) from pivot-turn (`PIVOT_LEFT`/`PIVOT_RIGHT`)** — the PC uses pivot during aim-assist (`_steer_body`), skid is kept for general movement in the future (see `decisions.md`)
12. **FIRE is driven through a single-GPIO MOSFET switch**, not a 3rd L298N channel — the two L298Ns (4 channels) already fit TRACK×2/TURRET/TILT exactly; FIRE is ON/OFF, one direction only, no need to reverse (see `hardware/pin_map.md`, `decisions.md`)
13. **ESP32-WROOM pin map is defined** (see `hardware/pin_map.md`) — not yet wired up for real
14. **`TRACK:MIX:left:right` (protocol v1.4)** — independent signed PWM per track; hardware already had separate L298N channels. Aim-assist still uses `PIVOT_*`. Manual curve in `drive_console.py` uses MIX (see `decisions.md`)

---

## 4. Still pending (TODO)

- **✅ Code updated to match the new protocol (2026-07-13):** `src/logic/aimer.py`, `src/actuators/command_sender.py`, `src/main.py`, `firmware/esp32_wroom/src/main.cpp` all use the `TURRET:direction:speed`, `TILT:direction:speed`, `FIRE:...` format per items 9-10 in §3 — all unit tests pass, but **the new firmware has not yet been flashed to a real board / had a UDP round-trip test**, and **PID gains have not been re-tuned** (see `handoff/current-task.md`)
- **Real values not yet fixed:** the real PWM speed range for the pan/tilt/fire motors (a different motor from track may need a different range), real PID gains (a rough starting estimate already exists in `config/settings.yaml`, but **not yet tuned against real hardware** — needs a full re-tune since it changed from position-PID to velocity/effort-PID), horizontal/vertical FOV (~60° estimate, not yet calibrated)
- **DHCP IP of both boards is not fixed:** if the router hands out a new IP, `config/settings.yaml` must be updated manually (no DHCP reservation/static IP set yet)
- **TARGET_CLASS / CONF_THRESHOLD / AIM_TOLERANCE:** placeholder values already set to test the pipeline (`person`, `0.5`, `15px`) — not the project's real target yet, still pending
- **fail-safe timeout:** still hardcoded at 500ms in the firmware skeleton — not yet tuned against the real loop frequency
- **web control:** scope of manual override / monitoring not yet defined
- **firmware language:** primarily C++/PlatformIO (leaving room for MicroPython if needed)
- **laser rangefinder (future idea):** no real hardware yet, not in the protocol currently — if implemented for real it would be a sensor input, a separate command from `FIRE`
