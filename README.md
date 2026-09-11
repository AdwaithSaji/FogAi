# FogAI — Intelligent Fog Computing for Real-Time IoT

> A low-latency AI-driven fog computing architecture for real-time decision-making in smart manufacturing.

## Overview

FogAI demonstrates how intelligent decisions can be moved closer to IoT devices using a fog-computing layer.

Instead of sending every sensor reading to the cloud, the system analyzes data locally and takes immediate action when critical conditions are detected.

This approach helps reduce latency, improve resilience during network failures, and enable autonomous decision-making at the edge.

## Architecture

```text
IoT Sensors
     │
     │ Sensor Data
     ▼
┌─────────────────────────────┐
│         Fog Node            │
│                             │
│   Feature Extraction        │
│          ↓                  │
│   FogAI Decision Engine     │
│          ↓                  │
│   Risk Evaluation           │
│          ↓                  │
│   Local Decision / Routing  │
└──────────┬──────────────────┘
           │
     ┌─────┴─────┐
     │           │
 Local Action   Cloud
 (< 5 ms)       Service
```
## Key Features

- Real-time sensor data simulation
- AI-based decision-making at the fog layer
- Weighted risk scoring
- Rule-based safety detection
- Local emergency response
- Network degradation and outage simulation
- Autonomous operation during cloud disconnection
- Cloud routing for low-risk telemetry
- Structured logs and decision reports

## Decision Rules

| Rule | Condition | Action |
|---|---|---|
| R1 | Temperature ≥ 90°C | Emergency Shutdown |
| R2 | Temperature ≥ 75°C | Alert |
| R3 | Network Offline | Fog-only Operation |
| R4 | Vibration ≥ 4.0 g | Emergency Shutdown |
| R5 | CPU ≥ 95% | Throttle Machine |

## Simulation

The system simulates 60 sensor cycles representing different industrial conditions:

- Normal operation
- Temperature spike
- Network degradation
- Network outage
- Machine overheating
- Critical vibration event
- Peak-risk conditions
- System recovery
  
## Results

A typical simulation demonstrates:

| Metric | Result |
|---|---:|
| Fog-layer decisions | ~75% |
| Average fog latency | ~3 ms |
| Average cloud latency | ~120 ms |
| Latency saved | ~66 ms/cycle |
| Emergency shutdowns | 25 |
| Network-down operation | Autonomous |

## Project Structure

```text
FogAi/
├── ai_engine.py
├── cloud_stub.py
├── config.py
├── dashboard.py
├── fog_node.py
├── main.py
├── paper/
├── templates/
└── README.md
```


### 5. How to Run
Make this structure:


## How to Run

### Requirements

- Python 3.8+
- NumPy
- Rich
- Colorama

### Installation


pip install rich numpy colorama

python main.py

run.bat

Command Options
Option	Description
--cycles N	Number of sensor cycles
--fast	Run without pacing delay
--no-dash	Disable dashboard output

### 6. Technologies
Change to:


## Technologies

- Python
- Artificial Intelligence
- Fog Computing
- Edge AI
- IoT
- Smart Manufacturing
- Industry 5.0

## Project Goal

FogAI explores how AI-enabled fog computing can support faster and more resilient decision-making in industrial IoT environments, particularly when cloud connectivity is unreliable or unavailable.

**Project:** Final Year Project  
**Domain:** AI / IoT / Fog Computing / Smart Manufacturing
