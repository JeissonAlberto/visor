#!/usr/bin/env bash
# ============================================================
# VISOR — Instalador automático para Linux / macOS
# Instala un entorno aislado y deja el comando `visor` global.
# ============================================================

set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
BIN_DIR="$HOME/.local/bin"
LAUNCHER="$ROOT/visor"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { printf "  %b[OK]%b %s\n" "$GREEN" "$NC" "$1"; }
warn() { printf "  %b[AVISO]%b %s\n" "$YELLOW" "$NC" "$1"; }
fail() { printf "  %b[ERROR]%b %s\n" "$RED" "$NC" "$1" >&2; exit 1; }

printf '\n  VISOR — Monitor de Red\n  Instalación automática\n\n'

if command -v python3 >/dev/null 2>&1; then
    PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON="$(command -v python)"
else
    fail 'Python 3.10 o superior no está instalado.'
fi

"$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
    || fail "Se necesita Python 3.10+. Versión encontrada: $("$PYTHON" --version 2>&1)"
ok "Python encontrado: $($PYTHON --version 2>&1)"

# El entorno queda dentro del repositorio: no modifica el Python del sistema
# y evita problemas de permisos o de PEP 668 en Linux.
if [ ! -x "$VENV/bin/python" ] || ! "$VENV/bin/python" --version >/dev/null 2>&1; then
    # --clear repara un .venv incompleto o movido sin tocar el código del proyecto.
    "$PYTHON" -m venv --clear "$VENV" \
        || fail 'No se pudo crear el entorno virtual. Instala el paquete python3-venv.'
    ok 'Entorno aislado creado o reparado.'
else
    ok 'Entorno aislado existente reutilizado.'
fi

PIP_USER=0 "$VENV/bin/python" -m pip install --no-user --editable "$ROOT" --no-deps --quiet \
    || fail 'No se pudo instalar Visor.'
ok 'Visor instalado.'

if ! chmod +x "$LAUNCHER" 2>/dev/null; then
    warn 'No se pudo marcar el lanzador como ejecutable; prueba con: chmod +x visor'
fi
mkdir -p "$BIN_DIR"
ln -sfn "$LAUNCHER" "$BIN_DIR/visor"
ok "Comando creado: $BIN_DIR/visor"

# Deja ~/.local/bin disponible en futuras terminales sin obligar al usuario
# a editar archivos a mano. La terminal actual también queda lista.
export PATH="$BIN_DIR:$PATH"
PROFILE_FILES=()
[ -f "$HOME/.bashrc" ] && PROFILE_FILES+=("$HOME/.bashrc")
[ -f "$HOME/.zshrc" ] && PROFILE_FILES+=("$HOME/.zshrc")
for profile in "${PROFILE_FILES[@]}"; do
    if ! grep -Fqx 'export PATH="$HOME/.local/bin:$PATH"' "$profile" 2>/dev/null; then
        printf '\n# Visor: comando global\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$profile"
    fi
done

if [ -x "$LAUNCHER" ]; then
    "$BIN_DIR/visor" --version >/dev/null \
        || fail 'El comando se instaló, pero la comprobación de versión falló.'
else
    "$VENV/bin/python" "$ROOT/main.py" --version >/dev/null \
        || fail 'La comprobación de versión de Visor falló.'
    warn 'El lanzador quedó sin permiso de ejecución; vuelve a ejecutar: chmod +x visor'
fi
ok "Comprobación correcta: escribe 'visor' desde cualquier carpeta."

printf '\n  Instalación terminada. No necesitas ejecutar pip ni configurar nada más.\n'
if [ "${#PROFILE_FILES[@]}" -eq 0 ]; then
    warn 'Abre una terminal nueva o agrega ~/.local/bin al PATH si el comando no aparece.'
fi
printf '\n'
