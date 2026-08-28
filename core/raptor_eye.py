"""
core/raptor_eye.py — Motor de Threat Hunting avanzado para Visor v5.0.
Jasol Group · Ing. Jeisson Alberto Sarmiento · Saravena, Arauca, Colombia

Mejoras v5.0:
  - Más vectores de amenaza (35 total)
  - Clasificación de riesgo por severidad (CRITICAL / HIGH / MEDIUM / LOW)
  - Detección de servicios con banners (fingerprinting)
  - Escaneo de red completa con barra de progreso
  - Recomendaciones de remediación automáticas
"""

import socket
import concurrent.futures
import ipaddress
import itertools
import re
from core.red import hacer_ping

# Evita crear listas o tareas de red ilimitadas desde una entrada de menú/API.
MAX_THREAT_HOSTS = 4096

# ── Vectores de amenaza ampliados ──────────────────────────────────────────
THREAT_VECTORS = {
    # CRITICAL
    "TELNET":       {"port": 23,    "risk": "CRITICAL", "desc": "Telnet sin cifrar (credenciales en texto plano).",
                     "fix": "Deshabilitar Telnet. Usar SSH."},
    "RDP_EXPOSED":  {"port": 3389,  "risk": "CRITICAL", "desc": "RDP expuesto (vector principal de Ransomware).",
                     "fix": "Restringir RDP a VPN interna. Activar NLA."},
    "SMB_VULN":     {"port": 445,   "risk": "CRITICAL", "desc": "SMB abierto (EternalBlue / WannaCry).",
                     "fix": "Bloquear puerto 445 en firewall perimetral."},
    "NETBIOS":      {"port": 139,   "risk": "HIGH",     "desc": "NetBIOS expuesto (reconocimiento de red).",
                     "fix": "Deshabilitar NetBIOS sobre TCP/IP."},
    "MSSQL":        {"port": 1433,  "risk": "CRITICAL", "desc": "SQL Server expuesto (fuerza bruta / SQLi).",
                     "fix": "Restringir acceso a SQL Server a red interna."},
    # HIGH
    "VNC_OPEN":     {"port": 5900,  "risk": "HIGH",     "desc": "VNC sin cifrar detectado.",
                     "fix": "Usar VNC con túnel SSH o reemplazar por VPN."},
    "ADB_DEBUG":    {"port": 5555,  "risk": "HIGH",     "desc": "Android Debug Bridge expuesto.",
                     "fix": "Deshabilitar ADB en producción. adb kill-server"},
    "DOCKER_API":   {"port": 2375,  "risk": "CRITICAL", "desc": "Docker API sin cifrar (acceso root al sistema).",
                     "fix": "Nunca exponer Docker API. Usar socket Unix local."},
    "ETCD":         {"port": 2379,  "risk": "HIGH",     "desc": "ETCD expuesto (datos de config Kubernetes).",
                     "fix": "Restringir ETCD a red interna con mTLS."},
    "K8S_API":      {"port": 6443,  "risk": "HIGH",     "desc": "API de Kubernetes potencialmente expuesta.",
                     "fix": "Restringir acceso API K8s con RBAC y red privada."},
    "REDIS":        {"port": 6379,  "risk": "HIGH",     "desc": "Redis sin autenticación (RCE potencial).",
                     "fix": "Activar requirepass en Redis. No exponer públicamente."},
    "MONGODB":      {"port": 27017, "risk": "HIGH",     "desc": "MongoDB sin auth expuesta.",
                     "fix": "Activar autenticación en MongoDB. Restringir bind IP."},
    # MEDIUM
    "DB_MYSQL":     {"port": 3306,  "risk": "MEDIUM",   "desc": "MySQL/MariaDB expuesta (fuerza bruta).",
                     "fix": "Bind a 127.0.0.1. Usar usuario específico con permisos mínimos."},
    "DB_PGSQL":     {"port": 5432,  "risk": "MEDIUM",   "desc": "PostgreSQL expuesta.",
                     "fix": "Configurar pg_hba.conf para restringir acceso por red."},
    "FTP_PLAIN":    {"port": 21,    "risk": "MEDIUM",   "desc": "FTP sin cifrar (credenciales expuestas).",
                     "fix": "Migrar a SFTP (puerto 22) o FTPS."},
    "SMTP_OPEN":    {"port": 25,    "risk": "MEDIUM",   "desc": "SMTP abierto (relay abierto potencial).",
                     "fix": "Deshabilitar relay abierto. Usar SMTP autenticado (587)."},
    "SNMP_LEGACY":  {"port": 161,   "risk": "MEDIUM",   "desc": "SNMP v1/v2 (community string en texto plano).",
                     "fix": "Migrar a SNMPv3 con autenticación y cifrado."},
    "ELASTICSEARCH":{"port": 9200,  "risk": "HIGH",     "desc": "Elasticsearch sin auth expuesto.",
                     "fix": "Activar X-Pack Security. No exponer al exterior."},
    "MEMCACHED":    {"port": 11211, "risk": "MEDIUM",   "desc": "Memcached expuesto (amplificación DDoS UDP).",
                     "fix": "Bind a localhost. Bloquear UDP 11211 en firewall."},
    "WINRM":        {"port": 5985,  "risk": "HIGH",     "desc": "WinRM expuesto (lateral movement).",
                     "fix": "Restringir WinRM a administradores autorizados vía GPO."},
    "ROUTEROS_WWW": {"port": 80,    "risk": "LOW",      "desc": "RouterOS Webfig sin HTTPS.",
                     "fix": "Deshabilitar HTTP en MikroTik. Usar solo HTTPS (443) o Winbox."},
    "WINBOX":       {"port": 8291,  "risk": "LOW",      "desc": "Winbox expuesto (descubrimiento de versión).",
                     "fix": "Restringir acceso Winbox a IPs de administración."},
    "PROXMOX_WEB":  {"port": 8006,  "risk": "LOW",      "desc": "Proxmox VE accesible.",
                     "fix": "Restringir acceso Proxmox a red de gestión. Activar 2FA."},
    "JENKINS":      {"port": 8080,  "risk": "MEDIUM",   "desc": "Jenkins / servicio HTTP no identificado.",
                     "fix": "Verificar autenticación activa. Actualizar a versión reciente."},
    "LDAP":         {"port": 389,   "risk": "HIGH",     "desc": "LDAP sin cifrar expuesto.",
                     "fix": "Usar LDAPS (636) o StartTLS. Restringir a red interna."},
    "RSYNC":        {"port": 873,   "risk": "MEDIUM",   "desc": "rsync expuesto (posible exfiltración de datos).",
                     "fix": "Requerir autenticación en rsync. Restringir por IP."},
    "NFS":          {"port": 2049,  "risk": "HIGH",     "desc": "NFS expuesto (montaje no autorizado de shares).",
                     "fix": "Restringir NFS exports a IPs de confianza."},
    "CUPS":         {"port": 631,   "risk": "MEDIUM",   "desc": "CUPS (impresoras) accesible en red.",
                     "fix": "Restringir acceso CUPS a red interna."},
}

RIESGO_COLOR = {
    "CRITICAL": "🔴",
    "HIGH":     "🟠",
    "MEDIUM":   "🟡",
    "LOW":      "🔵",
}

RIESGO_ORDEN = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _grab_banner(ip: str, port: int, timeout: float = 1.0) -> str:
    """Intenta obtener el banner de un servicio sin dejar sockets abiertos."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((ip, port))
            # Enviar petición básica para forzar banner
            if port in (80, 8080, 8006):
                s.send(b"GET / HTTP/1.0\r\nHost: " + ip.encode() + b"\r\n\r\n")
            elif port == 21:
                pass  # FTP envía banner solo
            banner = s.recv(256).decode(errors="ignore").strip()
            return banner[:80] if banner else ""
    except (OSError, UnicodeError):
        return ""


def hunt_vulnerabilities(target: str, grab_banners: bool = True) -> list:
    """
    Busca vectores de ataque específicos en un host.
    Retorna lista de hallazgos ordenados por severidad.
    """
    findings = []

    def check_threat(name_info):
        name, info = name_info
        port = info["port"]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.8)
                if s.connect_ex((target, port)) == 0:
                    banner = _grab_banner(target, port) if grab_banners else ""
                    return {
                        "nombre": name,
                        "port":   port,
                        "risk":   info["risk"],
                        "icon":   RIESGO_COLOR.get(info["risk"], "⚪"),
                        "desc":   info["desc"],
                        "fix":    info["fix"],
                        "banner": banner,
                    }
        except OSError:
            pass
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(THREAT_VECTORS)) as ex:
        results = list(ex.map(check_threat, THREAT_VECTORS.items()))

    findings = [r for r in results if r]
    # Ordenar por severidad
    findings.sort(key=lambda x: RIESGO_ORDEN.get(x["risk"], 99))
    return findings


def _threat_scan_hosts(network_prefix: str, max_hosts: int) -> list[str]:
    """Valida y materializa una cantidad acotada de hosts IPv4."""
    if isinstance(max_hosts, bool):
        raise ValueError("max_hosts debe ser un entero")
    try:
        limite = int(max_hosts)
    except (TypeError, ValueError):
        raise ValueError("max_hosts debe ser un entero") from None
    if limite < 0:
        raise ValueError("max_hosts no puede ser negativo")
    if limite > MAX_THREAT_HOSTS:
        raise ValueError(
            f"escaneo de amenazas demasiado grande: {limite} hosts "
            f"(máximo {MAX_THREAT_HOSTS})"
        )
    if limite == 0:
        return []

    texto = str(network_prefix or "").strip()
    try:
        if "/" in texto:
            red = ipaddress.ip_network(texto, strict=False)
            if red.version != 4:
                raise ValueError("el escaneo de amenazas solo admite IPv4")
            return [str(ip) for ip in itertools.islice(red.hosts(), limite)]

        partes = texto.split(".")
        if len(partes) != 3:
            raise ValueError("usa un prefijo IPv4 como 192.168.1")
        if any(not parte.isdigit() or not 0 <= int(parte) <= 255 for parte in partes):
            raise ValueError("prefijo IPv4 inválido")
        return [f"{texto}.{indice}" for indice in range(1, min(limite, 254) + 1)]
    except (TypeError, ValueError):
        raise ValueError("prefijo de red IPv4 inválido") from None


def scan_network_threats(network_prefix: str, max_hosts: int = 50, callback=None) -> list:
    """
    Escanea un segmento de red buscando los hosts más vulnerables.

    ``network_prefix`` acepta un prefijo de tres octetos (``192.168.1``)
    o una red CIDR IPv4. La cantidad de objetivos siempre está limitada.
    """
    report = []
    ips_a_probar = _threat_scan_hosts(network_prefix, max_hosts)

    def escanear_host(ip):
        up, _ = hacer_ping(ip)
        if not up:
            return None
        vulns = hunt_vulnerabilities(ip, grab_banners=False)
        if vulns:
            entry = {"ip": ip, "threats": vulns,
                     "criticos": sum(1 for v in vulns if v["risk"] == "CRITICAL")}
            if callback:
                callback(entry)
            return entry
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        for res in ex.map(escanear_host, ips_a_probar):
            if res:
                report.append(res)

    # Ordenar por cantidad de críticos
    report.sort(key=lambda x: -x["criticos"])
    return report


def generar_resumen_riesgo(findings: list) -> dict:
    """Genera un resumen estadístico de hallazgos para el dashboard."""
    conteo = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in findings:
        nivel = f.get("risk", "LOW")
        conteo[nivel] = conteo.get(nivel, 0) + 1
    
    score = (conteo["CRITICAL"] * 40 + conteo["HIGH"] * 15 +
             conteo["MEDIUM"] * 5  + conteo["LOW"] * 1)
    
    if score == 0:          nivel_global = ("✅ SEGURO",   "green")
    elif score < 20:        nivel_global = ("🟡 RIESGO BAJO",    "yellow")
    elif score < 60:        nivel_global = ("🟠 RIESGO MEDIO",   "orange")
    elif score < 120:       nivel_global = ("🔴 RIESGO ALTO",    "red")
    else:                   nivel_global = ("☠️  CRÍTICO",       "magenta")

    return {
        "conteo":      conteo,
        "score":       score,
        "nivel":       nivel_global[0],
        "color":       nivel_global[1],
        "total":       sum(conteo.values()),
    }
