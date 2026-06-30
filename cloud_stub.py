# ============================================================
#  Cloud Service Stub
#  Simulates a remote cloud endpoint for data storage and
#  long-term analytics. Introduces realistic network delay.
# ============================================================

import time
import json
import os
import random
from datetime import datetime
from typing import List
import config


class CloudService:
    """
    Simulates a cloud backend that:
      - Accepts telemetry packets from fog nodes
      - Persists data to a local JSONL file (demo substitute for real DB)
      - Simulates round-trip network delay
      - Tracks received record count and total bytes
    """

    def __init__(self, data_dir: str = "data"):
        os.makedirs(data_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_path = os.path.join(data_dir, f"cloud_telemetry_{timestamp_str}.jsonl")
        self._received = 0
        self._bytes_stored = 0
        self._endpoint = config.CLOUD_ENDPOINT
        self._online = True

    # ------------------------------------------------------------------

    def ingest(self, payload: dict, simulate_latency: bool = True) -> dict:
        """
        Push a payload to the cloud.
        Returns a receipt with status, latency, and record ID.
        """
        if simulate_latency:
            delay = max(0.001, (config.CLOUD_LATENCY_BASE + random.gauss(0, 30)) / 1000)
            time.sleep(delay)

        if not self._online:
            return {"status": "ERROR", "reason": "Cloud unreachable", "record_id": None}

        record_id = f"REC-{self._received + 1:06d}"
        payload["_cloud_record_id"] = record_id
        payload["_ingested_at"] = datetime.utcnow().isoformat() + "Z"

        line = json.dumps(payload) + "\n"
        with open(self._log_path, "a") as f:
            f.write(line)

        self._received    += 1
        self._bytes_stored += len(line)

        return {
            "status": "OK",
            "record_id": record_id,
            "endpoint": self._endpoint,
            "records_stored": self._received,
        }

    def set_online(self, online: bool):
        self._online = online

    def stats(self) -> dict:
        return {
            "endpoint":       self._endpoint,
            "records_stored": self._received,
            "bytes_stored":   self._bytes_stored,
            "log_file":       self._log_path,
            "status":         "ONLINE" if self._online else "OFFLINE",
        }
