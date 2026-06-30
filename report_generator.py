# ============================================================
#  Report Generator
#  Produces a structured text report summarising the
#  simulation run for submission / presentation purposes.
# ============================================================

import os
import json
from datetime import datetime
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich import box

import config


def generate_report(fog_summary: dict, all_readings: list, all_decisions: list,
                    report_dir: str = "reports") -> str:
    os.makedirs(report_dir, exist_ok=True)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(report_dir, f"FogAI_Report_{ts}.txt")

    ai  = fog_summary.get("ai_engine", {})
    cld = fog_summary.get("cloud_service", {})

    lines = []
    div   = "=" * 70

    lines += [
        div,
        "  FogAI: Low-Latency Intelligent IoT Architecture",
        "  Simulation Run Report",
        f"  Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"  Node      : {fog_summary.get('node_id', 'N/A')}",
        f"  Machine   : {config.MACHINE_ID}",
        f"  Uptime    : {fog_summary.get('uptime_sec', 0):.1f} s",
        div,
        "",
        "1. EXECUTIVE SUMMARY",
        "-" * 40,
        f"  Total sensor readings processed : {ai.get('total_decisions', 0)}",
        f"  Fog-only decisions              : {ai.get('fog_decisions', 0)}  ({ai.get('fog_pct', 0):.1f}%)",
        f"  Cloud-forwarded decisions       : {ai.get('cloud_decisions', 0)}",
        f"  Alerts fired                    : {ai.get('alerts_fired', 0)}",
        f"  Emergency shutdowns triggered   : {ai.get('emergency_shutdowns', 0)}",
        "",
        "2. LATENCY ANALYSIS",
        "-" * 40,
        f"  Avg fog processing latency      : {ai.get('avg_fog_latency_ms', 0):.2f} ms",
        f"  Avg effective system latency    : {ai.get('avg_effective_lat_ms', 0):.2f} ms",
        f"  Avg latency saved vs cloud-only : {ai.get('avg_latency_saved_ms', 0):.1f} ms",
        f"  Cloud records stored            : {cld.get('records_stored', 0)}",
        f"  Local log                       : {fog_summary.get('local_log', 'N/A')}",
        f"  Cloud telemetry file            : {cld.get('log_file', 'N/A')}",
        "",
        "3. ANOMALY EVENT TIMELINE",
        "-" * 40,
    ]

    # Anomaly events
    seen = set()
    for d in all_decisions:
        rules = d.get("triggered_rules", [])
        sev   = d.get("severity", "NORMAL")
        act   = d.get("action", "")
        cyc   = d.get("cycle", 0)
        if sev != "NORMAL" or act not in ("NONE", "LOG_ONLY", "CLOUD_SYNC"):
            key = (cyc, act)
            if key not in seen:
                seen.add(key)
                lines.append(
                    f"  Cycle {cyc:03d}  [{sev:<8}]  Action={act:<22}  Rules={','.join(rules)}"
                )

    if not seen:
        lines.append("  No anomalies detected during this run.")

    lines += [
        "",
        "4. SENSOR STATISTICS",
        "-" * 40,
    ]

    if all_readings:
        temps = [r.get("temperature_C", 0) for r in all_readings]
        cpus  = [r.get("cpu_load_pct", 0) for r in all_readings]
        vibs  = [r.get("vibration_g", 0) for r in all_readings]
        nets  = [r.get("network_latency_ms", 0) for r in all_readings if r.get("network_latency_ms", 0) < 9999]

        lines += [
            f"  Temperature  — min={min(temps):.1f}°C  max={max(temps):.1f}°C  avg={sum(temps)/len(temps):.1f}°C",
            f"  CPU Load     — min={min(cpus):.1f}%   max={max(cpus):.1f}%   avg={sum(cpus)/len(cpus):.1f}%",
            f"  Vibration    — min={min(vibs):.3f}g   max={max(vibs):.3f}g",
            f"  Net Latency  — min={min(nets) if nets else 0:.1f}ms  max={max(nets) if nets else 0:.1f}ms  avg={sum(nets)/len(nets) if nets else 0:.1f}ms",
        ]

    lines += [
        "",
        "5. SYSTEM CONFIGURATION",
        "-" * 40,
        f"  Fog Node ID          : {config.FOG_NODE_ID}",
        f"  Cloud Endpoint       : {config.CLOUD_ENDPOINT}",
        f"  Temp Warning Thresh  : {config.TEMP_WARNING} °C",
        f"  Temp Critical Thresh : {config.TEMP_CRITICAL} °C",
        f"  Vibration Warning    : {config.VIBRATION_WARNING} g",
        f"  Net Poor Latency     : {config.NETWORK_POOR_LATENCY} ms",
        f"  AI Weight — Temp     : {config.WEIGHT_TEMP}",
        f"  AI Weight — CPU      : {config.WEIGHT_CPU}",
        f"  AI Weight — Vibr     : {config.WEIGHT_VIBRATION}",
        f"  AI Weight — Network  : {config.WEIGHT_NETWORK}",
        "",
        div,
        "  END OF REPORT",
        div,
    ]

    with open(path, "w") as f:
        f.write("\n".join(lines))

    return path


def print_final_summary(fog_summary: dict):
    """Render a rich final summary to the terminal after the simulation ends."""
    console = Console()
    ai  = fog_summary.get("ai_engine", {})
    cld = fog_summary.get("cloud_service", {})

    console.print()
    console.rule("[bold cyan]FogAI Simulation Complete")
    console.print()

    # Key metrics table
    t = Table(title="Final Metrics", box=box.ROUNDED, border_style="cyan",
              show_header=True, header_style="bold magenta")
    t.add_column("Metric", style="dim", width=32)
    t.add_column("Value", justify="right")

    t.add_row("Total Cycles Processed",     str(ai.get("total_decisions", 0)))
    t.add_row("Fog-Layer Decisions",
              f"[cyan]{ai.get('fog_decisions', 0)}  ({ai.get('fog_pct', 0):.0f}%)[/cyan]")
    t.add_row("Cloud-Forwarded Decisions",  f"[blue]{ai.get('cloud_decisions', 0)}[/blue]")
    t.add_row("Alerts Fired",               f"[yellow]{ai.get('alerts_fired', 0)}[/yellow]")
    t.add_row("Emergency Shutdowns",        f"[bold red]{ai.get('emergency_shutdowns', 0)}[/bold red]")
    t.add_row("Avg Fog Latency",            f"[green]{ai.get('avg_fog_latency_ms', 0):.2f} ms[/green]")
    t.add_row("Avg Effective Latency",      f"[green bold]{ai.get('avg_effective_lat_ms', 0):.2f} ms[/green bold]")
    t.add_row("Avg Latency Saved vs Cloud", f"[green]{ai.get('avg_latency_saved_ms', 0):.1f} ms[/green]")
    t.add_row("Cloud Records Stored",       str(cld.get("records_stored", 0)))

    console.print(t)
    console.print()
    console.print(Panel(
        f"[bold green]Local decision log  :[/bold green] {fog_summary.get('local_log', 'N/A')}\n"
        f"[bold blue]Cloud telemetry log :[/bold blue] {cld.get('log_file', 'N/A')}",
        title="Output Files", border_style="dim"
    ))
    console.print()
