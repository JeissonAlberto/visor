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
        "  VISOR — Monitor de Red v2.0",
        "  Creado por Ing. Jeisson Alberto Sarmiento",
        "  Jasol Group  ·  Saravena, Arauca, Colombia",
        f"  Reporte: {ts}",
        "════════════════════════════════════════════",
        "",
    ]

    # Dispositivos
    devs = datos.get("dispositivos", [])
    if devs:
        lineas += ["DISPOSITIVOS DE RED", "───────────────────"]
        for d in devs:
            if not isinstance(d, dict):
                continue
            estado = "UP  " if d.get("online") else "DOWN"
            lat    = str(d.get("latencia")) + " ms" if d.get("latencia") else "Sin respuesta"
            lineas.append("[" + estado + "] " + str(d.get("nombre","")) + " (" + str(d.get("ip","")) + ") — " + lat)
        lineas.append("")

    # Web — nuevo formato por categorías (dict) o viejo formato (lista)
    webs = datos.get("web")
    if webs:
        lineas += ["SERVICIOS WEB", "─────────────"]
        if isinstance(webs, dict):
            # Nuevo formato: {"DNS y Red": [...], "Redes Sociales": [...], ...}
            for cat, servicios in webs.items():
                if not isinstance(servicios, list):
                    continue
                up  = sum(1 for s in servicios if isinstance(s, dict) and s.get("online"))
                tot = len(servicios)
                lineas.append("")
                lineas.append(cat + "  (" + str(up) + "/" + str(tot) + ")")
                lineas.append("  " + "─" * 40)
                for w in servicios:
                    if not isinstance(w, dict):
                        continue
                    estado = "UP  " if w.get("online") else "DOWN"
                    lat    = str(w.get("latencia")) + " ms" if w.get("latencia") else "—"
                    http   = "HTTP " + str(w.get("http", "—"))
                    lineas.append("  [" + estado + "] " + str(w.get("nombre","")) + " — " + lat + "  " + http)
        elif isinstance(webs, list):
            # Formato antiguo: lista plana
            for w in webs:
                if not isinstance(w, dict):
                    continue
                estado = "OK  " if w.get("online") else "DOWN"
                lat    = str(w.get("latencia")) + " ms" if w.get("latencia") else "—"
                http   = "HTTP " + str(w.get("http","—")) if w.get("http") else ""
                lineas.append("[" + estado + "] " + str(w.get("nombre","")) + " (" + str(w.get("url","")) + ") — " + lat + " " + http)
        lineas.append("")

    # Internet
    inet = datos.get("internet")
    if inet and isinstance(inet, dict):
        lineas += ["CALIDAD DE INTERNET", "───────────────────"]
        lineas.append("Calidad:              " + str(inet.get("calidad","—")))
        lineas.append("Latencia avg/min/max: " + str(inet.get("lat_avg")) + " / " + str(inet.get("lat_min")) + " / " + str(inet.get("lat_max")) + " ms")
        lineas.append("Jitter:               " + str(inet.get("jitter")) + " ms")
        lineas.append("Descarga:             " + str(inet.get("descarga_mbps","—")) + " Mbps")
        lineas.append("Subida:               " + str(inet.get("subida_mbps","—")) + " Mbps")
        lineas.append("Throughput local:     " + str(inet.get("throughput_mbps","—")) + " Mbps")
        lineas.append("Perdida de paquetes:  " + str(inet.get("perdida")) + "%")
        lineas.append("Pings OK / Total:     " + str(inet.get("pings_ok")) + " / " + str(inet.get("total_pings")))
        lineas.append("")

    lineas.append("════════════════════════════════════════════")
    lineas.append("Visor v2.0  ·  Creado por Ing. Jeisson Alberto Sarmiento")
    lineas.append("Jasol Group  ·  Saravena, Arauca, Colombia")
    return "\n".join(lineas)
