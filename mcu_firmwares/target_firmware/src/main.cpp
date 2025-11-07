/**
 * Target firmware for nRF52840.
 *
 * Drives the test harness through three stages:
 * 1) ALL_HIGH — drive all pins HIGH and hold for HOLD_ALL_HIGH_MS.
 * 2) ALL_LOW  — drive all pins LOW and hold for HOLD_ALL_LOW_MS.
 * 3) SEQUENCE — toggle each pin HIGH/LOW with SEQ_HIGH_MS/SEQ_LOW_MS timing.
 *
 * Prints status lines to Serial consumed by the Master.
 */
#include <Arduino.h>

#define LED_STATUS_PIN P0_15  // status LED: ON during ALL_HIGH stage
#define VCC_CTRL_PIN   P0_13  // Target controls external power

// Dynamic lines (exact same order as Master TEST_PINS)
const int TEST_PINS[] = {
  VCC_CTRL_PIN, // P0_13 (VCC) — externally powered rail controlled as a regular line
  P0_31,
  P0_29,
  P0_02,
  P1_15,
  P1_13,
  P1_11,
  P0_10,
  P0_09,
  P1_06,
  P1_04,
  P0_11,
  P1_00,
  P0_24,
  P0_22,
  P0_20,
  P0_17,
  P0_08,
  P0_06
};
const int NUM_TEST_PINS = sizeof(TEST_PINS) / sizeof(TEST_PINS[0]);

// Protocol timings
const int HOLD_ALL_HIGH_MS = 1000; // hold all HIGH so Master can sample
const int HOLD_ALL_LOW_MS  = 1000; // hold all LOW so Master can sample
const int SEQ_HIGH_MS      = 150;  // HIGH duration for each pin in sequence
const int SEQ_LOW_MS       = 150;  // LOW pause between sequence elements

/**
 * Drive all test pins to the provided logic level.
 * @param level Use `HIGH` or `LOW`.
 */
void setAll(int level) {
  for (int i = 0; i < NUM_TEST_PINS; i++) {
    digitalWrite(TEST_PINS[i], level);
  }
}

/**
 * Initialize Serial and pins, then execute the test sequence once.
 * Emits "Target: READY" followed by stage markers.
 */
void setup() {
  Serial.begin(115200);
#if defined(USBCON)
  unsigned long t0 = millis();
  while (!Serial && (millis() - t0) < 3000) { delay(10); }
#endif
  Serial.println("Target: READY");

  pinMode(LED_STATUS_PIN, OUTPUT);
  digitalWrite(LED_STATUS_PIN, LOW);

  pinMode(VCC_CTRL_PIN, OUTPUT);
  digitalWrite(VCC_CTRL_PIN, LOW); // external target power disabled by default

  for (int i = 0; i < NUM_TEST_PINS; i++) {
    pinMode(TEST_PINS[i], OUTPUT);
    digitalWrite(TEST_PINS[i], LOW);
  }

  // Stage 1 — all HIGH
  Serial.println("Target: STAGE — ALL_HIGH: BEGIN");
  setAll(HIGH);
  digitalWrite(LED_STATUS_PIN, HIGH);
  delay(HOLD_ALL_HIGH_MS);
  Serial.println("Target: STAGE — ALL_HIGH: OK");

  // Stage 2 — all LOW
  Serial.println("Target: STAGE — ALL_LOW: BEGIN");
  setAll(LOW);
  digitalWrite(LED_STATUS_PIN, LOW);
  delay(HOLD_ALL_LOW_MS);
  Serial.println("Target: STAGE — ALL_LOW: OK");

  // Stage 3 — per-pin sequence
  Serial.println("Target: STAGE — SEQUENCE: BEGIN");
  for (int i = 0; i < NUM_TEST_PINS; i++) {
    digitalWrite(TEST_PINS[i], HIGH);
    delay(SEQ_HIGH_MS);
    digitalWrite(TEST_PINS[i], LOW);
    delay(SEQ_LOW_MS);
  }
  Serial.println("Target: STAGE — SEQUENCE: ALL OK");
//   delay(100);
}

/**
 * Send periodic idle status line. Master uses this as a heartbeat.
 */
void loop() {
  Serial.println("Target: STAGE — IDLE: OK");
}


