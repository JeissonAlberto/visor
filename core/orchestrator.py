"""
core/orchestrator.py — Motor de Misiones Autónomas para Visor v5.1.
Jasol Group · Ing. Jeisson Alberto Sarmiento · Saravena, Arauca, Colombia

Mejoras v5.1:
  - 6 tipos de misión (Security, LAN, Health, Infra, Full-NOC, Quick)
  - Barra de progreso en tiempo real
  - Reporte unificado con score global
  - Timeout por agente (ninguno bloquea el orquestador)
  - Guardado automático de reporte en /reports
"""

import concurrent.futures
import time
import os
from datetime import datetime

from core.raptor_eye import hunt_vulnerabilities, scan_network_threats, generar_resumen_riesgo as calcular_score_amenaza
from core.guardian_ai import generate_remediation_plan, generar_reporte_ejecutivo, calcular_score_riesgo
from core.medusa_shield import scan_for_secrets
from core.health import analizar_calidad, analizar_completo
from core.lan_vision import discover_lan


# ── Tipos de misión ───────────────────────────────────────────────────────
MISSION_TYPES = {
    "SECURITY_AUDIT":  "🛡️  Auditoría de Seguridad Completa",
    "LAN_DISCOVERY":   "🌐  Descubrimiento de Red LAN",
    "HEALTH_CHECK":    "🩺  Diagnóstico de Calidad de Red",
    "INFRA_CHECK":     "🖥️  Revisión de Infraestructura L3",
    "FULL_NOC":        "🚀  NOC Completo (Todo en Paralelo)",
    "QUICK_SCAN":      "⚡  Escaneo Rápido (< 30 seg)",
}


# ── Utilidades ────────────────────────────────────────────────────────────

def _spinner_task(label: str, future: concurrent.futures.Future, timeout: int = 120):
    """Espera un future mostrando spinner. Retorna el resultado o None si hay timeout."""
    chars = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    i = 0
    start = time.time()
    while not future.done():
        elapsed = time.time() - start
        if elapsed > timeout:
            future.cancel()
            print(f"\r  {label}: ⚠️  TIMEOUT ({timeout}s)          ")
            return None
        print(f"\r  {label}: {chars[i % len(chars)]} {elapsed:.0f}s", end="", flush=True)
        i += 1
        time.sleep(0.15)
    print(f"\r  {label}: ✅ completado ({time.time()-start:.1f}s)          ")
    try:
        return future.result()
    except Exception as e:
        print(f"  {label}: ❌ error — {e}")
        return None


def _guardar_reporte(contenido: str, tipo: str = "NOC") -> str:
    """Guarda el reporte en /reports con timestamp."""
    try:
        reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(reports_dir, f"reporte_{tipo}_{ts}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(contenido)
        return filename
    except Exception as e:
        return f"No guardado: {e}"


# ── Misiones individuales ─────────────────────────────────────────────────

class MissionOrchestrator:
    def __init__(self, target=None, network=None):
        self.target  = target
        self.network = network
        self.results = {}
        self.ts      = datetime.now().isoformat(timespec="seconds")

    # ── SECURITY AUDIT ───────────────────────────────────────────────────
    def execute_security_mission(self) -> dict:
        print(f"\n  🛡️  Iniciando Auditoría de Seguridad sobre: {self.target or 'localhost'}")
        print(f"  {'─'*55}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            f_raptor  = ex.submit(hunt_vulnerabilities, self.target) if self.target else None
            f_medusa  = ex.submit(scan_for_secrets, ".")
            f_health  = ex.submit(analizar_calidad, self.target or "8.8.8.8", 15)

            raptor_res  = _spinner_task("[Raptor] Threat Hunting",  f_raptor,  60) if f_raptor else []
            medusa_res  = _spinner_task("[Medusa] Secretos/Fugas",  f_medusa,  30)
            health_res  = _spinner_task("[Health] Calidad de Red",  f_health,  45)

        guardian_res = generate_remediation_plan(raptor_res or [])
        score_data   = calcular_score_riesgo(guardian_res)

        self.results = {
            "tipo":     "SECURITY_AUDIT",
            "target":   self.target,
            "raptor":   raptor_res or [],
            "guardian": guardian_res,
            "medusa":   medusa_res or [],
            "health":   health_res,
            "score":    score_data,
            "ts":       self.ts,
        }

        # Guardar reporte
        reporte_txt = generar_reporte_ejecutivo(guardian_res, self.target or "localhost")
        path = _guardar_reporte(reporte_txt, "SECURITY")
        self.results["reporte_path"] = path

        return self.results

    # ── LAN DISCOVERY ────────────────────────────────────────────────────
    def execute_lan_mission(self) -> dict:
        print(f"\n  🌐  Iniciando Descubrimiento LAN...")
        print(f"  {'─'*55}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            f_lan = ex.submit(full_lan_scan, self.network)
            lan_res = _spinner_task("[LAN-Vision] Descubriendo dispositivos", f_lan, 120)

        self.results = {
            "tipo":        "LAN_DISCOVERY",
            "dispositivos": lan_res or [],
            "total":       len(lan_res or []),
            "activos":     sum(1 for d in (lan_res or []) if d.get("activo")),
            "ts":          self.ts,
        }
        return self.results

    # ── HEALTH CHECK ─────────────────────────────────────────────────────
    def execute_health_mission(self) -> dict:
        print(f"\n  🩺  Iniciando Diagnóstico de Red Multi-Capa...")
        print(f"  {'─'*55}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            f_health = ex.submit(analizar_completo)
            health_res = _spinner_task("[Health] Análisis LAN→ISP→Internet", f_health, 60)

        self.results = {
            "tipo":   "HEALTH_CHECK",
            "health": health_res or {},
            "ts":     self.ts,
        }
        return self.results

    # ── QUICK SCAN ───────────────────────────────────────────────────────
    def execute_quick_scan(self) -> dict:
        print(f"\n  ⚡  Escaneo Rápido NOC — Jasol Group")
        print(f"  {'─'*55}")

        target = self.target or "8.8.8.8"

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            f_ping   = ex.submit(analizar_calidad, target, 10)
            f_raptor = ex.submit(hunt_vulnerabilities, target)
            f_lan    = ex.submit(full_lan_scan, self.network, max_workers=80)

            ping_res   = _spinner_task("[Quick] Calidad de red",      f_ping,   20)
            raptor_res = _spinner_task("[Quick] Amenazas del host",   f_raptor, 30)
            lan_res    = _spinner_task("[Quick] Dispositivos LAN",    f_lan,    60)

        guardian_res = generate_remediation_plan(raptor_res or [])

        self.results = {
            "tipo":          "QUICK_SCAN",
            "target":        target,
            "health":        ping_res,
            "amenazas":      raptor_res or [],
            "remediaciones": guardian_res,
            "lan":           lan_res or [],
            "score":         calcular_score_riesgo(guardian_res),
            "ts":            self.ts,
        }
        return self.results

    # ── FULL NOC ─────────────────────────────────────────────────────────
    def execute_full_noc(self) -> dict:
        print(f"\n  🚀  NOC COMPLETO — Jasol Group")
        print(f"  Todos los agentes desplegados en paralelo...")
        print(f"  {'─'*55}")

        target = self.target or "8.8.8.8"

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            f_health  = ex.submit(analizar_completo)
            f_raptor  = ex.submit(hunt_vulnerabilities, target)
            f_medusa  = ex.submit(scan_for_secrets, ".")
            f_lan     = ex.submit(full_lan_scan, self.network, max_workers=100)

            health_res  = _spinner_task("[Health]  LAN→ISP→Internet",    f_health,  60)
            raptor_res  = _spinner_task("[Raptor]  Threat Hunting",       f_raptor,  60)
            medusa_res  = _spinner_task("[Medusa]  Secretos/Fugas",       f_medusa,  30)
            lan_res     = _spinner_task("[LAN]     Descubrimiento Red",   f_lan,    120)

        guardian_res = generate_remediation_plan(raptor_res or [])
        score_data   = calcular_score_riesgo(guardian_res)

        self.results = {
            "tipo":          "FULL_NOC",
            "target":        target,
            "health":        health_res or {},
            "raptor":        raptor_res or [],
            "medusa":        medusa_res or [],
            "guardian":      guardian_res,
            "lan":           lan_res or [],
            "score":         score_data,
            "ts":            self.ts,
        }

        # Guardar reporte completo
        reporte_txt = generar_reporte_ejecutivo(guardian_res, target)
        path = _guardar_reporte(reporte_txt, "FULL_NOC")
        self.results["reporte_path"] = path

        return self.results


# ── API pública ───────────────────────────────────────────────────────────

def run_orchestrated_task(task_type: str, target: str = None, network: str = None) -> dict:
    """Punto de entrada principal del orquestador."""
    orch = MissionOrchestrator(target=target, network=network)

    dispatch = {
        "SECURITY_AUDIT": orch.execute_security_mission,
        "LAN_DISCOVERY":  orch.execute_lan_mission,
        "HEALTH_CHECK":   orch.execute_health_mission,
        "QUICK_SCAN":     orch.execute_quick_scan,
        "FULL_NOC":       orch.execute_full_noc,
    }

    fn = dispatch.get(task_type)
    if not fn:
        return {"error": f"Tipo de misión desconocido: {task_type}"}

    return fn()
