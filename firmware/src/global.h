#pragma once

#include <Arduino.h>
#include <FastLED.h>
#include <Preferences.h>
#include <SHT31.h>

// Hardware definitions
#define NUM_LEDS 8
#define LED_PIN D6
#define FAN_PWM D3
#define FAN_TCH D2

#define IIC_SCL A5
#define IIC_SDA A4

// FanPulseCounter class definition
class FanPulseCounter {
private:
  unsigned long last_check = micros();
  unsigned long count;

public:
  inline void tick() { count++; }
  inline float rpm() {
    unsigned long now = micros();
    float dt = (now - last_check) * 1e-6; // seconds
    last_check = now;
    float rpm = 60.0 * ((float)count / dt) / 2.0; // 2 pulses per revolution
    count = 0;
    return rpm; // convert to RPM
  }
};

// Status struct definition
struct Status {
  float temperature = NAN;
  float humidity = NAN;
  float fan_rpm = 0.0f;
  struct Status &update();
};

// Global singleton declarations (defined in main.cpp)
extern CRGB leds[NUM_LEDS];
extern SHT31 sht;
extern Preferences preferences;
extern FanPulseCounter fan_pulse_counter;
extern Status status;
extern volatile bool wifi_connected;

float setFanPower(float power);
float getFanPower();