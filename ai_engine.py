# ============================================================
#  Fog-Layer AI Decision Engine
#
#  A lightweight, interpretable scoring model suitable for
#  deployment on resource-constrained edge/fog hardware.
#
#  Architecture:
#    1. Feature extraction  — normalise sensor values [0..1]
#    2. Rule-based triggers — hard safety rules (highest priority)
#    3. Weighted scoring    — continuous risk score [0..1]
#    4. Decision output     — action + destination + confidence
# ============================================================

from __future__ import annotations
import time
import random
from dataclasses import dataclass, field
from typing import List, Tuple
import config
from sensor import SensorReading


# ---- Decision constants ------------------------------------------------
DECISION_FOG   = "FOG"    # process entirely at fog node
DECISION_CLOUD = "CLOUD"  # forward to cloud for analysis
DECISION_BOTH  = "BOTH"   # critical: act at fog AND log to cloud

ACTION_NONE         = "NONE"
ACTION_ALERT        = "ALERT"
ACTION_SHUTDOWN     = "EMERGENCY_SHUTDOWN"
ACTION_THROTTLE     = "THROTTLE_MACHINE"
ACTION_LOG_ONLY     = "LOG_ONLY"
ACTION_CLOUD_SYNC   = "CLOUD_SYNC"


@dataclass
class DecisionResult:
    cycle: int
    timestamp: float

    # Core decision
    destination: str        # FOG / CLOUD / BOTH
    action: str             # what to do
    risk_score: float       # 0.0 – 1.0
    confidence: float       # 0.0 – 1.0

    # Latency breakdown
    fog_latency_ms: float
    cloud_latency_ms: float
    effective_latency_ms: float  # actual latency of the chosen path

    # Explanation
    triggered_rules: List[str] = field(default_factory=list)
    reason: str = ""
    severity: str = "NORMAL"    # NORMAL / WARNING / CRITICAL

    def to_dict(self) -> dict:
        return {
            "cycle": self.cycle,
            "timestamp": round(self.timestamp, 3),
            "destination": self.destination,
            "action": self.action,
            "risk_score": round(self.risk_score, 3),
            "confidence": round(self.confidence, 3),
            "fog_latency_ms": round(self.fog_latency_ms, 2),
            "cloud_latency_ms": round(self.cloud_latency_ms, 2),
            "effective_latency_ms": round(self.effective_latency_ms, 2),
            "triggered_rules": self.triggered_rules,
            "reason": self.reason,
            "severity": self.severity,
        }


class FogAIEngine:
    """
    Lightweight AI decision engine running on the fog node.

    Designed to operate with <5 ms inference time and
    <1 MB memory footprint — suitable for Raspberry Pi 4 class hardware.
    """

    def __init__(self):
        self._decision_history: List[DecisionResult] = []
        self._fog_decisions   = 0
        self._cloud_decisions = 0
        self._alerts_fired    = 0
        self._shutdowns       = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def decide(self, reading: SensorReading) -> DecisionResult:
        t_start = time.perf_counter()

        # Step 1 — simulate fog & cloud latencies independently
        fog_lat   = self._sample_fog_latency()
        cloud_lat = reading.network_latency  # actual measured round-trip

        # Step 2 — extract normalised features
        features = self._extract_features(reading)

        # Step 3 — hard safety rules (override everything)
        rules, action, destination, severity = self._apply_safety_rules(reading, cloud_lat)

        # Step 4 — weighted risk score
        risk = self._compute_risk_score(features)

        # Step 5 — if no hard rule fired, use score-based routing
        if not rules:
            destination, action, rules = self._score_based_routing(
                risk, cloud_lat, features
            )
            severity = self._score_to_severity(risk)

        # Step 6 — confidence from score sharpness + rule clarity
        confidence = self._compute_confidence(risk, bool(rules))

        effective_lat = fog_lat if destination in (DECISION_FOG, DECISION_BOTH) else cloud_lat

        t_end = time.perf_counter()
        engine_overhead = (t_end - t_start) * 1000  # ms — always <1 ms in Python

        result = DecisionResult(
            cycle=reading.cycle,
            timestamp=reading.timestamp,
            destination=destination,
            action=action,
            risk_score=risk,
            confidence=confidence,
            fog_latency_ms=fog_lat,
            cloud_latency_ms=cloud_lat,
            effective_latency_ms=effective_lat,
            triggered_rules=rules,
            reason=self._build_reason(reading, rules, destination, risk),
            severity=severity,
        )

        # Track stats
        self._decision_history.append(result)
        if destination == DECISION_CLOUD:
            self._cloud_decisions += 1
        else:
            self._fog_decisions += 1
        if action == ACTION_ALERT:
            self._alerts_fired += 1
        if action == ACTION_SHUTDOWN:
            self._shutdowns += 1

        return result

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    def _extract_features(self, r: SensorReading) -> dict:
        """Normalise raw sensor values to [0, 1] range."""
        def norm(val, lo, hi):
            return max(0.0, min(1.0, (val - lo) / (hi - lo)))

        return {
            "temp":    norm(r.temperature, config.TEMP_NORMAL_MIN, config.TEMP_CRITICAL),
            "cpu":     norm(r.cpu_load, 0, 100),
            "vibr":    norm(r.vibration, 0, config.VIBRATION_CRITICAL),
            "net":     norm(min(r.network_latency, 500), 0, 500),
        }

    # ------------------------------------------------------------------
    # Safety rules  (hard constraints — highest priority)
    # ------------------------------------------------------------------

    def _apply_safety_rules(
        self, r: SensorReading, cloud_lat: float
    ) -> Tuple[List[str], str, str, str]:
        rules   = []
        action  = ACTION_NONE
        dest    = DECISION_CLOUD
        severity = "NORMAL"

        # Rule R1 — Critical temperature → emergency shutdown
        if r.temperature >= config.TEMP_CRITICAL:
            rules.append("R1:TEMP_CRITICAL")
            action   = ACTION_SHUTDOWN
            dest     = DECISION_BOTH
            severity = "CRITICAL"

        # Rule R2 — Warning temperature → throttle + alert
        elif r.temperature >= config.TEMP_WARNING:
            rules.append("R2:TEMP_WARNING")
            action   = ACTION_ALERT
            dest     = DECISION_BOTH
            severity = "WARNING"

        # Rule R3 — Network down → fog must act alone
        if cloud_lat >= config.NETWORK_DOWN_LATENCY:
            rules.append("R3:NETWORK_DOWN")
            dest   = DECISION_FOG
            if action == ACTION_NONE:
                action = ACTION_LOG_ONLY
            severity = max(severity, "WARNING", key=["NORMAL","WARNING","CRITICAL"].index)

        # Rule R4 — Critical vibration
        if r.vibration >= config.VIBRATION_CRITICAL:
            rules.append("R4:VIBRATION_CRITICAL")
            action   = ACTION_SHUTDOWN
            dest     = DECISION_BOTH
            severity = "CRITICAL"

        # Rule R5 — CPU near max
        if r.cpu_load >= config.CPU_LOAD_CRITICAL:
            rules.append("R5:CPU_CRITICAL")
            if action == ACTION_NONE:
                action = ACTION_THROTTLE
            dest = DECISION_BOTH
            severity = max(severity, "WARNING", key=["NORMAL","WARNING","CRITICAL"].index)

        return rules, action, dest, severity

    # ------------------------------------------------------------------
    # Weighted risk score
    # ------------------------------------------------------------------

    def _compute_risk_score(self, features: dict) -> float:
        score = (
            features["temp"]  * config.WEIGHT_TEMP +
            features["cpu"]   * config.WEIGHT_CPU  +
            features["vibr"]  * config.WEIGHT_VIBRATION +
            features["net"]   * config.WEIGHT_NETWORK
        )
        return round(min(1.0, score), 4)

    # ------------------------------------------------------------------
    # Score-based routing (when no hard rule fires)
    # ------------------------------------------------------------------

    def _score_based_routing(
        self, risk: float, cloud_lat: float, features: dict
    ) -> Tuple[str, str, List[str]]:
        rules = []

        # Poor network → prefer fog
        if cloud_lat >= config.NETWORK_POOR_LATENCY:
            rules.append("SR1:POOR_NETWORK")
            return DECISION_FOG, ACTION_LOG_ONLY, rules

        # Low risk — just sync to cloud for storage
        if risk < 0.35:
            rules.append("SR2:LOW_RISK")
            return DECISION_CLOUD, ACTION_CLOUD_SYNC, rules

        # Medium risk — process at fog, also cloud
        if risk < 0.65:
            rules.append("SR3:MEDIUM_RISK")
            return DECISION_FOG, ACTION_LOG_ONLY, rules

        # High risk but no hard rule — alert at fog
        rules.append("SR4:HIGH_RISK_SCORE")
        return DECISION_BOTH, ACTION_ALERT, rules

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _sample_fog_latency(self) -> float:
        return round(
            max(1.0, config.FOG_LATENCY_BASE + random.gauss(0, config.FOG_LATENCY_JITTER)),
            2,
        )

    def _compute_confidence(self, risk: float, hard_rule: bool) -> float:
        if hard_rule:
            return round(0.92 + random.uniform(0, 0.07), 3)
        # Confidence is highest near extremes (0 or 1), lowest near 0.5
        base = 1.0 - 2 * abs(risk - 0.5)
        return round(max(0.55, base + random.uniform(-0.05, 0.05)), 3)

    def _score_to_severity(self, risk: float) -> str:
        if risk >= 0.9:
            return "CRITICAL"
        if risk >= 0.7:
            return "WARNING"
        return "NORMAL"

    def _build_reason(
        self, r: SensorReading, rules: list, dest: str, risk: float
    ) -> str:
        parts = []
        if r.temperature >= config.TEMP_CRITICAL:
            parts.append(f"temp={r.temperature:.1f}°C (CRITICAL)")
        elif r.temperature >= config.TEMP_WARNING:
            parts.append(f"temp={r.temperature:.1f}°C (WARNING)")
        else:
            parts.append(f"temp={r.temperature:.1f}°C")
        if r.vibration >= config.VIBRATION_WARNING:
            parts.append(f"vibr={r.vibration:.2f}g")
        if r.network_latency >= config.NETWORK_DOWN_LATENCY:
            parts.append("network=OFFLINE")
        elif r.network_latency >= config.NETWORK_POOR_LATENCY:
            parts.append(f"net={r.network_latency:.0f}ms (slow)")
        parts.append(f"risk={risk:.2f}")
        return " | ".join(parts)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        total = len(self._decision_history)
        if not total:
            return {}
        fog_lats   = [d.fog_latency_ms for d in self._decision_history]
        eff_lats   = [d.effective_latency_ms for d in self._decision_history]
        cloud_only = [d for d in self._decision_history if d.destination == DECISION_CLOUD]
        cloud_lats = [d.cloud_latency_ms for d in cloud_only]

        latency_saved = (
            sum(cloud_lats) / len(cloud_lats) - sum(fog_lats) / len(fog_lats)
            if cloud_lats else 0
        )

        return {
            "total_decisions":      total,
            "fog_decisions":        self._fog_decisions,
            "cloud_decisions":      self._cloud_decisions,
            "fog_pct":              round(100 * self._fog_decisions / total, 1),
            "alerts_fired":         self._alerts_fired,
            "emergency_shutdowns":  self._shutdowns,
            "avg_fog_latency_ms":   round(sum(fog_lats) / len(fog_lats), 2),
            "avg_effective_lat_ms": round(sum(eff_lats) / len(eff_lats), 2),
            "avg_latency_saved_ms": round(latency_saved, 1),
        }
