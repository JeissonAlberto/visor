"""
core/guardian_ai.py — Motor de Remediación para Visor v5.1.
Jasol Group · Ing. Jeisson Alberto Sarmiento · Saravena, Arauca, Colombia
"""

from datetime import datetime
from core.guardian_ai_kb import REMEDIATION_KB, DEFAULT_REMEDIATION


def generate_remediation_plan(findings: list) -> list:
    PRIORIDAD = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3, "INFO": 4}
    plan = []
    for finding in findings:
        port  = finding.get("port")
        riesgo = finding.get("risk", "DESCONOCIDO")
        desc  = finding.get("desc", "Sin descripción")
        banner = finding.get("banner", "")
        kb = REMEDIATION_KB.get(port, {})
        entrada = {
            "puerto":      port,
            "servicio":    kb.get("nombre", finding.get("service", f"Puerto {port}")),
            "riesgo":      kb.get("riesgo", riesgo),
            "descripcion": kb.get("descripcion", desc),
            "impacto":     kb.get("impacto", "Exposición de servicio no autorizado."),
            "remediacion": kb.get("remediacion", DEFAULT_REMEDIATION["remediacion"]),
            "comandos":    kb.get("comandos", DEFAULT_REMEDIATION["comandos"]),
            "referencias": kb.get("referencias", []),
            "banner":      banner,
            "ts":          datetime.now().isoformat(timespec="seconds"),
        }
        plan.append(entrada)
    plan.sort(key=lambda x: PRIORIDAD.get(x["riesgo"], 9))
    return plan


def generar_reporte_ejecutivo(plan: list, target: str = "Sistema Local") -> str:
    lineas = [
        "=" * 70,
        f"  REPORTE EJECUTIVO DE SEGURIDAD — VISOR v5.1",
        f"  Jasol Group · Ing. Jeisson Alberto Sarmiento",
        f"  Objetivo: {target}",
        f"  Fecha:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 70,
        f"
  Total hallazgos: {len(plan)}",
        f"  Críticos: {sum(1 for h in plan if h['riesgo'] == 'CRÍTICO')}  |  "
        f"Altos: {sum(1 for h in plan if h['riesgo'] == 'ALTO')}  |  "
        f"Medios: {sum(1 for h in plan if h['riesgo'] == 'MEDIO')}",
        "
" + "-" * 70,
    ]
    for i, h in enumerate(plan, 1):
        lineas += [
            f"
  [{i}] {h['servicio']} (Puerto {h['puerto']}) — Riesgo: {h['riesgo']}",
            f"  Descripción: {h['descripcion']}",
            f"  Impacto:     {h['impacto']}",
            f"  Remediación:",
        ]
        for paso in h["remediacion"]:
            lineas.append(f"    • {paso}")
        if h.get("banner"):
            lineas.append(f"  Banner: {h['banner']}")
        if h["referencias"]:
            lineas.append(f"  Referencias: {', '.join(h['referencias'])}")
        lineas.append("  " + "-" * 68)
    lineas += [
        "
  Este reporte fue generado automáticamente por Visor v5.1.",
        "  Validar todos los hallazgos antes de aplicar cambios en producción.",
        "=" * 70,
    ]
    return "
".join(lineas)


def calcular_score_riesgo(plan: list) -> dict:
    PESOS = {"CRÍTICO": 25, "ALTO": 10, "MEDIO": 4, "BAJO": 1, "INFO": 0}
    score = min(100, sum(PESOS.get(h["riesgo"], 0) for h in plan))
    if score == 0:    nivel = "✅ SEGURO"
    elif score < 20:  nivel = "🟡 BAJO RIESGO"
    elif score < 50:  nivel = "🟠 RIESGO MEDIO"
    elif score < 75:  nivel = "🔴 RIESGO ALTO"
    else:             nivel = "☠️  CRÍTICO"
    return {
        "score":    score, "nivel": nivel,
        "criticos": sum(1 for h in plan if h["riesgo"] == "CRÍTICO"),
        "altos":    sum(1 for h in plan if h["riesgo"] == "ALTO"),
        "medios":   sum(1 for h in plan if h["riesgo"] == "MEDIO"),
        "total":    len(plan),
    }
