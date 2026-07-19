// Master firmware for NRF52840 nice!nano: ALL_HIGH -> ALL_LOW -> SEQUENCE
#include <Adafruit_TinyUSB.h>
#include <Arduino.h>
#include <MiniShell.h>

// --- Special pins ---
#define LED_STATUS_PIN P0_15
#define LED_PCB_PIN P0_13
#define BUTTON_PIN P1_02
#define RESET_SENDER_PIN P1_01

// Master reads external Target power on P1_07; Target controls it via P0_13
const int VCC_PIN = P1_07; // Target power monitor

// Dynamic test pins (order is important and synchronized with Target)
const int TEST_PINS[] = {VCC_PIN, // P1_07 (VCC) — externally controlled power,
                                  // checked as a regular line
                         P0_31, P0_29, P0_02, P1_15, P1_13, P1_11, P0_10, P0_09,
                         P1_06, P1_04, P0_11, P1_00, P0_24, P0_22, P0_20, P0_17,
                         P0_08, P0_06};
const int NUM_TEST_PINS = sizeof(TEST_PINS) / sizeof(TEST_PINS[0]);

// Labels for console printing (must match TEST_PINS order)
const char *TEST_LABELS[] = {"P0_13(VCC)", "P0_31", "P0_29", "P0_02", "P1_15",
                             "P1_13",      "P1_11", "P0_10", "P0_09", "P1_06",
                             "P1_04",      "P0_11", "P1_00", "P0_24", "P0_22",
                             "P0_20",      "P0_17", "P0_08", "P0_06"};

// --- Test states ---
enum TestState {
  STATE_HANDSHAKE,
  STATE_WAIT_BUTTON,
  STATE_WAIT_ALL_HIGH,
  STATE_WAIT_ALL_LOW,
  STATE_SEQUENCE,
  STATE_SUCCESS,
  STATE_FAIL
};

// --- Timing parameters ---
const unsigned long DEBOUNCE_MS = 50;

// --- State variables ---
TestState state = STATE_HANDSHAKE;
unsigned long stateStartMs = 0;
unsigned long lastBlinkMs = 0;
unsigned long lastButtonEdgeMs = 0;
bool lastButtonState = HIGH; // INPUT_PULLUP
int expectedIndex = 0;
bool pinWasHigh[NUM_TEST_PINS];
bool precheckAllHighOk = false;
bool precheckAllLowOk = false;
bool startRequested = false; // start command via Serial
bool startAllHighRequested = false;
bool startAllLowRequested = false;
bool startSequenceRequested = false;
bool nextPinRequested = false;

// One-time BEGIN log flags for stages
bool beginAllHighPrinted = false;
bool beginAllLowPrinted = false;
bool beginSequencePrinted = false;
bool beginFailPrinted = false;

void toState(TestState s) {
  state = s;
  stateStartMs = millis();
}

// Initialize serial, pins, and state machine. Prints "Master: READY".
void setup() {
  Serial.begin(115200);
#if defined(USBCON)
  unsigned long t0 = millis();
  while (!Serial && (millis() - t0) < 3000) {
    delay(10);
  }
#endif
  pinMode(LED_STATUS_PIN, OUTPUT);
  pinMode(LED_PCB_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(RESET_SENDER_PIN, OUTPUT);
  digitalWrite(RESET_SENDER_PIN, HIGH);
  digitalWrite(LED_STATUS_PIN, LOW);
  digitalWrite(LED_PCB_PIN, LOW);

  // Test inputs
  pinMode(VCC_PIN, INPUT);
  for (int i = 0; i < NUM_TEST_PINS; i++) {
    pinMode(TEST_PINS[i], INPUT);
    pinWasHigh[i] = false;
  }
  toState(STATE_HANDSHAKE);
}

// Pulse reset line low-high to reset Target (100 ms low)
void pulseReset() {
  Serial.println("Master: SENT RESET");
  digitalWrite(RESET_SENDER_PIN, LOW); // drive LOW
  delay(100);                          // pulse duration
  digitalWrite(RESET_SENDER_PIN, HIGH);
}

// Enter DFU mode: double reset pulse. Used by FLASH/DFU command.
void enterFlashMode() {
  Serial.println("Master: FLASH command received.");
  pulseReset();
  delay(500);
  pulseReset();
}

// Main state machine loop: handles serial commands, button, and test stages.
void loop() {
  unsigned long now = millis();

  // Create a buffer for the current scan
  int currentLevels[NUM_TEST_PINS];

  // Serial commands
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.equalsIgnoreCase("INIT")) {
      if (state == STATE_HANDSHAKE || state == STATE_WAIT_BUTTON ||
          state == STATE_FAIL || state == STATE_SUCCESS) {
        // pulseReset();
        Serial.println("Master: READY");
        toState(STATE_WAIT_BUTTON);
      }
    } else if (cmd.equalsIgnoreCase("START")) {
      startRequested = true;
      Serial.println("Master: START command received.");
    } else if (cmd.equalsIgnoreCase("START_ALL_HIGH")) {
      startAllHighRequested = true;
    } else if (cmd.equalsIgnoreCase("START_ALL_LOW")) {
      startAllLowRequested = true;
    } else if (cmd.equalsIgnoreCase("START_SEQUENCE")) {
      startSequenceRequested = true;
    } else if (cmd.equalsIgnoreCase("NEXT_PIN")) {
      nextPinRequested = true;
    } else if (cmd.equalsIgnoreCase("FLASH") || cmd.equalsIgnoreCase("DFU")) {
      enterFlashMode();
    }
  }

  // Button handling with debouncing
  bool btn = digitalRead(BUTTON_PIN);
  if (btn != lastButtonState) {
    lastButtonEdgeMs = now;
    lastButtonState = btn;
  }
  bool pressed = (btn == LOW) && (now - lastButtonEdgeMs > DEBOUNCE_MS);

  switch (state) {
  case STATE_HANDSHAKE: {
    if (now - lastBlinkMs >= 200) {
      Serial.println("Hello! I am Master!");
      lastBlinkMs = now;
      digitalWrite(LED_STATUS_PIN, !digitalRead(LED_STATUS_PIN));
    }
  } break;

  case STATE_WAIT_BUTTON: {
    // Blinking indicates idle; awaiting button or START command
    if (now - lastBlinkMs >= 500) {
      Serial.println("Master: STAGE — IDLE: OK");
      lastBlinkMs = now;
      digitalWrite(LED_STATUS_PIN, !digitalRead(LED_STATUS_PIN));
    }
    if (pressed) {
      while (digitalRead(BUTTON_PIN) == LOW) {
        delay(10);
      }
      Serial.println("Master: BUTTON_PRESSED");
    }
    if (startRequested) {
      startRequested = false;
      Serial.println("Master: START");
      precheckAllHighOk = false;
      precheckAllLowOk = false;
      expectedIndex = 0;
      for (int i = 0; i < NUM_TEST_PINS; i++)
        pinWasHigh[i] = false;
      digitalWrite(LED_STATUS_PIN, LOW);
      beginAllHighPrinted = false;
      beginFailPrinted = false;

      // Reset stage requests
      startAllHighRequested = false;
      startAllLowRequested = false;
      startSequenceRequested = false;
      nextPinRequested = false;

      toState(STATE_WAIT_ALL_HIGH);
    }
  } break;

  case STATE_WAIT_ALL_HIGH: {
    // Require: all dynamic lines HIGH (including VCC as a regular line)
    if (!beginAllHighPrinted) {
      Serial.println("Master: STAGE — ALL_HIGH: AWAIT");
      beginAllHighPrinted = true;
    }

    if (startAllHighRequested) {
      startAllHighRequested = false;
      Serial.println("Master: STAGE — ALL_HIGH: BEGIN");

      bool allHigh = true;
      for (int i = 0; i < NUM_TEST_PINS; i++) {
        currentLevels[i] = digitalRead(TEST_PINS[i]);
        if (currentLevels[i] != HIGH)
          allHigh = false;
      }

      if (allHigh) {
        Serial.println("Master: STAGE — ALL_HIGH: OK");
        precheckAllHighOk = true;
        beginAllLowPrinted = false;
        toState(STATE_WAIT_ALL_LOW);
      } else {
        Serial.print("Master: STAGE — ALL_HIGH: ERROR. LOW_PINS: ");
        bool first = true;
        for (int i = 0; i < NUM_TEST_PINS; i++) {
          if (currentLevels[i] == LOW) {
            if (!first)
              Serial.print(", ");
            Serial.print(TEST_LABELS[i]);
            first = false;
          }
        }
        Serial.println();
        beginAllLowPrinted = false;
        toState(STATE_WAIT_ALL_LOW); // continue test regardless
      }
    }
  } break;

  case STATE_WAIT_ALL_LOW: {
    // Require: all dynamic lines LOW (including VCC as a regular line)
    if (!beginAllLowPrinted) {
      Serial.println("Master: STAGE — ALL_LOW: AWAIT");
      beginAllLowPrinted = true;
    }

    if (startAllLowRequested) {
      startAllLowRequested = false;
      Serial.println("Master: STAGE — ALL_LOW: BEGIN");

      bool allLow = true;
      for (int i = 0; i < NUM_TEST_PINS; i++) {
        currentLevels[i] = digitalRead(TEST_PINS[i]);
        if (currentLevels[i] != LOW)
          allLow = false;
      }

      if (allLow) {
        Serial.println("Master: STAGE — ALL_LOW: OK");
        precheckAllLowOk = true;
        beginSequencePrinted = false;
        toState(STATE_SEQUENCE);
      } else {
        Serial.print("Master: STAGE — ALL_LOW: ERROR. HIGH_PINS: ");
        bool first = true;
        for (int i = 0; i < NUM_TEST_PINS; i++) {
          if (currentLevels[i] == HIGH) {
            if (!first)
              Serial.print(", ");
            Serial.print(TEST_LABELS[i]);
            first = false;
          }
        }
        Serial.println();
        beginSequencePrinted = false;
        toState(STATE_SEQUENCE); // continue test regardless
      }
    }
  } break;

  case STATE_SEQUENCE: {
    // Ensure exactly one pin goes HIGH at a time, in strict order
    if (!beginSequencePrinted) {
      Serial.println("Master: STAGE — SEQUENCE: AWAIT");
      beginSequencePrinted = true;
      startSequenceRequested = false;
      nextPinRequested = false;
    }

    if (!startSequenceRequested) {
      break; // Stay in AWAIT until app says start the sequence
    }

    // Inside sequence: wait for NEXT_PIN command for each pin
    if (!nextPinRequested) {
      static unsigned long lastAwaitPrint = 0;
      if (now - lastAwaitPrint > 500) {
        Serial.print("Master: STAGE — SEQUENCE: AWAIT_PIN — ");
        Serial.println(TEST_LABELS[expectedIndex]);
        lastAwaitPrint = now;
      }
      break;
    }

    // NEXT_PIN received: now we check if that pin went high
    int highCount = 0;
    int lastHighIdx = -1;
    for (int i = 0; i < NUM_TEST_PINS; i++) {
      currentLevels[i] = digitalRead(TEST_PINS[i]);
      if (currentLevels[i] == HIGH) {
        highCount++;
        lastHighIdx = i;
      }
    }

    if (highCount > 1) {
      Serial.print("Master: STAGE — SEQUENCE: ERROR. FAIL_PINS: ");
      bool first = true;
      for (int i = 0; i < NUM_TEST_PINS; i++) {
        if (currentLevels[i] == HIGH) {
          if (!first)
            Serial.print(", ");
          Serial.print(TEST_LABELS[i]);
          first = false;
        }
      }
      Serial.println();
      nextPinRequested = false;
      startSequenceRequested = false;
      toState(STATE_FAIL);
      break;
    }

    if (highCount == 1) {
      nextPinRequested = false; // consume command
      Serial.print("Master: STAGE — SEQUENCE: OK — ");
      Serial.println(TEST_LABELS[lastHighIdx]);

      if (lastHighIdx == expectedIndex) {
        expectedIndex++;
        if (expectedIndex == NUM_TEST_PINS) {
          Serial.println("Master: STAGE — SEQUENCE: ALL OK");
          digitalWrite(LED_STATUS_PIN, HIGH);
          startSequenceRequested = false;
          toState(STATE_SUCCESS);
        }
      } else {
        Serial.print("Master: STAGE — SEQUENCE: ERROR. THE ORDER OF SEQUENCE "
                     "IS VIOLATED. EXPECTED: ");
        Serial.print(TEST_LABELS[expectedIndex]);
        Serial.print(", RECEIVED ");
        Serial.println(TEST_LABELS[lastHighIdx]);
        startSequenceRequested = false;
        toState(STATE_FAIL);
      }
    } else {
      // highCount == 0: wait or timeout
      if (now - stateStartMs > 5000) { // 5s timeout per pin
        Serial.print("Master: STAGE — SEQUENCE: ERROR. TIMEOUT. EXPECTED: ");
        Serial.println(TEST_LABELS[expectedIndex]);
        nextPinRequested = false;
        startSequenceRequested = false;
        toState(STATE_FAIL);
      }
    }
  } break;

  case STATE_SUCCESS: {
    // Steady LED — success; wait for new button press
    Serial.print("Master: STAGE — SUCCESS: OK\n");
    toState(STATE_WAIT_BUTTON);
  } break;

  case STATE_FAIL: {
    // Fast blinking — failure; wait for button
    if (!beginFailPrinted) {
      Serial.println("Master: FAIL");
      beginFailPrinted = true;
    }
    if (now - lastBlinkMs >= 150) {
      lastBlinkMs = now;
      digitalWrite(LED_STATUS_PIN, !digitalRead(LED_STATUS_PIN));
    }
    if (pressed || startRequested) {
      if (pressed) {
        while (digitalRead(BUTTON_PIN) == LOW) {
          delay(10);
        }
      }
      startRequested = false;
      Serial.println("Master: START");
      // pulseReset();
      expectedIndex = 0;
      for (int i = 0; i < NUM_TEST_PINS; i++)
        pinWasHigh[i] = false;
      digitalWrite(LED_STATUS_PIN, LOW);
      // Reset preparatory flags and BEGIN markers
      precheckAllHighOk = false;
      precheckAllLowOk = false;
      beginAllHighPrinted = false;
      beginAllLowPrinted = false;
      beginSequencePrinted = false;
      beginFailPrinted = false;

      startAllHighRequested = false;
      startAllLowRequested = false;
      startSequenceRequested = false;
      nextPinRequested = false;

      toState(STATE_WAIT_ALL_HIGH);
    }
  } break;
  }
}
