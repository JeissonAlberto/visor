#!/bin/bash
# ============================================================
#  VISOR — Instalador automático para Linux / macOS
#  by Jasol Group · Saravena, Arauca, Colombia
# ============================================================

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
err()  { echo -e "  ${RED}[ERROR]${NC} $1"; exit 1; }
warn() { echo -e "  ${YELLOW}[AVISO]${NC} $1"; }

echo ""
echo "  ============================================================"
echo "   VISOR - Monitor de Red v2.0 - by Jasol Group"
echo "   Instalador automatico para Linux / macOS"
echo "  ============================================================"
echo ""

# ── 1. Verificar Python ─────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    err "Python3 no instalado. Instálalo con: sudo apt install python3"
fi

PYVER=$(python3 --version 2>&1 | cut -d' ' -f2)
ok "Python encontrado: $PYVER"

# ── 2. Verificar version minima 3.10 ────────────────────────
python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" || \
    err "Necesitas Python 3.10+. Versión actual: $PYVER"
ok "Versión de Python compatible."

# ── 3. Verificar pip ────────────────────────────────────────
if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null; then
    err "pip no encontrado. Instálalo con: sudo apt install python3-pip"
fi
ok "pip disponible."
echo ""

# ── 4. Instalar Visor ───────────────────────────────────────
echo "  Instalando Visor..."
pip3 install -e . --quiet 2>/dev/null || python3 -m pip install -e . --quiet
ok "Visor instalado correctamente."
echo ""

# ── 5. Verificar comando visor ──────────────────────────────
if command -v visor &>/dev/null; then
    ok "Comando 'visor' disponible globalmente."
else
    warn "El comando 'visor' no está en el PATH todavía."
    warn "Agrega esta línea a tu ~/.bashrc o ~/.zshrc:"
    echo ""
    SCRIPTS=$(python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))")
    echo "    export PATH=\"\$PATH:$SCRIPTS\""
    echo ""
    warn "O usa directamente: python3 main.py"
fi

echo ""
echo "  ============================================================"
echo "   INSTALACIÓN COMPLETADA"
echo "  ============================================================"
echo ""
echo "   Comandos disponibles:"
echo ""
echo "     visor               → Menú interactivo"
echo "     visor --scan        → Escaneo rápido"
echo "     visor --web         → Servicios web"
echo "     visor --internet    → Test de internet"
echo "     visor --setup       → Configuración"
echo "     visor --report      → Último reporte"
echo ""
echo "  ============================================================"
echo ""
