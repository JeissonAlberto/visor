"""
core/health.py — Análisis de calidad de red (Jitter, Packet Loss).
Parte de Visor v2.7 NOC Edition.
"""

import time
import statistics
from core.red import hacer_ping

def analizar_calidad(target: str, ráfagas: int = 10):
    """Analiza Jitter y Pérdida de paquetes de un objetivo."""
    latencias = []
    perdidos = 0
    
    print(f"\n  {target} --> Realizando ráfaga de {ráfagas} paquetes...")
    
    for i in range(ráfagas):
        up, lat = hacer_ping(target)
        
        if up:
            latencias.append(lat if lat is not None else 0)
        else:
            perdidos += 1
        time.sleep(0.1) # Pequeña pausa entre ráfagas

    if not latencias:
        return {
            "estado": "OFFLINE",
            "loss": 100,
            "jitter": 0,
            "avg": 0,
            "calidad": "NULA"
        }

    # Cálculos
    avg_lat = sum(latencias) / len(latencias)
    packet_loss = (perdidos / ráfagas) * 100
    
    # Jitter: Desviación estándar de las latencias
    jitter = statistics.pstdev(latencias) if len(latencias) > 1 else 0
    
    # Clasificación de Calidad
    if packet_loss > 10 or jitter > 30:
        calidad = "CRÍTICA"
    elif packet_loss > 2 or jitter > 15:
        calidad = "INESTABLE"
    elif avg_lat > 100:
        calidad = "LATENCIA ALTA"
    else:
        calidad = "EXCELENTE"

    return {
        "estado": "ONLINE",
        "loss": packet_loss,
        "jitter": round(jitter, 2),
        "avg": round(avg_lat, 2),
        "max": round(max(latencias), 2),
        "min": round(min(latencias), 2),
        "calidad": calidad
    }
