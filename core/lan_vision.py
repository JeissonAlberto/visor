"""
core/lan_vision.py — LAN Discovery con OUI lookup (inspirado en whosthere).
Jasol Group · Ing. Jeisson Alberto Sarmiento · Saravena, Arauca, Colombia

Descubre todos los dispositivos de la LAN via ARP + ping multihilo.
Identifica fabricante por MAC usando OUI lookup offline.
Sin dependencias externas.
"""

import socket
import subprocess
import platform
import re
import concurrent.futures
import ipaddress
from datetime import datetime

# Prevent accidental LAN scans from materializing huge CIDR ranges.
MAX_LAN_HOSTS = 4096

# ── OUI Database (Top vendors relevantes para ISP) ───────────────────────
OUI_DB = {
    "00:00:5E": "IANA",
    "00:0C:29": "VMware",
    "00:1A:4B": "MikroTik",
    "00:1B:63": "Apple",
    "00:1C:B3": "Apple",
    "00:1D:7E": "Cisco-Linksys",
    "00:50:56": "VMware",
    "00:90:27": "Intel",
    "08:00:27": "VirtualBox",
    "18:FD:74": "MikroTik",
    "2C:C8:1B": "MikroTik",
    "48:8F:5A": "MikroTik",
    "4C:5E:0C": "MikroTik",
    "6C:3B:6B": "MikroTik",
    "74:4D:28": "MikroTik",
    "B8:69:F4": "MikroTik",
    "C4:AD:34": "MikroTik",
    "D4:CA:6D": "MikroTik",
    "DC:2C:6E": "MikroTik",
    "E4:8D:8C": "MikroTik",
    "00:10:DB": "Juniper",
    "00:13:10": "Linksys",
    "00:19:E3": "Huawei",
    "00:1E:10": "Ubiquiti",
    "00:27:22": "Ubiquiti",
    "04:18:D6": "Ubiquiti",
    "0C:80:63": "Ubiquiti",
    "18:E8:29": "Ubiquiti",
    "24:A4:3C": "Ubiquiti",
    "44:D9:E7": "Ubiquiti",
    "60:22:32": "Ubiquiti",
    "68:72:51": "Ubiquiti",
    "78:8A:20": "Ubiquiti",
    "80:2A:A8": "Ubiquiti",
    "F4:92:BF": "Ubiquiti",
    "FC:EC:DA": "Ubiquiti",
    "00:0E:8E": "Cisco",
    "00:1A:A2": "Cisco",
    "00:1B:D4": "Cisco",
    "00:24:13": "Cisco",
    "00:25:45": "Cisco",
    "B0:7D:47": "Huawei",
    "00:1E:A6": "Huawei",
    "00:25:9E": "Huawei",
    "04:BD:70": "Huawei",
    "18:CF:5E": "Huawei",
    "20:F3:A3": "Huawei",
    "28:6E:D4": "Huawei",
    "48:00:31": "Huawei",
    "50:9F:27": "Huawei",
    "6C:4B:90": "Huawei",
    "74:A0:2F": "Huawei",
    "84:BE:52": "Huawei",
    "88:E3:AB": "Huawei",
    "00:11:32": "Synology",
    "00:11:9B": "Apple",
    "A4:C3:F0": "Apple",
    "F8:FF:C2": "Apple",
    "AC:BC:32": "Apple",
    "00:08:22": "TP-Link",
    "54:C3:79": "TP-Link",
    "60:32:B1": "TP-Link",
    "90:F6:52": "TP-Link",
    "B0:48:7A": "TP-Link",
    "EC:08:6B": "TP-Link",
    "F0:9F:C2": "Ubiquiti",
    "00:E0:4C": "Realtek",
    "A8:5E:45": "Xiaomi",
    "28:6C:07": "Xiaomi",
    "50:64:2B": "Xiaomi",
    "7C:1E:52": "ZTE",
    "00:26:E8": "ZTE",
    "34:44:1F": "ZTE",
}


def lookup_oui(mac: str) -> str:
    """Identifica el fabricante de un dispositivo por su dirección MAC."""
    if not mac or mac == "—":
        return "Desconocido"
    # Normalizar: 00:1A:4B:xx:xx:xx → 00:1A:4B
    partes = re.findall(r"[0-9A-Fa-f]{2}", mac)
    if len(partes) < 3:
        return "Desconocido"
    oui = ":".join(partes[:3]).upper()
    return OUI_DB.get(oui, "Desconocido")


def _get_arp_table() -> dict:
    """Lee la tabla ARP del sistema y retorna {ip: mac}."""
    tabla = {}
    sistema = platform.system().lower()
    try:
        r = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5)
        for linea in r.stdout.splitlines():
            # Windows: "  192.168.1.1     00-0c-29-xx-xx-xx     dynamic"
            # Linux:   "192.168.1.1 ether 00:0c:29:xx:xx:xx C eth0"
            ip_m  = re.search(r"(\d+\.\d+\.\d+\.\d+)", linea)
            mac_m = re.search(r"([0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}"
                              r"[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2}[:\-][0-9a-fA-F]{2})", linea)
            if ip_m and mac_m:
                ip  = ip_m.group(1)
                mac = mac_m.group(1).replace("-", ":").upper()
                # Filtrar MACs de broadcast/multicast
                if mac not in ("FF:FF:FF:FF:FF:FF", "00:00:00:00:00:00"):
                    tabla[ip] = mac
    except Exception:
        pass
    return tabla


def _ping_host(ip: str) -> bool:
    """Ping rápido de un solo paquete."""
    sistema = platform.system().lower()
    if sistema == "windows":
        cmd = ["ping", "-n", "1", "-w", "500", ip]
    else:
        cmd = ["ping", "-c", "1", "-W", "1", ip]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        return "TTL=" in r.stdout.upper() or "bytes from" in r.stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return False


def _scan_ports_fast(ip: str, ports: list = None) -> list:
    """Escanea puertos comunes en un host y cierra cada socket siempre."""
    if ports is None:
        ports = [22, 23, 80, 443, 445, 3389, 8080, 8291, 8728, 8729]
    if not ports:
        return []

    abiertos = []

    def check(p):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex((ip, p)) == 0:
                    abiertos.append(p)
        except OSError:
            pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(ports)) as ex:
        ex.map(check, ports)
    return sorted(abiertos)


def _resolve_hostname(ip: str) -> str:
    """Resolución DNS inversa rápida."""
    try:
        return socket.gethostbyaddr(ip)[0]
    except OSError:
        return ""


def _classify_device(mac: str, hostname: str, ports: list) -> str:
    """Clasifica el tipo de dispositivo por fabricante y puertos abiertos."""
    vendor = lookup_oui(mac).lower()
    hostname = hostname.lower()

    if "mikrotik" in vendor:     return "🔴 Router MikroTik"
    if "ubiquiti" in vendor:     return "📡 Ubiquiti AP/Switch"
    if "huawei" in vendor:       return "📟 Huawei OLT/ONT"
    if "cisco" in vendor:        return "🔵 Cisco"
    if "zte" in vendor:          return "📟 ZTE OLT/ONT"
    if "vmware" in vendor or "virtualbox" in vendor: return "🖥️ VM/Hypervisor"
    if "synology" in vendor:     return "💾 NAS Synology"
    if 8291 in ports or 8728 in ports: return "🔴 RouterOS (MikroTik)"
    if 8006 in ports:            return "🖥️ Proxmox VE"
    if 22 in ports and 80 in ports: return "🖥️ Servidor Linux"
    if 3389 in ports:            return "🪟 Windows PC/Server"
    if 23 in ports:              return "⚠️ Telnet (inseguro)"
    if "android" in hostname or "phone" in hostname: return "📱 Smartphone"
    if "printer" in hostname or "print" in hostname: return "🖨️ Impresora"
    if "apple" in vendor:        return "🍎 Apple"
    if "tp-link" in vendor:      return "📶 TP-Link"
    if "xiaomi" in vendor:       return "📱 Xiaomi"
    return "💻 Host"


def discover_lan(rango: str = None, scan_ports: bool = True, callback=None) -> list:
    """
    Descubre todos los dispositivos activos en la LAN.
    
    Args:
        rango: CIDR como "192.168.1.0/24". Si es None, lo detecta automáticamente.
        scan_ports: Si True, escanea puertos comunes en cada host activo.
        callback: Función llamada con cada resultado parcial (para mostrar progreso).
    
    Returns:
        Lista de dicts con info completa de cada dispositivo.

    Raises:
        ValueError: si el CIDR contiene más de ``MAX_LAN_HOSTS`` hosts.
    """
    # ── 1. Detectar rango si no se especificó ─────────────────────────────
    if not rango:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip_local = s.getsockname()[0]
            partes = ip_local.split(".")
            rango = ".".join(partes[:3]) + ".0/24"
        except (OSError, IndexError, ValueError):
            rango = "192.168.1.0/24"

    # ── 2. Poblar ARP via ping-sweep concurrente ──────────────────────────
    try:
        red = ipaddress.ip_network(rango, strict=False)
    except (TypeError, ValueError):
        return []

    host_count = red.num_addresses
    if red.version == 4 and red.prefixlen < 31:
        host_count -= 2
    if host_count > MAX_LAN_HOSTS:
        raise ValueError(
            f"rango LAN demasiado grande: {host_count} hosts "
            f"(máximo {MAX_LAN_HOSTS})"
        )

    hosts_a_probar = [str(ip) for ip in red.hosts()]

    activos_ips = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, min(150, len(hosts_a_probar)))
    ) as ex:
        futures = {ex.submit(_ping_host, ip): ip for ip in hosts_a_probar}
        for fut in concurrent.futures.as_completed(futures):
            ip = futures[fut]
            try:
                if fut.result():
                    activos_ips.append(ip)
            except:
                pass

    # ── 3. Leer tabla ARP actualizada ─────────────────────────────────────
    arp = _get_arp_table()

    # ── 4. Enriquecer cada host activo ────────────────────────────────────
    resultados = []

    def enriquecer(ip):
        mac      = arp.get(ip, "—")
        vendor   = lookup_oui(mac)
        hostname = _resolve_hostname(ip)
        ports    = _scan_ports_fast(ip) if scan_ports else []
        tipo     = _classify_device(mac, hostname, ports)
        riesgo   = "⚠️ ALTO" if any(p in ports for p in [23, 3389, 445]) else (
                   "🟡 MEDIO" if any(p in ports for p in [80, 8080]) else "✅ BAJO")

        rec = {
            "ip":       ip,
            "mac":      mac,
            "vendor":   vendor,
            "hostname": hostname or "—",
            "tipo":     tipo,
            "puertos":  ports,
            "riesgo":   riesgo,
            "ts":       datetime.now().isoformat(timespec="seconds"),
        }
        if callback:
            callback(rec)
        return rec

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        resultados = list(ex.map(enriquecer, sorted(activos_ips,
                          key=lambda ip: tuple(int(x) for x in ip.split(".")))))

    return resultados
