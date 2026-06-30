# ============================================================
#  Real-Time Terminal Dashboard
#  Uses the 'rich' library to render a live updating panel
#  that shows sensor values, AI decisions, and system stats.
# ============================================================

from __future__ import annotations
import time
from typing import List, Optional
from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box
from rich.rule import Rule
from rich.align import Align

import config
from sensor import SensorReading
from ai_engine import DecisionResult

console = Console()


# ── colour helpers ──────────────────────────────────────────
def _temp_style(t: float) -> str:
    if t >= config.TEMP_CRITICAL:  return "bold red"
    if t >= config.TEMP_WARNING:   return "bold yellow"
    return "green"

def _risk_style(r: float) -> str:
    if r >= 0.7: return "bold red"
    if r >= 0.4: return "bold yellow"
    return "green"

def _dest_style(d: str) -> str:
    return {"FOG": "cyan", "CLOUD": "blue", "BOTH": "magenta"}.get(d, "white")

def _sev_style(s: str) -> str:
    return {"CRITICAL": "bold red", "WARNING": "bold yellow", "NORMAL": "green"}.get(s, "white")

def _action_style(a: str) -> str:
    return {
        "EMERGENCY_SHUTDOWN": "bold red on dark_red",
        "ALERT":              "bold yellow",
        "THROTTLE_MACHINE":   "yellow",
        "LOG_ONLY":           "dim white",
        "CLOUD_SYNC":         "blue",
        "NONE":               "dim white",
    }.get(a, "white")


# ── header ───────────────────────────────────────────────────
def build_header(cycle: int, total: int) -> Panel:
    now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    pct = int(100 * cycle / total)
    bar = ("█" * (pct // 5)).ljust(20)
    title_text = Text()
    title_text.append("  FogAI", style="bold white")
    title_text.append("  ·  ", style="dim")
    title_text.append("Low-Latency Intelligent IoT Architecture", style="italic cyan")
    title_text.append(f"  ·  Cycle {cycle}/{total}  [{bar}] {pct}%", style="dim white")
    title_text.append(f"  ·  {now}", style="dim")
    return Panel(Align.center(title_text), style="bold blue", height=3)


# ── sensor panel ─────────────────────────────────────────────
def build_sensor_panel(r: SensorReading) -> Panel:
    t = Table.grid(padding=(0, 2))
    t.add_column(style="dim", width=20)
    t.add_column(width=18)
    t.add_column(style="dim", width=20)
    t.add_column(width=18)

    net_str = (
        Text("OFFLINE", style="bold red")
        if r.network_latency >= 9999
        else Text(f"{r.network_latency:.1f} ms", style="yellow" if r.network_latency > 150 else "green")
    )

    t.add_row("Temperature",
              Text(f"{r.temperature:.2f} °C", style=_temp_style(r.temperature)),
              "Humidity",
              Text(f"{r.humidity:.1f} %", style="cyan"))
    t.add_row("CPU Load",
              Text(f"{r.cpu_load:.1f} %",
                   style="red" if r.cpu_load >= 95 else "yellow" if r.cpu_load >= 80 else "green"),
              "Vibration",
              Text(f"{r.vibration:.3f} g",
                   style="bold red" if r.vibration >= 4 else "yellow" if r.vibration >= 2.5 else "green"))
    t.add_row("Network Latency", net_str,
              "Power Draw",
              Text(f"{r.power_draw:.1f} W", style="cyan"))
    t.add_row("Machine ID",
              Text(r.machine_id, style="bold white"),
              "Anomaly",
              Text(r.anomaly_type or "—", style="bold red" if r.anomaly_type else "dim"))

    return Panel(t, title="[bold]IoT Sensor Readings", border_style="cyan", padding=(0, 1))


# ── decision panel ───────────────────────────────────────────
def build_decision_panel(d: DecisionResult) -> Panel:
    t = Table.grid(padding=(0, 2))
    t.add_column(style="dim", width=22)
    t.add_column(width=20)
    t.add_column(style="dim", width=22)
    t.add_column(width=20)

    t.add_row("Destination",
              Text(d.destination, style=_dest_style(d.destination) + " bold"),
              "Action",
              Text(d.action, style=_action_style(d.action)))
    t.add_row("Risk Score",
              Text(f"{d.risk_score:.3f}", style=_risk_style(d.risk_score)),
              "Confidence",
              Text(f"{d.confidence * 100:.1f}%", style="green"))
    t.add_row("Fog Latency",
              Text(f"{d.fog_latency_ms:.2f} ms", style="cyan"),
              "Cloud Latency",
              Text(f"{d.cloud_latency_ms:.1f} ms" if d.cloud_latency_ms < 9999 else "OFFLINE",
                   style="blue"))
    t.add_row("Effective Latency",
              Text(f"{d.effective_latency_ms:.2f} ms", style="bold green"),
              "Severity",
              Text(d.severity, style=_sev_style(d.severity)))
    t.add_row("Rules Fired",
              Text(", ".join(d.triggered_rules) or "—", style="dim"),
              "", "")

    return Panel(t, title="[bold]AI Decision Engine Output",
                 border_style="magenta", padding=(0, 1))


# ── event log ────────────────────────────────────────────────
class EventLog:
    MAX = 14

    def __init__(self):
        self._entries: List[tuple] = []   # (cycle, text, style)

    def add(self, cycle: int, msg: str, style: str = "white"):
        self._entries.append((cycle, msg, style))
        if len(self._entries) > self.MAX:
            self._entries.pop(0)

    def build_panel(self) -> Panel:
        t = Table(box=None, show_header=False, padding=(0, 1))
        t.add_column("cyc", style="dim", width=5)
        t.add_column("msg")
        for cyc, msg, style in reversed(self._entries):
            t.add_row(f"#{cyc:02d}", Text(msg, style=style))
        return Panel(t, title="[bold]Event Log", border_style="yellow", padding=(0, 1))


# ── stats panel ──────────────────────────────────────────────
def build_stats_panel(fog_node_summary: dict) -> Panel:
    ai  = fog_node_summary.get("ai_engine", {})
    cld = fog_node_summary.get("cloud_service", {})

    t = Table.grid(padding=(0, 3))
    t.add_column(style="dim", width=24)
    t.add_column()
    t.add_column(style="dim", width=24)
    t.add_column()

    t.add_row("Total Decisions",
              Text(str(ai.get("total_decisions", 0)), style="white bold"),
              "Fog Decisions",
              Text(f"{ai.get('fog_decisions', 0)}  ({ai.get('fog_pct', 0):.0f}%)",
                   style="cyan bold"))
    t.add_row("Cloud Decisions",
              Text(str(ai.get("cloud_decisions", 0)), style="blue"),
              "Alerts Fired",
              Text(str(ai.get("alerts_fired", 0)), style="yellow"))
    t.add_row("Emergency Shutdowns",
              Text(str(ai.get("emergency_shutdowns", 0)), style="bold red"),
              "Avg Fog Latency",
              Text(f"{ai.get('avg_fog_latency_ms', 0):.2f} ms", style="green"))
    t.add_row("Avg Effective Latency",
              Text(f"{ai.get('avg_effective_lat_ms', 0):.2f} ms", style="green bold"),
              "Cloud Records",
              Text(str(cld.get("records_stored", 0)), style="blue"))

    return Panel(t, title="[bold]System Statistics",
                 border_style="green", padding=(0, 1))


# ── latency comparison bar ───────────────────────────────────
def build_latency_bar(fog_ms: float, cloud_ms: float) -> Panel:
    MAX_W = 40
    fog_n   = min(1.0, fog_ms   / 350)
    cloud_n = min(1.0, cloud_ms / 350) if cloud_ms < 9999 else 1.0

    fog_bar   = "█" * max(1, int(fog_n   * MAX_W))
    cloud_bar = "█" * max(1, int(cloud_n * MAX_W))

    t = Table.grid(padding=(0, 1))
    t.add_column(style="dim", width=12)
    t.add_column()
    t.add_column(style="dim", width=10)

    cloud_disp = f"{cloud_ms:.1f} ms" if cloud_ms < 9999 else "OFFLINE"
    t.add_row("[cyan]Fog",
              Text(fog_bar,   style="cyan"),
              f"{fog_ms:.1f} ms")
    t.add_row("[blue]Cloud",
              Text(cloud_bar, style="blue"),
              cloud_disp)

    saving = cloud_ms - fog_ms if cloud_ms < 9999 else fog_ms
    saving_pct = (saving / cloud_ms * 100) if cloud_ms < 9999 and cloud_ms > 0 else 0

    footer = Text()
    footer.append(f"  Latency saving: ", style="dim")
    footer.append(f"{saving:.1f} ms  ({saving_pct:.0f}% faster)", style="bold green")

    return Panel(
        Columns([t, footer], equal=False),
        title="[bold]Latency Comparison  (Fog vs Cloud)",
        border_style="blue",
        padding=(0, 1),
    )
