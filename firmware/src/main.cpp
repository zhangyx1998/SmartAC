#include <HTTPClient.h>
#include <WiFi.h>
#include <Wire.h>

#include <FastLED.h>
#include <cmath>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include "connection.h"
#include "console.h"
#include "global.h"
#include "led.h"

// Global singleton definitions
CRGB leds[NUM_LEDS];
SHT31 sht;
Preferences preferences;
FanPulseCounter fan_pulse_counter;
Status status;
volatile bool wifi_connected = false;

float fan_power = 0.0f;

float setFanPower(float power) {
  if (isnan(power)) {
    fan_power = power;
    power = 0.0f;
  } else {
    if (power < 0.0f)
      power = 0.0f;
    if (power > 1.0f)
      power = 1.0f;
    fan_power = power;
  }
  analogWrite(FAN_PWM, (uint8_t)(power * 255));
  return power;
}

float getFanPower() { return fan_power; }
// Status update implementation
Status &Status::update() {
  if (sht.read()) {
    temperature = sht.getTemperature();
    humidity = sht.getHumidity();
  } else {
    temperature = NAN;
    humidity = NAN;
  }
  fan_rpm = fan_pulse_counter.rpm();
  return *this;
}

void fanTachISR() { fan_pulse_counter.tick(); }

unsigned long last_heartbeat = 0;

void telemetryTask(void *parameter) {
  HTTPClient http;
  while (true) {
    ensureWiFi();
    preferences.begin("config", true);
    auto serverUrl = preferences.getString("server", "");
    preferences.end();
    if (serverUrl.length() > 0) {
      http.begin(serverUrl);
      http.addHeader("Content-Type", "application/octet-stream");
      int httpCode = http.POST((uint8_t *)&status.update(), sizeof(status));
      if (httpCode > 0) {
        if (httpCode == HTTP_CODE_OK) {
          // Parse binary float response for fan power
          auto response = http.getString();
          if (response.length() >= sizeof(float))
            setFanPower(*reinterpret_cast<const float *>(response.c_str()));
          last_heartbeat = millis();
        } else {
          log("Heartbeat response code: " + String(httpCode));
        }
      } else {
        log("Heartbeat failed: " + http.errorToString(httpCode));
      }
      http.end();
    }
    vTaskDelay(pdMS_TO_TICKS(1000));
  }
}

void setup() {
  Serial.begin(115200);
  // Query and print MAC address
  WiFi.mode(WIFI_STA);
  String macAddress = WiFi.macAddress();
  log("MAC Address: " + macAddress);

  // Initialize I2C with custom pins
  Wire.begin(IIC_SDA, IIC_SCL);

  // Initialize SHT3X sensor

  FastLED.addLeds<NEOPIXEL, LED_PIN>(leds, NUM_LEDS);
  FastLED.setBrightness(192);

  // Initialize fan control
  pinMode(FAN_PWM, OUTPUT);
  pinMode(FAN_TCH, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(FAN_TCH), fanTachISR, FALLING);

  // Set initial fan speed to 0
  analogWrite(FAN_PWM, 0);

  // Create console task
  xTaskCreate(consoleTask, // Task function
              "Console",   // Task name
              8192,        // Stack size (bytes)
              NULL,        // Parameter
              1,           // Priority
              NULL         // Task handle
  );

  // Create WiFi and heartbeat task
  xTaskCreate(telemetryTask, // Task function
              "Telemetry",   // Task name
              8192,          // Stack size (bytes)
              NULL,          // Parameter
              1,             // Priority
              NULL           // Task handle
  );
}

void loop() {
  static float current_hue = 0.0f; // Current hue for smooth transition
  static unsigned long last_update = millis();
  static float brightness = 1.0f;
  static unsigned long last_blink = millis();

  unsigned long now = millis();
  float dt = (now - last_update) / 1000.0f; // Time delta in seconds
  last_update = now;

  // Calculate target hue based on fan power: 0% = red (0.0), 100% = blue
  // (0.667)
  float target_hue = std::isnan(fan_power) ? 0.0f : fan_power * 0.667f;

  // Smoothly transition current_hue towards target_hue at 0.5 hue units per
  // second
  float hue_diff = target_hue - current_hue;
  // Handle wraparound
  if (hue_diff > 0.5f)
    hue_diff -= 1.0f;
  if (hue_diff < -0.5f)
    hue_diff += 1.0f;

  float max_change = 0.5f * dt;
  if (abs(hue_diff) < max_change) {
    current_hue = target_hue;
  } else {
    current_hue += (hue_diff > 0 ? max_change : -max_change);
  }
  current_hue = fmod(current_hue + 1.0f, 1.0f); // Keep in [0, 1)

  // Check WiFi status and blink at 5Hz if not connected
  if (!WiFi.isConnected()) {
    if (now - last_blink >= 100) { // 5Hz = 200ms period = 100ms half period
      brightness = brightness > 0.5 ? 0.1 : 1.0;
      last_blink = now;
    }
  } else if (std::isnan(fan_power) || last_heartbeat + 2000 < now) {
    // Breathe at 1Hz if no control from server
    float phase = ((now % 1000) / 1000.0f) * 2.0f * PI;
    brightness = (sin(phase) + 1.0f) / 2.0f;
  } else {
    brightness = 1.0f; // Always on when connected
  }

  // Set LED color
  CRGB color = hsl(current_hue, 1.0f, brightness / 2.0f);
  for (auto &l : leds) {
    l = color;
  }
  FastLED.show();

  // Run at 60Hz (16.67ms per frame)
  delay(16);
}
