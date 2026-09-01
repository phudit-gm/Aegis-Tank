# Hardware — Pin Map

> Not yet wired up for real — pin map and wiring are pending assembly

## What's known so far

- **Main hardware:** ESP32-WROOM-32, ESP32-CAM, L298N x2, firing DC motor (spring-release, not a laser — see `decisions.md`)
- **Power:** Li-Po 2S through a DC-DC step-down for the boards + L298N draws directly from the battery

## ⚠️ Real hardware discovered (2026-07-01 — converted from a ~20-year-old RC car)

- **Pan** (left-right rotation): DC motor through L298N#2 channel A — **no angle sensor** (no potentiometer/encoder)
- **Tilt** (up-down): a single DC motor through L298N#2 channel B turns a cam/worm that **only pushes the gun mount down, one direction** — tilting up comes from a **passive return spring**, no motor involved, also no angle sensor
- **Firing mechanism (FIRE):** a DC motor spins one direction to release the firing spring — tested at 9V with the original RC car's motor, works (unknown how the torque compares to the original)
- Implication: pan/tilt cannot be controlled with absolute position (no feedback) — must use direction+speed + the camera as the closed loop instead (see `SPEC.md §1-2`, `decisions.md`)

## GPIOs never to touch (in any case)

- **GPIO 6–11** — internal flash chip
- **GPIO 0** — boot mode select
- **GPIO 34–39** — input only (can't be used as output)

## GPIO Map — ESP32-WROOM-32 (defined 2026-07-13, TRACK right remapped 2026-07-30)

> Avoid: GPIO 0 (boot mode), GPIO 1/3 (UART0 — used with Serial), GPIO 2/12/15 (boot strapping pins),
> GPIO 6–11 (internal flash), GPIO 34–39 (input-only — reserved for a future pan/tilt potentiometer)

| Function | IN A | IN B | PWM (EN) |
|---|---|---|---|
| TRACK left wheel (L298N#1 ch A) | GPIO4 | GPIO5 | GPIO13 |
| TRACK right wheel (L298N#1 ch B) | GPIO32 | GPIO33 | GPIO18 |
| TURRET (L298N#2 ch A) | GPIO19 | GPIO21 | GPIO22 |
| TILT (L298N#2 ch B, DOWN direction only) | GPIO23 | GPIO25 | GPIO26 |
| FIRE (MOSFET gate, purely digital, no PWM) | GPIO27 | — | — |

**Why TRACK right is GPIO32/33 (not 16/17):** many ESP32 DevKit boards do not break out GPIO16/GPIO17 (on classic modules those pins exist but are often unlabeled / missing from the header). GPIO32/33 are almost always available.

**Why FIRE doesn't use a 3rd L298N:** the two L298Ns (4 channels) already fit TRACK×2 + TURRET + TILT exactly. FIRE is just ON/OFF, one direction (no need to reverse) — a single-GPIO MOSFET switch is cheaper and simpler than a full driver channel.

Reserved: **GPIO34, GPIO35** (input-only ADC) — for a future pan/tilt potentiometer. **GPIO14** — spare / status LED.

Code implementing this pin map: `firmware/esp32_wroom/src/main.cpp`

## Pan-only wiring (L298N#2, one motor — 2026-08-28)

Use **channel A only**. Leave IN3 / IN4 / ENB and OUT3 / OUT4 disconnected until tilt exists.

Remove the **ENA jumper** on the module (the small cap on ENA). If that jumper stays on, GPIO22 cannot PWM — the motor runs full speed whenever IN1/IN2 are driven.

| L298N#2 (typical 2-channel module) | Goes to |
|---|---|
| IN1 | ESP32 **GPIO19** |
| IN2 | ESP32 **GPIO21** |
| ENA (after removing jumper) | ESP32 **GPIO22** |
| OUT1 | pan motor lead A |
| OUT2 | pan motor lead B |
| +12V / VCC (motor supply) | battery + (same pack as L298N#1 is fine; 2S Li-Po preferred) |
| GND | battery − **and** ESP32 GND (common ground — required) |
| +5V | leave unconnected if the 5V jumper is on (module regulator). Do **not** feed this into ESP32 5V/VIN while USB is plugged in |
| IN3, IN4, ENB | **not connected** (tilt later: GPIO23 / 25 / 26) |

ESP32 stays on USB for logic. L298N motor VIN must **not** come from USB.

LEFT/RIGHT polarity was inverted in firmware on 2026-08-28 (`handleTurret`) because the pan motor leads cannot be swapped on the robot. Do not swap OUT1/OUT2 at the motor.

Manual test: `python tests/hardware/turret_console.py --host <board-ip>`

## Still pending real assembly

- Power wiring and common ground plan — **important:** the L298N must draw from a separate battery, not USB (no auxiliary power connected yet)
- ESP32-CAM pin map
- (future, if more precision is needed) mounting points for a pan/tilt potentiometer/encoder — no real hardware yet (would use the GPIO32/33 reserved above)

Update this file with a wiring diagram once real wiring begins.
