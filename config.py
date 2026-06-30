# ============================================================
#  FogAI Configuration
#  Project: Low-Latency Intelligent IoT Architecture
# ============================================================

# --- Sensor thresholds ---
TEMP_NORMAL_MIN    = 20.0   # °C
TEMP_NORMAL_MAX    = 75.0   # °C
TEMP_WARNING       = 75.0   # °C  — fog triggers WARNING
TEMP_CRITICAL      = 90.0   # °C  — fog triggers SHUTDOWN

HUMIDITY_MIN       = 30.0   # %
HUMIDITY_MAX       = 80.0   # %

CPU_LOAD_WARNING   = 80.0   # %
CPU_LOAD_CRITICAL  = 95.0   # %

VIBRATION_WARNING  = 2.5    # g
VIBRATION_CRITICAL = 4.0    # g

# --- Network thresholds ---
NETWORK_GOOD_LATENCY   = 50   # ms  — send to cloud freely
NETWORK_POOR_LATENCY   = 150  # ms  — prefer fog processing
NETWORK_DOWN_LATENCY   = 9999 # ms  — offline; fog must handle alone

# --- Latency model (simulated, ms) ---
FOG_LATENCY_BASE   = 3      # ms
FOG_LATENCY_JITTER = 2      # ms
CLOUD_LATENCY_BASE = 120    # ms
CLOUD_LATENCY_JITTER = 60   # ms

# --- AI Decision Engine weights ---
WEIGHT_TEMP       = 0.35
WEIGHT_CPU        = 0.20
WEIGHT_VIBRATION  = 0.25
WEIGHT_NETWORK    = 0.20

# --- Simulation ---
TOTAL_CYCLES       = 60     # number of sensor readings to simulate
CYCLE_INTERVAL_SEC = 0.4    # pause between cycles (for demo pacing)

# --- Fog node identity ---
FOG_NODE_ID   = "FOG-NODE-001"
CLOUD_ENDPOINT = "cloud.fogai.internal:443"
MACHINE_ID     = "CNC-MACHINE-07"
