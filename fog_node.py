# ============================================================
#  Fog Node Processor
#  Orchestrates sensor ingestion, AI decision, local action,
#  and cloud forwarding within a single processing cycle.
# ============================================================

import time
import json
import os
import logging
from datetime import datetime
from typing import Optional

import config
from sensor import SensorReading
from ai_engine import FogAIEngine, DecisionResult, ACTION_SHUTDOWN, ACTION_ALERT, ACTION_THROTTLE
from cloud_stub import CloudService

logger = logging.getLogger("FogNode")


class FogNode:
    """
    Represents the fog computing node installed close to industrial equipment.

    Responsibilities:
      1. Receive raw sensor data from the IoT sensors
      2. Run AI decision engine locally (sub-10 ms)
      3. Execute immediate safety actions without cloud round-trip
      4. Optionally forward telemetry to the cloud for long-term analytics
    """

    def __init__(self, cloud: CloudService, log_dir: str = "logs"):
        self.node_id   = config.FOG_NODE_ID
        self.ai_engine = FogAIEngine()
        self.cloud     = cloud
        self._cycle_log: list = []

        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._local_log_path = os.path.join(log_dir, f"fog_decisions_{ts}.jsonl")

        self._alerts_sent    = 0
        self._shutdowns_exec = 0
        self._cloud_sends    = 0
        self._fog_only       = 0
        self._start_time     = time.time()

    # ------------------------------------------------------------------

    def process(self, reading: SensorReading) -> DecisionResult:
        """
        Full processing pipeline for one sensor reading.
        Returns the DecisionResult for dashboard display.
        """
        # 1. AI decides
        decision = self.ai_engine.decide(reading)

        # 2. Execute local action immediately (no cloud needed)
        self._execute_action(decision, reading)

        # 3. Forward to cloud if decision warrants it
        if decision.destination in ("CLOUD", "BOTH"):
            payload = {**reading.to_dict(), **decision.to_dict()}
            receipt = self.cloud.ingest(payload, simulate_latency=False)
            decision.reason += f" | cloud_receipt={receipt.get('record_id', 'ERR')}"
            self._cloud_sends += 1
        else:
            self._fog_only += 1

        # 4. Write to local JSONL log
        self._write_local_log(reading, decision)

        return decision

    # ------------------------------------------------------------------

    def _execute_action(self, decision: DecisionResult, reading: SensorReading):
        if decision.action == ACTION_SHUTDOWN:
            logger.critical(
                "[%s] EMERGENCY SHUTDOWN — %s | temp=%.1f°C vibr=%.2fg",
                self.node_id, reading.machine_id,
                reading.temperature, reading.vibration,
            )
            self._shutdowns_exec += 1

        elif decision.action == ACTION_ALERT:
            logger.warning(
                "[%s] ALERT — %s | risk=%.2f temp=%.1f°C",
                self.node_id, reading.machine_id,
                decision.risk_score, reading.temperature,
            )
            self._alerts_sent += 1

        elif decision.action == ACTION_THROTTLE:
            logger.warning(
                "[%s] THROTTLE — CPU load=%.1f%% | %s",
                self.node_id, reading.cpu_load, reading.machine_id,
            )

    def _write_local_log(self, reading: SensorReading, decision: DecisionResult):
        record = {
            "node_id": self.node_id,
            **reading.to_dict(),
            **decision.to_dict(),
        }
        with open(self._local_log_path, "a") as f:
            f.write(json.dumps(record) + "\n")

    # ------------------------------------------------------------------

    def summary(self) -> dict:
        ai_stats = self.ai_engine.stats()
        elapsed  = round(time.time() - self._start_time, 1)
        return {
            "node_id":           self.node_id,
            "uptime_sec":        elapsed,
            "cloud_service":     self.cloud.stats(),
            "ai_engine":         ai_stats,
            "local_log":         self._local_log_path,
        }
