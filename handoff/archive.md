# Handoff Archive — งานปิดแล้ว/ประวัติ

> ย้ายมาจาก `handoff/current-task.md` (2026-07-14) เพื่อให้ current-task.md เหลือแค่สถานะปัจจุบัน+งานถัดไป
> ไฟล์นี้เก็บ log ประวัติที่ปิดงานแล้ว ไม่ต้องอ่านก่อนเริ่มงานใหม่ (อ่าน `handoff/current-task.md` ก่อนเสมอ)

---

## ✅ แก้โค้ดให้ตรง protocol v1.2 แล้ว (2026-07-13) — สรุปสิ่งที่เปลี่ยน

- `src/logic/aimer.py`: `compute()` คืนค่า `AimCommand(pan_direction, pan_speed, tilt_direction, tilt_speed, pan_error_deg)` แทน absolute angle — ไม่มี `current_pan`/`current_tilt` accumulator หรือ clamp -180..180/-90..90 แล้ว tilt error ทิศขึ้น (effort <= 0) จะได้ `STOP` เสมอ (ไม่มีคำสั่งเงยขึ้น)
- `src/actuators/command_sender.py`: `turret(direction, speed)`, `tilt(direction, speed)` (validate enum `TURRET_DIRECTIONS`/`TILT_DIRECTIONS`), `fire(state, duration_ms)` แทน `laser(...)`
- `src/main.py`: `Orchestrator._on_target_found`/`_on_target_lost` เรียก method ใหม่ตามข้างบน, `_steer_body` เปลี่ยนมาใช้ `pan_error_deg` (จาก aimer รอบปัจจุบัน) แทน absolute pan angle สะสม, `ScanPattern` เปลี่ยนมาคืน `(direction, speed)` โดยใช้มุมเสมือน (dead-reckoning โดยประมาณ) แค่กำหนดจังหวะสลับทิศ ไม่ใช่ตำแหน่งจริง
- `firmware/esp32_wroom/src/main.cpp`: `handleTurret`/`handleTilt` รับ `(direction, speed)` พร้อม validate enum, `handleLaser`→`handleFire`, dispatch เช็ค `"FIRE"` แทน `"LASER"`
- `config/settings.yaml`: `laser_burst_ms`→`fire_burst_ms`, เพิ่ม `control.scan_speed` (ความเร็วมอเตอร์ป้อมตอนกวาด แยกจาก `scan_step_deg_per_sec` ที่ตอนนี้ใช้แค่จับจังหวะ)
- `tests/test_aimer.py`, `test_command_sender.py`, `test_orchestrator.py`: เขียนใหม่ตาม interface ใหม่ทั้งหมด — รันผ่านหมด (`python tests/test_<name>.py -v`)

**ยังไม่ทำ (งานถัดไป ณ ตอนนั้น):**
- Flash `firmware/esp32_wroom` ตัวที่แก้แล้ว แล้วทดสอบ UDP round-trip จริงกับ format v1.2 (parse/clamp/fail-safe ของ TURRET/TILT/FIRE)
- Tune PID gains จริง (position-PID เดิม → velocity/effort-PID) กับฮาร์ดแวร์จริง

---

## เดิม: เรื่องด่วนที่สุด (ปิดแล้ว 2026-07-13) — protocol เปลี่ยนแล้ว โค้ดยังไม่ตาม (2026-07-01)

วันนี้ค้นพบว่าฮาร์ดแวร์จริง (ดัดแปลงจากรถบังคับอายุ ~20 ปี) **ไม่มีเซนเซอร์วัดมุมเลยทั้ง pan และ tilt** — เดิมคิดว่า pan/tilt เป็น servo เลยออกแบบให้ส่งองศาสัมบูรณ์ (`TURRET:PAN:angle`) ซึ่งทำไม่ได้จริงกับมอเตอร์ DC เปล่า

**แก้เอกสารแล้ว** (`decisions.md`, `SPEC.md`, `config/protocol_contract.yaml`, `AGENTS.md`, `overview/overview.md`, `README.md`, `hardware/pin_map.md`) ให้ตรงกับฮาร์ดแวร์จริง:
- `TURRET:direction:speed` (LEFT/RIGHT/STOP) แทน `TURRET:PAN:angle`
- `TILT:direction:speed` (DOWN/STOP เท่านั้น ไม่มี UP — เงยขึ้นเป็นสปริงคืนตัวเอง) แทน `TILT:PITCH:angle`
- `LASER` เปลี่ยนชื่อเป็น `FIRE` (ของจริงคือกลไกสปริงยิงด้วยมอเตอร์ DC ไม่ใช่เลเซอร์)
- แนวคิด: ใช้กล้องเป็น feedback แทน potentiometer (visual servoing) — ส่งทิศทาง+ความเร็วทุกรอบ loop ~20Hz แทนองศาสัมบูรณ์

**โค้ดยังไม่แก้ตาม ณ ตอนนั้น** (ตั้งใจแยกเป็นสองงาน: เอกสารก่อน โค้ดทีหลัง — งานนี้เสร็จแล้วดูหัวข้อด้านบน) — ไฟล์ที่ต้องแก้ตอนนั้น:
- `src/logic/aimer.py` — เปลี่ยน output จาก absolute angle (`current_pan`/`current_tilt` accumulator) เป็น (direction, speed) ต่อแกน, ลบ clamp -180..180/-90..90 แบบเดิม
- `src/actuators/command_sender.py` — เปลี่ยน `turret(angle)`→`turret(direction, speed)`, `tilt(angle)`→`tilt(direction, speed)`, `laser(...)`→`fire(...)`
- `src/main.py` — `Orchestrator._on_target_found`/`_on_target_lost`/`ScanPattern` ต้องเรียก method ใหม่ตามข้างบน
- `firmware/esp32_wroom/src/main.cpp` — `handleTurret`/`handleTilt`/`handleLaser` ต้องเปลี่ยน signature รับ direction enum ไม่ใช่ angle, เปลี่ยนชื่อ handleLaser→handleFire
- `tests/test_aimer.py`, `tests/test_command_sender.py`, `tests/test_orchestrator.py` — ต้องเขียนใหม่ตาม interface ใหม่
- `config/settings.yaml` — key `control.laser_burst_ms` อาจเปลี่ยนชื่อให้ตรง (`fire_burst_ms`?), ทบทวน PID gains (จาก position-PID เป็น velocity/effort-PID ความหมายเปลี่ยน ต้อง tune ใหม่)

---

## ฮาร์ดแวร์จริงที่รู้แล้ว (2026-07-01)

- **Pan** (ซ้าย-ขวา): มอเตอร์ DC ผ่าน L298N#2, ไม่มี potentiometer/encoder
- **Tilt** (ก้ม-เงย): มอเตอร์ DC ตัวเดียวดันลงทางเดียวผ่าน cam/worm, เงยขึ้น = สปริงคืนตัวเอง (passive), ไม่มีเซนเซอร์
- **ตัวยิง (FIRE):** มอเตอร์ DC หมุนทางเดียวปล่อยสปริงยิง — ทดสอบ 9V กับมอเตอร์รถบังคับเดิมแล้วใช้ได้ (ไม่รู้แรงเทียบเท่าของเดิมแค่ไหน)
- **เลเซอร์วัดระยะ:** แค่ไอเดียอนาคต ยังไม่มีของจริง ไม่อยู่ใน protocol ตอนนี้
- **บอร์ด:** ESP32-CAM ที่ COM4 (CH340), ESP32-WROOM ที่ COM5 (CH9102) — **มีสาย USB data ใช้งานได้เส้นเดียว ต้องสลับใช้ทีละบอร์ด**
- ทั้งสองบอร์ดตอนนี้กินไฟจากสาย USB อัปโหลดเท่านั้น ยังไม่ได้ต่อไฟเสริม/แบต — **ห้ามต่อ L298N เข้าจริงตอนนี้** (รอ pin map + โค้ดขับ PWM จริง + แบตแยก — pin map + PWM ทำเสร็จแล้ว ดู current-task.md)

---

## src/ ที่เขียนไปแล้ว (รอบแรก — ใช้ protocol เก่า)

| บทบาท | ไฟล์ | ทดสอบ |
|---|---|---|
| ตัวรับภาพ | `src/vision/frame_receiver.py` | live-test กับกล้องจริงแล้ว (`scripts/test_camera_stream.py`) |
| ตัวตรวจจับ | `src/vision/detector.py` (YOLOv8n) | สั่ง inference จริงแล้ว, โหลดโมเดลอัตโนมัติ |
| ตัวติดตาม | `src/logic/tracker.py` (Kalman constant-velocity) | `tests/test_tracker.py` — ไม่กระทบจาก protocol เปลี่ยน |
| ตัวเล็ง | `src/logic/aimer.py` | ✅ แก้ตาม protocol v1.2 แล้ว (2026-07-13) |
| ตัวสั่งบอร์ด | `src/actuators/command_sender.py` | ✅ แก้ตาม protocol v1.2 แล้ว (2026-07-13) |
| ตัวคุมหลัก | `src/main.py` (`Orchestrator`) | ✅ แก้ตาม protocol v1.2 แล้ว (2026-07-13) |

รัน unit test ทั้งหมด: `python tests/test_<name>.py -v` (ยังไม่ได้ตั้ง pytest — ใช้ stdlib `unittest`) — 25 เคสผ่านหมด (2026-07-13)
