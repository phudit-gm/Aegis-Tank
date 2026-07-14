# Changelog

## [Unreleased]

### Added
- Protocol v1.2 → v1.3: เปลี่ยน `TURRET`/`TILT` จาก absolute angle เป็น `direction`+`speed` (visual servoing, ไม่มีเซนเซอร์วัดมุม), `LASER`→`FIRE`, เพิ่ม `TRACK:PIVOT_LEFT/PIVOT_RIGHT` แยกจาก skid-turn เดิม
- `firmware/esp32_cam` — เขียน+flash แล้ว ทำงานจริง (MJPEG stream `:81/stream`, index page `:80`, ~38-58 fps)
- `firmware/esp32_wroom` — โค้ดขับ PWM/GPIO จริงแล้วตาม protocol v1.3 (`driveChannel`, `enterSafeState` fail-safe, non-blocking `handleFire`), compile ผ่านทั้ง `esp32wroom`/`esp32wroom_ota`, ยังไม่ flash ตัวจริง
- `src/` ฝั่ง PC — ครบ 6 บทบาท (`vision/`, `logic/`, `actuators/`, `utils/`, `main.py`) ตรง protocol v1.3, unit test ผ่านหมด 26 เคส
- `hardware/pin_map.md` กำหนด pin map จริงแล้ว
- Wokwi simulation: `wokwi.toml` + `diagram.json` ที่ root, custom chip `chip-l298n` (`github:drf5n/Wokwi-Chip-L298N@1.0.5`) x2 สำหรับ TRACK/TURRET/TILT, `wokwi-cli lint` ผ่าน

### Added (initial)
- สร้างโครงโปรเจค **Aegis-Tank** (รื้อใหม่จาก R.N.T. ที่กระจัดกระจาย 3 ที่)
- AGENTS.md, SPEC.md, README.md, overview, handoff
- `config/protocol_contract.yaml` v1.0 — ยกจากโปรเจคเดิม
- `hardware/pin_map.md` — pin map, power wiring, EMI, ข้อควรระวังแบต
- โครงโฟลเดอร์: src/{vision,logic,actuators,utils}, firmware/{esp32_cam,esp32_wroom}, hardware, models, data, web, scripts, tests
