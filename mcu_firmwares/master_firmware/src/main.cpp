// Master firmware for NRF52840 nice!nano: ALL_HIGH -> ALL_LOW -> SEQUENCE
#include <Arduino.h>

// --- Special pins ---
#define LED_STATUS_PIN    P0_15
#define LED_PCB_PIN       P0_13
#define BUTTON_PIN        P1_02
#define RESET_SENDER_PIN  P1_01

// Master reads external Target power on P1_07; Target controls it via P0_13
const int VCC_PIN = P1_07; // Target power monitor

// Dynamic test pins (order is important and synchronized with Target)
const int TEST_PINS[] = {
  VCC_PIN,  // P1_07 (VCC) — externally controlled power, checked as a regular line
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

// Labels for console printing (must match TEST_PINS order)
const char* TEST_LABELS[] = {
  "P1_07(VCC)",
  "P0_31",
  "P0_29",
  "P0_02",
  "P1_15",
  "P1_13",
  "P1_11",
  "P0_10",
  "P0_09",
  "P1_06",
  "P1_04",
  "P0_11",
  "P1_00",
  "P0_24",
  "P0_22",
  "P0_20",
  "P0_17",
  "P0_08",
  "P0_06"
};

// --- Test states ---
enum TestState {
  STATE_WAIT_BUTTON,
  STATE_WAIT_ALL_HIGH,
  STATE_WAIT_ALL_LOW,
  STATE_SEQUENCE,
  STATE_SUCCESS,
  STATE_FAIL
};

// --- Timing parameters ---
const unsigned long PRECHECK_TIMEOUT_MS = 3000;   // wait for ALL_HIGH
const unsigned long LOW_STAGE_TIMEOUT_MS = 3000;  // wait for ALL_LOW
const unsigned long SEQUENCE_TIMEOUT_MS = 15000;  // sequence stage total
const unsigned long DEBOUNCE_MS = 50;

// --- State variables ---
TestState state = STATE_WAIT_BUTTON;
unsigned long stateStartMs = 0;
unsigned long lastBlinkMs = 0;
unsigned long lastButtonEdgeMs = 0;
bool lastButtonState = HIGH; // INPUT_PULLUP
int expectedIndex = 0;
bool pinWasHigh[NUM_TEST_PINS];
bool precheckAllHighOk = false;
bool precheckAllLowOk = false;
bool startRequested = false; // start command via Serial
// One-time BEGIN log flags for stages
bool beginAllHighPrinted = false;
bool beginAllLowPrinted = false;
bool beginSequencePrinted = false;
bool beginFailPrinted = false;

// Utility: print dynamic pins filtered by level
void printDynamicPinsByLevel(int level) {
  bool first = true;
  for (int i = 0; i < NUM_TEST_PINS; i++) {
    int lvl = digitalRead(TEST_PINS[i]);
    if (lvl == level) {
      if (!first) Serial.print(", ");
      Serial.print(TEST_LABELS[i]);
      first = false;
    }
  }
  Serial.println();
}

void toState(TestState s) {
  state = s;
  stateStartMs = millis();
}

// Initialize serial, pins, and state machine. Prints "Master: READY".
void setup() {
  Serial.begin(115200);
#if defined(USBCON)
  unsigned long t0 = millis();
  while (!Serial && (millis() - t0) < 3000) { delay(10); }
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
  Serial.println("Master: READY");
  toState(STATE_WAIT_BUTTON);
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
  delay(200);
  pulseReset();
}

// Main state machine loop: handles serial commands, button, and test stages.
void loop() {
  unsigned long now = millis();

  // START command from Serial
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.equalsIgnoreCase("START")) {
      startRequested = true;
      Serial.println("Master: START command received.");
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
    case STATE_WAIT_BUTTON: {
      // Blinking indicates idle; awaiting button or START command
      if (now - lastBlinkMs >= 500) {
        Serial.println("Master: STAGE — IDLE: OK");
        lastBlinkMs = now;
        digitalWrite(LED_STATUS_PIN, !digitalRead(LED_STATUS_PIN));
      }
      if (pressed || startRequested) {
        startRequested = false;
        while (digitalRead(BUTTON_PIN) == LOW) { delay(10); }
        Serial.println("Master: START");
        pulseReset();
        precheckAllHighOk = false;
        precheckAllLowOk = false;
        expectedIndex = 0;
        for (int i = 0; i < NUM_TEST_PINS; i++) pinWasHigh[i] = false;
        digitalWrite(LED_STATUS_PIN, LOW);
        beginAllHighPrinted = false;
        beginFailPrinted = false;
        toState(STATE_WAIT_ALL_HIGH);
      }
    } break;

    case STATE_WAIT_ALL_HIGH: {
      // Require: all dynamic lines HIGH (including VCC as a regular line)
      bool allHigh = true;
      if (!beginAllHighPrinted) {
        Serial.println("Master: STAGE — ALL_HIGH: BEGIN");
        beginAllHighPrinted = true;
      }
      
      for (int i = 0; i < NUM_TEST_PINS; i++) {
        if (digitalRead(TEST_PINS[i]) != HIGH) { allHigh = false; break; }
      }
      if (allHigh) {
        Serial.println("Master: STAGE — ALL_HIGH: OK");
        precheckAllHighOk = true;
        beginAllLowPrinted = false;
        toState(STATE_WAIT_ALL_LOW);
      } else if (now - stateStartMs > PRECHECK_TIMEOUT_MS) {
        Serial.print("Master: STAGE — ALL_HIGH: ERROR. LOW_PINS: ");
        printDynamicPinsByLevel(LOW);
        beginAllLowPrinted = false;
        toState(STATE_WAIT_ALL_LOW); // continue test regardless
      }
    } break;

    case STATE_WAIT_ALL_LOW: {
      // Require: all dynamic lines LOW (including VCC as a regular line)
      bool allLow = true;
      if (!beginAllLowPrinted) {
        Serial.println("Master: STAGE — ALL_LOW: BEGIN");
        beginAllLowPrinted = true;
      }

      for (int i = 0; i < NUM_TEST_PINS; i++) {
        if (digitalRead(TEST_PINS[i]) != LOW) { allLow = false; break; }
      }
      if (allLow) {
        Serial.println("Master: STAGE — ALL_LOW: OK");
        precheckAllLowOk = true;
        beginSequencePrinted = false;
        toState(STATE_SEQUENCE);
      } else if (now - stateStartMs > LOW_STAGE_TIMEOUT_MS) {
        Serial.print("Master: STAGE — ALL_LOW: ERROR. HIGH_PINS: ");
        printDynamicPinsByLevel(HIGH);
        beginSequencePrinted = false;
        toState(STATE_SEQUENCE); // continue test regardless
      }
    } break;

    case STATE_SEQUENCE: {
      // Ensure exactly one pin goes HIGH at a time, in strict order
      if (!beginSequencePrinted) {
        Serial.println("Master: STAGE — SEQUENCE: BEGIN");
        beginSequencePrinted = true;
      }
      
      int highCount = 0;
      int highIdx = -1;
      for (int i = 0; i < NUM_TEST_PINS; i++) {
        int lvl = digitalRead(TEST_PINS[i]);
        if (lvl == HIGH) {
          highCount++;
          highIdx = i;
        }
      }

      if (highCount > 1) {
        Serial.print("Master: STAGE — SEQUENCE: ERROR. FAIL_PINS: ");
        printDynamicPinsByLevel(HIGH);
        toState(STATE_FAIL);
        break;
      }

      if (highCount == 1) {
        // Detect rising edge (LOW->HIGH)
        if (!pinWasHigh[highIdx]) {
          pinWasHigh[highIdx] = true;
          Serial.print("Master: STAGE — SEQUENCE: OK — ");
          Serial.println(TEST_LABELS[highIdx]);

          if (highIdx == expectedIndex) {
            expectedIndex++;
            if (expectedIndex == NUM_TEST_PINS) {
              Serial.println("Master: STAGE — SEQUENCE: ALL OK");
              digitalWrite(LED_STATUS_PIN, HIGH);
              toState(STATE_SUCCESS);
              break;
            }
          } else if (highIdx > expectedIndex) {
            Serial.print("Master: STAGE — SEQUENCE: ERROR. THE ORDER OF SEQUENCE IS VIOLATED. EXPECTED: ");
            Serial.print(TEST_LABELS[expectedIndex]);
            Serial.print(", RECIVED ");
            Serial.println(TEST_LABELS[highIdx]);
            toState(STATE_FAIL);
            break;
          } else { // highIdx < expectedIndex
            Serial.print("Master: STAGE — SEQUENCE: ERROR. REPEATED/EARLIER RAISE ");
            Serial.println(TEST_LABELS[highIdx]);
            toState(STATE_FAIL);
            break;
          }
        }
      } else {
        // No pin HIGH — clear marks to catch future rising edges
        for (int i = 0; i < NUM_TEST_PINS; i++) {
          if (digitalRead(TEST_PINS[i]) == LOW) pinWasHigh[i] = false;
        }
      }

      if (now - stateStartMs > SEQUENCE_TIMEOUT_MS) {
        Serial.print("Master: STAGE — SEQUENCE: ERROR. TIMEOUT. EXPECTED: ");
        Serial.println(expectedIndex < NUM_TEST_PINS ? TEST_LABELS[expectedIndex] : "end");
        toState(STATE_FAIL);
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
          while (digitalRead(BUTTON_PIN) == LOW) { delay(10); }
        }
        startRequested = false;
        Serial.println("Master: START");
        pulseReset();
        expectedIndex = 0;
        for (int i = 0; i < NUM_TEST_PINS; i++) pinWasHigh[i] = false;
        digitalWrite(LED_STATUS_PIN, LOW);
        // Reset preparatory flags and BEGIN markers
        precheckAllHighOk = false;
        precheckAllLowOk = false;
        beginAllHighPrinted = false;
        beginAllLowPrinted = false;
        beginSequencePrinted = false;
        beginFailPrinted = false;
        toState(STATE_WAIT_ALL_HIGH);
      }
    } break;
  }
}
