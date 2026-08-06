"""
core/mikrotik_agent.py — Telemetría en Tiempo Real para RouterOS MikroTik.
Jasol Group · Ing. Jeisson Alberto Sarmiento · Saravena, Arauca, Colombia
Protocolo: SSH + RouterOS CLI (sin dependencias externas de librería)
"""

import socket
import subprocess
import re
from datetime import datetime

def _ssh_cmd(host: str, user: str, password: str, command: str, timeout: int = 5) -> str:
    """Ejecuta un comando RouterOS vía SSH y retorna la salida."""
    try:
        resultado = subprocess.run(
            # Accept a new key once, but reject unexpected changes to a known key.
            ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", f"ConnectTimeout={timeout}",
             f"{user}@{host}", command],
            capture_output=True, text=True, timeout=timeout + 2
        )
        return resultado.stdout.strip()
    except (OSError, subprocess.SubprocessError) as e:
        return f"ERROR: {e}"

def ping_mikrotik(host: str) -> bool:
    """Verifica si el MikroTik responde al ping."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            return s.connect_ex((host, 22)) == 0
    except OSError:
        return False

def get_mikrotik_info(host: str, user: str = "admin", password: str = "") -> dict:
    """
    Obtiene información de salud del MikroTik: CPU, memoria, uptime, identidad.
    Retorna dict con los datos o error.
    """
    if not ping_mikrotik(host):
        return {"online": False, "error": "No responde en puerto 22 (SSH)"}

    data = {"online": True, "host": host, "ts": datetime.now().isoformat(timespec="seconds")}

    # Identidad
    identity = _ssh_cmd(host, user, password, ":put [/system identity get name]")
    data["identity"] = identity if not identity.startswith("ERROR") else "—"

    # Uptime
    uptime = _ssh_cmd(host, user, password, ":put [/system resource get uptime]")
    data["uptime"] = uptime if not uptime.startswith("ERROR") else "—"

    # CPU
    cpu = _ssh_cmd(host, user, password, ":put [/system resource get cpu-load]")
    try:
        data["cpu_load"] = int(cpu)
    except (TypeError, ValueError):
        data["cpu_load"] = None

    # Memoria libre
    mem_free = _ssh_cmd(host, user, password, ":put [/system resource get free-memory]")
    mem_total = _ssh_cmd(host, user, password, ":put [/system resource get total-memory]")
    try:
        data["mem_free_mb"]  = round(int(mem_free) / 1024 / 1024, 1)
        data["mem_total_mb"] = round(int(mem_total) / 1024 / 1024, 1)
        data["mem_used_pct"] = round((1 - int(mem_free) / int(mem_total)) * 100, 1)
    except (TypeError, ValueError, ZeroDivisionError):
        data["mem_free_mb"] = data["mem_total_mb"] = data["mem_used_pct"] = None

    # Temperatura (si aplica CCR/hAP)
    temp = _ssh_cmd(host, user, password, ":put [/system health get temperature]")
    try:
        data["temperature"] = float(temp)
    except (TypeError, ValueError):
        data["temperature"] = None

    # Versión RouterOS
    version = _ssh_cmd(host, user, password, ":put [/system package get routeros version]")
    data["ros_version"] = version if not version.startswith("ERROR") else "—"

    return data

def get_interfaces_traffic(host: str, user: str = "admin", password: str = "") -> list:
    """
    Obtiene el tráfico de las interfaces principales del MikroTik.
    """
    raw = _ssh_cmd(host, user, password,
        ":foreach i in=[/interface find] do={ :put ([/interface get $i name].\" \".([/interface monitor-traffic $i once as-value] -> \"rx-bits-per-second\").\" \".([/interface monitor-traffic $i once as-value] -> \"tx-bits-per-second\")) }"
    )
    interfaces = []
    for line in raw.splitlines():
        parts = line.strip().split()
        if len(parts) >= 3:
            try:
                interfaces.append({
                    "name":    parts[0],
                    "rx_mbps": round(int(parts[1]) / 1_000_000, 2),
                    "tx_mbps": round(int(parts[2]) / 1_000_000, 2),
                })
            except (TypeError, ValueError):
                pass
    return interfaces

def get_active_clients(host: str, user: str = "admin", password: str = "") -> int:
    """Retorna el número de clientes DHCP activos."""
    raw = _ssh_cmd(host, user, password, ":put [:len [/ip dhcp-server lease find status=bound]]")
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return 0
