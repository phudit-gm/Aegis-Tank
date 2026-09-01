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
- ✅ Command protocol format + pixel→degree principle: `SPEC.md` (protocol v1.4)
- ✅ Each role + project structure: `AGENTS.md`
- ✅ `firmware/esp32_cam` — written, flashed, working for real (MJPEG stream at `:81/stream` + index page at `:80`, ~38-58 fps)
- ✅ `firmware/esp32_wroom` — protocol v1.4 MIX + real PWM/GPIO — **flashed COM5 2026-08-28**, IP **192.168.1.137**
- ✅ Pin map: TRACK left GPIO4/5/13, TRACK right **GPIO32/33/18**, TURRET 19/21/22, TILT 23/25/26, FIRE 27
- ✅ PC-side `src/` — all 6 roles, unit tests pass
- ✅ Wokwi diagram present (sim CLI still flaky — skip)
- ⚠️ Motor power still temporary (9V alkaline) — replace with 2S Li-Po before serious drive tests
- ⚠️ TURRET / TILT / FIRE not wired or tested yet
- ⚠️ PID / FOV / `body_turn_speed` still untuned placeholders

---

## 📌 TRACK speed-limits script (2026-08-27)

- Added `tests/hardware/speed_limits.py` — Stage 2 wizard: PWM deadband (left/right, step 10) then
  speed 255 from rest (`FORWARD` / `PIVOT_LEFT` / `PIVOT_RIGHT`). Operator records PSU amps; yaml
  is not edited until numbers exist.
- Run: `python tests/hardware/speed_limits.py --host <board-ip>` (wheels off ground, PSU 3A limit)
- WROOM DHCP this session: **`192.168.1.137`** (`.129` is stale — UDP to the old lease looks fine but motors stay still)
- Deadband (wheels up, 2026-08-27): LEFT **60**, RIGHT **60** → `body_turn_speed` must stay above 60 (still 120, unedited)
- Speed 255 current **wheels up / free-spin** (2026-08-27, PSU display): FORWARD peak 1 A / run 1 A; PIVOT_LEFT 1 / 0.95 A; PIVOT_RIGHT 2 / 2 A. Not at the 3A limit. On-ground (loaded) currents not measured yet.

## 📌 TRACK MIX protocol v1.4 (2026-08-28)

- Additive command `TRACK:MIX:left:right` (signed PWM -255..255 per wheel). Old 3-token TRACK unchanged.
- `drive_console.py`: Q/E = forward curves (MIX), A/D = pivot, M = speed 255. `_steer_body` still `PIVOT_*`.
- **Flash required** before Q/E do anything — old firmware `[DROP]`s MIX. Disconnect motor VIN before USB upload (no USB+VIN). Then `sightglass upload --env esp32wroom --port COM5` from the repo (or `pio run -e esp32wroom -t upload` in `firmware/esp32_wroom`).
- Last known WROOM IP: **`192.168.1.137`** — re-flashed COM5 2026-08-28 23:37 via `sightglass upload --env esp32wroom`; boot log `Connected! IP: 192.168.1.137`, ping + `aegis-wroom.local` OK

## 📌 TURRET pan-only console (2026-08-28)

- `tests/hardware/turret_console.py` — A/D (or J/L) send `TURRET:LEFT/RIGHT`, SPACE stop. Same 20Hz / fail-safe as drive console.
- Wire L298N#2 **channel A only**: IN1→GPIO19, IN2→GPIO21, ENA→GPIO22 (remove ENA jumper), motor on OUT1/OUT2. Leave IN3/IN4/ENB off. See `hardware/pin_map.md`.
- Firmware already has `handleTurret` — re-flashed COM5 2026-08-28 evening (same IP).
- **Polarity invert 2026-08-28:** `handleTurret` LEFT/RIGHT swapped in firmware (cannot swap OUT1/OUT2 on the robot). **OTA flashed** to `aegis-wroom.local` / `192.168.1.137` (USB COM not attached).
- TILT / FIRE still not wired.

## Next tasks (in a reasonable order)

1. ~~Flash WROOM + UDP TRACK path~~ — **done (2026-07-30)**
1b. **Re-flash WROOM with v1.4 MIX** before using Q/E on the console
2. Get a **2S Li-Po** on the L298N; on-ground speed 255 + pivot deg/s (wheels-up deadband 60 already measured)
3. Wire + test TURRET pan (L298N#2 ch A) with `turret_console.py`; TILT later; FIRE disconnected until ready
4. Run `python -m src.main` for first full end-to-end (both boards on WiFi)
5. Calibrate FOV, PID gains (velocity/effort), aim tolerance, fail-safe timeout
6. Decide real `TARGET_CLASS` (currently `"person"` for pipeline testing)
7. DHCP reservation / static IP for both boards (`192.168.1.129` was last WROOM lease — not durable)
8. Optional: project folder cleanup / Wokwi CLI rabbit hole (low priority)

---

## 📌 Sightglass linked (2026-08-29)

- `C:\sightglass\sightglass.config.json` now points at this repo: `sketchRoots` = Aegis-Tank, default sketch `firmware/esp32_wroom`, `env` = `esp32wroom`.
- Dashboard is **not** running until `npm start` in `C:\sightglass` — then http://127.0.0.1:7391. Pick `esp32_cam` in the sketch list when flashing the camera.
- Web Upload uses `esp32wroom` unless you change the selected sketch/`env`. CLI still needs `--env` when `--sketch` is the repo root.

## Good to know

- Flash: use `embedded-flash-monitor` skill — prefer `sightglass upload --port COM5` (from the board's firmware folder); fallback `pio run -e esp32wroom -t upload` if sightglass is missing or you need a specific env (`esp32wroom` / `esp32wroom_ota`). If the sightglass dashboard is running, do **not** start `pio device monitor` — poll its log under `C:\sightglass\logs\` instead. WROOM is COM5; if upload says `Wrong boot mode (0x13)`, hold BOOT, tap RST, retry
- Drive test: `python tests/hardware/drive_console.py --host <board-ip>` — keys latch; SPACE stops; `F` probes fail-safe
- Networking: home WiFi client mode (`decisions.md`)
- Tracker: Kalman (`decisions.md`); pan/tilt: direction+speed visual servoing (`decisions.md`)

> Older closed work (protocol migration, 2026-07-01 hardware discoveries) lives in `handoff/archive.md`
