# Current Task — Handoff

## ✅ Real TRACK hardware test passed (2026-07-30 evening)

- TRACK left/right wired to L298N#1 per `hardware/pin_map.md`
- Firmware flashed to ESP32-WROOM on **COM5** (`pio run -e esp32wroom -t upload`) — first flash needed hold BOOT + tap RST (`Wrong boot mode 0x13`); retry succeeded
- Boot log: WiFi connected, UDP `:5555`, `Ready -- driving real PWM/GPIO outputs`
- Last observed DHCP IP: **`192.168.1.129`** (can change — set a reservation when convenient)
- `python tests/hardware/drive_console.py --host 192.168.1.129` — **works** (UDP path + motors respond)
- Power: tested with **alkaline 9V** — motion works but **underpowered** (high internal resistance / L298N drop). Next: switch to **2S Li-Po 7.4V, 1500–3000 mAh, ≥20C**; L298N from battery, common GND with ESP32 (USB OK for logic)

**Not done yet this session:** TURRET / TILT / FIRE wiring, Stage 3 on-ground drive, deadband measurement for `body_turn_speed`

## ✅ TRACK right pins remapped off GPIO16/17 (2026-07-30)

- User board does not break out GPIO16/GPIO17
- TRACK right IN A/B: **GPIO16/17 → GPIO32/33** (PWM stays GPIO18)
- Updated: `firmware/esp32_wroom/src/main.cpp`, `hardware/pin_map.md`, `diagram.json` (Wokwi `RX2`/`TX2` → `D32`/`D33`), `CHANGELOG.md`
- Future pan/tilt pots reserved on **GPIO34/35** (input-only ADC) instead of 32/33; GPIO14 spare

## ✅ Drive console added (`tests/hardware/`)

- Manual TRACK-only UDP console — no camera/YOLO — for isolating motor/wiring issues
- Docs: `tests/hardware/README.md` (staged procedure: bench → blocks → ground)

## ✅ Made the Wokwi wire routing easier to read (2026-07-14)

- Layout/colors only; pin pairing unchanged. Wokwi CLI full sim still broken (deprioritized — see archive notes below)

## 📌 Wokwi CLI bug — simulation never finishes (2026-07-14, **deprioritized**)

Full isolation notes kept in earlier revisions / still open: McAfee untested, mobile hotspot untested, GA workflow on branch `wokwi-ci-control-test` needs PAT `workflow` scope. Not a blocker — real hardware path is active.

**Left behind:** `esp32-test/` scratch folder; empty `wokwi_serial*.log` artifacts (safe to delete); branch `wokwi-ci-control-test`

---

## 📌 Outstanding work (from a previous round)

1. **Make the file structure cleaner** — details not yet agreed on (e.g. whether to move `wokwi.toml`/`diagram.json` into a subfolder) — discuss at session start if needed

---

## Status (updated 2026-07-30)

- ✅ Working principles + design reasoning: `overview/overview.md`
- ✅ Command protocol format + pixel→degree principle: `SPEC.md` (protocol v1.3)
- ✅ Each role + project structure: `AGENTS.md`
- ✅ `firmware/esp32_cam` — written, flashed, working for real (MJPEG stream at `:81/stream` + index page at `:80`, ~38-58 fps)
- ✅ `firmware/esp32_wroom` — protocol v1.3 + real PWM/GPIO — **flashed to real board (COM5)** — TRACK verified via `drive_console.py`
- ✅ Pin map: TRACK left GPIO4/5/13, TRACK right **GPIO32/33/18**, TURRET 19/21/22, TILT 23/25/26, FIRE 27
- ✅ PC-side `src/` — all 6 roles, unit tests pass
- ✅ Wokwi diagram present (sim CLI still flaky — skip)
- ⚠️ Motor power still temporary (9V alkaline) — replace with 2S Li-Po before serious drive tests
- ⚠️ TURRET / TILT / FIRE not wired or tested yet
- ⚠️ PID / FOV / `body_turn_speed` still untuned placeholders

---

## Next tasks (in a reasonable order)

1. ~~Flash WROOM + UDP TRACK path~~ — **done (2026-07-30)**
2. Get a **2S Li-Po** on the L298N; re-run drive console on blocks; measure PWM deadband → raise `config/settings.yaml control.body_turn_speed` above it
3. Wire + test TURRET / TILT (L298N#2) and optionally FIRE (MOSFET / GPIO27) — keep FIRE disconnected until ready
4. Run `python -m src.main` for first full end-to-end (both boards on WiFi)
5. Calibrate FOV, PID gains (velocity/effort), aim tolerance, fail-safe timeout
6. Decide real `TARGET_CLASS` (currently `"person"` for pipeline testing)
7. DHCP reservation / static IP for both boards (`192.168.1.129` was last WROOM lease — not durable)
8. Optional: project folder cleanup / Wokwi CLI rabbit hole (low priority)

---

## Good to know

- Flash: PlatformIO + `embedded-flash-monitor` skill — WROOM is COM5; if upload says `Wrong boot mode (0x13)`, hold BOOT, tap RST, retry
- Drive test: `python tests/hardware/drive_console.py --host <board-ip>` — keys latch; SPACE stops; `F` probes fail-safe
- Networking: home WiFi client mode (`decisions.md`)
- Tracker: Kalman (`decisions.md`); pan/tilt: direction+speed visual servoing (`decisions.md`)

> Older closed work (protocol migration, 2026-07-01 hardware discoveries) lives in `handoff/archive.md`
