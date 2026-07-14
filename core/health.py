"""
core/health.py — Diagnóstico avanzado de calidad de red para Visor v5.1.
Jasol Group · Ing. Jeisson Alberto Sarmiento · Saravena, Arauca, Colombia

Mejoras v5.1:
  - MOS Score (Mean Opinion Score) para VoIP/Video
  - MTU Path Discovery
  - Traceroute integrado con latencia por salto
  - Análisis comparativo: LAN vs. Gateway vs. Internet
  - Detección automática de problemas (congestion, QoS, bufferbloat)
"""

import time
import statistics
import subprocess
import platform
import socket
import re
from datetime import datetime
from core.red import hacer_ping


# ── Constantes ────────────────────────────────────────────────────────────
TARGETS_INTERNET = [
    ("Google DNS",    "8.8.8.8"),
    ("Cloudflare",    "1.1.1.1"),
    ("OpenDNS",       "208.67.222.222"),
]

UMBRALES = {
    "lat_excelente":  30,    # ms
    "lat_buena":      80,    # ms
    "lat_aceptable":  150,   # ms
    "jitter_ok":      10,    # ms
    "jitter_voip":    20,    # ms jitter máximo para VoIP decente
    "loss_ok":        1.0,   # % pérdida aceptable
    "loss_critica":   5.0,   # % pérdida crítica
}


# ── Análisis básico (mejorado) ────────────────────────────────────────────

def analizar_calidad(target: str, rafagas: int = 20) -> dict:
    """
    Análisis avanzado de calidad: latencia, jitter, pérdida y MOS Score.
    """
    latencias = []
    perdidos = 0

    for _ in range(rafagas):
        up, lat = hacer_ping(target)
        if up and lat is not None:
            latencias.append(lat)
        else:
            perdidos += 1
        time.sleep(0.05)

    if not latencias:
        return {
            "estado": "OFFLINE", "loss": 100, "jitter": 0,
            "avg": 0, "max": 0, "min": 0, "calidad": "NULA",
            "mos": 0, "calidad_voip": "INUTILIZABLE",
        }

    avg_lat     = sum(latencias) / len(latencias)
    packet_loss = (perdidos / rafagas) * 100
    jitter      = statistics.pstdev(latencias) if len(latencias) > 1 else 0
    lat_max     = max(latencias)
    lat_min     = min(latencias)

    # ── MOS Score (E-Model simplificado) ─────────────────────────────────
    # Penalización por latencia (R Factor)
    r = 93.2
    if avg_lat > 160:
        r -= (avg_lat - 160) * 0.1 + (avg_lat - 160) ** 1.5 / 1e6
    r -= jitter * 0.5
    r -= packet_loss * 2.5
    r = max(0, min(100, r))

    if r >= 90:    mos = 4.5; calidad_voip = "EXCELENTE"
    elif r >= 80:  mos = 4.0; calidad_voip = "BUENA"
    elif r >= 70:  mos = 3.5; calidad_voip = "ACEPTABLE"
    elif r >= 60:  mos = 3.0; calidad_voip = "DEGRADADA"
    elif r >= 50:  mos = 2.5; calidad_voip = "MALA"
    else:          mos = 1.0; calidad_voip = "INUTILIZABLE"

    # ── Clasificación general ─────────────────────────────────────────────
    if packet_loss >= UMBRALES["loss_critica"] or jitter > 50:
        calidad = "CRÍTICA"
    elif packet_loss >= UMBRALES["loss_ok"] or jitter > UMBRALES["jitter_voip"]:
        calidad = "INESTABLE"
    elif avg_lat > UMBRALES["lat_aceptable"]:
        calidad = "LATENCIA ALTA"
    elif avg_lat > UMBRALES["lat_buena"]:
        calidad = "ACEPTABLE"
    else:
        calidad = "EXCELENTE"

    # ── Diagnóstico automático ────────────────────────────────────────────
    diagnosticos = []
    if jitter > lat_min * 0.5 and avg_lat > 50:
        diagnosticos.append("🟠 Posible Bufferbloat detectado (jitter alto relativo a latencia base)")
    if packet_loss > 0 and jitter < 5:
        diagnosticos.append("🔴 Pérdida de paquetes sin jitter: probable fallo de hardware o enlace")
    if packet_loss > 0 and jitter > 10:
        diagnosticos.append("🟠 Pérdida + jitter: posible congestión en enlace intermedio")
    if avg_lat > 200:
        diagnosticos.append("🔴 Latencia muy alta: revisar rutas BGP o enlace satelital")
    if not diagnosticos:
        diagnosticos.append("✅ Sin anomalías detectadas en el análisis de calidad")

    return {
        "target":        target,
        "estado":        "ONLINE",
        "rafagas":       rafagas,
        "recibidos":     len(latencias),
        "perdidos":      perdidos,
        "loss":          round(packet_loss, 2),
        "avg":           round(avg_lat, 2),
        "min":           round(lat_min, 2),
        "max":           round(lat_max, 2),
        "jitter":        round(jitter, 2),
        "calidad":       calidad,
        "mos":           round(mos, 2),
        "calidad_voip":  calidad_voip,
        "diagnosticos":  diagnosticos,
        "ts":            datetime.now().isoformat(timespec="seconds"),
    }


# ── Traceroute ────────────────────────────────────────────────────────────

def traceroute(target: str, max_hops: int = 20) -> list:
    """
    Ejecuta un traceroute y retorna saltos con IP, hostname y latencia.
    """
    sistema = platform.system().lower()
    saltos = []

    if sistema == "windows":
        cmd = ["tracert", "-d", "-w", "1000", "-h", str(max_hops), target]
    else:
        cmd = ["traceroute", "-n", "-m", str(max_hops), "-w", "2", target]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        lineas = r.stdout.splitlines()

        for linea in lineas:
            # Windows: "  1    <1 ms    <1 ms    <1 ms  192.168.1.1"
            # Linux:   "  1  192.168.1.1  0.543 ms  0.421 ms  0.398 ms"
            match = re.search(
                r'^\s*(\d+)\s+(?:(<?\d+)\s*ms.*?(<?\d+)\s*ms.*?(<?\d+)\s*ms\s+)?([\d.]+)',
                linea
            )
            if match:
                hop_num = int(match.group(1))
                ip_hop  = match.group(5) or "*"
                try:
                    lats = [float(x.replace('<','')) for x in re.findall(r'(\d+)\s*ms', linea)]
                    lat_avg = round(sum(lats) / len(lats), 1) if lats else None
                except:
                    lat_avg = None

                hostname = None
                try:
                    if ip_hop and ip_hop != "*":
                        hostname = socket.gethostbyaddr(ip_hop)[0]
                except:
                    pass

                saltos.append({
                    "hop":      hop_num,
                    "ip":       ip_hop,
                    "hostname": hostname,
                    "lat_ms":   lat_avg,
                    "timeout":  "*" in linea and lat_avg is None,
                })
    except Exception as e:
        saltos.append({"hop": 0, "ip": "error", "hostname": str(e), "lat_ms": None, "timeout": True})

    return saltos


# ── Análisis multi-punto (LAN + GW + Internet) ───────────────────────────

def analizar_completo(gateway: str = None) -> dict:
    """
    Análisis de 3 capas: LAN (gateway) → ISP → Internet.
    Detecta en qué punto está el problema.
    """
    from core.red import detectar_gateway

    if not gateway:
        gateway = detectar_gateway() or "192.168.1.1"

    resultados = {}

    # Capa 1: Gateway local
    print(f"  🔍 Analizando gateway local ({gateway})...")
    resultados["lan"] = analizar_calidad(gateway, rafagas=15)
    resultados["lan"]["label"] = "Gateway LAN"

    # Capa 2: DNS del ISP (si el GW responde bien)
    print(f"  🔍 Analizando salida a Internet (8.8.8.8)...")
    resultados["internet"] = analizar_calidad("8.8.8.8", rafagas=15)
    resultados["internet"]["label"] = "Internet (Google DNS)"

    # Capa 3: Cloudflare como segundo punto
    print(f"  🔍 Verificando Cloudflare (1.1.1.1)...")
    resultados["cloudflare"] = analizar_calidad("1.1.1.1", rafagas=10)
    resultados["cloudflare"]["label"] = "Internet (Cloudflare)"

    # ── Diagnóstico de dónde está el problema ────────────────────────────
    diagnostico_global = ""
    lan_ok  = resultados["lan"]["calidad"] in ("EXCELENTE", "ACEPTABLE")
    inet_ok = resultados["internet"]["calidad"] in ("EXCELENTE", "ACEPTABLE")

    if lan_ok and inet_ok:
        diagnostico_global = "✅ Red saludable. LAN y conexión a Internet operando correctamente."
    elif not lan_ok and not inet_ok:
        diagnostico_global = "🔴 Problema en LAN o enlace del gateway. Revisar router/OLT/uplink."
    elif lan_ok and not inet_ok:
        diagnostico_global = "🟠 LAN OK pero Internet degradado. Problema en ISP upstream o fibra."
    else:
        diagnostico_global = "🟡 Gateway con problemas pero Internet intermitente. Revisar equipo local."

    resultados["diagnostico_global"] = diagnostico_global
    resultados["gateway"] = gateway
    resultados["ts"] = datetime.now().isoformat(timespec="seconds")

    return resultados
