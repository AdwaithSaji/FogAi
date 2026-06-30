# ============================================================
#  IoT Sensor Simulator
#  Generates realistic multi-parameter sensor readings with
#  controlled anomaly injection for demonstration purposes.
# ============================================================

import random
import math
import time
from dataclasses import dataclass, field
from typing import Optional
import config


@dataclass
class SensorReading:
    timestamp: float
    cycle: int
    temperature: float      # °C
    humidity: float         # %
    cpu_load: float         # %
    vibration: float        # g  (gravitational units)
    network_latency: float  # ms (measured round-trip to cloud)
    power_draw: float       # W
    machine_id: str = config.MACHINE_ID

    # Derived flags set after creation
    anomaly_type: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "timestamp": round(self.timestamp, 3),
            "cycle": self.cycle,
            "machine_id": self.machine_id,
            "temperature_C": round(self.temperature, 2),
            "humidity_pct": round(self.humidity, 2),
            "cpu_load_pct": round(self.cpu_load, 2),
            "vibration_g": round(self.vibration, 3),
            "network_latency_ms": round(self.network_latency, 1),
            "power_draw_W": round(self.power_draw, 1),
            "anomaly_type": self.anomaly_type,
        }


class SensorSimulator:
    """
    Simulates an array of IoT sensors attached to industrial equipment.

    The simulation models:
      - Normal operation with Gaussian noise
      - Gradual drift (temperature creep)
      - Sudden spike events (vibration shock)
      - Persistent fault states (overheating scenario)
      - Network degradation episodes
    """

    def __init__(self):
        self._cycle = 0
        self._base_temp = 42.0          # baseline machine temperature
        self._temp_drift = 0.0          # accumulated drift
        self._overheating_mode = False  # flag for sustained fault
        self._net_degraded = False      # network degradation window
        self._net_degraded_count = 0
        self._vibration_shock = False
        self._shock_count = 0

        # Schedule anomaly injection at deterministic cycles for demo
        self._anomaly_schedule = {
            12: "TEMP_SPIKE",
            22: "NET_DEGRADATION",
            33: "OVERHEATING_START",
            38: "VIBRATION_SHOCK",
            45: "OVERHEATING_PEAK",
            52: "NET_DOWN",
            58: "RECOVERY",
        }

    def _noise(self, sigma: float) -> float:
        return random.gauss(0, sigma)

    def _generate_temperature(self) -> float:
        if self._overheating_mode:
            # Rapidly rising temperature during fault
            target = 88.0 + self._temp_drift
            return max(target + self._noise(1.5), 70.0)
        temp = self._base_temp + self._temp_drift + self._noise(1.2)
        return round(max(min(temp, 95.0), 18.0), 2)

    def _generate_network_latency(self) -> float:
        if self._net_degraded:
            base = 220.0 + random.uniform(0, 120)
            if self._net_degraded_count > 5:
                return 9999.0  # network down
            return round(base + self._noise(30), 1)
        return round(max(10.0, config.CLOUD_LATENCY_BASE + self._noise(config.CLOUD_LATENCY_JITTER)), 1)

    def _generate_vibration(self) -> float:
        if self._vibration_shock:
            return round(3.8 + self._noise(0.4), 3)
        return round(0.8 + abs(self._noise(0.3)), 3)

    def read(self) -> SensorReading:
        self._cycle += 1
        c = self._cycle

        # Inject scheduled anomalies
        event = self._anomaly_schedule.get(c)
        anomaly_label = None

        if event == "TEMP_SPIKE":
            self._temp_drift += 8.0
            anomaly_label = "TEMP_SPIKE"
        elif event == "NET_DEGRADATION":
            self._net_degraded = True
            self._net_degraded_count = 0
            anomaly_label = "NETWORK_DEGRADED"
        elif event == "OVERHEATING_START":
            self._overheating_mode = True
            self._temp_drift = 15.0
            anomaly_label = "OVERHEATING_BEGIN"
        elif event == "VIBRATION_SHOCK":
            self._vibration_shock = True
            self._shock_count = 0
            anomaly_label = "VIBRATION_SHOCK"
        elif event == "OVERHEATING_PEAK":
            self._temp_drift = 28.0
            anomaly_label = "OVERHEATING_CRITICAL"
        elif event == "NET_DOWN":
            self._net_degraded = True
            self._net_degraded_count = 10  # force offline
            anomaly_label = "NETWORK_DOWN"
        elif event == "RECOVERY":
            self._overheating_mode = False
            self._temp_drift = max(0.0, self._temp_drift - 20.0)
            self._net_degraded = False
            self._vibration_shock = False
            anomaly_label = "SYSTEM_RECOVERY"

        # Advance state counters
        if self._net_degraded:
            self._net_degraded_count += 1
        if self._vibration_shock:
            self._shock_count += 1
            if self._shock_count > 4:
                self._vibration_shock = False

        # Slow drift during overheating
        if self._overheating_mode and not event:
            self._temp_drift += 0.6

        # Gradual temperature normalization outside fault
        if not self._overheating_mode and self._temp_drift > 0:
            self._temp_drift = max(0.0, self._temp_drift - 0.8)

        temperature = self._generate_temperature()
        cpu_load    = round(min(40.0 + abs(self._noise(15)) + (temperature - 42) * 0.3, 99.9), 1)
        humidity    = round(50.0 + self._noise(8.0), 1)
        vibration   = self._generate_vibration()
        net_latency = self._generate_network_latency()
        power_draw  = round(280 + cpu_load * 1.8 + self._noise(10), 1)

        # Infer anomaly label from values if not explicitly set
        if not anomaly_label:
            if temperature >= config.TEMP_CRITICAL:
                anomaly_label = "HIGH_TEMP"
            elif vibration >= config.VIBRATION_WARNING:
                anomaly_label = "HIGH_VIBRATION"
            elif net_latency >= config.NETWORK_DOWN_LATENCY:
                anomaly_label = "NETWORK_DOWN"

        return SensorReading(
            timestamp=time.time(),
            cycle=c,
            temperature=temperature,
            humidity=max(20.0, min(95.0, humidity)),
            cpu_load=cpu_load,
            vibration=vibration,
            network_latency=net_latency,
            power_draw=power_draw,
            anomaly_type=anomaly_label,
        )
