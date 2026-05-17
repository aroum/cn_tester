/**
 * Target firmware for nRF52840.
 *
 * Drives the test harness through three stages:
 * 1) ALL_HIGH — drive all pins HIGH.
 * 2) ALL_LOW  — drive all pins LOW.
 * 3) SEQUENCE — toggle each pin HIGH/LOW.
 *
 * Each stage is triggered by an app command.
 */
#include <Adafruit_TinyUSB.h>
#include <Arduino.h>
#include <MiniShell.h>

#define LED_STATUS_PIN P0_15 // status LED
#define VCC_CTRL_PIN P0_13   // Target controls external power

// Dynamic lines (exact same order as Master TEST_PINS)
const int TEST_PINS[] = {VCC_CTRL_PIN, // P0_13 (VCC)
                         P0_31,        P0_29, P0_02, P1_15, P1_13, P1_11,
                         P0_10,        P0_09, P1_06, P1_04, P0_11, P1_00,
                         P0_24,        P0_22, P0_20, P0_17, P0_08, P0_06};
const int NUM_TEST_PINS = sizeof(TEST_PINS) / sizeof(TEST_PINS[0]);

// Protocol timings
const int SEQ_MS = 150; // duration for each pin in sequence

enum State { STATE_HANDSHAKE, STATE_IDLE };

State state = STATE_HANDSHAKE;
unsigned long lastBlinkMs = 0;

void setAll(int level) {
  for (int i = 0; i < NUM_TEST_PINS; i++) {
    digitalWrite(TEST_PINS[i], level);
  }
}

void setup() {
  Serial.begin(115200);
#if defined(USBCON)
  unsigned long t0 = millis();
  while (!Serial && (millis() - t0) < 3000) {
    delay(10);
  }
#endif

  pinMode(LED_STATUS_PIN, OUTPUT);
  digitalWrite(LED_STATUS_PIN, LOW);

  pinMode(VCC_CTRL_PIN, OUTPUT);
  digitalWrite(VCC_CTRL_PIN, LOW);

  for (int i = 0; i < NUM_TEST_PINS; i++) {
    pinMode(TEST_PINS[i], OUTPUT);
    digitalWrite(TEST_PINS[i], LOW);
  }
}

void loop() {
  unsigned long now = millis();
  static int seqIndex = 0;

  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.equalsIgnoreCase("INIT")) {
      state = STATE_IDLE;
      Serial.println("Target: READY");
      digitalWrite(LED_STATUS_PIN, LOW);
    } else if (cmd.equalsIgnoreCase("START_ALL_HIGH")) {
      state = STATE_IDLE; // auto-transition if INIT was missed
      Serial.println("Target: STAGE — ALL_HIGH: BEGIN");
      setAll(HIGH);
      digitalWrite(LED_STATUS_PIN, HIGH);
      Serial.println("Target: STAGE — ALL_HIGH: OK");
    } else if (cmd.equalsIgnoreCase("START_ALL_LOW")) {
      state = STATE_IDLE;
      Serial.println("Target: STAGE — ALL_LOW: BEGIN");
      setAll(LOW);
      digitalWrite(LED_STATUS_PIN, LOW);
      Serial.println("Target: STAGE — ALL_LOW: OK");
    } else if (cmd.equalsIgnoreCase("START_SEQUENCE")) {
      state = STATE_IDLE;
      Serial.println("Target: STAGE — SEQUENCE: BEGIN");
      seqIndex = 0;
    } else if (cmd.equalsIgnoreCase("NEXT_PIN")) {
      state = STATE_IDLE;
      if (seqIndex < NUM_TEST_PINS) {
        digitalWrite(TEST_PINS[seqIndex], HIGH);
        delay(SEQ_MS);
        digitalWrite(TEST_PINS[seqIndex], LOW);
        seqIndex++;
        if (seqIndex == NUM_TEST_PINS) {
          Serial.println("Target: STAGE — SEQUENCE: ALL OK");
        }
      }
    }
  }

  if (state == STATE_HANDSHAKE) {
    if (now - lastBlinkMs >= 200) {
      Serial.println("Hello! I am Target!");
      lastBlinkMs = now;
      digitalWrite(LED_STATUS_PIN, !digitalRead(LED_STATUS_PIN));
    }
  } else {
    // Heartbeat
    if (now - lastBlinkMs >= 500) {
      Serial.println("Target: STAGE — IDLE: OK");
      lastBlinkMs = now;
    }
  }
}
