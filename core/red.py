"""
core/red.py — Utilidades de red: ping, ARP, escaneo de rangos.
"""

import subprocess
import platform
import re
import socket
import ipaddress
import concurrent.futures
from datetime import datetime
from core.colores import dim


# ── Ping ──────────────────────────────────────────────────────────────────

def hacer_ping(host: str, count: int = 1, timeout: int = 2) -> tuple[bool, float | None]:
    """
    Hace ping a un host. Devuelve (éxito, latencia_ms | None).
    Funciona en Windows y Linux/macOS.
    """
    sistema = platform.system().lower()
    if sistema == "windows":
        cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
    else:
        cmd = ["ping", "-c", str(count), "-W", str(timeout), host]

    try:
        resultado = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout + 2
        )
        if resultado.returncode != 0:
            return False, None

        # Extraer latencia del output
        lat = _extraer_latencia(resultado.stdout)
        return True, lat
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, None


def _extraer_latencia(output: str) -> float | None:
    """Extrae la latencia promedio del output de ping."""
    patrones = [
        r"tiempo[=<]\s*([\d.]+)\s*ms",          # Windows ES
        r"time[=<]\s*([\d.]+)\s*ms",             # Linux/macOS
        r"Average\s*=\s*([\d.]+)ms",             # Windows EN
        r"avg.*?=\s*[\d.]+/([\d.]+)/",           # Linux rtt avg
        r"media[=<]\s*([\d.]+)\s*ms",            # Windows variante
    ]
    for p in patrones:
        m = re.search(p, output, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    # Fallback: buscar cualquier número seguido de ms
    m = re.search(r"([\d.]+)\s*ms", output, re.IGNORECASE)
    return float(m.group(1)) if m else None


# ── ARP ───────────────────────────────────────────────────────────────────

def normalizar_mac(mac: str) -> str:
    return re.sub(r"[^0-9a-fA-F]", "", mac).lower()


def obtener_tabla_arp() -> str:
    try:
        r = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5)
        return r.stdout
    except Exception:
        return ""


def buscar_ip_por_mac(mac_objetivo: str) -> str | None:
    """Busca la IP asociada a una MAC en la tabla ARP local."""
    mac_norm = normalizar_mac(mac_objetivo)
    tabla = obtener_tabla_arp()
    for linea in tabla.splitlines():
        if "-" in linea or ":" in linea:
            partes = linea.split()
            if len(partes) >= 2:
                ip = partes[0]
                mac_linea = normalizar_mac(partes[1] if len(partes) > 1 else "")
                if mac_linea == mac_norm:
                    # Validar que es una IP válida
                    try:
                        socket.inet_aton(ip)
                        return ip
                    except Exception:
                        pass
    return None


# ── Resolución DNS ────────────────────────────────────────────────────────

def resolver_host(host: str) -> str | None:
    """Resuelve un hostname a IP. Devuelve None si falla."""
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return None


# ── Escaneo de rango IP ───────────────────────────────────────────────────

def escanear_rango(rango: str, max_workers: int = 50) -> list[dict]:
    """
    Escanea un rango CIDR (ej: "192.168.1.0/24") buscando hosts activos.
    Devuelve lista de dicts: {ip, activo, latencia, hostname}
    """
    try:
        red = ipaddress.ip_network(rango, strict=False)
    except ValueError:
        return []

    hosts = [str(ip) for ip in red.hosts()]
    resultados = []

    def probar_host(ip):
        activo, lat = hacer_ping(ip, count=1, timeout=1)
        hostname = None
        if activo:
            try:
                hostname = socket.gethostbyaddr(ip)[0]
            except Exception:
                pass
        return {
            "ip":       ip,
            "activo":   activo,
            "latencia": round(lat, 1) if lat else None,
            "hostname": hostname,
            "estado":   "UP" if activo else "DOWN",
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        resultados = list(ex.map(probar_host, hosts))

    # Ordenar: primero los activos
    resultados.sort(key=lambda x: (not x["activo"], x["ip"]))
    return resultados


# ── Detectar gateway ─────────────────────────────────────────────────────

def detectar_gateway() -> str | None:
    """Intenta detectar el gateway por defecto."""
    sistema = platform.system().lower()
    try:
        if sistema == "windows":
            r = subprocess.run(["ipconfig"], capture_output=True, text=True)
            m = re.search(r"Puerta de enlace.*?:\s*([\d.]+)", r.stdout, re.IGNORECASE)
            if not m:
                m = re.search(r"Default Gateway.*?:\s*([\d.]+)", r.stdout, re.IGNORECASE)
        else:
            r = subprocess.run(["ip", "route"], capture_output=True, text=True)
            m = re.search(r"default via ([\d.]+)", r.stdout)
        return m.group(1) if m else None
    except Exception:
        return None
