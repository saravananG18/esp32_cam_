
#include "esp_camera.h"
#include "img_converters.h"
#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";


// -------- Camera pins: AI Thinker --------
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5

#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

WebServer server(80);

// -------- Camera Initialization --------
bool startCamera() {

  camera_config_t config={};

  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;

  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;

  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;

  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;

  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;

  // RHYX M21-45 camera settings
  config.pixel_format = PIXFORMAT_RGB565;
  config.frame_size = FRAMESIZE_QVGA;

  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;

  esp_err_t result = esp_camera_init(&config);

  if (result != ESP_OK) {
    Serial.printf("Camera initialization failed: 0x%x\n", result);
    return false;
  }

  Serial.println("Camera initialized successfully!");
  return true;
}

// -------- Webpage --------
void handleRoot() {

  String page = R"rawliteral(
  <!DOCTYPE html>
  <html>
  <head>
    <title>RHYX ESP32 Camera</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body {
        background: #202124;
        color: white;
        text-align: center;
        font-family: Arial;
      }
      img {
        width: 95%;
        max-width: 640px;
        border: 2px solid white;
        border-radius: 8px;
      }
    </style>
  </head>
  <body>
    <h2>RHYX ESP32-CAM</h2>
    <p>Live Camera Feed</p>
    <img src="/stream">
  </body>
  </html>
  )rawliteral";

  server.send(200, "text/html", page);
}

// -------- Camera Streaming --------
void handleStream() {

  WiFiClient client = server.client();

  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.setContentLength(CONTENT_LENGTH_UNKNOWN);

  server.send(200, "multipart/x-mixed-replace; boundary=frame", "");

  Serial.println("Camera stream started");

  while (client.connected()) {

    camera_fb_t *fb = esp_camera_fb_get();

    if (!fb) {
      Serial.println("Camera capture failed");
      break;
    }

    uint8_t *jpgBuffer = NULL;
    size_t jpgLength = 0;

    // Convert RGB565 to JPEG in software
    bool converted = frame2jpg(fb, 60, &jpgBuffer, &jpgLength);

    esp_camera_fb_return(fb);

    if (!converted || jpgBuffer == NULL) {
      Serial.println("JPEG conversion failed");
      if (jpgBuffer) free(jpgBuffer);
      break;
    }

    server.sendContent("--frame\r\n");
    server.sendContent("Content-Type: image/jpeg\r\n");
    server.sendContent("Content-Length: " + String(jpgLength) + "\r\n\r\n");

    server.sendContent((const char*)jpgBuffer, jpgLength);
    server.sendContent("\r\n");

    free(jpgBuffer);

    delay(100);

    if (!client.connected()) {
      break;
    }
  }

  Serial.println("Camera stream stopped");
}

// -------- Setup --------
void setup() {

  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("Starting RHYX ESP32-CAM...");

  if (!startCamera()) {
    Serial.println("Check camera connection!");
    return;
  }

  WiFi.begin(ssid, password);

  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected!");

  Serial.print("Open this IP address: ");
  Serial.println(WiFi.localIP());

  server.on("/", HTTP_GET, handleRoot);
  server.on("/stream", HTTP_GET, handleStream);

  server.begin();

  Serial.println("Web server started!");
}

// -------- Main Loop --------
void loop() {
  server.handleClient();
}
