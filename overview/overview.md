# Aegis-Tank — Project Overview

> This document tells someone new to the project what Aegis-Tank is and why it's designed this way
> Status (2026-07-14): **real code now exists** — the PC-side `src/` has all 6 roles written with all unit tests passing, `firmware/esp32_cam` is written+flashed and working for real (MJPEG stream), `firmware/esp32_wroom` has real PWM/GPIO driving code that compiles, awaiting flash testing with real motors — see `handoff/current-task.md` for the latest detailed status

---

## What is Aegis-Tank

A semi-autonomous sentry robot that "sees → thinks → aims → moves", splitting the work across 3 separate brains:
- **Sees** with a camera (ESP32-CAM)
- **Thinks** with AI on a PC (detects objects + computes aiming)
- **Moves** with a motor controller board (ESP32-WROOM)

Rebuilt from the earlier **R.N.T. (Rear-Naked Tank)** project, whose structure was scattered — this project is the reorganized version that keeps only the knowledge that has crystallized, with all code rewritten from scratch.

---

## The Split-Brain concept

The heart of Aegis-Tank is **separating the (heavy) AI processing from the (light, real-time) motor controller** so both can run at once without competing for resources:

| Brain | Device | Nature of work |
|---|---|---|
| Eyes | ESP32-CAM | continuous video stream |
| Thinking brain | PC + Python + AI | heavy, needs high GPU/CPU |
| Muscle | ESP32-WROOM | light, must respond fast (real-time) |

If one board did everything: the AI would eat resources until the motors respond slowly, or the motors would compete for CPU and make the AI stutter.

---

## System data flow (CAM → PC → WROOM → motors)

```
[ESP32-CAM]  sees
    │  sends a video image over WiFi
    ↓
[PC + AI]  thinks
    │  - detects objects in the image
    │  - smooths the position (reduces noise)
    │  - computes how far and which way to turn
    │  sends commands over WiFi
    ↓
[ESP32-WROOM]  moves
    │  translates commands → motor control signals
    ↓
[Motors]  move for real (wheels / turret / tilt / fire)
```

Data flows in **one loop (one-way loop):**
image flows up to the PC → commands flow down to the board → motors move → the camera sees the new result → loop again

---

## The "thinking" steps on the PC

This is the heart of the system — the sequence that converts raw image data into motor commands:

```
1 frame of image
   ↓ detect objects
Object found: position (x, y) + confidence + class known
   ↓ smooth (Kalman filter)
Smoothed position + velocity of motion
   ↓ compute error (how far the target is from image center)
error in pixels
   ↓ convert pixels → degree error
   ↓ run through a controller (PID) to move smoothly, without jitter, without overshoot
direction+speed to command this cycle (pan / tilt)
   ↓ build into a command
send command to the board → motors move → camera sees the next frame's result → loop to correct the error further (visual servoing, no angle sensor on the board)
```

---

## Why a Kalman filter

The position detected from the camera image "jitters back and forth" (noise). Commanding the motors directly off that would make the turret shake. Kalman fixes 2 things:

1. **Filters noise** — gives a smoother position, like drawing an average line through scattered points
2. **Predicts direction** — computes the velocity of motion, to guess the next position before the next frame arrives (helps track a moving target)

---

## Why PID

If the motors were commanded to drive straight at the target, it would "overshoot" and oscillate back and forth without stopping. PID fixes this:

- **P (Proportional):** move fast when far from the target, slow down when close — proportional directly to the distance
- **I (Integral):** corrects long-term accumulated deviation, prevents staying aimed off to one side of the target forever
- **D (Derivative):** dampens the approach to the target, prevents oscillation around the destination

Result: the turret settles onto the target smoothly, without jitter, without overshoot.
