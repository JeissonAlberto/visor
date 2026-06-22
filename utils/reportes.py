"""
utils/reportes.py — Generación y gestión de reportes de escaneo.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from config.settings import GUARDAR_REPORTES, FORMATO_REPORTE, MAX_REPORTES

REPORTS_DIR = Path(__file__).parent.parent / "reports"


def _asegurar_dir():
    REPORTS_DIR.mkdir(exist_ok=True)
    gitkeep = REPORTS_DIR / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()


def guardar_reporte(datos: dict) -> Path | None:
    """Guarda un reporte. Devuelve la ruta del archivo creado."""
    if not GUARDAR_REPORTES:
        return None
    _asegurar_dir()

    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = FORMATO_REPORTE.lower()

    if ext == "json":
        ruta = REPORTS_DIR / f"visor_{ts}.json"
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2, default=str)
    else:
        ruta = REPORTS_DIR / f"visor_{ts}.txt"
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(_formato_txt(datos))

    _limpiar_viejos()
    return ruta


def _limpiar_viejos():
    """Mantiene solo los últimos MAX_REPORTES reportes."""
    archivos = sorted(REPORTS_DIR.glob("visor_*"), key=lambda p: p.stat().st_mtime)
    while len(archivos) > MAX_REPORTES:
        archivos.pop(0).unlink(missing_ok=True)


def leer_ultimo_reporte() -> str:
    """Devuelve el contenido del reporte más reciente como string."""
    _asegurar_dir()
    archivos = sorted(REPORTS_DIR.glob("visor_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    archivos = [a for a in archivos if a.suffix in (".txt", ".json")]
    if not archivos:
        return "No hay reportes guardados."
    ruta = archivos[0]
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def _formato_txt(datos: dict) -> str:
    ts = datos.get("ts", datetime.now().isoformat())
    lineas = [
        "════════════════════════════════════════════",
        f"  VISOR — Jasol Group",
        f"  Reporte: {ts}",
        "════════════════════════════════════════════",
        "",
    ]

    # Dispositivos
    devs = datos.get("dispositivos", [])
    if devs:
        lineas += ["📡 DISPOSITIVOS DE RED", "─────────────────────"]
        for d in devs:
            estado = "UP  " if d.get("online") else "DOWN"
            lat    = f"{d.get('latencia')} ms" if d.get("latencia") else "Sin respuesta"
            lineas.append(f"[{estado}] {d.get('nombre','')} ({d.get('ip','')}) — {lat}")
        lineas.append("")

    # Web
    webs = datos.get("web", [])
    if webs:
        lineas += ["🌐 SERVICIOS WEB", "────────────────"]
        for w in webs:
            estado = "OK  " if w.get("online") else "DOWN"
            lat    = f"{w.get('latencia')} ms" if w.get("latencia") else "—"
            http   = f"HTTP {w.get('http','—')}" if w.get("http") else ""
            lineas.append(f"[{estado}] {w.get('nombre','')} ({w.get('url','')}) — {lat} {http}")
        lineas.append("")

    # Internet
    inet = datos.get("internet")
    if inet:
        lineas += ["📶 CALIDAD DE INTERNET", "──────────────────────"]
        lineas.append(f"Calidad:           {inet.get('calidad','—')}")
        lineas.append(f"Latencia avg/min/max: {inet.get('lat_avg')} / {inet.get('lat_min')} / {inet.get('lat_max')} ms")
        lineas.append(f"Jitter:            {inet.get('jitter')} ms")
        lineas.append(f"Pérdida de paquetes: {inet.get('perdida')}%")
        lineas.append(f"Pings OK / Total:  {inet.get('pings_ok')} / {inet.get('total_pings')}")
        lineas.append("")

    lineas.append("────────────────────────────────────────────")
    lineas.append("Visor v2.0 · by Jasol Group · Arauca, Colombia")
    return "\n".join(lineas)
