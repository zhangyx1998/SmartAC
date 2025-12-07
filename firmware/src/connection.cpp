#include "connection.h"
#include "console.h"
#include "global.h"
#include <WiFi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

void ensureWiFi() {
  // Return immediately if already connected
  if (WiFi.status() == WL_CONNECTED)
    return;

  String ssid = "";
  String passwd = "";

  // Block until valid WiFi credentials are configured
  while (true) {
    preferences.begin("wifi", true);
    ssid = preferences.getString("ssid", "");
    passwd = preferences.getString("passwd", "");
    preferences.end();
    if (ssid.length() > 0) {
      break;
    }
    log("Waiting for WiFi credentials to be configured...");
    vTaskDelay(pdMS_TO_TICKS(2000));
  }

  // Try to connect
  while (WiFi.status() != WL_CONNECTED) {
    wifi_connected = false;
    // Reload credentials on each retry
    preferences.begin("wifi", true);
    ssid = preferences.getString("ssid", "");
    passwd = preferences.getString("passwd", "");
    preferences.end();

    if (ssid.length() == 0) {
      log("WiFi credentials missing...");
      vTaskDelay(pdMS_TO_TICKS(2000));
      continue;
    }

    log("Connecting to WiFi: " + ssid);
    WiFi.begin(ssid.c_str(), passwd.c_str());
    if (WiFi.status() != WL_CONNECTED) {
      // Retry after 1 second
      vTaskDelay(pdMS_TO_TICKS(1000));
    }
  }
  wifi_connected = true;
}
