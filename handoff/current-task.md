# Current Task — Handoff

## สถานะ (อัปเดต 2026-07-01 ค่ำ)

- ✅ หลักการการทำงาน + เหตุผลการออกแบบ: `overview/overview.md`
- ✅ รูปแบบคำสั่งสื่อสาร + หลักการพิกเซล→องศา: `SPEC.md` (**เพิ่งแก้รอบใหญ่ — อ่านหัวข้อถัดไปก่อน**)
- ✅ บทบาทแต่ละส่วน + โครงสร้างโปรเจค: `AGENTS.md`
- ✅ `firmware/esp32_cam` — เขียนแล้ว, flash แล้ว, ทำงานจริง (MJPEG stream ที่ `:81/stream` + index page ที่ `:80`, ~38-58 fps)
- ✅ `firmware/esp32_wroom` — เขียน skeleton แล้ว, flash แล้ว (COM5, IP `192.168.1.111`), ทดสอบ UDP round-trip สำเร็จ (parse/clamp/fail-safe ผ่านหมด) — **แต่ยังใช้ protocol แบบเก่า (angle-based) อยู่ ต้องแก้**
- ✅ `src/` ฝั่ง PC — เขียนครบทั้ง 6 บทบาทแล้ว มี unit test ผ่านหมด — **แต่ `aimer.py`/`command_sender.py`/`main.py` ยังใช้ protocol แบบเก่าอยู่เช่นกัน ต้องแก้**
- ⚠️ ค่า config บางส่วนยังเป็น placeholder ทดสอบ pipeline เท่านั้น ไม่ใช่ค่าจริง

---

## ⚠️⚠️ เรื่องด่วนที่สุด: protocol เปลี่ยนแล้ว โค้ดยังไม่ตาม (2026-07-01)

วันนี้ค้นพบว่าฮาร์ดแวร์จริง (ดัดแปลงจากรถบังคับอายุ ~20 ปี) **ไม่มีเซนเซอร์วัดมุมเลยทั้ง pan และ tilt** — เดิมคิดว่า pan/tilt เป็น servo เลยออกแบบให้ส่งองศาสัมบูรณ์ (`TURRET:PAN:angle`) ซึ่งทำไม่ได้จริงกับมอเตอร์ DC เปล่า

**แก้เอกสารแล้ว** (`decisions.md`, `SPEC.md`, `config/protocol_contract.yaml`, `AGENTS.md`, `overview/overview.md`, `README.md`, `hardware/pin_map.md`) ให้ตรงกับฮาร์ดแวร์จริง:
- `TURRET:direction:speed` (LEFT/RIGHT/STOP) แทน `TURRET:PAN:angle`
- `TILT:direction:speed` (DOWN/STOP เท่านั้น ไม่มี UP — เงยขึ้นเป็นสปริงคืนตัวเอง) แทน `TILT:PITCH:angle`
- `LASER` เปลี่ยนชื่อเป็น `FIRE` (ของจริงคือกลไกสปริงยิงด้วยมอเตอร์ DC ไม่ใช่เลเซอร์)
- แนวคิด: ใช้กล้องเป็น feedback แทน potentiometer (visual servoing) — ส่งทิศทาง+ความเร็วทุกรอบ loop ~20Hz แทนองศาสัมบูรณ์

**โค้ดยังไม่แก้ตาม** (ตั้งใจแยกเป็นสองงาน: เอกสารก่อน โค้ดทีหลัง) — ไฟล์ที่ต้องแก้รอบหน้า:
- `src/logic/aimer.py` — เปลี่ยน output จาก absolute angle (`current_pan`/`current_tilt` accumulator) เป็น (direction, speed) ต่อแกน, ลบ clamp -180..180/-90..90 แบบเดิม
- `src/actuators/command_sender.py` — เปลี่ยน `turret(angle)`→`turret(direction, speed)`, `tilt(angle)`→`tilt(direction, speed)`, `laser(...)`→`fire(...)`
- `src/main.py` — `Orchestrator._on_target_found`/`_on_target_lost`/`ScanPattern` ต้องเรียก method ใหม่ตามข้างบน
- `firmware/esp32_wroom/src/main.cpp` — `handleTurret`/`handleTilt`/`handleLaser` ต้องเปลี่ยน signature รับ direction enum ไม่ใช่ angle, เปลี่ยนชื่อ handleLaser→handleFire
- `tests/test_aimer.py`, `tests/test_command_sender.py`, `tests/test_orchestrator.py` — ต้องเขียนใหม่ตาม interface ใหม่
- `config/settings.yaml` — key `control.laser_burst_ms` อาจเปลี่ยนชื่อให้ตรง (`fire_burst_ms`?), ทบทวน PID gains (จาก position-PID เป็น velocity/effort-PID ความหมายเปลี่ยน ต้อง tune ใหม่)

**อย่าเชื่อว่าโค้ดตรงกับ `config/protocol_contract.yaml`/`SPEC.md` จนกว่าจะเช็ค/แก้ตามลิสต์นี้ก่อน**

---

## ฮาร์ดแวร์จริงที่รู้แล้ว (2026-07-01)

- **Pan** (ซ้าย-ขวา): มอเตอร์ DC ผ่าน L298N#2, ไม่มี potentiometer/encoder
- **Tilt** (ก้ม-เงย): มอเตอร์ DC ตัวเดียวดันลงทางเดียวผ่าน cam/worm, เงยขึ้น = สปริงคืนตัวเอง (passive), ไม่มีเซนเซอร์
- **ตัวยิง (FIRE):** มอเตอร์ DC หมุนทางเดียวปล่อยสปริงยิง — ทดสอบ 9V กับมอเตอร์รถบังคับเดิมแล้วใช้ได้ (ไม่รู้แรงเทียบเท่าของเดิมแค่ไหน)
- **เลเซอร์วัดระยะ:** แค่ไอเดียอนาคต ยังไม่มีของจริง ไม่อยู่ใน protocol ตอนนี้
- **บอร์ด:** ESP32-CAM ที่ COM4 (CH340), ESP32-WROOM ที่ COM5 (CH9102) — **มีสาย USB data ใช้งานได้เส้นเดียว ต้องสลับใช้ทีละบอร์ด**
- ทั้งสองบอร์ดตอนนี้กินไฟจากสาย USB อัปโหลดเท่านั้น ยังไม่ได้ต่อไฟเสริม/แบต — **ห้ามต่อ L298N เข้าจริงตอนนี้** (รอ pin map + โค้ดขับ PWM จริง + แบตแยก)

---

## src/ ที่เขียนไปแล้ว (รอบแรก — ใช้ protocol เก่า)

| บทบาท | ไฟล์ | ทดสอบ |
|---|---|---|
| ตัวรับภาพ | `src/vision/frame_receiver.py` | live-test กับกล้องจริงแล้ว (`scripts/test_camera_stream.py`) |
| ตัวตรวจจับ | `src/vision/detector.py` (YOLOv8n) | สั่ง inference จริงแล้ว, โหลดโมเดลอัตโนมัติ |
| ตัวติดตาม | `src/logic/tracker.py` (Kalman constant-velocity) | `tests/test_tracker.py` — ไม่กระทบจาก protocol เปลี่ยน |
| ตัวเล็ง | `src/logic/aimer.py` | **ต้องแก้ตามหัวข้อด้านบน** |
| ตัวสั่งบอร์ด | `src/actuators/command_sender.py` | **ต้องแก้ตามหัวข้อด้านบน** |
| ตัวคุมหลัก | `src/main.py` (`Orchestrator`) | **ต้องแก้ตามหัวข้อด้านบน** |

รัน unit test ทั้งหมด: `python tests/test_<name>.py -v` (ยังไม่ได้ตั้ง pytest — ใช้ stdlib `unittest`)

---

## งานถัดไป (เรียงตามความสมเหตุสมผล)

1. **แก้โค้ดให้ตรง protocol ใหม่** ตามลิสต์ไฟล์ในหัวข้อ "เรื่องด่วนที่สุด" ด้านบน
2. Flash `firmware/esp32_wroom` ใหม่ (ตอนนี้ยังเป็น skeleton เก่า) แล้วทดสอบ UDP round-trip กับ format ใหม่
3. รัน `python -m src.main` ทดสอบ end-to-end ครั้งแรกทั้งระบบ (ต้องมีทั้งสองบอร์ดต่อ WiFi พร้อมกัน แต่ USB flash ทีละบอร์ดได้ ไม่ต้องต่อ USB พร้อมกันตอนรัน main loop จริง)
4. Calibrate ค่าจริง: horizontal/vertical FOV, PID gains (ความหมายเปลี่ยนจาก position เป็น velocity/effort แล้ว), aim tolerance, fail-safe timeout ms
5. ตัดสินใจ `TARGET_CLASS` จริงของโปรเจค (ตอนนี้ตั้ง `"person"` ไว้ทดสอบ pipeline เท่านั้น)
6. ตั้ง DHCP reservation หรือ static IP ให้ทั้งสองบอร์ด (ตอนนี้ IP เปลี่ยนได้ถ้า router reboot)
7. ตัดสินใจ pin map จริง (`hardware/pin_map.md`) + ต่อไฟเสริม/แบตแยกให้ L298N ก่อนต่อฮาร์ดแวร์จริง

---

## ข้อควรรู้

- ของเก่ายังอยู่ครบ: `C:\Project_RNT_Specification`, vault R.N.T, vault ESP32-CAM MJPEG Streaming — ดึงโค้ดอ้างอิงได้ถ้าต้องการ
- flash ESP32 ใช้ PlatformIO CLI ได้แล้ว (ดู global skill `embedded-flash-monitor` — auto-reset ได้ผ่าน RTS pin ไม่ต้องกด RST เอง ทั้ง esp32_cam (COM4) และ esp32_wroom (COM5))
- เครือข่าย: ตัดสินใจแล้วว่าใช้ **home WiFi client mode** ไม่ทำ AP (ดู `decisions.md`)
- tracking algorithm: ตัดสินใจแล้วว่าใช้ **Kalman filter** (ดู `decisions.md`)
- pan/tilt/fire: ตัดสินใจแล้วว่าใช้ **direction+speed แบบ visual servoing** ไม่ใช่ absolute angle (ดู `decisions.md`)
