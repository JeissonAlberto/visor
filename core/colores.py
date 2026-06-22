"""
core/colores.py — Colores, estilos y banner para la consola.
Compatible con Windows (secuencias ANSI estándar, sin dependencias).
"""

import sys
import os
from config.settings import COLORES_ACTIVOS, VERSION, AUTOR, ORGANIZATION, UBICACION

# ── Detectar soporte de color ─────────────────────────────────────────────
_COLOR = COLORES_ACTIVOS and (
    sys.platform != "win32"
    or os.environ.get("TERM") is not None
    or os.environ.get("WT_SESSION") is not None   # Windows Terminal
    or os.environ.get("ANSICON") is not None
    or os.environ.get("ConEmuANSI") == "ON"
)

# ── Códigos ANSI ──────────────────────────────────────────────────────────
RESET    = "\033[0m"   if _COLOR else ""
BOLD     = "\033[1m"   if _COLOR else ""
DIM      = "\033[2m"   if _COLOR else ""
VERDE    = "\033[92m"  if _COLOR else ""
ROJO     = "\033[91m"  if _COLOR else ""
AMARILLO = "\033[93m"  if _COLOR else ""
CYAN     = "\033[96m"  if _COLOR else ""
VIOLETA  = "\033[95m"  if _COLOR else ""
BLANCO   = "\033[97m"  if _COLOR else ""
GRIS     = "\033[90m"  if _COLOR else ""
AZUL     = "\033[94m"  if _COLOR else ""
NARANJA  = "\033[33m"  if _COLOR else ""


# ── Funciones de color ────────────────────────────────────────────────────
def ok(texto):       return f"{VERDE}{BOLD}✅ {texto}{RESET}"
def fallo(texto):    return f"{ROJO}{BOLD}❌ {texto}{RESET}"
def warn(texto):     return f"{AMARILLO}⚠️  {texto}{RESET}"
def info(texto):     return f"{CYAN}ℹ  {texto}{RESET}"
def titulo(texto):   return f"{VIOLETA}{BOLD}{texto}{RESET}"
def dim(texto):      return f"{GRIS}{texto}{RESET}"
def resaltar(texto): return f"{BLANCO}{BOLD}{texto}{RESET}"
def azul(texto):     return f"{AZUL}{BOLD}{texto}{RESET}"
def naranja(texto):  return f"{NARANJA}{BOLD}{texto}{RESET}"


# ── Banner ────────────────────────────────────────────────────────────────
def banner():
    print(f"""
{VIOLETA}{BOLD} ██╗   ██╗██╗███████╗ ██████╗ ██████╗
 ██║   ██║██║██╔════╝██╔═══██╗██╔══██╗
 ██║   ██║██║███████╗██║   ██║██████╔╝
 ╚██╗ ██╔╝██║╚════██║██║   ██║██╔══██╗
  ╚████╔╝ ██║███████║╚██████╔╝██║  ██║
   ╚═══╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝{RESET}
{GRIS} Monitor de Red v{VERSION}  ·  {ORGANIZATION}{RESET}
{GRIS} Creado por {AUTOR}{RESET}
{GRIS} {UBICACION}{RESET}
""")


def firma():
    """Línea de firma para cierre y reportes."""
    return f"{GRIS}Visor v{VERSION}  ·  {AUTOR}  ·  {ORGANIZATION}  ·  {UBICACION}{RESET}"


# ── Separadores ───────────────────────────────────────────────────────────
def separador(titulo_sec="", ancho=50):
    if titulo_sec:
        pad = max((ancho - len(titulo_sec) - 2) // 2, 1)
        print(f"\n{GRIS}{'─'*pad}{RESET} {VIOLETA}{BOLD}{titulo_sec}{RESET} {GRIS}{'─'*pad}{RESET}")
    else:
        print(f"{GRIS}{'─'*ancho}{RESET}")


# ── Tabla de dispositivos ─────────────────────────────────────────────────
def tabla_estado(resultados):
    if not resultados:
        return
    ancho_nombre = max((len(r.get("nombre", "")) for r in resultados), default=20) + 2
    ancho_ip     = max((len(str(r.get("ip", r.get("addr", "")))) for r in resultados), default=18) + 2

    print(f"\n  {BOLD}{BLANCO}{'DISPOSITIVO':<{ancho_nombre}}{'DIRECCIÓN':<{ancho_ip}}{'ESTADO':<10}{'LATENCIA':>10}  MÉTODO{RESET}")
    print(f"  {GRIS}{'─'*(ancho_nombre+ancho_ip+32)}{RESET}")

    for r in resultados:
        nombre = r.get("nombre") or r.get("name", "—")
        ip     = r.get("ip") or r.get("addr") or r.get("url", "—")
        estado = r.get("estado", "UP" if r.get("online") else "DOWN")
        lat    = r.get("latencia") or r.get("lat")
        lat_s  = f"{lat} ms" if lat is not None else "—"
        metodo = r.get("metodo", r.get("method", ""))
        estado_s = f"{VERDE}{BOLD}● UP{RESET}" if estado == "UP" else f"{ROJO}{BOLD}● DOWN{RESET}"

        print(
            f"  {nombre:<{ancho_nombre}}"
            f"{GRIS}{ip:<{ancho_ip}}{RESET}"
            f"{estado_s:<20}"
            f"{CYAN}{lat_s:>10}{RESET}"
            f"  {GRIS}{metodo}{RESET}"
        )
    print()
