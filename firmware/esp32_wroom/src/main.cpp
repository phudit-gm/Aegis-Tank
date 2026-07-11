#include <WiFi.h>
#include <WiFiUdp.h>
#include <ESPmDNS.h>
#include <ArduinoOTA.h>
#include "esp_ota_ops.h"
#include "secrets.h"

// ── UDP (ตาม config/protocol_contract.yaml -> motor_controller) ─────────────
constexpr uint16_t UDP_PORT = 5555;
constexpr uint32_t FAILSAFE_TIMEOUT_MS = 500;

WiFiUDP udp;
char packet_buf[128];
uint32_t last_command_ms = 0;
bool in_safe_state = true;
bool ota_in_progress = false;

// ── Clamp — ESP32 คือด่าน authoritative สุดท้าย (SPEC.md §1) เพราะ UDP อาจ corrupt ──
long clampl(long v, long lo, long hi) {
    return v < lo ? lo : (v > hi ? hi : v);
}

void enterSafeState() {
    if (in_safe_state) return;
    in_safe_state = true;
    Serial.println("[SAFE STATE] motor stop / turret center / tilt level / laser off");
    // TODO: ต่อ L298N/servo/laser จริงแล้วใส่โค้ดสั่งฮาร์ดแวร์เข้า safe state ตรงนี้
}

void handleTrack(const char* direction, long speed) {
    static const char* valid[] = {"FORWARD", "BACKWARD", "STOP", "TURN_LEFT", "TURN_RIGHT"};
    bool ok = false;
    for (auto v : valid) {
        if (strcmp(direction, v) == 0) { ok = true; break; }
    }
    if (!ok) {
        Serial.printf("[DROP] TRACK direction invalid: %s\n", direction);
        return;
    }
    speed = clampl(speed, 0, 255);
    Serial.printf("[TRACK] %s speed=%ld\n", direction, speed);
    // TODO: แปลง speed -> PWM ของ L298N #1 (GPIO รอกำหนดใน hardware/pin_map.md)
}

void handleTurret(long angle) {
    angle = clampl(angle, -180, 180);
    Serial.printf("[TURRET] PAN=%ld deg\n", angle);
    // TODO: แปลง angle -> PWM servo (GPIO รอกำหนด)
}

void handleTilt(long angle) {
    angle = clampl(angle, -90, 90);
    Serial.printf("[TILT] PITCH=%ld deg\n", angle);
    // TODO: แปลง angle -> PWM servo (GPIO รอกำหนด)
}

void handleLaser(const char* state, long duration_ms) {
    if (strcmp(state, "ON") != 0 && strcmp(state, "OFF") != 0) {
        Serial.printf("[DROP] LASER state invalid: %s\n", state);
        return;
    }
    duration_ms = clampl(duration_ms, 0, 32767);
    Serial.printf("[LASER] %s duration=%ld ms\n", state, duration_ms);
    // TODO: ขับ GPIO เลเซอร์จริง (GPIO รอกำหนด)
}

void dispatch(char* msg) {
    if (ota_in_progress) {
        Serial.println("[DROP] command ignored: OTA update in progress");
        return;
    }

    // แยก 3 ส่วนด้วย ':' ตาม SPEC.md §1 — parser ไม่ต้องมีกรณีพิเศษ
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
        handleTurret(atol(field3));
    } else if (strcmp(type, "TILT") == 0) {
        handleTilt(atol(field3));
    } else if (strcmp(type, "LASER") == 0) {
        handleLaser(field2, atol(field3));
    } else {
        Serial.printf("[DROP] unknown TYPE: %s\n", type);
        return;
    }

    last_command_ms = millis();
    in_safe_state = false;
}

void setup() {
    Serial.begin(115200);
    Serial.println("\n== Aegis-Tank ESP32-WROOM ==");

    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.printf("Connecting to %s", WIFI_SSID);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.printf("\nConnected! IP: %s\n", WiFi.localIP().toString().c_str());

    udp.begin(UDP_PORT);
    Serial.printf("Listening UDP on port %u\n", UDP_PORT);
    Serial.println("Ready (skeleton firmware -- logs commands only, no motor/servo output yet)");

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
}
