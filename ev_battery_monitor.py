import argparse
import csv
import sys
import time
from collections import deque
from datetime import datetime

import serial
from serial import SerialException
from sklearn.tree import DecisionTreeClassifier


def train_risk_model() -> DecisionTreeClassifier:
    """Train and return a decision tree for battery risk prediction."""
    x_train = [
        [30, 0.5, 3.8],
        [35, 0.8, 3.7],
        [42, 1.2, 3.6],
        [48, 1.5, 3.5],
    ]
    y_train = ["Normal", "Normal", "Warning", "Critical"]

    model = DecisionTreeClassifier(random_state=42)
    model.fit(x_train, y_train)
    return model


def parse_serial_line(line: str):
    """Parse expected serial format: temperature,current,voltage,status."""
    parts = [segment.strip() for segment in line.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Expected 4 fields, got {len(parts)}")

    temperature = float(parts[0])
    current = float(parts[1])
    voltage = float(parts[2])
    status = parts[3]

    if not status:
        raise ValueError("Status field is empty")

    return temperature, current, voltage, status


def write_csv_row(csv_writer, timestamp, temperature, current, voltage, esp_status, ai_prediction):
    csv_writer.writerow(
        {
            "timestamp": timestamp,
            "temperature_c": temperature,
            "current_a": current,
            "voltage_v": voltage,
            "esp_status": esp_status,
            "ai_prediction": ai_prediction,
        }
    )


def start_live_plot(max_points=100):
    import matplotlib.pyplot as plt

    plt.ion()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_title("EV Battery Temperature")
    ax.set_xlabel("Samples")
    ax.set_ylabel("Temperature (C)")
    line, = ax.plot([], [], color="tab:red", linewidth=2)
    return plt, fig, ax, line, deque(maxlen=max_points)


def update_live_plot(plt, ax, line, buffer_values):
    x_values = list(range(len(buffer_values)))
    y_values = list(buffer_values)
    line.set_data(x_values, y_values)
    ax.relim()
    ax.autoscale_view()
    plt.pause(0.001)


def monitor_battery(
    port: str,
    baudrate: int,
    timeout: float,
    enable_csv: bool,
    csv_path: str,
    enable_plot: bool,
):
    model = train_risk_model()

    csv_file = None
    csv_writer = None
    if enable_csv:
        csv_file = open(csv_path, mode="a", newline="", encoding="utf-8")
        fieldnames = [
            "timestamp",
            "temperature_c",
            "current_a",
            "voltage_v",
            "esp_status",
            "ai_prediction",
        ]
        csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if csv_file.tell() == 0:
            csv_writer.writeheader()

    plt = fig = ax = line = temp_buffer = None
    if enable_plot:
        plt, fig, ax, line, temp_buffer = start_live_plot()

    try:
        with serial.Serial(port=port, baudrate=baudrate, timeout=timeout) as ser:
            print(f"Connected to {port} at {baudrate} baud. Listening for data...")
            print("Press Ctrl+C to stop.")

            while True:
                raw_bytes = ser.readline()
                if not raw_bytes:
                    continue

                raw_line = raw_bytes.decode("utf-8", errors="ignore").strip()
                if not raw_line:
                    continue

                # Ignore monitor/debug lines and only parse strict CSV payload rows.
                if raw_line.count(",") != 3:
                    continue

                try:
                    temperature, current, voltage, esp_status = parse_serial_line(raw_line)
                except ValueError as exc:
                    print(f"Invalid data skipped: '{raw_line}' ({exc})")
                    continue

                ai_prediction = model.predict([[temperature, current, voltage]])[0]

                print("-" * 60)
                print(f"Temperature (\u00b0C):  {temperature:.2f}")
                print(f"Current (A):       {current:.2f}")
                print(f"Voltage (V):       {voltage:.2f}")
                print(f"Status from ESP:   {esp_status}")
                print(f"AI Prediction:     {ai_prediction}")

                if ai_prediction == "Critical":
                    print("ALERT: HIGH RISK DETECTED")
                elif ai_prediction == "Warning":
                    print("ALERT: Warning Stage")
                else:
                    print("ALERT: System Normal")

                timestamp = datetime.now().isoformat(timespec="seconds")
                if csv_writer:
                    write_csv_row(
                        csv_writer,
                        timestamp,
                        temperature,
                        current,
                        voltage,
                        esp_status,
                        ai_prediction,
                    )
                    csv_file.flush()

                if enable_plot and temp_buffer is not None:
                    temp_buffer.append(temperature)
                    update_live_plot(plt, ax, line, temp_buffer)

                time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    except SerialException as exc:
        print(f"Serial error: {exc}")
    finally:
        if csv_file:
            csv_file.close()
        if enable_plot and plt is not None:
            plt.ioff()
            plt.show()


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Real-time EV battery monitoring from ESP serial data with AI prediction."
    )
    parser.add_argument("--port", required=True, help="COM port (example: COM3)")
    parser.add_argument("--baudrate", type=int, default=9600, help="Serial baud rate")
    parser.add_argument("--timeout", type=float, default=1.0, help="Serial read timeout in seconds")
    parser.add_argument("--log-csv", action="store_true", help="Enable CSV logging")
    parser.add_argument("--csv-path", default="battery_log.csv", help="CSV file path for logs")
    parser.add_argument("--plot", action="store_true", help="Enable live temperature plot")
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    monitor_battery(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
        enable_csv=args.log_csv,
        csv_path=args.csv_path,
        enable_plot=args.plot,
    )


if __name__ == "__main__":
    if sys.version_info < (3, 9):
        raise RuntimeError("Python 3.9 or higher is required.")
    main()
