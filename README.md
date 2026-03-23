# Real-Time EV Battery Monitoring and Safety System

This project combines:

1. Reactive safety on ESP32/Arduino based on fixed electrical thresholds.
2. Predictive AI analysis on PC (Python) using a Decision Tree model.

The ESP32 reads battery-related sensor values and immediately applies hardware safety actions.
At the same time, the Python app receives serial data in real time and predicts battery risk.

## Project Files

- `esp32_ev_monitor.ino`: ESP32 firmware for sensing, threshold checks, relay/buzzer/LED control, serial output, and LoRa transmission.
- `ev_battery_monitor.py`: Python real-time serial monitor with Decision Tree prediction, alerts, optional CSV logging, and optional live plotting.
- `requirements.txt`: Python dependencies.

## Data Format (ESP32 -> Python)

Serial payload format:

`temperature,current,voltage,status`

Example:

`34,0.8,3.7,NORMAL`

## What Happens in This Project

1. ESP32 reads three analog sensors:
   - Temperature sensor
   - Current sensor
   - Voltage sensor
2. ESP32 converts raw ADC values to engineering units:
   - Temperature in C
   - Current in A
   - Voltage in V
3. ESP32 safety logic checks thresholds:
   - Temperature > 45 C -> unsafe
   - Current > 1.2 A -> unsafe
   - Voltage < 3.5 V -> unsafe
4. If unsafe:
   - Relay OFF (disconnect battery)
   - Buzzer ON
   - LED ON
   - Status = DISCONNECTED
5. If safe:
   - Relay ON
   - Buzzer OFF
   - LED OFF
   - Status = NORMAL
6. ESP32 sends the same message through:
   - Serial (for Python)
   - LoRa
7. Python app reads serial continuously at 9600 baud.
8. Python safely parses and validates incoming lines.
9. Python model predicts risk with Decision Tree:
   - Normal, Warning, or Critical
10. Python prints formatted values and alert text:
   - Critical -> HIGH RISK DETECTED
   - Warning -> Warning Stage
   - Else -> System Normal

## AI Model Used in Python

Training data used in `ev_battery_monitor.py`:

```python
X = [
    [30, 0.5, 3.8],
    [35, 0.8, 3.7],
    [42, 1.2, 3.6],
    [48, 1.5, 3.5]
]
y = ["Normal", "Normal", "Warning", "Critical"]
```

Model type:

- `DecisionTreeClassifier` from scikit-learn

## How to Run (Python Side)

### 1) Prerequisites

- Python 3.9+
- ESP32 connected over USB and streaming serial data

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

### 3) Run monitor

Replace COM3 with your actual COM port.

```powershell
python ev_battery_monitor.py --port COM3 --baudrate 9600
```

### 4) Run with optional features

CSV logging:

```powershell
python ev_battery_monitor.py --port COM3 --baudrate 9600 --log-csv --csv-path battery_log.csv
```

Live plot:

```powershell
python ev_battery_monitor.py --port COM3 --baudrate 9600 --plot
```

CSV + live plot:

```powershell
python ev_battery_monitor.py --port COM3 --baudrate 9600 --log-csv --plot
```

## How to Run (ESP32 Side)

### 1) Open firmware

- Open `esp32_ev_monitor.ino` in Arduino IDE.

### 2) Install required library

- Install LoRa library that provides `LoRa.h`.

### 3) Select board and port

- Board: your ESP32 board
- Port: your ESP32 COM port

### 4) Verify pin mappings and calibration constants

In `esp32_ev_monitor.ino`, check and adjust:

- Sensor pins (`TEMP_PIN`, `CURRENT_PIN`, `VOLTAGE_PIN`)
- Actuator pins (`RELAY_PIN`, `BUZZER_PIN`, `LED_PIN`)
- LoRa pins (`LORA_SS`, `LORA_RST`, `LORA_DIO0`) and frequency
- Sensor calibration constants:
  - `TEMP_SENSOR_SCALE`
  - `CURRENT_ZERO_V`
  - `CURRENT_SENSITIVITY_V_PER_A`
  - `VOLTAGE_DIVIDER_RATIO`

### 5) Upload and monitor

- Upload firmware to ESP32.
- Open Serial Monitor at 9600 baud.
- Confirm continuous output every 1 second.

## Output Example

```text
------------------------------------------------------------
Temperature (°C):  34.00
Current (A):       0.80
Voltage (V):       3.70
Status from ESP:   NORMAL
AI Prediction:     Normal
ALERT: System Normal
```

## Notes and Assumptions

- Current firmware uses generic calibration defaults (LM35/ACS712/divider-style assumptions).
- For accurate real hardware values, calibrate constants using your sensor datasheets and measured references.
- Python script skips malformed serial lines safely and keeps running.

## Optional Extensions

- Add GSM SMS alert in unsafe condition (DISCONNECTED).
- Add MOSFET-based heating simulation logic in ESP32 loop.
- Save LoRa receiver logs and compare with serial stream.
