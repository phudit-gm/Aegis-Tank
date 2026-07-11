#include "Arduino.h"
#include "esp_camera.h"
#include "esp_http_server.h"
#include "esp_ota_ops.h"
#include "WiFi.h"
#include "ESPmDNS.h"
#include "ArduinoOTA.h"
#include "secrets.h"

// ── Camera pins (AI Thinker ESP32-CAM) ───────────────────────────────────────
#define PWDN_GPIO_NUM   32
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM    0
#define SIOD_GPIO_NUM   26
#define SIOC_GPIO_NUM   27
#define Y9_GPIO_NUM     35
#define Y8_GPIO_NUM     34
#define Y7_GPIO_NUM     39
#define Y6_GPIO_NUM     36
#define Y5_GPIO_NUM     21
#define Y4_GPIO_NUM     19
#define Y3_GPIO_NUM     18
#define Y2_GPIO_NUM      5
#define VSYNC_GPIO_NUM  25
#define HREF_GPIO_NUM   23
#define PCLK_GPIO_NUM   22

// ── Servers ───────────────────────────────────────────────────────────────────
// Port 80  → index page + /fps
// Port 81  → /stream  (blocks its worker, needs separate server)
static httpd_handle_t cam_httpd  = NULL;
static httpd_handle_t stream_httpd = NULL;

// ── FPS counter ───────────────────────────────────────────────────────────────
static volatile uint32_t frame_count = 0;
static volatile float    current_fps = 0.0f;
static uint32_t          last_fps_ms  = 0;

// ── Stream handler (port 81) ──────────────────────────────────────────────────
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* STREAM_CONTENT_TYPE =
    "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* STREAM_PART =
    "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static esp_err_t stream_handler(httpd_req_t* req) {
    camera_fb_t* fb = NULL;
    char part_buf[64];

    httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) { Serial.println("Camera capture failed"); continue; }

        // FPS measurement
        frame_count++;
        uint32_t now = millis();
        if (now - last_fps_ms >= 1000) {
            current_fps  = frame_count * 1000.0f / (now - last_fps_ms);
            frame_count  = 0;
            last_fps_ms  = now;
        }

        if (httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY)) != ESP_OK ||
            snprintf(part_buf, sizeof(part_buf), STREAM_PART, fb->len) < 0 ||
            httpd_resp_send_chunk(req, part_buf, strlen(part_buf)) != ESP_OK ||
            httpd_resp_send_chunk(req, (const char*)fb->buf, fb->len) != ESP_OK) {
            esp_camera_fb_return(fb);
            break;
        }
        esp_camera_fb_return(fb);
    }
    return ESP_OK;
}

// ── Index page (port 80) ──────────────────────────────────────────────────────
static esp_err_t index_handler(httpd_req_t* req) {
    httpd_resp_set_type(req, "text/html");
    const char* html = R"(<!DOCTYPE html>
<html>
<head><title>Aegis-Tank Cam</title>
<style>body{background:#111;color:#eee;font-family:sans-serif;text-align:center}
img{max-width:100%;border:2px solid #444}
#fps{font-size:1.5em;margin:8px}</style>
</head>
<body>
<h2>Aegis-Tank Camera</h2>
<div id="fps">FPS: --</div>
<img id="stream">
<script>
document.getElementById('stream').src = "http://" + location.hostname + ":81/stream";
setInterval(()=>fetch('/fps').then(r=>r.text()).then(t=>document.getElementById('fps').textContent='FPS: '+t),1000);
</script>
</body></html>)";
    return httpd_resp_send(req, html, strlen(html));
}

static esp_err_t fps_handler(httpd_req_t* req) {
    char buf[16];
    snprintf(buf, sizeof(buf), "%.1f", current_fps);
    httpd_resp_set_type(req, "text/plain");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, buf, strlen(buf));
}

// ── Start servers ─────────────────────────────────────────────────────────────
void startCameraServer() {
    httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();

    // Port 80 — index + fps
    cfg.server_port  = 80;
    cfg.ctrl_port    = 32080;
    if (httpd_start(&cam_httpd, &cfg) == ESP_OK) {
        httpd_uri_t index_uri = {"/",    HTTP_GET, index_handler, NULL};
        httpd_uri_t fps_uri   = {"/fps", HTTP_GET, fps_handler,   NULL};
        httpd_register_uri_handler(cam_httpd, &index_uri);
        httpd_register_uri_handler(cam_httpd, &fps_uri);
    }

    // Port 81 — stream only
    cfg.server_port  = 81;
    cfg.ctrl_port    = 32081;
    if (httpd_start(&stream_httpd, &cfg) == ESP_OK) {
        httpd_uri_t stream_uri = {"/stream", HTTP_GET, stream_handler, NULL};
        httpd_register_uri_handler(stream_httpd, &stream_uri);
    }
}

// ── setup ─────────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    Serial.println("\n== Aegis-Tank ESP32-CAM ==");

    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer   = LEDC_TIMER_0;
    config.pin_d0       = Y2_GPIO_NUM;
    config.pin_d1       = Y3_GPIO_NUM;
    config.pin_d2       = Y4_GPIO_NUM;
    config.pin_d3       = Y5_GPIO_NUM;
    config.pin_d4       = Y6_GPIO_NUM;
    config.pin_d5       = Y7_GPIO_NUM;
    config.pin_d6       = Y8_GPIO_NUM;
    config.pin_d7       = Y9_GPIO_NUM;
    config.pin_xclk     = XCLK_GPIO_NUM;
    config.pin_pclk     = PCLK_GPIO_NUM;
    config.pin_vsync    = VSYNC_GPIO_NUM;
    config.pin_href     = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn     = PWDN_GPIO_NUM;
    config.pin_reset    = RESET_GPIO_NUM;
    config.xclk_freq_hz = 24000000;   // 24MHz — proven good for >35fps
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size   = FRAMESIZE_QVGA;   // 320x240
    config.jpeg_quality = 12;
    config.fb_count     = 2;
    config.grab_mode    = CAMERA_GRAB_LATEST;

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed: 0x%x\n", err);
        Serial.println("→ ลองรีเสต ribbon cable OV2640 แล้ว upload ใหม่");
        return;
    }

    // ── Exposure / gain tuning ────────────────────────────────────────────────
    sensor_t* s = esp_camera_sensor_get();
    s->set_exposure_ctrl(s, 0);     // manual exposure (ต้อง set ก่อน aec_value)
    s->set_aec_value(s, 250);       // 180=เร็ว/มืด · 250=สว่างห้องปกติ · 350=มืด
    s->set_gain_ctrl(s, 1);         // auto gain
    s->set_gainceiling(s, GAINCEILING_32X);
    s->set_brightness(s, 1);
    s->set_whitebal(s, 1);

    Serial.println("Camera OK");

    // ── WiFi ──────────────────────────────────────────────────────────────────
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.printf("Connecting to %s", WIFI_SSID);
    while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
    Serial.printf("\nConnected! IP: http://%s\n", WiFi.localIP().toString().c_str());
    Serial.printf("Stream:      http://%s:81/stream\n", WiFi.localIP().toString().c_str());

    last_fps_ms = millis();
    startCameraServer();
    Serial.println("Servers started");

    // ── OTA ───────────────────────────────────────────────────────────────────
    ArduinoOTA.setHostname("aegis-cam");
    ArduinoOTA.setPassword(OTA_PASSWORD);
    ArduinoOTA.begin();
    Serial.println("OTA ready: aegis-cam.local");

    // Reached a known-good state (camera + WiFi + servers all up) — confirm this
    // build to the bootloader so it won't be auto-rolled-back on next boot.
    esp_ota_mark_app_valid_cancel_rollback();
}

void loop() {
    ArduinoOTA.handle();
    delay(10);
}
