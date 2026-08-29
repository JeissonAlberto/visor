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


# Prevent accidental scans from creating millions of subprocesses/futures.
MAX_SCAN_HOSTS = 4096
MAX_SCAN_WORKERS = 100


# ── Ping ──────────────────────────────────────────────────────────────────

def hacer_ping(host: str, count: int = 1, timeout: int = 2) -> tuple[bool, float | None]:
    """
    Hace ping a un host de forma robusta.
    """
    sistema = platform.system().lower()
    if sistema == "windows":
        # -n paquetes, -w espera en ms
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
        
        output = resultado.stdout
        # En Windows, el returncode puede ser 0 incluso si falla el destino
        # Buscamos patrones de éxito
        exito = False
        if sistema == "windows":
            # Si hay TTL es que respondió el host
            if "TTL=" in output.upper():
                exito = True
        else:
            if "bytes from" in output.lower():
                exito = True
        
        if not exito and resultado.returncode == 0 and "ms" in output.lower():
            exito = True # Fallback por si acaso
            
        if not exito:
            return False, None

        lat = _extraer_latencia(output)
        return True, lat
    except (OSError, subprocess.SubprocessError):
        return False, None


def _extraer_latencia(output: str) -> float | None:
    """Extrae la latencia del output de ping usando regex robusto."""
    # Intentar buscar el tiempo individual o promedio
    patrones = [
        r"(?:tiempo|time)[=<]([\d.]+)\s*ms",
        r"media[=<]([\d.]+)\s*ms",
        r"Average\s*=\s*([\d.]+)ms",
        r"avg.*?=\s*[\d.]+/([\d.]+)/",
    ]
    
    for p in patrones:
        m = re.search(p, output, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    
    # Fallback final
    m = re.search(r"([\d.]+)\s*ms", output, re.IGNORECASE)
    if m:
        try: return float(m.group(1))
        except ValueError: pass
        
    return None


# ── ARP ───────────────────────────────────────────────────────────────────

def normalizar_mac(mac: str) -> str:
    return re.sub(r"[^0-9a-fA-F]", "", mac).lower()


def obtener_tabla_arp() -> str:
    try:
        r = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5)
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def buscar_ip_por_mac(mac_objetivo: str) -> str | None:
    """Busca la IP asociada a una MAC en la tabla ARP local de forma flexible."""
    mac_norm = normalizar_mac(mac_objetivo)
    if not mac_norm: return None
    
    tabla = obtener_tabla_arp()
    for linea in tabla.splitlines():
        linea = linea.lower().strip()
        if mac_norm[:4] in linea.replace("-", "").replace(":", ""): # pre-filtro rápido
            partes = re.findall(r"[\d.]+|[0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2}[:-][0-9a-f]{2}", linea)
            
            # Buscamos algo que parezca IP y algo que parezca la MAC normalizada
            ip_encontrada = None
            for p in partes:
                if "." in p and p.count(".") == 3:
                    ip_encontrada = p
                elif normalizar_mac(p) == mac_norm:
                    if ip_encontrada:
                        return ip_encontrada
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

    # Check the size before materializing hosts or creating futures. For IPv4
    # networks up to /30, network and broadcast addresses are not scannable;
    # /31, /32 and IPv6 use all addresses returned by ``hosts()``.
    host_count = red.num_addresses
    if red.version == 4 and red.prefixlen < 31:
        host_count -= 2
    if host_count > MAX_SCAN_HOSTS:
        raise ValueError(
            f"rango demasiado grande: {host_count} hosts (máximo {MAX_SCAN_HOSTS})"
        )
    hosts = [str(ip) for ip in red.hosts()]
    try:
        workers = max(1, min(int(max_workers), MAX_SCAN_WORKERS))
    except (TypeError, ValueError):
        workers = 50
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

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        resultados = list(ex.map(probar_host, hosts))

    # Ordenar primero los activos y después por dirección, soportando IPv4 e
    # IPv6 sin intentar separar una dirección IPv6 por puntos.
    def clave_ip(resultado):
        try:
            direccion = ipaddress.ip_address(resultado["ip"])
            return (not resultado["activo"], direccion.version, int(direccion))
        except (ValueError, TypeError):
            return (not resultado["activo"], 99, 0)

    resultados.sort(key=clave_ip)
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
    except (OSError, subprocess.SubprocessError):
        return None
