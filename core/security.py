"""
core/security.py — Motor de Auditoría de Puertos y Servicios.
Inspirado en METATRON para Visor v2.5.
"""

import socket
import concurrent.futures
import time
from datetime import datetime

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
    except:
        pass
    return None

def auditoria_completa(ip: str, rango_puertos: list = None) -> dict:
    """Realiza un escaneo de seguridad profundo a una IP."""
    if not rango_puertos:
        # Escaneamos los puertos comunes por defecto
        rango_puertos = list(PUERTOS_COMUNES.keys())

    resultados = []
    t_inicio = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futuros = [executor.submit(escanear_puerto, ip, p) for p in rango_puertos]
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
