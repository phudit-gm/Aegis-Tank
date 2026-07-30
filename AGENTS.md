# Aegis-Tank — AGENTS.md

> Every AI always reads this file before starting work

## ⚠️ Project status

**Real code now exists (2026-07-01)** — `firmware/esp32_cam` (camera, flashed, working for real) and the PC-side `src/` (all 6 roles written, has unit tests) are done.
**No code yet in `firmware/esp32_wroom`** (motor controller board) — not written yet.
Always check the detailed status in `handoff/current-task.md` before writing/changing anything.

---

## What is this project?

**Aegis-Tank** — a semi-autonomous sentry robot that detects a target with AI on a PC, then aims and fires (a spring-release mechanism driven by a DC motor — not a laser, see `decisions.md`)
Rebuilt from the earlier R.N.T. (Rear-Naked Tank) project — a single clean structure, code rewritten entirely from scratch.
Full principles are in `overview/overview.md`

---

## Architecture — 3 main parts (Split-Brain)

```
[ESP32-CAM]  eyes
    │  sends a video stream over WiFi
    ↓
[PC + Python + AI]  brain
    │  detect → track → compute aiming error → send commands
    ↓
[ESP32-WROOM]  muscle
    │  receive commands → convert → drive motors
    ↓
[Motors / turret / firing mechanism]
```

**Core principle:** the PC sends "intent" (direction/speed/ms), not raw PWM — the ESP32 converts it to PWM itself
> **Note, 2026-07-01:** originally assumed pan/tilt could send an absolute angle (assuming servos) — the real hardware is a DC motor with no angle sensor, so it sends direction+speed like TRACK instead. See `decisions.md` and `SPEC.md §2-3`

---

## PC-side roles — 6 conceptual parts

> These are "roles", not code file names — how to split files/modules is decided during actual implementation

| Role | Responsibility |
|---|---|
| Frame receiver | Connects to the camera stream, pulls frames one at a time |
| Detector | Feeds the frame into AI to find whether/where a target object is |
| Tracker | Smooths the position (Kalman) + estimates target velocity |
| Aimer | Computes pixel error → converts to degree error → runs through PID → gets direction+speed to command this cycle |
| Board commander | Converts direction/speed/commands into a message sent to the board over WiFi |
| Main controller (orchestrator) | Calls every part above in order, looping repeatedly |

---

## Main Loop (logical — not real code)

```
Loop repeatedly (at a fixed frequency):
  1. Receive a frame from the camera
     If no frame → skip this cycle

  2. Detect + track the target

  3. If a target is found:
       - Compute aiming → command turret/tilt
       - If the target is too far right → turn the vehicle body right
         If too far left → turn left
         If already centered → stop
       - If aimed accurately enough → fire

  4. If no target is found:
       - Scan for a target (sweep the turret per a pattern)

  5. Wait for the cycle to complete → loop again
```

The loop must run at a **fixed frequency (fixed dt)** so Kalman/PID compute correctly

---

## Active folders

| Folder | Contains |
|---|---|
| `src/` | PC-side Python code — all 6 roles fully written (`vision/`, `logic/`, `actuators/`, `utils/`, `main.py`) |
| `firmware/` | `esp32_cam/` written+flashed · `esp32_wroom/` **not yet written** |
| `overview/` | `overview.md` — explains the project for newcomers |
| `hardware/` | hardware docs (pin map not yet defined) |
| `models/` | YOLOv8 weights (*.pt) — large files not committed (`yolov8n.pt` downloads automatically) |
| `data/` | test videos, dataset — large files not committed |
| `config/` | `protocol_contract.yaml` (command format) + `settings.yaml` (real/tunable values) — both already exist |
| `tests/` | unit tests |
| `scripts/` | helper tools (flash, convert, deploy) |
| `web/` | manual override control / monitoring system via browser |
| `handoff/` | `current-task.md` — work status handed off between sessions |

---

## Rules for AI

- Read `SPEC.md` before changing any interface or command format
- Update `handoff/current-task.md` at the end of a session
- If adding a new folder — add a description to this table too
- **Never write as if code already exists** — always check the real status in `handoff/current-task.md` first
- See closed decisions in `SPEC.md` — don't relitigate them without a new reason
