# Aegis-Tank — Decisions

Reasoning and trade-offs behind closed design decisions.
The (brief) outcome of each decision lives in `SPEC.md §3`

---

> [!decision] ~~Send degrees, not PWM~~ — **revised 2026-07-01, see next item** (the original assumption was wrong: assumed pan/tilt were servos)
> **Original decision:** the PC sends angles in degrees (pan/tilt) over the network — no raw PWM values
> **Original reasoning:** PWM values are tied to the real servo/motor and gear ratio, which are hardware details — swapping hardware only requires changing the ESP32 firmware, not the PC code
> **Trade-off accepted at the time:** the ESP32 takes on the extra burden of converting angle→PWM, but gets a clearer separation of concerns — the PC knows nothing about hardware details
> **Why it had to change:** this decision assumed pan/tilt were servos (with their own built-in feedback) — the real hardware is a plain DC motor with no potentiometer/encoder at all, so sending "go to angle X" directly isn't possible. See the new decision below
> **Date:** 2026-06-26 (revised 2026-07-01)

---

> [!decision] Pan/Tilt send direction+speed every loop cycle (visual servoing) instead of an absolute angle
> **Decision:** drop the absolute-angle `TURRET:PAN:angle` / `TILT:PITCH:angle` format, change to `TURRET:direction:speed` / `TILT:direction:speed` matching the `TRACK` format — the ESP32 never needs to know the turret's real angular position
> **Reasoning:** the real hardware (a converted ~20-year-old RC car) has no angle sensor at all — pan is driven by a DC motor through L298N#2 (can spin both directions), tilt is driven by a single DC motor pushing a cam/worm down in one direction only, with tilting up coming from a passive return spring (no motor pushes it up) — there is no way to compute/command "go to angle X degrees" accurately without a sensor
> **Solution:** use the camera (already running every cycle at ~20Hz) as the feedback source instead of a potentiometer — compute pixel error every frame, run it through PID to get an effort, convert that to a short direction+speed command sent each cycle, and the next frame the camera sees the new result and corrects the error further (closed-loop via vision instead of closed-loop via encoder)
> **Tilt-specific limitation:** the "tilt up" direction has no motor command that can actually actuate it — the only option is "stop pushing down" and wait for the spring to pull it back up, which is slower and less precisely controlled than the down direction (so the allowed TILT direction enum is only `DOWN`/`STOP`, no `UP`)
> **Trade-off accepted:** lower precision than true closed-loop servo positioning — but avoids a major hardware structural mod (the existing vehicle frame wasn't designed for a servo mount), which is sufficient for a sentry-turret task that doesn't need lab-grade precision — a potentiometer can be added later if truly needed
> **Date:** 2026-07-01

---

> [!decision] `TRACK` separates skid-turn from pivot-turn (new `PIVOT_LEFT`/`PIVOT_RIGHT`)
> **Decision:** added `PIVOT_LEFT`/`PIVOT_RIGHT` in protocol v1.3 — both wheels spin opposite directions at equal speed (recommended), distinct from the existing `TURN_LEFT`/`TURN_RIGHT` which officially became skid-turn (one side stops, the other drives)
> **Reasoning:** originally there was no mode separation — `_steer_body` (aim-assist, turning the body to help the turret) just used plain `TURN_LEFT/TURN_RIGHT` — the project owner wanted skid-turn for general movement, but pivot-turn for tight situations/while aiming (aim-assist), since it's more precise and doesn't drag the vehicle position away from the aim point
> **Usage:** `_steer_body` (`src/main.py`) always calls `PIVOT_LEFT/PIVOT_RIGHT` since it's the only caller right now (aim-assist) — `TURN_LEFT/TURN_RIGHT` (skid) is kept for future manual-drive/web-control code that isn't implemented yet
> **Trade-off accepted:** an extra enum in the protocol (both PC/ESP32 must be updated together) in exchange for aiming precision — pivot doesn't shift the vehicle position as much as skid-turn
> **Date:** 2026-07-13

---

> [!decision] `TRACK:MIX` sends independent left/right PWM (protocol v1.4)
> **Decision:** add a 4-token command `TRACK:MIX:<left>:<right>` with signed integers -255..255 per wheel (positive=forward, negative=reverse, 0=coast). Existing 3-token TRACK directions stay valid.
> **Reasoning:** the L298N already drives left and right on separate GPIO; the old packet only had one speed, so a curve (inner wheel slower) was impossible without pretending skid (one wheel at 0). MIX is additive so `_steer_body` can keep using `PIVOT_*` and deadband tests can keep using `TURN_*`.
> **Usage:** `drive_console.py` Q/E send MIX curves; A/D send pivot. `CommandSender.track_mix()`, not `track("MIX", ...)`.
> **Trade-off accepted:** the TRACK parser now has one special case (4 tokens) instead of a strictly uniform 3-token grammar.
> **Date:** 2026-08-28

---

> [!decision] FIRE is driven through a single-GPIO MOSFET switch, not a 3rd L298N channel
> **Decision:** use one MOSFET module to drive the firing mechanism's motor through a single GPIO (digital ON/OFF) instead of sourcing a 3rd board driver
> **Reasoning:** the two L298Ns have 4 channels which already exactly fit TRACK left/right + TURRET + TILT — there's no channel left for FIRE — but FIRE is a one-direction motor (no need to reverse), so a full H-bridge isn't necessary; a plain MOSFET switch is cheaper and easier to wire
> **Trade-off accepted:** no PWM force control (per the existing protocol which is already ON/OFF+duration_ms, not speed) — if variable firing force is wanted in the future, a different driver would be needed
> **Date:** 2026-07-13

---

> [!decision] Renamed the `LASER` command to `FIRE`
> **Decision:** renamed the command type from `LASER` to `FIRE` — the format/fields stay the same (`FIRE:state:duration_ms`)
> **Reasoning:** the original name came from a wrong assumption during the initial design (thought there'd be a laser diode for pointing at the target) — what actually exists now is a mechanical firing mechanism: a DC motor spins one direction to release the firing spring (tested at 9V with the original RC car's motor, works)
> **Note:** the laser rangefinder sensor idea is just a future concept, no real hardware yet and not implemented — if built for real in the future it would be a separate command from `FIRE` (an input sensor reporting distance data back, not an output actuator)
> **Date:** 2026-07-01

---

> [!decision] Use ESP32 instead of Raspberry Pi
> **Decision:** use ESP32-WROOM as the motor controller, not a Raspberry Pi
> **Reasoning:** boot < 1s, low power draw, does real-time control well, much cheaper — the heavy AI work is offloaded to the PC so the ESP32 doesn't have to carry it
> **Trade-off accepted:** limited processing on the ESP32 — more complex logic has to be added on the PC side and sent as additional commands; it can't run complex logic on the board itself
> **Date:** 2026-06-26

---

> [!decision] One-way UDP + fail-safe timeout
> **Decision:** use UDP (one-way, no handshake) instead of TCP for sending PC→ESP32 commands, with a fail-safe timeout on the ESP32
> **Reasoning:** lower latency than TCP, well-suited to a command stream the PC re-sends frequently every second — a lost packet is simply replaced by the next one on the following cycle anyway
> **Trade-off accepted:** UDP doesn't guarantee delivery — packet loss is accepted and compensated for with a fail-safe timeout: if the ESP32 doesn't receive a command for longer than the set duration, it automatically returns to safe state
> **Date:** 2026-06-26

---

> [!decision] ESP32-CAM connects to home WiFi as a client (no self-hosted AP)
> **Decision:** use the existing home WiFi (client mode, DHCP) instead of having the ESP32-CAM host its own AP (as the earlier R.N.T. project did)
> **Reasoning:** the existing network is already there, so there's no need to change firmware/reconnect to a new WiFi every time it's tested; testing is more convenient since the PC and boards are on the same network used for everyday use
> **Trade-off accepted:** the IP is DHCP-assigned, not fixed — if the router hands out a new IP, `config/settings.yaml` must be updated manually (no DHCP reservation or static IP set in firmware yet)
> **Date:** 2026-07-01

---

> [!decision] Chose Kalman filter as the tracking algorithm (closes the TODO in SPEC.md §4)
> **Decision:** use a Kalman filter (constant-velocity model) instead of plain centroid for the tracker
> **Reasoning:** overview.md explains the reasoning from the start (filters noise + predicts target velocity) — plain centroid does neither, and PID needs an error signal stable enough to not make the turret jitter
> **Trade-off accepted:** slightly more complex code than centroid (4D state, matrix inverse on every update) but still very lightweight compared to the much heavier AI detection work — doesn't impact real-time performance
> **Date:** 2026-07-01
