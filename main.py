#!/usr/bin/env python3
"""
Visor v5.2.1 — NOC Command Suite
Jasol Group · Ing. Jeisson Alberto Sarmiento · Saravena, Arauca, Colombia

Uso:
    visor                       # Menú interactivo
    visor --scan                # Escaneo rápido de red
    visor --web                 # Solo servicios web
    visor --internet            # Test de calidad de internet
    visor --watch               # Monitoreo continuo LAN + servicios públicos
    visor --setup               # Asistente de configuración
    visor --report              # Ver último reporte
    visor --connect             # Handshake con MikroTik/Proxmox
    visor --lan                 # Descubrimiento LAN (whosthere-style)
    visor --hunt <ip>           # Threat Hunting sobre IP/host
    visor --noc                 # Misión NOC Completa (todos los agentes)
    visor --health              # Diagnóstico de calidad multi-capa
    visor --traceroute <host>   # Traceroute con latencia por salto
    visor --topology [host]    # Topología LAN + ruta L3 verificada
"""

import sys
import argparse
from ui.menu import menu_principal
from ui.setup_wizard import setup_wizard


def parse_args():
    parser = argparse.ArgumentParser(
        prog="visor",
        description="Visor v5.2.1 NOC Command Suite · Jasol Group",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--scan",       action="store_true",  help="Escaneo rápido de red")
    parser.add_argument("--web",        action="store_true",  help="Verificar servicios web")
    parser.add_argument("--internet",   action="store_true",  help="Test de calidad de internet")
    parser.add_argument("--watch",      action="store_true",  help="Monitoreo continuo LAN + servicios públicos")
    parser.add_argument("--setup",      action="store_true",  help="Asistente de configuración")
    parser.add_argument("--report",     action="store_true",  help="Ver último reporte guardado")
    parser.add_argument("--connect",    action="store_true",  help="Conectar con infraestructura (MikroTik/Proxmox)")
    parser.add_argument("--lan",        action="store_true",  help="Descubrimiento LAN completo")
    parser.add_argument("--hunt",       metavar="HOST",       help="Threat Hunting sobre un host específico")
    parser.add_argument("--noc",        action="store_true",  help="Misión NOC Completa (todos los agentes)")
    parser.add_argument("--health",     action="store_true",  help="Diagnóstico de calidad de red multi-capa")
    parser.add_argument("--traceroute", metavar="HOST",       help="Traceroute con latencia por salto")
    parser.add_argument("--topology", nargs="?", const="8.8.8.8", metavar="HOST", help="Mapea LAN y ruta L3 verificada hacia HOST")
    parser.add_argument("--topology-watch", nargs="?", const="8.8.8.8", metavar="HOST", help="Monitor continuo de ruta estilo PingPlotter")
    parser.add_argument("--watch-interval", type=int, default=60, metavar="SEG", help="Intervalo del monitor continuo (mínimo 10 s)")
    parser.add_argument("--watch-cycles", type=int, default=0, metavar="N", help="Número de muestras; 0 mantiene el monitor activo")
    parser.add_argument("--version",    action="store_true",  help="Versión de Visor")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.version:
        from config.settings import VERSION, APP_NAME, ORGANIZATION
        print(f"{APP_NAME} — {ORGANIZATION}")
        print(f"Versión: {VERSION}")
        sys.exit(0)

    if args.setup:
        setup_wizard()
        sys.exit(0)

    if args.watch:
        from config.settings import INTERVALO_MONITOREO
        from core.monitor import monitoreo_continuo
        monitoreo_continuo(intervalo=INTERVALO_MONITOREO)
        sys.exit(0)

    # ── Flags directos sin menú ───────────────────────────────────────────
    if args.scan or args.web or args.internet or args.report:
        from ui.menu import run_direct
        run_direct(args)
        sys.exit(0)

    if args.connect:
        from ui.menu_infraestructura import menu_infraestructura
        menu_infraestructura()
        sys.exit(0)

    if args.lan:
        from ui.menu_lan_vision import menu_lan_vision
        menu_lan_vision()
        sys.exit(0)

    if args.hunt:
        from core.colores import banner, separador, titulo, fallo, ok, warn, resaltar, dim
        from core.raptor_eye import hunt_vulnerabilities, describir_hallazgos
        from core.guardian_ai import generate_remediation_plan, generar_reporte_ejecutivo
        banner()
        print(f"\n  {titulo('RAPTOR EYE — Threat Hunting')}")
        separador()
        print(f"  Objetivo: {resaltar(args.hunt)}\n")
        hallazgos = hunt_vulnerabilities(args.hunt)
        if hallazgos:
            print(f"  {fallo(f'{len(hallazgos)} vector(es) de amenaza detectado(s):')}\n")
            for h in hallazgos:
                print(f"  [{h['risk']:<8}] Puerto {h['port']:<6} — {h['desc']}")
                if h.get('banner'):
                    print(f"           Banner: {dim(h['banner'])}")
            plan = generate_remediation_plan(hallazgos)
            reporte = generar_reporte_ejecutivo(plan, args.hunt)
            print(f"\n{reporte}")
        else:
            print(f"  {ok('Sin vectores de amenaza detectados en ' + args.hunt)}")
        sys.exit(0)

    if args.health:
        from core.colores import banner, separador, titulo, ok, fallo, warn, dim, resaltar
        from core.health import analizar_completo
        banner()
        print(f"\n  {titulo('DIAGNÓSTICO DE CALIDAD — Multi-Capa')}")
        separador()
        res = analizar_completo()
        for key in ["lan", "internet", "cloudflare"]:
            if key in res:
                r = res[key]
                calidad_color = ok if r["calidad"] in ("EXCELENTE","ACEPTABLE") else fallo
                print(f"\n  {resaltar(r.get('label', key))}")
                print(f"  {'─'*40}")
                print(f"  Latencia avg : {r['avg']} ms  (min:{r['min']} max:{r['max']})")
                print(f"  Jitter       : {r['jitter']} ms")
                print(f"  Pérdida      : {r['loss']}%")
                print(f"  MOS Score    : {r['mos']} — {r['calidad_voip']}")
                print(f"  Calidad      : {calidad_color(r['calidad'])}")
                for d in r.get("diagnosticos", []):
                    print(f"  {d}")
        print(f"\n  {res.get('diagnostico_global','')}")
        separador()
        sys.exit(0)

    if args.traceroute:
        from core.colores import banner, separador, titulo, ok, fallo, warn, dim, resaltar
        from core.health import traceroute
        banner()
        print(f"\n  {titulo('TRACEROUTE')} → {args.traceroute}")
        separador()
        saltos = traceroute(args.traceroute)
        for s in saltos:
            lat_str = f"{s['lat_ms']} ms" if s['lat_ms'] is not None else "* * *"
            host_str = f" ({s['hostname']})" if s['hostname'] else ""
            marker = fallo("●") if s['timeout'] else ok("●")
            print(f"  {marker} Hop {s['hop']:>2}  {s['ip']:<18} {lat_str:<10}{host_str}")
        separador()
        sys.exit(0)

    if args.topology_watch:
        from core.path_monitor import run_topology_watch
        run_topology_watch(args.topology_watch, interval_s=args.watch_interval, cycles=args.watch_cycles)
        return

    if args.topology:
        from core.colores import banner, separador, titulo, ok, dim
        from core.topology import build_topology, render_topology_text, save_topology_reports
        banner()
        print(f"\n  {titulo('TOPOLOGÍA VERIFICADA — LAN + RUTA L3')}")
        separador()
        print(f"  {dim('Se usarán ARP, ICMP, ruta por defecto y traceroute. No se inventan enlaces.')}")
        print(f"  {dim('Destino de la traza: ' + args.topology)}\n")
        topology = build_topology(trace_targets=[args.topology])
        print(render_topology_text(topology))
        paths = save_topology_reports(topology)
        print(f"  {ok('Reportes guardados:')}")
        for kind, path in paths.items():
            print(f"    {kind.upper()}: {path}")
        separador()
        sys.exit(0)

    if args.noc:
        from core.colores import banner, separador, titulo, ok, fallo, warn, dim, resaltar
        from core.orchestrator import run_orchestrated_task
        banner()
        print(f"\n  {titulo('🚀 MISIÓN NOC COMPLETA — Jasol Group')}")
        res = run_orchestrated_task("FULL_NOC")
        score = res.get("score", {})
        print(f"\n  ─── RESUMEN EJECUTIVO ───────────────────────────────")
        print(f"  Score de Riesgo  : {score.get('score',0)}/100 — {score.get('nivel','?')}")
        print(f"  Críticos         : {score.get('criticos',0)}")
        print(f"  Altos            : {score.get('altos',0)}")
        print(f"  Medios           : {score.get('medios',0)}")
        lan = res.get("lan", [])
        print(f"  Dispositivos LAN : {sum(1 for d in lan if d.get('activo'))}/{len(lan)}")
        if res.get("reporte_path"):
            print(f"\n  📄 Reporte guardado en: {ok(res['reporte_path'])}")
        separador()
        sys.exit(0)

    # Menú interactivo por defecto
    menu_principal()


if __name__ == "__main__":
    main()
