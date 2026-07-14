# Hardware — Pin Map

> ยังไม่ได้ต่อสายจริง — pin map และ wiring รอกำหนดตอนประกอบ

## สิ่งที่ทราบแล้ว

- **อุปกรณ์หลัก:** ESP32-WROOM-32, ESP32-CAM, L298N x2, มอเตอร์ DC ยิง (spring-release, ไม่ใช่เลเซอร์ — ดู `decisions.md`)
- **ไฟเลี้ยง:** Li-Po 2S ผ่าน DC-DC step-down สำหรับบอร์ด + L298N รับตรงจากแบต

## ⚠️ ฮาร์ดแวร์จริงที่ค้นพบ (2026-07-01 — ดัดแปลงจากรถบังคับอายุ ~20 ปี)

- **Pan** (หมุนซ้าย-ขวา): มอเตอร์ DC ผ่าน L298N#2 channel A — **ไม่มีเซนเซอร์วัดมุม** (ไม่มี potentiometer/encoder)
- **Tilt** (ก้ม-เงย): มอเตอร์ DC ตัวเดียวผ่าน L298N#2 channel B หมุน cam/worm **ดันโครงปืนลงทางเดียวเท่านั้น** — เงยขึ้นเกิดจาก **สปริงคืนตัวเอง (passive return spring)** ไม่ใช้มอเตอร์ ไม่มีเซนเซอร์วัดมุมเช่นกัน
- **ตัวยิง (FIRE):** มอเตอร์ DC หมุนทางเดียวปล่อยสปริงยิง — ทดสอบด้วย 9V กับมอเตอร์รถบังคับเดิมแล้วใช้ได้ (ไม่รู้แรงบิดเทียบเท่าของเดิมแค่ไหน)
- ผลกระทบ: pan/tilt ควบคุมแบบ position สัมบูรณ์ไม่ได้ (ไม่มี feedback) ต้องใช้ทิศทาง+ความเร็ว + กล้องเป็นตัวปิด loop แทน (ดู `SPEC.md §1-2`, `decisions.md`)

## GPIO ที่ห้ามแตะ (ทุกกรณี)

- **GPIO 6–11** — flash chip ภายใน
- **GPIO 0** — boot mode select
- **GPIO 34–39** — input only (ใช้ output ไม่ได้)

## GPIO Map — ESP32-WROOM-32 (กำหนดแล้ว 2026-07-13, ยังไม่ได้ต่อสายจริง)

> เลี่ยง: GPIO 0 (boot mode), GPIO 1/3 (UART0 — ใช้กับ Serial), GPIO 2/12/15 (boot strapping pins),
> GPIO 6–11 (flash ภายใน), GPIO 34–39 (input-only — กันไว้ให้ potentiometer pan/tilt ในอนาคต)

| ฟังก์ชัน | IN A | IN B | PWM (EN) |
|---|---|---|---|
| TRACK ล้อซ้าย (L298N#1 ch A) | GPIO4 | GPIO5 | GPIO13 |
| TRACK ล้อขวา (L298N#1 ch B) | GPIO16 | GPIO17 | GPIO18 |
| TURRET (L298N#2 ch A) | GPIO19 | GPIO21 | GPIO22 |
| TILT (L298N#2 ch B, ทิศ DOWN เท่านั้น) | GPIO23 | GPIO25 | GPIO26 |
| FIRE (MOSFET gate, digital ล้วน ไม่มี PWM) | GPIO27 | — | — |

**เหตุผลที่ FIRE ไม่ใช้ L298N ตัวที่ 3:** L298N สองตัว (4 channel) พอดีกับ TRACK×2 + TURRET + TILT อยู่แล้ว FIRE เป็นแค่ ON/OFF ทิศเดียว (ไม่ต้องกลับทิศ) ใช้ MOSFET switch 1 GPIO ถูกกว่าและง่ายกว่า driver เต็ม channel

สำรองไว้: **GPIO32, GPIO33** — เผื่อ potentiometer pan/tilt ในอนาคต หรือ status LED

โค้ดที่ implement ตาม pin map นี้: `firmware/esp32_wroom/src/main.cpp`

## รอกำหนดตอนประกอบจริง

- Power wiring และ common ground plan — **สำคัญ:** L298N ต้องกินไฟจากแบตแยก ไม่ใช่ USB (ยังไม่ได้ต่อไฟเสริมตอนนี้)
- Pin map ของ ESP32-CAM
- (อนาคต ถ้าต้องการความแม่นยำขึ้น) จุดติดตั้ง potentiometer/encoder วัดมุม pan/tilt — ยังไม่มีของจริง (จะใช้ GPIO32/33 สำรองด้านบน)

อัปเดตไฟล์นี้พร้อมแผนผัง wiring ตอนเริ่มต่อสายจริง
