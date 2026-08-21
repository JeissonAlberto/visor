"""
core/security.py — Motor de Auditoría de Puertos y Servicios.
Inspirado en METATRON para Visor v2.5.
"""

import socket
import concurrent.futures
import time
from datetime import datetime

# Evita que una entrada de configuración cree miles de tareas de red.
MAX_AUDIT_PORTS = 1024

# Puertos comunes y su nivel de riesgo
PUERTOS_COMUNES = {
    21:    {"servicio": "FTP",       "riesgo": "ALTO",   "desc": "Transferencia de archivos sin cifrar."},
    22:    {"servicio": "SSH",       "riesgo": "MEDIO",  "desc": "Acceso remoto seguro."},
    23:    {"servicio": "Telnet",    "riesgo": "CRÍTICO","desc": "Acceso remoto obsoleto y peligroso."},
    25:    {"servicio": "SMTP",      "riesgo": "MEDIO",  "desc": "Servidor de correo."},
    53:    {"servicio": "DNS",       "riesgo": "BAJO",   "desc": "Resolución de nombres."},
    80:    {"servicio": "HTTP",      "riesgo": "MEDIO",  "desc": "Servidor web (no cifrado)."},
    139:   {"servicio": "NetBIOS",   "riesgo": "ALTO",   "desc": "Compartición de archivos Windows."},
    443:   {"servicio": "HTTPS",     "riesgo": "BAJO",   "desc": "Servidor web seguro."},
    445:   {"servicio": "SMB",       "riesgo": "ALTO",   "desc": "Compartición de archivos (objetivo de ransomware)."},
    3306:  {"servicio": "MySQL",     "riesgo": "ALTO",   "desc": "Base de datos expuesta."},
    3389:  {"servicio": "RDP",       "riesgo": "ALTO",   "desc": "Escritorio remoto (objetivo frecuente de ataques)."},
    8080:  {"servicio": "HTTP-Proxy","riesgo": "MEDIO",  "desc": "Puerto alternativo para web."},
}

def escanear_puerto(ip: str, puerto: int, timeout: float = 0.5) -> dict | None:
    """Intenta conectar a un puerto específico."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            resultado = s.connect_ex((ip, puerto))
            if resultado == 0:
                info = PUERTOS_COMUNES.get(puerto, {"servicio": "Desconocido", "riesgo": "INCIERTO", "desc": "Servicio no identificado."})
                return {
                    "puerto": puerto,
                    "servicio": info["servicio"],
                    "riesgo": info["riesgo"],
                    "descripcion": info["desc"]
                }
    except (OSError, TypeError, ValueError):
        pass
    return None


def _normalizar_puertos(rango_puertos) -> list[int]:
    """Filtra puertos TCP válidos, únicos y acotados para una auditoría."""
    try:
        candidatos = list(rango_puertos)
    except TypeError:
        return []

    puertos = []
    vistos = set()
    for candidato in candidatos:
        if isinstance(candidato, bool):
            continue
        try:
            puerto = int(candidato)
        except (TypeError, ValueError):
            continue
        if not 1 <= puerto <= 65535 or puerto in vistos:
            continue
        vistos.add(puerto)
        puertos.append(puerto)
        if len(puertos) >= MAX_AUDIT_PORTS:
            break
    return puertos


def auditoria_completa(ip: str, rango_puertos: list = None) -> dict:
    """Realiza un escaneo de seguridad profundo a una IP.

    Las entradas externas se validan y limitan a ``MAX_AUDIT_PORTS`` para
    evitar agotar memoria o crear una cantidad accidental de conexiones.
    """
    if not rango_puertos:
        # Escaneamos los puertos comunes por defecto
        rango_puertos = list(PUERTOS_COMUNES.keys())
    else:
        rango_puertos = _normalizar_puertos(rango_puertos)

    resultados = []
    t_inicio = time.time()

    if rango_puertos:
        worker_count = min(50, len(rango_puertos))
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            # Procesar por lotes mantiene acotadas las tareas pendientes; usar
            # submit() sobre toda la lista puede consumir memoria en auditorías
            # configuradas con cientos de puertos.
            for inicio in range(0, len(rango_puertos), worker_count):
                lote = rango_puertos[inicio:inicio + worker_count]
                futuros = [executor.submit(escanear_puerto, ip, p) for p in lote]
                for f in concurrent.futures.as_completed(futuros):
                    res = f.result()
                    if res:
                        resultados.append(res)

    t_total = round(time.time() - t_inicio, 2)
    
    # Calcular nivel de riesgo general del host
    riesgos = [r["riesgo"] for r in resultados]
    riesgo_max = "BAJO"
    if "CRÍTICO" in riesgos: riesgo_max = "CRÍTICO"
    elif "ALTO" in riesgos: riesgo_max = "ALTO"
    elif "MEDIO" in riesgos: riesgo_max = "MEDIO"

    return {
        "ip": ip,
        "puertos_abiertos": sorted(resultados, key=lambda x: x["puerto"]),
        "total_abiertos": len(resultados),
        "tiempo_escaneo": t_total,
        "riesgo_general": riesgo_max,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
