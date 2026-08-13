"""Monitor de ruta continuo estilo PingPlotter para Visor.

Usa traceroute + muestras ICMP periódicas y guarda un estado draw.io vivo,
historial JSONL y CSV. Es observación de red: no cambia routers ni hosts.
"""

from __future__ import annotations

import csv
import json
import platform
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from core.telemetry import TelemetryClient
from core.topology import REPORTS_DIR, build_topology, render_topology_drawio, render_topology_text


def parse_ping_output(output: str) -> dict:
    """Extrae pérdida y latencia promedio de la salida EN/ES de ping.

    Admite los resúmenes de Windows/macOS en inglés y español, además del
    formato Linux ``rtt min/avg/max/...``. No depende de un locale concreto.
    """
    text = output or ""
    loss_match = re.search(
        r"(?:\(\s*)?(\d+(?:\.\d+)?)%\s*"
        r"(?:loss|lost|packet\s+loss|perdidos?|perdida)\s*\)?",
        text,
        re.IGNORECASE,
    )
    avg_match = re.search(
        r"(?:Average|Media|Promedio)\s*[=<]\s*(\d+(?:\.\d+)?)\s*ms",
        text,
        re.IGNORECASE,
    )
    if avg_match is None:
        avg_match = re.search(
            r"(?:Average|Media|Promedio)[^\d<]*(?:<\s*)?(\d+(?:\.\d+)?)\s*ms",
            text,
            re.IGNORECASE,
        )
    if avg_match is None:
        # Linux/macOS: rtt/round-trip min/avg/max[/mdev] = 1/2/3/4 ms
        avg_match = re.search(
            r"(?:rtt|round-trip)[^=]*=\s*"
            r"\d+(?:\.\d+)?/(\d+(?:\.\d+)?)/",
            text,
            re.IGNORECASE,
        )

    loss_pct = float(loss_match.group(1)) if loss_match else None
    if loss_pct is not None and loss_pct.is_integer():
        loss_pct = int(loss_pct)
    avg_ms = float(avg_match.group(1)) if avg_match else None
    return {
        "perdida_pct": loss_pct,
        "promedio_ms": avg_ms,
        "alcanzable": loss_pct is not None and loss_pct < 100,
    }


def probe_host(host: str, count: int = 3, timeout_ms: int = 1000,
               run_fn: Callable | None = None) -> dict:
    """Realiza una muestra ICMP sin usar shell ni exponer comandos arbitrarios."""
    count = max(1, min(int(count), 10))
    timeout_ms = max(250, min(int(timeout_ms), 5000))
    if run_fn is None:
        if platform.system().lower() == "windows":
            command = ["ping", "-n", str(count), "-w", str(timeout_ms), str(host)]
        else:
            command = ["ping", "-c", str(count), "-W", str(max(1, timeout_ms // 1000)), str(host)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=(count * timeout_ms / 1000) + 3)
            output = (result.stdout or "") + "\n" + (result.stderr or "")
        except (OSError, subprocess.SubprocessError):
            return {"host": host, "perdida_pct": 100, "promedio_ms": None, "alcanzable": False, "error": "ping no disponible o agotó el tiempo"}
    else:
        try:
            output = run_fn(host, count, timeout_ms)
        except (OSError, subprocess.SubprocessError):
            return {"host": host, "perdida_pct": 100, "promedio_ms": None, "alcanzable": False, "error": "fallo de prueba ICMP"}
    metric = parse_ping_output(output)
    metric["host"] = host
    return metric


def _path_hosts(topology: dict) -> list[str]:
    hosts: list[str] = []
    for trace in topology.get("trazas", []):
        for hop in trace.get("saltos", []):
            host = hop.get("ip") if isinstance(hop, dict) else ""
            if host and host not in hosts:
                hosts.append(host)
        target = trace.get("ip_destino", "")
        if target and target not in hosts:
            hosts.append(target)
    return hosts


def monitor_once(host: str, ping_count: int = 3,
                 topology_fn: Callable | None = None,
                 probe_fn: Callable | None = None) -> dict:
    """Genera una muestra de topología y añade métricas por salto."""
    topology = (topology_fn or build_topology)(trace_targets=[host], scan_ports=False)
    probe = probe_fn or probe_host
    metrics = [probe(path_host, ping_count) for path_host in _path_hosts(topology)]
    by_host = {metric.get("host"): metric for metric in metrics}
    for node in topology.get("nodos", []):
        metric = by_host.get(node.get("ip"))
        if not metric:
            continue
        node["monitorizacion"] = metric
        if metric.get("promedio_ms") is not None:
            node["latencia_ms"] = metric["promedio_ms"]
        node.setdefault("verificaciones", []).append(
            f"Muestra ICMP: {metric.get('perdida_pct', '—')}% pérdida"
        )
    topology["monitorizacion"] = {
        "motor": "visor_pingplotter_like",
        "objetivo": host,
        "muestras_por_salto": ping_count,
        "saltos": metrics,
    }
    return topology


def write_live_reports(topology: dict, report_dir: Path | None = None) -> dict:
    """Actualiza archivos estables y añade una fila al historial 24/7."""
    directory = Path(report_dir or REPORTS_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": directory / "topology_live.json",
        "txt": directory / "topology_live.txt",
        "drawio": directory / "topology_live.drawio",
        "history": directory / "topology_watch_history.jsonl",
        "csv": directory / "topology_watch_history.csv",
    }
    paths["json"].write_text(json.dumps(topology, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["txt"].write_text(render_topology_text(topology), encoding="utf-8")
    paths["drawio"].write_text(render_topology_drawio(topology), encoding="utf-8")
    with paths["history"].open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(topology, ensure_ascii=False) + "\n")
    csv_exists = paths["csv"].exists()
    with paths["csv"].open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ts", "objetivo", "host", "perdida_pct", "promedio_ms", "alcanzable"])
        if not csv_exists:
            writer.writeheader()
        monitor = topology.get("monitorizacion", {})
        for metric in monitor.get("saltos", []):
            writer.writerow({"ts": topology.get("ts", ""), "objetivo": monitor.get("objetivo", ""), **metric})
    return {key: str(path) for key, path in paths.items()}


def run_topology_watch(host: str = "8.8.8.8", interval_s: int = 60,
                       cycles: int = 0, ping_count: int = 3,
                       report_dir: Path | None = None) -> None:
    """Ejecuta el monitor continuamente; cycles=0 significa 24/7 hasta Ctrl+C."""
    interval_s = max(10, int(interval_s))
    cycles = max(0, int(cycles))
    completed = 0
    telemetry = TelemetryClient()
    print(f"Monitor de topología activo: {host} cada {interval_s}s | Ctrl+C para detener")
    try:
        while cycles == 0 or completed < cycles:
            started = time.monotonic()
            try:
                topology = monitor_once(host, ping_count=ping_count)
                paths = write_live_reports(topology, report_dir)
                telemetry_result = telemetry.send_topology(topology)
                metrics = topology.get("monitorizacion", {}).get("saltos", [])
                loss = [m.get("perdida_pct") for m in metrics if m.get("perdida_pct") is not None]
                avg_loss = round(sum(loss) / len(loss), 1) if loss else "—"
                print(f"[{datetime.now().isoformat(timespec='seconds')}] muestra={completed + 1} saltos={len(metrics)} pérdida_media={avg_loss}%")
                print(f"  draw.io: {paths['drawio']}")
                if telemetry_result.get("sent"):
                    print("  telemetría: evento enviado")
            except (OSError, RuntimeError, ValueError) as exc:
                print(f"[{datetime.now().isoformat(timespec='seconds')}] muestra no disponible: {exc}")
            completed += 1
            if cycles and completed >= cycles:
                break
            time.sleep(max(0, interval_s - (time.monotonic() - started)))
    except KeyboardInterrupt:
        print("\nMonitor de topología detenido por el usuario.")
