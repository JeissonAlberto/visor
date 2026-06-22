#!/usr/bin/env python3
"""
Visor — Monitor de Red
by Jasol Group · Saravena, Arauca, Colombia

Uso:
    python main.py                  # Menú interactivo
    python main.py --scan           # Escaneo rápido de red
    python main.py --web            # Solo servicios web
    python main.py --internet       # Solo test de internet
    python main.py --setup          # Asistente de configuración
    python main.py --report         # Ver último reporte
"""

import sys
import argparse
from ui.menu import menu_principal
from ui.setup_wizard import setup_wizard


def parse_args():
    parser = argparse.ArgumentParser(
        prog="visor",
        description="Visor — Monitor de Red by Jasol Group"
    )
    parser.add_argument("--scan",     action="store_true", help="Escaneo rápido de red")
    parser.add_argument("--web",      action="store_true", help="Verificar servicios web")
    parser.add_argument("--internet", action="store_true", help="Test de calidad de internet")
    parser.add_argument("--setup",    action="store_true", help="Asistente de configuración")
    parser.add_argument("--report",   action="store_true", help="Ver último reporte guardado")
    parser.add_argument("--version",  action="store_true", help="Versión de Visor")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.version:
        from config.settings import VERSION
        print(f"Visor v{VERSION} — by Jasol Group")
        sys.exit(0)

    if args.setup:
        setup_wizard()
        sys.exit(0)

    if args.scan or args.web or args.internet or args.report:
        from ui.menu import run_direct
        run_direct(args)
        sys.exit(0)

    # Menú interactivo por defecto
    menu_principal()


if __name__ == "__main__":
    main()
