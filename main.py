#!/usr/bin/env python3
# ============================================================
#  FogAI — Main Simulation Runner
#  Project: Low-Latency Intelligent IoT Architecture
#
#  Run:  python main.py
#        python main.py --cycles 80 --fast
# ============================================================

import argparse
import logging
import os
import sys
import time
import json

# ── configure logging before any other import ───────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/fogai_system.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("Main")

# ── project imports ─────────────────────────────────────────
import config
from sensor import SensorSimulator
from fog_node import FogNode
from cloud_stub import CloudService
from report_generator import generate_report, print_final_summary

try:
    from rich.live import Live
    from rich.layout import Layout
    from rich.console import Console
    import dashboard as db
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


# ── CLI args ─────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(
        description="FogAI — Low-Latency Intelligent IoT Architecture Simulation"
    )
    p.add_argument("--cycles",  type=int, default=config.TOTAL_CYCLES,
                   help="Number of sensor cycles to simulate (default: %(default)s)")
    p.add_argument("--fast",    action="store_true",
                   help="Run at full speed (no display delay)")
    p.add_argument("--no-dash", action="store_true",
                   help="Disable live dashboard (plain log output only)")
    return p.parse_args()


# ── build rich layout ────────────────────────────────────────
def build_layout(
    cycle: int, total: int,
    reading, decision,
    event_log, summary: dict,
) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header",   size=3),
        Layout(name="sensors",  size=9),
        Layout(name="decision", size=9),
        Layout(name="latency",  size=5),
        Layout(name="bottom",   size=9),
    )
    layout["header"].update(db.build_header(cycle, total))
    layout["sensors"].update(db.build_sensor_panel(reading))
    layout["decision"].update(db.build_decision_panel(decision))
    layout["latency"].update(
        db.build_latency_bar(decision.fog_latency_ms, decision.cloud_latency_ms)
    )

    layout["bottom"].split_row(
        Layout(name="events", ratio=3),
        Layout(name="stats",  ratio=2),
    )
    layout["bottom"]["events"].update(event_log.build_panel())
    layout["bottom"]["stats"].update(db.build_stats_panel(summary))
    return layout


# ── event log message builder ────────────────────────────────
ACTION_MSG = {
    "EMERGENCY_SHUTDOWN": ("!! EMERGENCY SHUTDOWN triggered", "bold red"),
    "ALERT":              ("!! ALERT — Fog acted immediately", "yellow"),
    "THROTTLE_MACHINE":   ("-- Machine throttled (CPU overload)", "yellow"),
    "LOG_ONLY":           ("   Fog processed locally",          "dim"),
    "CLOUD_SYNC":         (">> Forwarded to cloud for storage", "blue"),
    "NONE":               ("   Monitoring — no action needed",  "dim"),
}


# ── main ─────────────────────────────────────────────────────
def main():
    args = parse_args()
    total_cycles = args.cycles
    use_dash     = RICH_AVAILABLE and not args.no_dash
    interval     = 0.05 if args.fast else config.CYCLE_INTERVAL_SEC

    log.info("=" * 60)
    log.info("FogAI Simulation Starting")
    log.info("Cycles=%d  Fast=%s  Dashboard=%s", total_cycles, args.fast, use_dash)
    log.info("=" * 60)

    sensor   = SensorSimulator()
    cloud    = CloudService(data_dir="data")
    fog_node = FogNode(cloud=cloud, log_dir="logs")

    all_readings  = []
    all_decisions = []

    if use_dash:
        event_log = db.EventLog()
        console.print()
        console.rule("[bold cyan]  FogAI System Initialising  ")
        console.print(f"  [dim]Node    :[/dim] [bold]{config.FOG_NODE_ID}[/bold]")
        console.print(f"  [dim]Machine :[/dim] [bold]{config.MACHINE_ID}[/bold]")
        console.print(f"  [dim]Cloud   :[/dim] [bold]{config.CLOUD_ENDPOINT}[/bold]")
        console.print(f"  [dim]Cycles  :[/dim] [bold]{total_cycles}[/bold]")
        console.print()
        time.sleep(0.8)

        # Initial dummy reading for layout bootstrap
        r0 = sensor.read()
        d0 = fog_node.process(r0)
        all_readings.append(r0.to_dict())
        all_decisions.append(d0.to_dict())

        with Live(
            build_layout(1, total_cycles, r0, d0, event_log, fog_node.summary()),
            console=console,
            refresh_per_second=10,
            screen=True,
        ) as live:
            for cycle in range(2, total_cycles + 1):
                time.sleep(interval)

                reading  = sensor.read()
                decision = fog_node.process(reading)

                all_readings.append(reading.to_dict())
                all_decisions.append(decision.to_dict())

                msg, style = ACTION_MSG.get(decision.action, ("   Processing...", "dim"))
                event_log.add(cycle, msg, style)

                # Extra event for anomaly labels
                if reading.anomaly_type:
                    event_log.add(cycle,
                        f"   Sensor anomaly detected: {reading.anomaly_type}",
                        "bold red" if "CRITICAL" in (reading.anomaly_type or "") else "yellow")

                live.update(
                    build_layout(cycle, total_cycles, reading, decision,
                                 event_log, fog_node.summary())
                )

    else:
        # Plain output mode
        for cycle in range(1, total_cycles + 1):
            time.sleep(interval)
            reading  = sensor.read()
            decision = fog_node.process(reading)
            all_readings.append(reading.to_dict())
            all_decisions.append(decision.to_dict())
            log.info(
                "Cycle %02d | Temp=%.1f°C CPU=%.0f%% Vibr=%.2fg | "
                "%s | Risk=%.2f | Action=%s | Latency=%.1fms",
                cycle, reading.temperature, reading.cpu_load, reading.vibration,
                decision.destination, decision.risk_score, decision.action,
                decision.effective_latency_ms,
            )

    # ── final report ────────────────────────────────────────
    summary = fog_node.summary()
    report_path = generate_report(summary, all_readings, all_decisions)

    if use_dash:
        print_final_summary(summary)
        console.print(f"[bold green]Report saved:[/bold green] {report_path}\n")
    else:
        log.info("Report saved: %s", report_path)

    log.info("Simulation complete.")


if __name__ == "__main__":
    main()
