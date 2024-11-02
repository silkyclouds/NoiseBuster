// PWM to Serial converter script for Sound Level Meters with PWM output but no supported USB protocol
// Created by Alexander Koch
// 2024-11-01

#include <Arduino.h>

const int pwmPin = 15;  // Pin connected to the PWM signal
volatile unsigned long highTime = 0;  // Duration the signal is HIGH
volatile unsigned long lowTime = 0;    // Duration the signal is LOW
volatile unsigned long lastTransitionTime = 0; // Time of the last edge

void handleInterrupt() {
  unsigned long currentTime = micros();
  
  // Calculate the time since the last transition
  unsigned long timeSinceLastTransition = currentTime - lastTransitionTime;
  
  if (digitalRead(pwmPin) == HIGH) {
    // Signal went HIGH
    lowTime += timeSinceLastTransition;  // Accumulate LOW time
    lastTransitionTime = currentTime;    // Update last transition time
  } else {
    // Signal went LOW
    highTime += timeSinceLastTransition; // Accumulate HIGH time
    lastTransitionTime = currentTime;    // Update last transition time
  }
}


void setup() {
  Serial.begin(9600);
  pinMode(pwmPin, INPUT);
  attachInterrupt(digitalPinToInterrupt(pwmPin), handleInterrupt, CHANGE);
}

void loop() {
  // Calculate duty cycle every quarter second
  static unsigned long lastPrintTime = 0;
  if (millis() - lastPrintTime >= 250) {
    lastPrintTime = millis();
    unsigned long totalTime = highTime + lowTime;
    if (totalTime > 0) {
      float dutyCycle = (float)highTime / (float)totalTime * 100.0; // Duty cycle in percentage
      Serial.println(dutyCycle*3.3); //Multiply by 3.3 to get to dB (see datasheet in manual)
    }
    highTime = 0;
    lowTime = 0;
  }
}
