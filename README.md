# Aegis-Tank

A tracked AI sentry tank that detects targets (YOLOv8) and aims/fires (a spring-release mechanism driven by a DC motor) · Split-Brain architecture (PC = brain, ESP32 = muscle)
Rebuilt from the earlier R.N.T. project — this structure is ready, the code is being rewritten from scratch.

## Setup

```bash
# PC side (Python)
pip install -r requirements.txt   # opencv-python, torch, ultralytics, numpy, pyyaml, ...

# Firmware side (ESP32) — flash from VS Code + PlatformIO only
# firmware/esp32_cam     → AI Thinker ESP32-CAM (MJPEG streamer + WiFi AP)
# firmware/esp32_wroom   → ESP32 Dev Module (UDP receiver + motor control)
```

Before OTA-flashing either board (`pio run -e esp32cam_ota` / `esp32wroom_ota`), set the `OTA_PASSWORD` environment variable to match the value in your `secrets.h`.

## How to run (once the code is written)

```bash
python src/main.py            # run the full system (must be connected to the WiFi network configured in your secrets.h)
python src/main.py --webcam   # test the AI with a laptop webcam (no ESP32-CAM required)
```

Boot order: ESP32-CAM (starts up) → ESP32-WROOM (joins the network) → PC (joins the network) → run

## Project structure

| Folder | Description |
|---|---|
| `config/` | `protocol_contract.yaml` — the single source of truth for the protocol (both Python and ESP32 reference it directly) |
| `src/` | PC brain (Python): `vision/` `logic/` `actuators/` `utils/` |
| `firmware/` | `esp32_cam/` (MJPEG streamer) · `esp32_wroom/` (motor controller) |
| `hardware/` | pin map, wiring, power, BOM |
| `models/` | YOLOv8 weights |
| `data/` | recordings, dataset, experiment results |
| `web/` | manual control / monitoring system via browser |
| `scripts/` | flash / convert / deploy helpers |
| `tests/` | unit tests |

## Docs to read first
1. `AGENTS.md` — overview + working rules
2. `SPEC.md` — contract, pin map, decisions, gotchas
3. `handoff/current-task.md` — latest outstanding work
