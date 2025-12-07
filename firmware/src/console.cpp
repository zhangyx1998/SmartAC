#include "console.h"

#include <cmath>
#include <global.h>

#include <WiFi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

static String current_input = "";
static String last_log_message = "";
static int log_repeat_count = 0;

// Log function that preserves the interactive prompt
void log(const String &message) {
  // Check if this is a repeat of the last message
  if (message == last_log_message) {
    log_repeat_count++;
    // Erase the previous line with count
    int total_chars = 2 + current_input.length();
    for (int i = 0; i < total_chars; i++) {
      Serial.print("\b \b");
    }
    // Print updated message with count
    Serial.print(message);
    Serial.print(" (");
    Serial.print(log_repeat_count);
    Serial.println(")");
    // Restore prompt and current input
    Serial.print("> ");
    Serial.print(current_input);
    return;
  }

  // New message - reset counter
  last_log_message = message;
  log_repeat_count = 1;

  // Erase current line using backspaces
  // Erase "> " prompt (2 chars) + current input
  int total_chars = 2 + current_input.length();
  for (int i = 0; i < total_chars; i++) {
    Serial.print("\b \b");
  }

  // Print the log message
  Serial.println(message);

  // Restore prompt and current input
  Serial.print("> ");
  Serial.print(current_input);
}

void consoleTask(void *parameter) {
  Serial.println("\n=== Smart AC Console ===");
  Serial.println("Type 'help' for available commands");
  Serial.print("> ");
  while (true) {
    if (Serial.available()) {
      char c = Serial.read();
      if (c == '\n' || c == '\r') {
        if (current_input.length() > 0) {
          Serial.println();
          current_input.trim();
          // Parse and execute command
          if (current_input == "help") {
            Serial.println(
                "Available commands:\n"
                "  help                 - Show this help message\n"
                "  wifi status          - Show WiFi connection status\n"
                "  wifi ssid [value]    - Get/set WiFi SSID\n"
                "  wifi passwd [value]  - Get/set WiFi password\n"
                "  server [url]         - Get/set server URL\n"
                "  status               - Show sensor and fan status\n"
                "  fan [speed]          - Get/set fan speed (0.0-1.0)\n"
                "  reset                - Wipe all settings and reboot");
          } else if (current_input == "wifi status") {
            Serial.print("WiFi Status: ");
            if (WiFi.status() == WL_CONNECTED) {
              Serial.println("Connected");
              Serial.print("SSID: ");
              Serial.println(WiFi.SSID());
              Serial.print("IP Address: ");
              Serial.println(WiFi.localIP());
              Serial.print("Signal Strength: ");
              Serial.print(WiFi.RSSI());
              Serial.println(" dBm");
            } else {
              Serial.println("Disconnected");
            }
            Serial.print("MAC Address: ");
            Serial.println(WiFi.macAddress());
          } else if (current_input.startsWith("wifi ssid")) {
            String arg = current_input.substring(9);
            arg.trim();
            if (arg.length() > 0) {
              preferences.begin("wifi", false);
              preferences.putString("ssid", arg);
              preferences.end();
              if (WiFi.status() == WL_CONNECTED) {
                WiFi.disconnect();
              }
              Serial.print("SSID set to: ");
              Serial.println(arg);
            } else {
              preferences.begin("wifi", true);
              String ssid = preferences.getString("ssid", "");
              preferences.end();
              if (ssid.length() > 0) {
                Serial.print("Current SSID: ");
                Serial.println(ssid);
              } else {
                Serial.println("SSID not set");
              }
            }
          } else if (current_input.startsWith("wifi passwd")) {
            String arg = current_input.substring(11);
            arg.trim();
            if (arg.length() > 0) {
              preferences.begin("wifi", false);
              preferences.putString("passwd", arg);
              preferences.end();
              if (WiFi.status() == WL_CONNECTED) {
                WiFi.disconnect();
              }
              Serial.print("Password set to: ");
              Serial.println(arg);
            } else {
              preferences.begin("wifi", true);
              String passwd = preferences.getString("passwd", "");
              preferences.end();
              if (passwd.length() > 0) {
                Serial.print("Current password: ");
                Serial.println(passwd);
              } else {
                Serial.println("Password not set");
              }
            }
          } else if (current_input.startsWith("server")) {
            String arg = current_input.substring(6);
            arg.trim();
            if (arg.length() > 0) {
              preferences.begin("config", false);
              preferences.putString("server", arg);
              preferences.end();
              Serial.print("Server URL set to: ");
              Serial.println(arg);
            } else {
              preferences.begin("config", true);
              String server = preferences.getString("server", "");
              preferences.end();
              if (server.length() > 0) {
                Serial.print("Current server URL: ");
                Serial.println(server);
              } else {
                Serial.println("Server URL not set");
              }
            }
          } else if (current_input == "status") {
            status.update();
            Serial.print("Temperature: ");
            Serial.print(status.temperature);
            Serial.print(" °C, Humidity: ");
            Serial.print(status.humidity);
            Serial.print("%, Fan Speed: ");
            Serial.print(status.fan_rpm);
            Serial.println(" RPM");
            Serial.print("Fan Power: ");
            Serial.print(getFanPower() * 100.0f);
            Serial.println("%");
          } else if (current_input.startsWith("fan")) {
            String arg = current_input.substring(3);
            arg.trim();
            if (arg.length() > 0) {
              float power = arg.toFloat();
              Serial.print("Fan power set to: ");
              Serial.print(setFanPower(power) * 100.0f);
              Serial.println("%");
            } else {
              Serial.print("Current fan power: ");
              auto power = getFanPower();
              if (std::isnan(power)) {
                Serial.println("(NaN)");
              } else {
                Serial.print(power * 100.0f);
                Serial.println("%");
              }
            }
          } else if (current_input == "reset") {
            Serial.println("Wiping all preferences...");
            preferences.begin("wifi", false);
            preferences.clear();
            preferences.end();
            preferences.begin("config", false);
            preferences.clear();
            preferences.end();
            Serial.println("Rebooting...");
            delay(500);
            ESP.restart();
          } else {
            Serial.print("Unknown command: ");
            Serial.println(current_input);
            Serial.println("Type 'help' for available commands");
          }
          current_input = "";
          Serial.print("> ");
        }
      } else if (c == 8 || c == 127) { // Backspace
        if (current_input.length() > 0) {
          current_input.remove(current_input.length() - 1);
          Serial.print("\b \b");
        }
      } else if (c >= 32 && c <= 126) { // Printable characters
        current_input += c;
        Serial.print(c);
      }
    } else {
      vTaskDelay(pdMS_TO_TICKS(10));
    }
  }
}
