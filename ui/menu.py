"""
ui/menu.py — Menú principal de Visor.
"""

from datetime import datetime
from core.colores import banner, separador, titulo, info, ok, fallo, warn, dim, resaltar, tabla_estado
from config.settings import INTERVALO_MONITOREO


def menu_principal():
    banner()
    while True:
        print(f"\n  {titulo('MENÚ PRINCIPAL')}")
        separador()
        print(f"  {resaltar('1.')} 📡  Monitoreo continuo de red")
        print(f"  {resaltar('2.')} 🔍  Escaneo único de dispositivos")
        print(f"  {resaltar('3.')} 🌐  Verificar servicios web")
        print(f"  {resaltar('4.')} 📶  Test de calidad de internet")
        print(f"  {resaltar('5.')} 🗺️   Escanear rango IP")
        print(f"  {resaltar('6.')} 📋  Ver último reporte")
        print(f"  {resaltar('7.')} ⚙️   Configuración rápida")
        print(f"  {resaltar('0.')} ❌  Salir")
        separador()

        opcion = input(f"\n  {info('Elige una opción:')} ").strip()

        if opcion == "1":
            _menu_monitoreo()
        elif opcion == "2":
            _escaneo_unico()
        elif opcion == "3":
            _menu_web()
        elif opcion == "4":
            _menu_internet()
        elif opcion == "5":
            _menu_rango()
        elif opcion == "6":
            _ver_reporte()
        elif opcion == "7":
            _configuracion_rapida()
        elif opcion == "0":
            print(f"\n  {dim('Hasta luego — Visor by Jasol Group')}\n")
            break
        else:
            print(f"\n  {warn('Opción inválida. Intenta de nuevo.')}")


# ── Monitoreo continuo ────────────────────────────────────────────────────

def _menu_monitoreo():
    from core.monitor import monitoreo_continuo
    separador("Monitoreo continuo")
    print(f"\n  {info(f'Intervalo: {INTERVALO_MONITOREO}s   ·   Ctrl+C para detener')}\n")
    try:
        monitoreo_continuo(intervalo=INTERVALO_MONITOREO)
    except KeyboardInterrupt:
        pass


# ── Escaneo único ─────────────────────────────────────────────────────────

def _escaneo_unico():
    from core.monitor import escanear_dispositivos
    from utils.reportes import guardar_reporte

    separador("Escaneo de dispositivos")
    print(f"\n  {info('Escaneando...')}\n")

    resultados = escanear_dispositivos()

    up   = [r for r in resultados if r["online"]]
    down = [r for r in resultados if not r["online"]]

    tabla_estado(resultados)
    separador()
    print(f"  {ok(f'{len(up)} en línea')}   {fallo(f'{len(down)} caídos')}   {dim(f'Total: {len(resultados)}')}")

    # Guardar reporte
    ruta = guardar_reporte({
        "ts":          datetime.now().isoformat(),
        "dispositivos": resultados,
    })
    if ruta:
        print(f"\n  {dim(f'Reporte guardado: {ruta.name}')}")

    input(f"\n  {dim('Enter para continuar...')}")


# ── Web ───────────────────────────────────────────────────────────────────

def _menu_web():
    from core.web_service import escanear_servicios_web
    from utils.reportes import guardar_reporte

    separador("Servicios web")
    print(f"\n  {info('Verificando servicios...')}\n")

    resultados = escanear_servicios_web()

    # Mostrar tabla
    ancho = max((len(r.get("nombre", "")) for r in resultados), default=15) + 2
    print(f"  {'SERVICIO':<{ancho}}  {'URL':<40}  {'ESTADO':<10}  {'HTTP':>6}  {'MS':>8}")
    print(f"  {'─'*(ancho+70)}")

    for r in resultados:
        estado_s = f"{ok('OK')}" if r["online"] else f"{fallo('DOWN')}"
        http_s   = str(r.get("http") or "—")
        lat_s    = f"{r['latencia']} ms" if r.get("latencia") else "—"
        url_corta = r.get("url", "")[:38]
        print(f"  {r.get('nombre',''):<{ancho}}  {url_corta:<40}  {estado_s:<20}  {http_s:>6}  {lat_s:>8}")

    up = sum(1 for r in resultados if r["online"])
    print(f"\n  {ok(f'{up}/{len(resultados)} servicios activos')}")

    ruta = guardar_reporte({"ts": datetime.now().isoformat(), "web": resultados})
    if ruta:
        print(f"  {dim(f'Reporte: {ruta.name}')}")

    input(f"\n  {dim('Enter para continuar...')}")


# ── Internet ──────────────────────────────────────────────────────────────

def _menu_internet():
    from core.test_internet import test_internet
    from utils.reportes import guardar_reporte

    separador("Test de calidad de internet")
    print(f"\n  {info('Midiendo latencia, velocidad y throughput...')}")
    print(f"  {dim('(Esto puede tardar 20-30 segundos)')}\n")

    r = test_internet()

    calidad   = r["calidad"]
    color_cal = ok if calidad in ("EXCELENTE", "BUENA") else (warn if calidad == "REGULAR" else fallo)

    def _mbps(val, fuente=""):
        if val is None:
            return fallo("No disponible")
        color = ok if val >= 10 else (warn if val >= 2 else fallo)
        s = color(f"{val} Mbps")
        if fuente:
            s += f"  {dim('via ' + fuente)}"
        return s

    def _ms(val):
        if val is None:
            return dim("—")
        color = ok if val < 50 else (warn if val < 150 else fallo)
        return color(f"{val} ms")

    separador()
    print(f"  {'Calidad:':<26} {color_cal(calidad)}")
    separador()

    # ── Latencia ──
    print(f"\n  {resaltar('LATENCIA')}")
    print(f"  {'Promedio:':<26} {_ms(r['lat_avg'])}")
    print(f"  {'Mínima:':<26} {_ms(r['lat_min'])}")
    print(f"  {'Máxima:':<26} {_ms(r['lat_max'])}")
    print(f"  {'Jitter:':<26} {_ms(r['jitter'])}")
    print(f"  {'Pérdida de paquetes:':<26} {warn(str(r['perdida'])+'%') if r['perdida'] > 0 else ok('0%')}")
    print(f"  {'Pings OK / Total:':<26} {dim(str(r['pings_ok']) + ' / ' + str(r['total_pings']))}")

    # ── Velocidad ──
    print(f"\n  {resaltar('VELOCIDAD')}")
    print(f"  {'Descarga:':<26} {_mbps(r.get('descarga_mbps'), r.get('fuente_dl',''))}")
    print(f"  {'Subida:':<26} {_mbps(r.get('subida_mbps'), r.get('fuente_ul',''))}")

    # ── Throughput ──
    print(f"\n  {resaltar('THROUGHPUT TCP LOCAL')}")
    tp = r.get("throughput_mbps")
    if tp:
        color_tp = ok if tp >= 500 else (warn if tp >= 100 else fallo)
        print(f"  {'Stack de red:':<26} {color_tp(str(tp) + ' Mbps')}  {dim('(loopback)')}")
    else:
        print(f"  {'Stack de red:':<26} {fallo('No disponible')}")

    # ── Por host ──
    separador()
    print(f"  {resaltar('HOSTS DE REFERENCIA')}")
    for h in r.get("hosts", []):
        lats = h.get("lats", [])
        avg  = round(sum(lats) / len(lats), 1) if lats else None
        s    = ok(f"{avg} ms") if lats else fallo("Sin respuesta")
        perdidos = h.get("perdidos", 0)
        p_str = f"  {dim(str(perdidos) + ' perdido(s)')}" if perdidos else ""
        print(f"  {h['nombre']:<16} {dim(h['host']):<16} {s}{p_str}")

    separador()
    ruta = guardar_reporte({"ts": datetime.now().isoformat(), "internet": r})
    if ruta:
        print(f"  {dim('Reporte guardado: ' + ruta.name)}")

    input(f"\n  {dim('Enter para continuar...')}")


# ── Escaneo de rango ──────────────────────────────────────────────────────

def _menu_rango():
    from core.red import escanear_rango
    from config.device import RANGO_SCAN

    separador("Escanear rango IP")
    print(f"\n  {info(f'Rango configurado: {RANGO_SCAN}')}")
    rango = input(f"  Introduce el rango CIDR (Enter = {RANGO_SCAN}): ").strip() or RANGO_SCAN

    print(f"\n  {info(f'Escaneando {rango}... (puede tardar unos segundos)')}\n")
    resultados = escanear_rango(rango)

    activos = [r for r in resultados if r["activo"]]
    print(f"  {'IP':<18} {'ESTADO':<10} {'LATENCIA':>10}  HOSTNAME")
    print(f"  {'─'*60}")
    for r in activos:
        lat_s = f"{r['latencia']} ms" if r['latencia'] else "—"
        host  = r.get("hostname") or ""
        print(f"  {r['ip']:<18} {ok('UP'):<20} {lat_s:>10}  {dim(host)}")

    if not activos:
        print(f"  {warn('No se encontraron hosts activos en el rango.')}")

    print(f"\n  {resaltar(f'{len(activos)} host(s) activos de {len(resultados)} IPs escaneadas')}")
    input(f"\n  {dim('Enter para continuar...')}")


# ── Reporte ───────────────────────────────────────────────────────────────

def _ver_reporte():
    from utils.reportes import leer_ultimo_reporte
    separador("Último reporte")
    print(f"\n{leer_ultimo_reporte()}\n")
    input(f"  {dim('Enter para continuar...')}")


# ── Config rápida ─────────────────────────────────────────────────────────

def _configuracion_rapida():
    separador("Configuración rápida")
    print(f"""
  {info('Archivos de configuración:')}

  {resaltar('config/device.py')}
    → Lista de dispositivos a monitorear (IP, MAC, nombre, grupo)
    → Servicios web a verificar
    → Rango IP para escaneo automático

  {resaltar('config/smtp_config.py')}
    → Credenciales de correo para alertas automáticas

  {resaltar('config/settings.py')}
    → Intervalo de monitoreo, timeouts, reportes

  {dim('Edita estos archivos con tu editor de texto favorito.')}
""")
    input(f"  {dim('Enter para volver...')}")


# ── Ejecución directa (flags CLI) ────────────────────────────────────────

def run_direct(args):
    banner()
    if args.scan:
        _escaneo_unico()
    if args.web:
        _menu_web()
    if args.internet:
        _menu_internet()
    if args.report:
        _ver_reporte()
