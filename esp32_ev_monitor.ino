#include <SPI.h>
#include <LoRa.h>

// -------- Sensor pins (ESP32 ADC pins) --------
const int TEMP_PIN = 34;
const int CURRENT_PIN = 35;
const int VOLTAGE_PIN = 32;

// -------- Actuator pins --------
const int RELAY_PIN = 26;
const int BUZZER_PIN = 27;
const int LED_PIN = 25;

// -------- LoRa pins / config (adjust for your module) --------
const int LORA_SS = 5;
const int LORA_RST = 14;
const int LORA_DIO0 = 2;
const long LORA_FREQUENCY = 433E6;

// -------- Safety thresholds --------
const float TEMP_LIMIT_C = 45.0;
const float CURRENT_LIMIT_A = 1.2;
const float MIN_VOLTAGE_V = 3.5;

// -------- Calibration constants --------
const float ADC_REF_V = 3.3;
const float ADC_MAX = 4095.0;

// LM35 example: 10 mV / degree C
const float TEMP_SENSOR_SCALE = 100.0;

// ACS712 example: 185 mV / A, 2.5 V zero-current offset
const float CURRENT_ZERO_V = 2.5;
const float CURRENT_SENSITIVITY_V_PER_A = 0.185;

// Voltage divider scaling (example for 2:1 divider)
const float VOLTAGE_DIVIDER_RATIO = 2.0;

float adcToVoltage(int raw) {
  return (raw * ADC_REF_V) / ADC_MAX;
}

float readTemperatureC() {
  int raw = analogRead(TEMP_PIN);
  float sensorV = adcToVoltage(raw);
  return sensorV * TEMP_SENSOR_SCALE;
}

float readCurrentA() {
  int raw = analogRead(CURRENT_PIN);
  float sensorV = adcToVoltage(raw);
  float current = (sensorV - CURRENT_ZERO_V) / CURRENT_SENSITIVITY_V_PER_A;
  if (current < 0) {
    current = -current;
  }
  return current;
}

float readVoltageV() {
  int raw = analogRead(VOLTAGE_PIN);
  float sensorV = adcToVoltage(raw);
  return sensorV * VOLTAGE_DIVIDER_RATIO;
}

void applySafeState() {
  digitalWrite(RELAY_PIN, HIGH);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_PIN, LOW);
}

void applyUnsafeState() {
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(BUZZER_PIN, HIGH);
  digitalWrite(LED_PIN, HIGH);
}

void setup() {
  Serial.begin(9600);

  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);

  applySafeState();

  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(LORA_FREQUENCY)) {
    Serial.println("LoRa init failed");
  } else {
    Serial.println("LoRa init success");
  }
}

void loop() {
  float temperatureC = readTemperatureC();
  float currentA = readCurrentA();
  float voltageV = readVoltageV();

  bool unsafe = (temperatureC > TEMP_LIMIT_C) ||
                (currentA > CURRENT_LIMIT_A) ||
                (voltageV < MIN_VOLTAGE_V);

  const char* status;
  if (unsafe) {
    applyUnsafeState();
    status = "DISCONNECTED";

    // Optional: GSM SMS alert can be sent here when unsafe becomes true.
    // Optional: MOSFET-based heating simulation can be toggled here.
  } else {
    applySafeState();
    status = "NORMAL";
  }

  char payload[64];
  snprintf(payload, sizeof(payload), "%.2f,%.2f,%.2f,%s", temperatureC, currentA, voltageV, status);

  // Machine-readable CSV line for Python parser
  Serial.println(payload);

  // Human-readable lines for Arduino Serial Monitor
  Serial.println("--------------------------------");
  Serial.print("Temperature (C): ");
  Serial.println(temperatureC, 2);
  Serial.print("Current (A): ");
  Serial.println(currentA, 2);
  Serial.print("Voltage (V): ");
  Serial.println(voltageV, 2);
  Serial.print("Status: ");
  Serial.println(status);

  // Send same payload over LoRa
  LoRa.beginPacket();
  LoRa.print(payload);
  LoRa.endPacket();

  delay(1000);
}
