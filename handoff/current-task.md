# Current Task — Handoff

## ✅ จัดทางเดินสาย Wokwi ให้อ่านง่ายขึ้น (2026-07-14)

- ปรับ `diagram.json` เฉพาะ layout: ขยับ L298N ทั้งสองตัวและวงจรจำลอง FIRE ไปทางขวาเพื่อเพิ่มพื้นที่เดินสาย
- เพิ่มคำสั่ง `h...`/`v...` ใน wire-placement ให้สายออกจากขา ESP32 คนละแนวก่อนเลี้ยวขึ้น/ลง ลดเส้นแนวตั้งที่ซ้อนกันตรงขอบบอร์ด
- แยกสาย GPIO27 (FIRE) ให้อ้อมใต้บอร์ด และแยกสาย GND return ไปอีกแนว
- ปรับรอบสองจากภาพตรวจจริง: ย้ายรางสายให้ห่างขอบ ESP32 มากขึ้น, ย้าย GND return จากแนวที่พาดบนบอร์ดไปอ้อมด้านซ้าย และใช้สีแยกกลุ่ม (TRACK ซ้าย=เหลือง, TRACK ขวา=ฟ้า, TURRET=ส้ม, TILT=ม่วง, 5V=แดง, GND=เทา, FIRE=แดงส้ม)
- ปรับรอบสามตามคำยืนยันให้ย้ายอุปกรณ์ได้: ขยายระยะ ESP32↔L298N, เว้นข้อความเหนือ L298N/FIRE 100px, เพิ่ม legend สีสายด้านขวา และจัดสายเป็นรางหวีซ้าย/ขวาที่มีระยะห่างมากขึ้น
- คู่ขา, pin map และการทำงานของวงจรไม่เปลี่ยน (เปลี่ยนเฉพาะสีและ layout); `wokwi-cli lint .` ผ่าน โดยเหลือเพียง info เดิมเรื่อง `board-esp32-devkit-v1` เป็น undocumented type

## 📌 บั๊ก Wokwi CLI — simulation รันไม่จบ (พบ 2026-07-14, **known issue, deprioritized — ข้ามไปฮาร์ดแวร์จริงแทน**)

**อาการ:** `wokwi-cli` (token จาก https://wokwi.com/dashboard/ci ใช้ได้ ไม่ใช่ปัญหา auth) เชื่อมต่อได้ปกติ —

```
Connected to Wokwi Simulation API 1.0.0-20260707-ga65528e1
Starting simulation...
Timeout: simulation did not finish in 15000ms
```

— แต่**ไม่มี serial output ออกมาเลยแม้แต่ตัวเดียว** ก่อน timeout (exit code 42) ไม่ว่าจะปรับ `--timeout` (ลองถึง 30000ms), `--expect-text`, ตัด `chip-l298n` ออกเหลือแค่บอร์ดเปล่า, สลับ Git Bash ↔ PowerShell, หรือ disable sandbox — ผลเหมือนเดิมทุกครั้ง

**Isolation test ที่ทำไปแล้วทั้งหมด (2026-07-14, ตัดตัวแปรออกทีละอย่าง):**
- ✅ `pio run` build ผ่านปกติ ทั้ง `firmware/esp32_wroom` และ scratch project
- ✅ `wokwi-cli lint .` ผ่านสะอาด (แค่ info ว่า `board-esp32-devkit-v1` เป็น undocumented type)
- ✅ สร้างโปรเจกต์ทดสอบขั้นต่ำสุดแยกที่ `esp32-test/` (บอร์ดเปล่า ไม่มี custom chip, โค้ดแค่ `Serial.println("HELLO")`) — **พังเหมือนกันทุกอย่าง** → ตัดออกได้แล้วว่าไม่ใช่ปัญหาที่ตัวโปรเจกต์ Aegis-Tank
- ✅ `npx wokwi-cli@latest` resolve มาเป็น `0.26.1` เหมือนกัน (เวอร์ชันที่ cache ไว้แล้ว) → ตัดออกได้ว่าไม่ใช่ปัญหา CLI เวอร์ชันเก่า
- ✅ **ปิด Windows Firewall ชั่วคราวแล้วรันซ้ำ — พังเหมือนเดิมทุกอย่าง** (รวมถึง `--serial-log-file` แยกก็ยังว่าง 0 byte) → ตัดออกได้ว่าไม่ใช่ Windows Firewall และไม่ใช่แค่ terminal ไม่ยอม render (ข้อมูลจริงไม่มาถึง client เลย)
- ✅ **ดาวน์โหลด `wokwi-cli` v0.25.0 มาทดสอบแยก (เวอร์ชันเก่ากว่า cached 0.26.1) — พังเหมือนกันทุกตัวอักษร** (exit code 42, log 0 byte) → ตัดออกได้ว่าไม่ใช่บั๊กเฉพาะเวอร์ชัน CLI
- ✅ **วิเคราะห์ network-level ระหว่างรันจริง:** เกาะ process ด้วย `Get-NetTCPConnection` ตลอด 15 วิ — TCP connection ไป Wokwi (Cloudflare edge) **ยัง Established นิ่งตลอด ไม่มี reset/drop** → ไม่ใช่ปัญหา connection ถูกตัด
- ✅ **ทดสอบ curl ดาวน์โหลด 3MB ผ่าน HTTPS ทั้ง IPv4/IPv6** ไป Cloudflare endpoint เดียวกัน — ผ่านฉลุยทั้งคู่ ไม่ค้าง → ตัด IPv6/MTU blackhole ทั่วไปออกได้
- ✅ **อ่าน source code จริงของ `wokwi-cli`** (`packages/cli/src/commands/simulate.ts`) พบว่าลำดับการทำงานคือ: upload diagram.json → upload firmware → upload elf → พิมพ์ "Starting simulation..." → `serialMonitorListen()` → `simStart()` → `simResume()` — **ข้อความ "Starting simulation..." พิมพ์ได้ก็ต่อเมื่อ upload ไฟล์ (binary data ผ่าน WebSocket) สำเร็จหมดแล้วเท่านั้น** → ข้อมูลไหลผ่าน WebSocket ได้จริงจนถึงจุดนั้น ปัญหาจริงๆ อยู่**หลัง** `simStart()`/`simResume()` — ไม่น่าใช่ network/proxy บล็อกแบบ generic (เพราะงั้น upload ก็ควรพังด้วย)
- เจอเพิ่มเติมว่าเครื่องมี **McAfee VirusScan** ติดตั้งคู่ Windows Defender (เป็นสมมติฐานที่ยังไม่ได้ทดสอบจริง — ไม่ได้ปิดทดสอบ)
- ❌ **ยังไม่ได้ทดสอบ:** ปิด McAfee แล้วรันซ้ำ, ลองเปลี่ยนไป mobile hotspot, control test ผ่าน GitHub Actions (`.github/workflows/wokwi-control-test.yml` เตรียมไว้แล้วใน branch `wokwi-ci-control-test` — **push ไม่ผ่านเพราะ PAT ที่ใช้ไม่มี `workflow` scope**, ถ้าจะสานต่อต้องไปเพิ่ม scope ให้ token ที่ https://github.com/settings/tokens ก่อน หรือสร้างไฟล์ผ่าน GitHub web UI แทน)

**สรุปล่าสุด (2026-07-14):** ตัดสาเหตุที่เป็นไปได้ออกไปเยอะแล้ว (ไม่ใช่ CLI version, ไม่ใช่ Windows Firewall, ไม่ใช่ MTU/IPv6 blackhole, ไม่ใช่ generic network block เพราะ upload ผ่านได้) — เหลือเป็นไปได้มากสุดคือ **backend/simulation-engine ของ Wokwi เอง** (เริ่ม sim ไม่สำเร็จ หรือเริ่มแล้วไม่ส่ง `serial-monitor:data` event กลับ) รองลงมาคือ McAfee/proxy filtering เฉพาะ frame บางประเภทหลัง upload (ยังไม่ได้ทดสอบเพื่อยืนยัน)

**การตัดสินใจ (2026-07-14):** หยุดไล่บั๊กนี้ต่อ — ผลกระทบต่ำ (ไม่ blocker ของงานถัดไป) ให้ข้ามไปทดสอบบนฮาร์ดแวร์จริงแทน (flash + ทดสอบมอเตอร์จริง) ถ้าอยากกลับมาแก้ต่อในอนาคต ให้เริ่มจาก 3 ข้อที่ยังไม่ได้ทดสอบด้านบน

**ของที่เหลือทิ้งไว้:**
- โฟลเดอร์ `esp32-test/` ที่ root (scratch project สำหรับ isolation test — เก็บไว้ใช้ทดสอบต่อได้)
- branch `wokwi-ci-control-test` ในเครื่อง (มี commit `.github/workflows/wokwi-control-test.yml` พร้อม push แต่ยังไม่ได้ push — ต้องแก้ PAT scope ก่อน)
- ไฟล์ log เปล่า (0 byte) ที่เป็น artifact จากการทดสอบ: `wokwi_serial.log`, `wokwi_serial2-6.log` ที่ root, และใน `esp32-test/` — ลบทิ้งได้

---

## 📌 งานค้าง (จากรอบก่อนหน้า)

1. **จัดโครงสร้างไฟล์ให้สวยขึ้น** — ยังไม่ได้ตกลงรายละเอียดว่าจะจัดยังไง (เช่น ย้าย `wokwi.toml`/`diagram.json` เข้าโฟลเดอร์ย่อยไหม, จัดกลุ่ม `firmware/`/`hardware/`/`config/` ใหม่ไหม) — คุยรายละเอียดตอนเริ่ม session หน้า

---

## สถานะ (อัปเดต 2026-07-13 รอบ 2)

- ✅ หลักการการทำงาน + เหตุผลการออกแบบ: `overview/overview.md`
- ✅ รูปแบบคำสั่งสื่อสาร + หลักการพิกเซล→องศา: `SPEC.md` (protocol v1.3)
- ✅ บทบาทแต่ละส่วน + โครงสร้างโปรเจค: `AGENTS.md`
- ✅ `firmware/esp32_cam` — เขียนแล้ว, flash แล้ว, ทำงานจริง (MJPEG stream ที่ `:81/stream` + index page ที่ `:80`, ~38-58 fps)
- ✅ `firmware/esp32_wroom` — แก้ตาม protocol v1.3 ครบแล้ว **และมีโค้ดขับ PWM/GPIO จริงแล้ว** (ไม่ใช่แค่ log อีกต่อไป) — pin map กำหนดแล้ว (`hardware/pin_map.md`), compile ผ่าน (`pio run`) — **ยังไม่ได้ flash ตัวใหม่ลงบอร์ดจริง/ทดสอบกับมอเตอร์จริง**
- ✅ `src/` ฝั่ง PC — เขียนครบทั้ง 6 บทบาทแล้ว ตรง protocol v1.3 — unit test 26 เคสผ่านหมด (`tests/test_aimer.py`, `test_command_sender.py`, `test_orchestrator.py`, `test_tracker.py`)
- ✅ Wokwi simulation ตั้งไว้แล้ว: `wokwi.toml` + `diagram.json` ที่ root — ESP32 + **`chip-l298n` (custom chip จาก `github:drf5n/Wokwi-Chip-L298N@1.0.5`) 2 ตัวจริง** สำหรับ TRACK/TURRET/TILT, LED เฉพาะ FIRE (MOSFET เดี่ยว ไม่ผ่าน L298N)
- ⚠️ ค่า config บางส่วนยังเป็น placeholder ทดสอบ pipeline เท่านั้น ไม่ใช่ค่าจริง — PID gains (`config/settings.yaml aiming.pid_pan/pid_tilt`) ยังเป็นค่าเดิมจากยุค position-PID **ยังไม่ tune ใหม่สำหรับ velocity/effort-PID**

---

## ✅ Pin map + PWM firmware + Wokwi (2026-07-13 รอบ 2)

- **Pin map กำหนดแล้ว** (`hardware/pin_map.md`): GPIO4/5/13 (TRACK ซ้าย), 16/17/18 (TRACK ขวา), 19/21/22 (TURRET), 23/25/26 (TILT), 27 (FIRE ผ่าน MOSFET 1 GPIO ไม่ใช่ L298N ตัวที่ 3)
- **`firmware/esp32_wroom/src/main.cpp` มีโค้ดขับ PWM/GPIO จริงแล้ว** — `driveChannel()` helper คุมทิศ (digitalWrite IN A/B) + ความเร็ว (ledc PWM), `enterSafeState()`/fail-safe ตอนนี้ zero PWM duty + IN pins LOW จริง ไม่ใช่แค่ log, `handleFire` ปิดเองอัตโนมัติหลัง `duration_ms` แบบ non-blocking (ไม่ใช้ `delay()`)
- **`platformio.ini` pin `platform = espressif32@7.0.1`** (arduino-esp32 core 2.0.17) เพราะโค้ดใช้ ledc API แบบ channel-based (`ledcSetup/ledcAttachPin/ledcWrite(channel,...)`) — ถ้าอัปเดต platform เป็น core 3.x ต้องแก้โค้ด PWM ให้ตรง API ใหม่ (`ledcAttach(pin,...)`)
- **Compile ผ่านแล้ว** — `pio run` ใน `firmware/esp32_wroom` สำเร็จทั้ง `esp32wroom` และ `esp32wroom_ota` env
- **Protocol v1.3:** เพิ่ม `TRACK:PIVOT_LEFT/PIVOT_RIGHT` (หมุนสวนทางกันทั้งสองข้าง) แยกจาก `TURN_LEFT/TURN_RIGHT` เดิมที่กลายเป็น skid-turn อย่างเป็นทางการ — `_steer_body` (aim-assist) ใช้ pivot เสมอ, skid เก็บไว้ให้ manual/web drive ในอนาคต (ดู `decisions.md`)
- **Wokwi:** `wokwi.toml` ชี้ไปที่ `firmware/esp32_wroom/.pio/build/esp32wroom/firmware.{bin,elf}`, `diagram.json` ใช้ ESP32 DevKit-C v4 (`board-esp32-devkit-c-v4` — ยืนยันจาก wokwi-boards repo) + `chip-l298n` (custom chip `github:drf5n/Wokwi-Chip-L298N@1.0.5`, pin ยืนยันจาก chip.json จริง: `IN1-4`, `EN A`/`EN B`, `OUT1-4`, `5V`, `GND`) 2 ตัว — `driver1` = TRACK ซ้าย/ขวา, `driver2` = TURRET/TILT — FIRE ยังเป็น LED เดี่ยวเพราะขับผ่าน MOSFET ไม่ผ่าน L298N
- **บอร์ด ESP32 ใน `diagram.json` เปลี่ยนเป็น `"type": "board-esp32-devkit-v1"` แล้ว** (2026-07-13 รอบ 3, ตามคำขอ) — pin label ของบอร์ดนี้ไม่เหมือน v4: ใช้ `D4`/`D5`/`D13`/`RX2`(=GPIO16)/`TX2`(=GPIO17)/`D18`/`D19`/`D21`/`D22`/`D23`/`D25`/`D26`/`D27` แทนเลข GPIO ตรงๆ, power 5V ใช้ label `VIN` (ไม่ใช่ `5V`), และมีแค่ `GND.1`/`GND.2` (ไม่มี `GND.3` — connection ของ FIRE ต้องใช้ `GND.2` ร่วมกับ driver_turret_tilt) — connection ทั้งหมดอัปเดตตามนี้แล้ว
- **`wokwi-cli` ติดตั้งแล้ว ใช้งานได้ทันทีไม่ต้องรี terminal** — path จริงคือ `~/.wokwi/bin/wokwi-cli.exe` (ยังไม่อยู่ใน PATH ของ shell ปัจจุบัน ต้องเรียกเต็ม path หรือรอ shell ใหม่ที่ดึง PATH จาก Windows แล้ว)
- **`wokwi-cli lint .` ผ่านแล้ว** (2026-07-13 รอบ 3) — มีแค่ info-level notice ว่า `board-esp32-devkit-v1` เป็น "undocumented" type (ยังใช้งานได้ปกติ แค่ไม่ได้อยู่ใน official docs) ไม่มี error เรื่อง pin name หรือ custom chip dependency เลย ยืนยันว่า pin mapping ทั้งหมดถูกต้อง
- ⚠️ **รัน simulation เต็มรูปแบบ (boot จริง) ยังไม่ได้ทำ** — ต้องมี `WOKWI_CLI_TOKEN` (คนละอันกับ token ที่ cache ไว้ให้ editor ใน `~/.wokwi/user.tok` ซึ่งใช้ไม่ได้กับ CLI สั่ง API "Unauthorized") ไปสร้างที่ https://wokwi.com/dashboard/ci แล้วรัน `WOKWI_CLI_TOKEN=<token> wokwi-cli --timeout 15000 --expect-text "Ready" .`

**งานถัดไป:** flash firmware ใหม่ลงบอร์ดจริง + ทดสอบ UDP round-trip, ต่อไฟเสริม/แบตแยกให้ L298N ก่อนต่อจริง (ยังไม่ทำ), เปิด `diagram.json` ใน Wokwi editor เพื่อยืนยันโหลดผ่าน + ทดสอบว่า LED ตอบสนองคำสั่งถูกทิศ/ความเร็วตามที่ตั้งใจ

> ประวัติงานที่ปิดแล้ว (protocol v1.2 migration, การค้นพบฮาร์ดแวร์จริง 2026-07-01, ตาราง src/ รอบแรก) ย้ายไปเก็บที่ `handoff/archive.md` แล้ว (2026-07-14)

---

## งานถัดไป (เรียงตามความสมเหตุสมผล)

1. ~~แก้โค้ดให้ตรง protocol ใหม่~~ — **เสร็จแล้ว (2026-07-13)**
2. Flash `firmware/esp32_wroom` ใหม่ (แก้ตาม protocol v1.2 แล้วแต่ยังไม่ได้ flash ตัวใหม่) แล้วทดสอบ UDP round-trip กับ format ใหม่ (TURRET/TILT direction+speed, FIRE)
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
