"""
core/test_internet.py — Test de calidad de internet.
Mide latencia (avg/min/max/jitter) y pérdida de paquetes.
"""

import subprocess
import platform
import re
import statistics
import time
import urllib.request
import ssl
from config.settings import PING_COUNT


HOSTS_REFERENCIA = [
    ("Google DNS",    "8.8.8.8"),
    ("Cloudflare",    "1.1.1.1"),
    ("Google DNS 2",  "8.8.4.4"),
]


def _ping_latencias(host: str, count: int = 4) -> list[float]:
    """Devuelve lista de latencias individuales o lista vacía si falla."""
    sistema = platform.system().lower()
    if sistema == "windows":
        cmd = ["ping", "-n", str(count), "-w", "2000", host]
    else:
        cmd = ["ping", "-c", str(count), "-W", "2", host]

    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, timeout=count * 3 + 2)
        salida = r.stdout
        # Extraer cada latencia individual
        # Linux: tiempo=X ms / time=X ms
        # Windows: tiempo=X ms / time=X ms
        lats = re.findall(r"tiempo[=<]([\d.]+)\s*ms|time[=<]([\d.]+)\s*ms", salida, re.IGNORECASE)
        valores = []
        for a, b in lats:
            v = a or b
            if v:
                try:
                    valores.append(float(v))
                except ValueError:
                    pass
        # Fallback: buscar "min/avg/max" en Linux
        if not valores:
            m = re.search(r"([\d.]+)/([\d.]+)/([\d.]+)", salida)
            if m:
                return [float(m.group(1)), float(m.group(2)), float(m.group(3))]
        return valores
    except Exception:
        return []


def test_internet(count: int | None = None) -> dict:
    """
    Test completo de calidad de internet.
    Devuelve dict con latencias, jitter, pérdida y calificación.
    """
    if count is None:
        count = PING_COUNT

    todas_lats = []
    resultados_hosts = []

    for nombre, host in HOSTS_REFERENCIA:
        lats = _ping_latencias(host, count=count)
        perdidos = count - len(lats)
        perdidos = max(0, perdidos)

        resultados_hosts.append({
            "host":    host,
            "nombre":  nombre,
            "lats":    lats,
            "perdidos": perdidos,
        })
        todas_lats.extend(lats)

    # Métricas globales
    total_pings  = count * len(HOSTS_REFERENCIA)
    total_perdidos = sum(r["perdidos"] for r in resultados_hosts)
    tasa_perdida = round((total_perdidos / total_pings) * 100, 1) if total_pings else 100.0

    if todas_lats:
        lat_avg  = round(statistics.mean(todas_lats), 1)
        lat_min  = round(min(todas_lats), 1)
        lat_max  = round(max(todas_lats), 1)
        jitter   = round(statistics.stdev(todas_lats), 1) if len(todas_lats) > 1 else 0.0
    else:
        lat_avg = lat_min = lat_max = jitter = None

    # Calificación
    calidad = _calificar(lat_avg, tasa_perdida, jitter)

    return {
        "lat_avg":       lat_avg,
        "lat_min":       lat_min,
        "lat_max":       lat_max,
        "jitter":        jitter,
        "perdida":       tasa_perdida,
        "total_pings":   total_pings,
        "pings_ok":      total_pings - total_perdidos,
        "calidad":       calidad,
        "hosts":         resultados_hosts,
        "ts":            __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }


def _calificar(avg: float | None, perdida: float, jitter: float | None) -> str:
    if avg is None or perdida >= 80:
        return "SIN CONEXIÓN"
    if perdida > 30 or (avg and avg > 500):
        return "MUY MALA"
    if perdida > 10 or (avg and avg > 200) or (jitter and jitter > 50):
        return "MALA"
    if perdida > 5  or (avg and avg > 100) or (jitter and jitter > 20):
        return "REGULAR"
    if perdida > 0  or (avg and avg > 50)  or (jitter and jitter > 10):
        return "BUENA"
    return "EXCELENTE"
