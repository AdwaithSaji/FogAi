#!/usr/bin/env python3
# ============================================================
#  FogAI — Web Dashboard Server
#  Run:  python web_app.py
#  Opens: http://localhost:5000
# ============================================================

import json
import os
import sys
import time
import threading
import webbrowser

from flask import Flask, render_template, Response, stream_with_context

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sensor import SensorSimulator
from fog_node import FogNode
from cloud_stub import CloudService
import config

app = Flask(__name__, template_folder="templates")


# ── SSE simulation stream ────────────────────────────────────
@app.route("/stream")
def stream():
    def generate():
        simulator = SensorSimulator()
        cloud     = CloudService(data_dir="data")
        fog       = FogNode(cloud=cloud, log_dir="logs")

        # Initial handshake
        init = {
            "type": "init",
            "node_id":       config.FOG_NODE_ID,
            "machine_id":    config.MACHINE_ID,
            "total_cycles":  config.TOTAL_CYCLES,
            "temp_warning":  config.TEMP_WARNING,
            "temp_critical": config.TEMP_CRITICAL,
        }
        yield f"data: {json.dumps(init)}\n\n"

        try:
            for _ in range(config.TOTAL_CYCLES):
                reading  = simulator.read()
                decision = fog.process(reading)

                payload = {
                    "type":     "update",
                    "reading":  reading.to_dict(),
                    "decision": decision.to_dict(),
                    "stats":    fog.ai_engine.stats(),
                }
                yield f"data: {json.dumps(payload)}\n\n"
                time.sleep(0.75)

        except GeneratorExit:
            return  # browser disconnected — restart on next connect

        # Completion event
        summary = fog.summary()
        yield f"data: {json.dumps({'type': 'complete', 'summary': summary})}\n\n"

    resp = Response(stream_with_context(generate()), mimetype="text/event-stream")
    resp.headers["Cache-Control"]    = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Connection"]        = "keep-alive"
    return resp


@app.route("/")
def index():
    return render_template("index.html")


# ── entry point ──────────────────────────────────────────────
if __name__ == "__main__":
    url = "http://localhost:5000"
    print(f"\n  ╔══════════════════════════════════════════════════╗")
    print(f"  ║   FogAI Web Dashboard                           ║")
    print(f"  ║   Open: {url:<40} ║")
    print(f"  ╚══════════════════════════════════════════════════╝\n")
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(debug=False, threaded=True, host="127.0.0.1", port=5000)
