#include <WiFi.h>
#include <WiFiUdp.h>
#include <ESPmDNS.h>
#include <ArduinoOTA.h>
#include "esp_ota_ops.h"
#include "secrets.h"

// ── UDP (per config/protocol_contract.yaml -> motor_controller) ─────────────
constexpr uint16_t UDP_PORT = 5555;
constexpr uint32_t FAILSAFE_TIMEOUT_MS = 500;

WiFiUDP udp;
char packet_buf[128];
uint32_t last_command_ms = 0;
bool in_safe_state = true;
bool ota_in_progress = false;

// ── Pin map (see hardware/pin_map.md — defined 2026-07-13, remapped 2026-07-30) ──
// L298N#1 — TRACK
// TRACK right uses GPIO32/33 (not 16/17) — many DevKit boards do not break out 16/17
constexpr uint8_t TRACK_L_IN_A = 4, TRACK_L_IN_B = 5, TRACK_L_PWM = 13;
constexpr uint8_t TRACK_R_IN_A = 32, TRACK_R_IN_B = 33, TRACK_R_PWM = 18;
// L298N#2 — TURRET/TILT
constexpr uint8_t TURRET_IN_A = 19, TURRET_IN_B = 21, TURRET_PWM = 22;
constexpr uint8_t TILT_IN_A = 23, TILT_IN_B = 25, TILT_PWM = 26;
// FIRE — MOSFET switch, digital only (does not go through the L298N — see decisions.md)
constexpr uint8_t FIRE_PIN = 27;

// the framework-arduinoespressif32 pinned to core v2.x -> ledc uses a channel number separate from the pin
// (ledcSetup/ledcAttachPin/ledcWrite(channel,...), not the ledcAttach(pin,...) of core v3)
constexpr uint8_t TRACK_L_PWM_CH = 0, TRACK_R_PWM_CH = 1, TURRET_PWM_CH = 2, TILT_PWM_CH = 3;

constexpr uint32_t PWM_FREQ_HZ = 5000;
constexpr uint8_t PWM_RESOLUTION_BITS = 8;  // duty 0-255 matches speed 0-255 in the protocol exactly

uint32_t fire_off_at_ms = 0;
bool fire_active = false;

// ── Clamp — the ESP32 is the final authoritative gate (SPEC.md §1) because UDP may get corrupted ──
long clampl(long v, long lo, long hi) {
    return v < lo ? lo : (v > hi ? hi : v);
}

// ── Motor helper — drives 1 channel of the L298N (IN A/B set direction, ledc channel sets speed) ──
// forward=true -> INA=HIGH/INB=LOW, forward=false -> INA=LOW/INB=HIGH, speed=0 -> both LOW (coast/stop)
void driveChannel(uint8_t inA, uint8_t inB, uint8_t pwmChannel, bool forward, uint8_t speed) {
    if (speed == 0) {
        digitalWrite(inA, LOW);
        digitalWrite(inB, LOW);
    } else {
        digitalWrite(inA, forward ? HIGH : LOW);
        digitalWrite(inB, forward ? LOW : HIGH);
    }
    ledcWrite(pwmChannel, speed);
}

void setFire(bool on) {
    fire_active = on;
    digitalWrite(FIRE_PIN, on ? HIGH : LOW);
}

void stopAllMotors() {
    driveChannel(TRACK_L_IN_A, TRACK_L_IN_B, TRACK_L_PWM_CH, true, 0);
    driveChannel(TRACK_R_IN_A, TRACK_R_IN_B, TRACK_R_PWM_CH, true, 0);
    driveChannel(TURRET_IN_A, TURRET_IN_B, TURRET_PWM_CH, true, 0);
    driveChannel(TILT_IN_A, TILT_IN_B, TILT_PWM_CH, true, 0);
    setFire(false);
}

void enterSafeState() {
    if (in_safe_state) return;
    in_safe_state = true;
    stopAllMotors();
    Serial.println("[SAFE STATE] track stop / turret stop / tilt stop / fire off");
}

void handleTrack(const char* direction, long speed) {
    speed = clampl(speed, 0, 255);
    uint8_t s = (uint8_t)speed;

    if (strcmp(direction, "FORWARD") == 0) {
        driveChannel(TRACK_L_IN_A, TRACK_L_IN_B, TRACK_L_PWM_CH, true, s);
        driveChannel(TRACK_R_IN_A, TRACK_R_IN_B, TRACK_R_PWM_CH, true, s);
    } else if (strcmp(direction, "BACKWARD") == 0) {
        driveChannel(TRACK_L_IN_A, TRACK_L_IN_B, TRACK_L_PWM_CH, false, s);
        driveChannel(TRACK_R_IN_A, TRACK_R_IN_B, TRACK_R_PWM_CH, false, s);
    } else if (strcmp(direction, "STOP") == 0) {
        driveChannel(TRACK_L_IN_A, TRACK_L_IN_B, TRACK_L_PWM_CH, true, 0);
        driveChannel(TRACK_R_IN_A, TRACK_R_IN_B, TRACK_R_PWM_CH, true, 0);
    } else if (strcmp(direction, "TURN_LEFT") == 0) {
        // skid-turn: left wheel stops, right wheel drives forward
        driveChannel(TRACK_L_IN_A, TRACK_L_IN_B, TRACK_L_PWM_CH, true, 0);
        driveChannel(TRACK_R_IN_A, TRACK_R_IN_B, TRACK_R_PWM_CH, true, s);
    } else if (strcmp(direction, "TURN_RIGHT") == 0) {
        driveChannel(TRACK_L_IN_A, TRACK_L_IN_B, TRACK_L_PWM_CH, true, s);
        driveChannel(TRACK_R_IN_A, TRACK_R_IN_B, TRACK_R_PWM_CH, true, 0);
    } else if (strcmp(direction, "PIVOT_LEFT") == 0) {
        // pivot-turn: both wheels spin opposite directions (see decisions.md — used during aim-assist)
        driveChannel(TRACK_L_IN_A, TRACK_L_IN_B, TRACK_L_PWM_CH, false, s);
        driveChannel(TRACK_R_IN_A, TRACK_R_IN_B, TRACK_R_PWM_CH, true, s);
    } else if (strcmp(direction, "PIVOT_RIGHT") == 0) {
        driveChannel(TRACK_L_IN_A, TRACK_L_IN_B, TRACK_L_PWM_CH, true, s);
        driveChannel(TRACK_R_IN_A, TRACK_R_IN_B, TRACK_R_PWM_CH, false, s);
    } else {
        Serial.printf("[DROP] TRACK direction invalid: %s\n", direction);
        return;
    }
    Serial.printf("[TRACK] %s speed=%ld\n", direction, speed);
}

void handleTurret(const char* direction, long speed) {
    speed = clampl(speed, 0, 255);
    uint8_t s = (uint8_t)speed;

    if (strcmp(direction, "LEFT") == 0) {
        driveChannel(TURRET_IN_A, TURRET_IN_B, TURRET_PWM_CH, false, s);
    } else if (strcmp(direction, "RIGHT") == 0) {
        driveChannel(TURRET_IN_A, TURRET_IN_B, TURRET_PWM_CH, true, s);
    } else if (strcmp(direction, "STOP") == 0) {
        driveChannel(TURRET_IN_A, TURRET_IN_B, TURRET_PWM_CH, true, 0);
    } else {
        Serial.printf("[DROP] TURRET direction invalid: %s\n", direction);
        return;
    }
    Serial.printf("[TURRET] %s speed=%ld\n", direction, speed);
}

void handleTilt(const char* direction, long speed) {
    speed = clampl(speed, 0, 255);
    uint8_t s = (uint8_t)speed;

    // Only DOWN direction (pushes down) — tilting up comes from the return spring when STOP is issued (SPEC.md §1)
    if (strcmp(direction, "DOWN") == 0) {
        driveChannel(TILT_IN_A, TILT_IN_B, TILT_PWM_CH, true, s);
    } else if (strcmp(direction, "STOP") == 0) {
        driveChannel(TILT_IN_A, TILT_IN_B, TILT_PWM_CH, true, 0);
    } else {
        Serial.printf("[DROP] TILT direction invalid: %s\n", direction);
        return;
    }
    Serial.printf("[TILT] %s speed=%ld\n", direction, speed);
}

void handleFire(const char* state, long duration_ms) {
    if (strcmp(state, "ON") != 0 && strcmp(state, "OFF") != 0) {
        Serial.printf("[DROP] FIRE state invalid: %s\n", state);
        return;
    }
    duration_ms = clampl(duration_ms, 0, 32767);

    if (strcmp(state, "ON") == 0) {
        setFire(true);
        fire_off_at_ms = millis() + (uint32_t)duration_ms;  // loop() turns it off automatically, non-blocking
    } else {
        setFire(false);
        fire_off_at_ms = 0;
    }
    Serial.printf("[FIRE] %s duration=%ld ms\n", state, duration_ms);
}

void dispatch(char* msg) {
    if (ota_in_progress) {
        Serial.println("[DROP] command ignored: OTA update in progress");
        return;
    }

    // Split into 3 parts by ':' per SPEC.md §1 — parser doesn't need special cases
    char* type = strtok(msg, ":");
    char* field2 = strtok(nullptr, ":");
    char* field3 = strtok(nullptr, ":");

    if (!type || !field2 || !field3) {
        Serial.printf("[DROP] malformed packet (need 3 tokens): %s\n", msg);
        return;
    }

    if (strcmp(type, "TRACK") == 0) {
        handleTrack(field2, atol(field3));
    } else if (strcmp(type, "TURRET") == 0) {
        handleTurret(field2, atol(field3));
    } else if (strcmp(type, "TILT") == 0) {
        handleTilt(field2, atol(field3));
    } else if (strcmp(type, "FIRE") == 0) {
        handleFire(field2, atol(field3));
    } else {
        Serial.printf("[DROP] unknown TYPE: %s\n", type);
        return;
    }

    last_command_ms = millis();
    in_safe_state = false;
}

void setupMotorPins() {
    const uint8_t dirPins[] = {
        TRACK_L_IN_A, TRACK_L_IN_B, TRACK_R_IN_A, TRACK_R_IN_B,
        TURRET_IN_A, TURRET_IN_B, TILT_IN_A, TILT_IN_B,
    };
    for (uint8_t pin : dirPins) {
        pinMode(pin, OUTPUT);
        digitalWrite(pin, LOW);
    }

    pinMode(FIRE_PIN, OUTPUT);
    digitalWrite(FIRE_PIN, LOW);

    const uint8_t pwmPins[] = {TRACK_L_PWM, TRACK_R_PWM, TURRET_PWM, TILT_PWM};
    const uint8_t pwmChannels[] = {TRACK_L_PWM_CH, TRACK_R_PWM_CH, TURRET_PWM_CH, TILT_PWM_CH};
    for (uint8_t i = 0; i < 4; i++) {
        ledcSetup(pwmChannels[i], PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
        ledcAttachPin(pwmPins[i], pwmChannels[i]);
        ledcWrite(pwmChannels[i], 0);
    }
}

void setup() {
    Serial.begin(115200);
    Serial.println("\n== Aegis-Tank ESP32-WROOM ==");

    setupMotorPins();
    Serial.println("Motor pins initialized (see hardware/pin_map.md) -- all outputs LOW/0 duty");

    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.printf("Connecting to %s", WIFI_SSID);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\nConnected! IP: %s\n", WiFi.localIP().toString().c_str());

    udp.begin(UDP_PORT);
    Serial.printf("Listening UDP on port %u\n", UDP_PORT);
    Serial.println("Ready -- driving real PWM/GPIO outputs per hardware/pin_map.md");

    // ── OTA ───────────────────────────────────────────────────────────────────
    ArduinoOTA.setHostname("aegis-wroom");
    ArduinoOTA.setPassword(OTA_PASSWORD);

    ArduinoOTA.onStart([]() {
        // Force disarm before any flash write proceeds -- an update must never
        // start while motors/fire mechanism could still be commanded.
        enterSafeState();
        ota_in_progress = true;
        Serial.println("[OTA] update starting -- forced safe state");
    });
    ArduinoOTA.onEnd([]() {
        ota_in_progress = false;
        Serial.println("[OTA] update complete, rebooting");
    });
    ArduinoOTA.onError([](ota_error_t error) {
        ota_in_progress = false;
        Serial.printf("[OTA] error [%u]\n", error);
    });

    ArduinoOTA.begin();
    Serial.println("OTA ready: aegis-wroom.local");

    // Reached a known-good state (WiFi + UDP listener up) -- confirm this build
    // to the bootloader so it won't be auto-rolled-back on next boot.
    esp_ota_mark_app_valid_cancel_rollback();
}

void loop() {
    ArduinoOTA.handle();

    int packet_size = udp.parsePacket();
    if (packet_size > 0) {
        int len = udp.read(packet_buf, sizeof(packet_buf) - 1);
        if (len > 0) {
            packet_buf[len] = '\0';
            dispatch(packet_buf);
        }
    }

    if (!in_safe_state && millis() - last_command_ms > FAILSAFE_TIMEOUT_MS) {
        enterSafeState();
    }

    if (fire_active && fire_off_at_ms != 0 && millis() >= fire_off_at_ms) {
        setFire(false);
        fire_off_at_ms = 0;
        Serial.println("[FIRE] burst duration elapsed -> auto OFF");
    }
}
