"""
core/raptor_eye.py — Motor de Threat Hunting avanzado para Visor v2.8.
Inspirado en RAPTOR (Offensive/Defensive AI agent).
"""

import socket
import concurrent.futures
from core.red import hacer_ping

# Firmas de amenazas comunes y vectores de ataque
THREAT_VECTORS = {
    "RDP_EXPOSED": {"port": 3389, "risk": "CRITICAL", "desc": "Escritorio remoto expuesto (Vector principal de Ransomware)."},
    "SMB_VULN":    {"port": 445,  "risk": "HIGH",     "desc": "SMB abierto (Vulnerable a EternalBlue / WannaCry)."},
    "TELNET_OLD":  {"port": 23,   "risk": "CRITICAL", "desc": "Protocolo inseguro de administración remota."},
    "ADB_DEBUG":   {"port": 5555, "risk": "HIGH",     "desc": "Android Debug Bridge expuesto (Control total de dispositivos)."},
    "VNC_OPEN":    {"port": 5900, "risk": "HIGH",     "desc": "VNC sin cifrar detectado."},
    "DB_EXPOSED":  {"port": 3306, "risk": "MEDIUM",   "desc": "Base de Datos MySQL expuesta."},
}

def hunt_vulnerabilities(target: str):
    """Busca vectores de ataque específicos en un host."""
    findings = []
    
    def check_port(port_info):
        p_num = port_info["port"]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                if s.connect_ex((target, p_num)) == 0:
                    return port_info
        except:
            pass
        return None

    # Escaneo paralelo de vectores de amenaza
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(THREAT_VECTORS)) as executor:
        results = list(executor.map(check_port, THREAT_VECTORS.values()))
        findings = [r for r in results if r]

    return findings

def scan_network_threats(network_prefix: str):
    """Escanea un segmento de red buscando los hosts más vulnerables."""
    report = []
    # Escaneamos solo los primeros 30 hosts para velocidad en este demo
    for i in range(1, 31):
        ip = f"{network_prefix}.{i}"
        up, _ = hacer_ping(ip)
        if up:
            vulns = hunt_vulnerabilities(ip)
            if vulns:
                report.append({"ip": ip, "threats": vulns})
    return report
