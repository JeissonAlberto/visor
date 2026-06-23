"""
core/web_service.py — Verificación de servicios web y geolocalización de IPs.
"""

import urllib.request
import urllib.error
import socket
import ssl
import time
import json
from config.device import SERVICIOS_WEB


# ── Categorías de servicios ───────────────────────────────────────────────

SERVICIOS_BUILTIN = {
    "DNS y Red": [
        {"nombre": "Cloudflare DNS",    "url": "https://1.1.1.1"},
        {"nombre": "Google DNS",        "url": "https://8.8.8.8"},
        {"nombre": "Cloudflare Web",    "url": "https://www.cloudflare.com"},
        {"nombre": "Google",            "url": "https://www.google.com"},
        {"nombre": "OpenDNS",           "url": "https://www.opendns.com"},
    ],
    "Redes Sociales": [
        {"nombre": "Facebook",          "url": "https://www.facebook.com"},
        {"nombre": "Instagram",         "url": "https://www.instagram.com"},
        {"nombre": "Twitter / X",       "url": "https://www.x.com"},
        {"nombre": "TikTok",            "url": "https://www.tiktok.com"},
        {"nombre": "YouTube",           "url": "https://www.youtube.com"},
        {"nombre": "WhatsApp Web",      "url": "https://web.whatsapp.com"},
        {"nombre": "LinkedIn",          "url": "https://www.linkedin.com"},
    ],
    "Inteligencias Artificiales": [
        {"nombre": "ChatGPT",           "url": "https://chat.openai.com"},
        {"nombre": "Gemini",            "url": "https://gemini.google.com"},
        {"nombre": "Claude",            "url": "https://claude.ai"},
        {"nombre": "Copilot",           "url": "https://copilot.microsoft.com"},
        {"nombre": "Perplexity",        "url": "https://www.perplexity.ai"},
        {"nombre": "Grok",              "url": "https://grok.com"},
    ],
    "Mis Servicios": [],   # se carga desde config/device.py
}


# ── Verificación HTTP ─────────────────────────────────────────────────────

# Contexto SSL global para reutilización y ahorro de overhead
_SSL_CONTEXT = None

def _ssl_ctx():
    global _SSL_CONTEXT
    if _SSL_CONTEXT is None:
        _SSL_CONTEXT = ssl.create_default_context()
        _SSL_CONTEXT.check_hostname = False
        _SSL_CONTEXT.verify_mode    = ssl.CERT_NONE
    return _SSL_CONTEXT


def verificar_url(url: str, timeout: int = 5) -> dict:
    """
    Verifica una URL optimizando para medir tanto latencia de red (TCP) como 
    tiempo de respuesta web (TTFB). Usa el método HEAD para mayor velocidad.
    """
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host   = parsed.hostname
    port   = parsed.port or (443 if parsed.scheme == "https" else 80)
    
    t_red = None
    t0    = time.monotonic()
    
    # 1. Medir latencia de red pura (TCP Handshake) - similar al ping
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        t_sock = time.monotonic()
        sock.connect((host, port))
        t_red  = round((time.monotonic() - t_sock) * 1000, 1)
        sock.close()
    except Exception:
        pass

    # 2. Medir tiempo de respuesta Web (HTTP/SSL) usando HEAD
    ctx = _ssl_ctx()
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Connection": "close"
        }
        # Intentamos HEAD primero; si falla, urlopen con GET es el fallback automático
        req = urllib.request.Request(url, headers=headers, method="HEAD")
        
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            lat_web = round((time.monotonic() - t0) * 1000, 1)
            return {
                "url":      url,
                "online":   True,
                "estado":   "UP",
                "http":     resp.status,
                "latencia": lat_web,
                "lat_red":  t_red,
                "error":    None,
            }
    except urllib.error.HTTPError as e:
        # Algunos servidores no aceptan HEAD (405, 403), reintentamos con GET rápido
        if e.code in (403, 405):
            try:
                req_get = urllib.request.Request(url, headers=headers, method="GET")
                with urllib.request.urlopen(req_get, timeout=timeout, context=ctx) as resp:
                    lat_web = round((time.monotonic() - t0) * 1000, 1)
                    return {
                        "url":      url,
                        "online":   True,
                        "estado":   "UP",
                        "http":     resp.status,
                        "latencia": lat_web,
                        "lat_red":  t_red,
                        "error":    None,
                    }
            except Exception:
                pass
        
        lat_web = round((time.monotonic() - t0) * 1000, 1)
        return {
            "url":      url,
            "online":   e.code < 500,
            "estado":   "UP" if e.code < 500 else "DOWN",
            "http":     e.code,
            "latencia": lat_web,
            "lat_red":  t_red,
            "error":    str(e.reason),
        }
    except Exception as e:
        lat_web = round((time.monotonic() - t0) * 1000, 1)
        return {
            "url":      url,
            "online":   False,
            "estado":   "DOWN",
            "http":     None,
            "latencia": lat_web,
            "lat_red":  t_red,
            "error":    str(e)[:80],
        }


def escanear_servicios_web(servicios: list | None = None) -> list:
    """Verifica lista de servicios. Si no se pasa, usa config/device.py."""
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


def escanear_por_categorias() -> dict:
    """
    Verifica todos los servicios agrupados por categoría de forma concurrente
    usando hilos para disminuir el tiempo total y mejorar la precisión.
    """
    import datetime
    from concurrent.futures import ThreadPoolExecutor
    
    # Cargar "Mis Servicios" desde config
    mis = list(SERVICIOS_WEB)
    SERVICIOS_BUILTIN["Mis Servicios"] = mis

    # Preparar lista plana de tareas
    tareas = []
    for cat, servicios in SERVICIOS_BUILTIN.items():
        for svc in servicios:
            url = svc.get("url", "").strip()
            if url:
                tareas.append((cat, svc))

    # Ejecutar en paralelo (máximo 15 hilos para no saturar)
    def _tarea_verificar(item):
        cat, svc = item
        r = verificar_url(svc["url"])
        r["nombre"] = svc.get("nombre", svc["url"])
        r["ts"]     = datetime.datetime.now().isoformat(timespec="seconds")
        return cat, r

    categorias = {c: [] for c in SERVICIOS_BUILTIN.keys() if SERVICIOS_BUILTIN[c] or c == "Mis Servicios"}
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        for cat, resultado in executor.map(_tarea_verificar, tareas):
            categorias[cat].append(resultado)

    return {k: v for k, v in categorias.items() if v}


# ── Geolocalización de IP ─────────────────────────────────────────────────

def geolocalizacion_ip(ip: str) -> dict:
    """
    Geolocaliza una IP usando ip-api.com (gratuito, sin clave).
    Devuelve dict con país, ciudad, ISP, lat/lon, etc.
    """
    # No geolocalizar IPs privadas
    partes = ip.strip().split(".")
    if len(partes) == 4:
        a, b = int(partes[0]), int(partes[1])
        if a == 10 or a == 127:
            return {"ip": ip, "privada": True, "info": "IP privada — sin geolocalización"}
        if a == 172 and 16 <= b <= 31:
            return {"ip": ip, "privada": True, "info": "IP privada — sin geolocalización"}
        if a == 192 and b == 168:
            return {"ip": ip, "privada": True, "info": "IP privada — sin geolocalización"}

    try:
        url = "http://ip-api.com/json/" + ip + "?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,isp,org,as,query&lang=es"
        req = urllib.request.Request(url, headers={"User-Agent": "Visor-NOC/2.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
        if data.get("status") == "success":
            return {
                "ip":          data.get("query", ip),
                "privada":     False,
                "pais":        data.get("country", "?"),
                "codigo":      data.get("countryCode", "?"),
                "region":      data.get("regionName", "?"),
                "ciudad":      data.get("city", "?"),
                "zip":         data.get("zip", ""),
                "lat":         data.get("lat"),
                "lon":         data.get("lon"),
                "isp":         data.get("isp", "?"),
                "org":         data.get("org", "?"),
                "as":          data.get("as", "?"),
            }
        else:
            return {"ip": ip, "privada": False, "error": data.get("message", "Sin datos")}
    except Exception as e:
        return {"ip": ip, "privada": False, "error": str(e)[:80]}


def geolocalizacion_rango(ips: list) -> list:
    """
    Geolocaliza una lista de IPs. Respeta el límite de ip-api.com (45 req/min).
    """
    import time
    resultados = []
    for i, ip in enumerate(ips):
        if i > 0 and i % 40 == 0:
            time.sleep(1.5)   # respetar rate limit
        resultados.append(geolocalizacion_ip(ip))
    return resultados
