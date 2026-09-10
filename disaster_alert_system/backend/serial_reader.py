"""
serial_reader.py
-----------------
Reads telemetry lines from the ESP32 over USB serial and parses them into
a structured dict. Runs in its own thread so the Flask/SocketIO server
stays responsive.

Expected line format (from printSerialTelemetry() in the firmware):
Cycle #123 | Accel: 3.5 m/s^2 | Temp: 25.0 C | Gas: 100 | Dist: 50.0 cm | Soil: 30%
"""

import re
import time
import serial
import threading

TELEMETRY_PATTERN = re.compile(
    r"Cycle #(?P<cycle>\d+)\s*\|\s*"
    r"Accel:\s*(?P<accel>[-\d.]+)\s*m/s\^2\s*\|\s*"
    r"Temp:\s*(?P<temp>[-\d.]+)\s*C\s*\|\s*"
    r"Gas:\s*(?P<gas>\d+)\s*\|\s*"
    r"Dist:\s*(?P<dist>[-\d.]+)\s*cm\s*\|\s*"
    r"Soil:\s*(?P<soil>\d+)%"
)


def parse_line(line: str):
    """Return a dict of parsed telemetry, or None if the line doesn't match."""
    match = TELEMETRY_PATTERN.search(line)
    if not match:
        return None
    d = match.groupdict()
    return {
        "cycle": int(d["cycle"]),
        "accel": float(d["accel"]),
        "temp": float(d["temp"]),
        "gas": int(d["gas"]),
        "dist": float(d["dist"]),
        "soil": int(d["soil"]),
        "timestamp": time.time(),
    }


class SerialReader(threading.Thread):
    """
    Background thread that continuously reads lines from the serial port,
    parses them, and calls `on_reading(data_dict)` for each valid reading.

    If `port` is None or the port can't be opened, falls back to a
    simulator so the dashboard can still be developed/tested without
    hardware attached.
    """

    def __init__(self, port=None, baudrate=115200, on_reading=None):
        super().__init__(daemon=True)
        self.port = port
        self.baudrate = baudrate
        self.on_reading = on_reading or (lambda data: None)
        self._stop_event = threading.Event()
        self._ser = None

    def stop(self):
        self._stop_event.set()

    def run(self):
        if self.port:
            try:
                self._ser = serial.Serial(self.port, self.baudrate, timeout=2)
                print(f"[serial_reader] Connected to {self.port} @ {self.baudrate} baud")
                self._run_real()
                return
            except serial.SerialException as e:
                print(f"[serial_reader] Could not open {self.port}: {e}")
                print("[serial_reader] Falling back to simulated data.")

        self._run_simulated()

    def _run_real(self):
        while not self._stop_event.is_set():
            try:
                raw = self._ser.readline().decode("utf-8", errors="ignore").strip()
            except serial.SerialException:
                print("[serial_reader] Serial connection lost.")
                break
            if not raw:
                continue
            data = parse_line(raw)
            if data:
                self.on_reading(data)
        if self._ser:
            self._ser.close()

    def _run_simulated(self):
        """Generates plausible sensor data for dev/demo without hardware."""
        import random

        cycle = 0
        while not self._stop_event.is_set():
            cycle += 1
            data = {
                "cycle": cycle,
                "accel": round(random.gauss(3.5, 0.3), 2),
                "temp": round(random.gauss(26, 1.5), 1),
                "gas": int(random.gauss(80, 15)),
                "dist": round(random.gauss(80, 10), 1),
                "soil": int(max(0, min(100, random.gauss(35, 8)))),
                "timestamp": time.time(),
            }
            # Occasionally inject a disaster spike for demo purposes
            if cycle % 40 == 0:
                spike = random.choice(["accel", "temp", "gas", "dist", "soil"])
                if spike == "accel":
                    data["accel"] = 5.2
                elif spike == "temp":
                    data["temp"] = 38.0
                elif spike == "gas":
                    data["gas"] = 200
                elif spike == "dist":
                    data["dist"] = 6.0
                elif spike == "soil":
                    data["soil"] = 85
            self.on_reading(data)
            time.sleep(0.5)
