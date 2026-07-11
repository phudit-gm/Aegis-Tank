# Aegis-Tank

รถถังตีนตะขาบ AI ตรวจจับเป้า (YOLOv8) แล้วเล็งยิง (กลไกสปริงยิงด้วยมอเตอร์ DC) · สถาปัตยกรรม Split-Brain (PC = สมอง, ESP32 = กล้ามเนื้อ)
รื้อใหม่จากโปรเจคเดิม R.N.T. — โครงสร้างนี้พร้อมแล้ว โค้ดจะเขียนใหม่

## Setup

```bash
# ฝั่ง PC (Python)
pip install -r requirements.txt   # opencv-python, torch, ultralytics, numpy, pyyaml, ...

# ฝั่ง Firmware (ESP32) — flash ใน VS Code + PlatformIO เท่านั้น
# firmware/esp32_cam     → AI Thinker ESP32-CAM (MJPEG streamer + WiFi AP)
# firmware/esp32_wroom   → ESP32 Dev Module (UDP receiver + motor control)
```

## วิธีรัน (เมื่อเขียนโค้ดแล้ว)

```bash
python src/main.py            # รันเต็มระบบ (ต้องต่อ WiFi RNT_TANK)
python src/main.py --webcam   # ทดสอบ AI ด้วย webcam laptop (ไม่ต้องมี ESP32-CAM)
```

ลำดับเปิดระบบ: ESP32-CAM (ปล่อย AP) → ESP32-WROOM (เชื่อม AP) → PC (เชื่อม AP) → รัน

## โครงสร้างโปรเจค

| โฟลเดอร์ | คำอธิบาย |
|---|---|
| `config/` | `protocol_contract.yaml` — ความจริงเดียวของ protocol (Python + ESP32 อ้างอิงจริง) |
| `src/` | PC brain (Python): `vision/` `logic/` `actuators/` `utils/` |
| `firmware/` | `esp32_cam/` (MJPEG streamer) · `esp32_wroom/` (motor controller) |
| `hardware/` | pin map, wiring, power, BOM |
| `models/` | YOLOv8 weights |
| `data/` | recordings, dataset, ผลทดลอง |
| `web/` | ระบบควบคุมบังคับ/monitoring ผ่าน browser |
| `scripts/` | flash / convert / deploy helpers |
| `tests/` | unit tests |

## เอกสารที่ต้องอ่านก่อน
1. `AGENTS.md` — ภาพรวม + กฎทำงาน
2. `SPEC.md` — contract, pin map, decisions, gotchas
3. `handoff/current-task.md` — งานค้างล่าสุด
