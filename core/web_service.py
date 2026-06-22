"""
core/web_service.py — Verificación de servicios web vía HTTP.
"""

import urllib.request
import urllib.error
import ssl
import time
from config.device import SERVICIOS_WEB


def verificar_url(url: str, timeout: int = 5) -> dict:
    """
    Verifica una URL. Devuelve estado, código HTTP y tiempo de respuesta.
    """
    t0 = time.monotonic()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Visor-Monitor/2.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            lat = round((time.monotonic() - t0) * 1000, 1)
            return {
                "url":      url,
                "online":   True,
                "estado":   "UP",
                "http":     resp.status,
                "latencia": lat,
                "error":    None,
            }
    except urllib.error.HTTPError as e:
        lat = round((time.monotonic() - t0) * 1000, 1)
        # Códigos 4xx/5xx siguen siendo "reachable"
        return {
            "url":      url,
            "online":   e.code < 500,
            "estado":   "UP" if e.code < 500 else "DOWN",
            "http":     e.code,
            "latencia": lat,
            "error":    str(e.reason),
        }
    except Exception as e:
        lat = round((time.monotonic() - t0) * 1000, 1)
        return {
            "url":      url,
            "online":   False,
            "estado":   "DOWN",
            "http":     None,
            "latencia": lat,
            "error":    str(e)[:80],
        }


def escanear_servicios_web(servicios: list[dict] | None = None) -> list[dict]:
    """
    Verifica todos los servicios web. Si no se pasa lista, usa config/device.py.
    """
    if servicios is None:
        servicios = SERVICIOS_WEB

    resultados = []
    for svc in servicios:
        url    = svc.get("url", "").strip()
        nombre = svc.get("nombre", url)
        if not url:
            continue

        r = verificar_url(url)
        r["nombre"] = nombre
        r["ts"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
        resultados.append(r)

    return resultados
