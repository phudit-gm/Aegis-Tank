# Changelog

## [Unreleased]

### Changed
- Pointed Sightglass (`C:\sightglass\sightglass.config.json`) at this repo: sketch root Aegis-Tank, default sketch `firmware/esp32_wroom`, env `esp32wroom`.

### Changed
- TURRET LEFT/RIGHT motor polarity inverted in firmware (`handleTurret`) — pan leads cannot be swapped on the robot. Re-flash WROOM.

### Added
- `tests/hardware/turret_console.py` — pan-only UDP console (`TURRET:LEFT/RIGHT/STOP`). L298N#2 channel A wiring in `hardware/pin_map.md`.

### Added
- Protocol v1.4: `TRACK:MIX:left:right` (signed PWM per wheel, -255..255). Firmware `handleTrackMix`, `CommandSender.track_mix()`, drive console Q/E curves / A/D pivot / M=max. `_steer_body` still uses `PIVOT_*`.

### Changed
- TRACK right wheel IN pins remapped **GPIO16/17 → GPIO32/33** (PWM stays GPIO18) — many DevKit boards do not break out 16/17; updated `firmware/esp32_wroom/src/main.cpp`, `hardware/pin_map.md`, `diagram.json`

### Added
- `tests/hardware/drive_console.py` — manual TRACK-only UDP console for real-board motor tests (see `tests/hardware/README.md`)
- Real TRACK path verified on hardware (2026-07-30): WROOM flashed on COM5, drive console works; 9V alkaline underpowered — need 2S Li-Po

### Added
- Protocol v1.2 → v1.3: changed `TURRET`/`TILT` from absolute angle to `direction`+`speed` (visual servoing, no angle sensor), `LASER`→`FIRE`, added `TRACK:PIVOT_LEFT/PIVOT_RIGHT` separate from the existing skid-turn
- `firmware/esp32_cam` — written+flashed, working for real (MJPEG stream `:81/stream`, index page `:80`, ~38-58 fps)
- `firmware/esp32_wroom` — real PWM/GPIO driving code now in place per protocol v1.3 (`driveChannel`, `enterSafeState` fail-safe, non-blocking `handleFire`), compiles for both `esp32wroom`/`esp32wroom_ota`, not yet flashed to a real board
- PC-side `src/` — all 6 roles complete (`vision/`, `logic/`, `actuators/`, `utils/`, `main.py`) matching protocol v1.3, all 26 unit test cases pass
- `hardware/pin_map.md` real pin map now defined
- Wokwi simulation: `wokwi.toml` + `diagram.json` at root, custom chip `chip-l298n` (`github:drf5n/Wokwi-Chip-L298N@1.0.5`) x2 for TRACK/TURRET/TILT, `wokwi-cli lint` passes

### Added (initial)
- Created the **Aegis-Tank** project skeleton (rebuilt from R.N.T., which was scattered across 3 locations)
- AGENTS.md, SPEC.md, README.md, overview, handoff
- `config/protocol_contract.yaml` v1.0 — carried over from the previous project
- `hardware/pin_map.md` — pin map, power wiring, EMI, battery precautions
- Folder skeleton: src/{vision,logic,actuators,utils}, firmware/{esp32_cam,esp32_wroom}, hardware, models, data, web, scripts, tests
