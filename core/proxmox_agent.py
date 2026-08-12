"""
core/proxmox_agent.py — Telemetría de Nodos Proxmox VE.
Jasol Group · Ing. Jeisson Alberto Sarmiento · Saravena, Arauca, Colombia
Usa la API REST de Proxmox (puerto 8006).
"""

import json
import os
import socket
import urllib.request
import urllib.error
import ssl
import ipaddress
from datetime import datetime


def _proxmox_ssl_context(host: str) -> ssl.SSLContext:
    """Crea un contexto TLS verificable para la API de Proxmox.

    Proxmox suele usar certificados autofirmados. La operación segura por
    defecto valida la CA del sistema (o ``VISOR_PROXMOX_CA_FILE``); la
    excepción de TLS inseguro debe habilitarse explícitamente para instalaciones
    antiguas que aún no puedan instalar su CA.
    """
    ca_file = os.getenv("VISOR_PROXMOX_CA_FILE")
    insecure = os.getenv("VISOR_PROXMOX_INSECURE_TLS", "").lower() in {
        "1", "true", "yes", "si"
    }

    if ca_file:
        context = ssl.create_default_context(cafile=ca_file)
    else:
        context = ssl.create_default_context()

    if insecure:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    else:
        # Para una IP literal no es posible comprobar el nombre del certificado
        # de forma fiable; la cadena de confianza sigue siendo obligatoria.
        try:
            ipaddress.ip_address(host)
        except (ValueError, TypeError):
            context.check_hostname = True
        else:
            context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
    return context


def _proxmox_get(host: str, token_id: str, token_secret: str, endpoint: str) -> dict:
    """Realiza una petición GET a la API de Proxmox."""
    url = f"https://{host}:8006/api2/json{endpoint}"

    try:
        ctx = _proxmox_ssl_context(host)
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"PVEAPIToken={token_id}={token_secret}")
        with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError, ValueError, UnicodeError) as e:
        return {"error": str(e)}


def ping_proxmox(host: str) -> bool:
    """Verifica que el API de Proxmox esté accesible."""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        return sock.connect_ex((host, 8006)) == 0
    except OSError:
        return False
    finally:
        if sock is not None:
            sock.close()

def get_nodes_status(host: str, token_id: str = "root@pam!visor", token_secret: str = "") -> list:
    """
    Retorna el estado de todos los nodos del cluster Proxmox.
    """
    if not ping_proxmox(host):
        return [{"online": False, "error": "No responde en puerto 8006"}]

    raw = _proxmox_get(host, token_id, token_secret, "/nodes")
    nodes = []
    for node in raw.get("data", []):
        cpu_pct = round(node.get("cpu", 0) * 100, 1)
        mem_total = node.get("maxmem", 0)
        mem_used  = node.get("mem", 0)
        disk_total = node.get("maxdisk", 0)
        disk_used  = node.get("disk", 0)

        nodes.append({
            "node":       node.get("node", "—"),
            "status":     node.get("status", "—"),
            "cpu_pct":    cpu_pct,
            "mem_used_gb":  round(mem_used  / 1024**3, 1) if mem_total else 0,
            "mem_total_gb": round(mem_total / 1024**3, 1) if mem_total else 0,
            "mem_pct":    round(mem_used / mem_total * 100, 1) if mem_total else 0,
            "disk_used_gb":  round(disk_used  / 1024**3, 1) if disk_total else 0,
            "disk_total_gb": round(disk_total / 1024**3, 1) if disk_total else 0,
            "uptime_h":   round(node.get("uptime", 0) / 3600, 1),
            "ts":         datetime.now().isoformat(timespec="seconds"),
        })
    return nodes

def get_vms_status(host: str, node: str, token_id: str = "root@pam!visor", token_secret: str = "") -> list:
    """Retorna el estado de las VMs en un nodo Proxmox."""
    raw = _proxmox_get(host, token_id, token_secret, f"/nodes/{node}/qemu")
    vms = []
    for vm in raw.get("data", []):
        vms.append({
            "vmid":    vm.get("vmid"),
            "name":    vm.get("name", "—"),
            "status":  vm.get("status", "—"),
            "cpu_pct": round(vm.get("cpu", 0) * 100, 1),
            "mem_mb":  round(vm.get("mem", 0) / 1024**2, 1),
            "uptime_h": round(vm.get("uptime", 0) / 3600, 1),
        })
    return vms
