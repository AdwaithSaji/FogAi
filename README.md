# FogAI: Low-Latency Intelligent IoT Architecture

> Final Year Project — Industry 5.0 / Smart Manufacturing  
> Demonstrates fog-layer AI decision-making for real-time IoT control.

---

## How to Run

### Option A — Double-click (Windows)
```
run.bat
```

### Option B — Terminal
```bash
pip install rich numpy colorama
python main.py
```

### Options
| Flag | Description |
|------|-------------|
| `--cycles N` | Number of sensor cycles (default: 60) |
| `--fast` | Run at full speed (no pacing delay) |
| `--no-dash` | Plain log output only |

---

## What the Simulation Does

The system simulates **60 sensor reading cycles** from an industrial CNC machine:

| Phase | Cycles | Event |
|-------|--------|-------|
| Normal operation | 1–11 | Cloud sync for low-risk data |
| Temperature spike | 12 | Fog detects +8°C drift |
| Network degradation | 22–26 | Fog routes locally (slow cloud) |
| Network outage | 27–32 | Fog operates fully offline |
| Overheating begins | 33 | Fog triggers EMERGENCY_SHUTDOWN in < 4 ms |
| Vibration shock | 38 | R4:VIBRATION_CRITICAL fires |
| Peak crisis | 45 | Temp exceeds 117°C |
| Recovery | 58 | System normalises |

---

## Architecture

```
IoT Sensors (sensor.py)
       │ raw readings
       ▼
┌──────────────────────────────────┐
│         FOG NODE (fog_node.py)   │
│  ┌───────────────────────────┐   │
│  │   FogAI Decision Engine   │   │
│  │   (ai_engine.py)          │   │
│  │                           │   │
│  │  Feature Extraction       │   │
│  │  Safety Rules (R1–R5)     │   │
│  │  Weighted Risk Score      │   │
│  │  Score-Based Routing      │   │
│  └───────────────────────────┘   │
│    │               │             │
│  Local             │             │
│  Action        Forward?          │
│  (< 5 ms)          │             │
└────────────────────┼─────────────┘
                     ▼
              Cloud Service
              (cloud_stub.py)
              Long-term storage
```

### AI Decision Rules

| Rule | Condition | Action |
|------|-----------|--------|
| R1 | Temperature ≥ 90°C | EMERGENCY_SHUTDOWN (fog, instant) |
| R2 | Temperature ≥ 75°C | ALERT (fog + cloud) |
| R3 | Network offline | FOG only (autonomous) |
| R4 | Vibration ≥ 4.0 g | EMERGENCY_SHUTDOWN |
| R5 | CPU ≥ 95% | THROTTLE_MACHINE |
| SR1 | Network slow (>150ms) | Route to FOG |
| SR2 | Risk score < 0.35 | CLOUD_SYNC (low priority) |
| SR3 | Risk 0.35–0.65 | FOG (medium risk) |
| SR4 | Risk > 0.65 | ALERT (both) |

---

## Output Files

After a run, three output directories are populated:

```
logs/
  fogai_system.log           ← full system log
  fog_decisions_*.jsonl      ← per-cycle decision records

data/
  cloud_telemetry_*.jsonl    ← cloud-bound telemetry packets

reports/
  FogAI_Report_*.txt         ← structured analysis report
```

---

## Key Results (Typical Run)

| Metric | Value |
|--------|-------|
| Fog-layer decisions | ~75% |
| Avg fog latency | ~3 ms |
| Avg cloud latency | ~120 ms |
| Latency saved | ~66 ms per cycle |
| Emergency shutdowns | 25 (all < 5 ms response) |
| Network-down resilience | Fully autonomous operation |

---

## Project Info

- **Platform**: Python 3.8+ (no hardware required)
- **Dependencies**: `rich`, `numpy`, `colorama`
- **Architecture pattern**: Fog Computing + Edge AI
- **Use case**: Industry 5.0 smart manufacturing
