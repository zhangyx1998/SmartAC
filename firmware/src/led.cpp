#include "led.h"
#include <cmath>

// 0.0-1.0 for h, s, l
CRGB hsl(float h, float s, float l) {
  float c = (1.0f - fabs(2.0f * l - 1.0f)) * s;
  float x = c * (1.0f - fabs(fmod(h * 6.0f, 2.0f) - 1.0f));
  float m = l - c / 2.0f;

  float r, g, b;

  if (h < 1.0f / 6.0f) {
    r = c;
    g = x;
    b = 0;
  } else if (h < 2.0f / 6.0f) {
    r = x;
    g = c;
    b = 0;
  } else if (h < 3.0f / 6.0f) {
    r = 0;
    g = c;
    b = x;
  } else if (h < 4.0f / 6.0f) {
    r = 0;
    g = x;
    b = c;
  } else if (h < 5.0f / 6.0f) {
    r = x;
    g = 0;
    b = c;
  } else {
    r = c;
    g = 0;
    b = x;
  }

  return CRGB((uint8_t)((r + m) * 255), (uint8_t)((g + m) * 255),
              (uint8_t)((b + m) * 255));
}
