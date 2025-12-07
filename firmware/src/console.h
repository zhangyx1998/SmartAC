#pragma once

#include <Arduino.h>

// Log function that preserves the interactive prompt
void log(const String &message);

// Console task function
void consoleTask(void *parameter);
