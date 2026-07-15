"""
ui/menu_lan_vision.py — Menú LAN Vision (whosthere-inspired) para Visor v5.0
Jasol Group · Ing. Jeisson Alberto Sarmiento · Saravena, Arauca, Colombia

Descubrimiento completo de LAN con:
  - Identificación de fabricantes (OUI)
  - Clasificación de dispositivos
  - Escaneo de puertos por host
  - Detección de amenazas integrada
"""

import socket
from core.colores import (
    separador, titulo, info, ok, fallo, warn, dim, resaltar, naranja, azul, firma
)


def _barra_progreso(actual: int, total: int, ancho: int = 30) -> str:
    if total == 0:
        return "░" * ancho
    lleno = int(actual / total * ancho)
    return "█" * lleno + "░" * (ancho - lleno)


def _ip_sort_key(ip: str):
    try:
        return tuple(int(x) for x in ip.split("."))
    except:
        return (0, 0, 0, 0)


def menu_lan_vision():
    """Menú principal del módulo LAN Vision."""
    from core.colores import separador, titulo, info, ok, fallo, warn, dim, resaltar

    while True:
        print(f"\n  {titulo('🌐 LAN VISION — Descubrimiento de Red Local')}")
        separador()
        print(f"  {resaltar('1.')} 🔭  Escaneo completo (hosts + fabricantes + puertos)")
        print(f"  {resaltar('2.')} ⚡  Escaneo rápido (solo hosts activos)")
        print(f"  {resaltar('3.')} 🔍  Investigar host específico (puertos + banner)")
        print(f"  {resaltar('4.')} 🛡️   Threat Hunting en red (Raptor v5.0)")
        print(f"  {resaltar('5.')} 📊  Mapa de red visual (ASCII)")
        print(f"  {resaltar('0.')} ↩️   Volver al menú principal")
        separador()

        opcion = input(f"  {info('Selecciona:')} ").strip()

        if opcion == "1":
            _escaneo_completo()
        elif opcion == "2":
            _escaneo_rapido()
        elif opcion == "3":
            _investigar_host()
        elif opcion == "4":
            _threat_hunting_red()
        elif opcion == "5":
            _mapa_visual()
        elif opcion == "0":
            break


def _detectar_rango() -> str:
    """Detecta el rango de red local automáticamente."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        partes = ip.split(".")
        return ".".join(partes[:3]) + ".0/24"
    except:
        return "192.168.1.0/24"


def _escaneo_completo():
    """Escaneo completo de la LAN con enriquecimiento de datos."""
    from core.lan_vision import discover_lan

    rango = _detectar_rango()
    print(f"\n  {info(f'Escaneando red: {rango}')}")
    print(f"  {dim('Esto puede tomar 30-60 segundos...')}\n")

    encontrados = []
    lock_count = [0]

    def on_host(rec):
        lock_count[0] += 1
        n = lock_count[0]
        color = ok if rec["riesgo"].startswith("✅") else (
                fallo if rec["riesgo"].startswith("⚠️") else warn)
        print(f"  [{n:>3}] {rec['ip']:<16} {rec['mac']:<19} {rec['vendor']:<20} "
              f"{rec['tipo']:<28} {rec['riesgo']}", flush=True)
        encontrados.append(rec)

    separador("DISPOSITIVOS ENCONTRADOS")
    print(f"  {'#':<5} {'IP':<16} {'MAC':<19} {'Fabricante':<20} {'Tipo':<28} {'Riesgo'}")
    separador()

    resultados = discover_lan(rango=rango, scan_ports=True, callback=on_host)

    # Resumen
    separador("RESUMEN")
    total = len(resultados)
    riesgo_alto = sum(1 for r in resultados if "ALTO" in r.get("riesgo",""))
    riesgo_medio = sum(1 for r in resultados if "MEDIO" in r.get("riesgo",""))
    riesgo_bajo  = sum(1 for r in resultados if "BAJO" in r.get("riesgo",""))

    print(f"  {ok(f'Total hosts activos: {total}')}")
    if riesgo_alto:
        print(f"  {fallo(f'⚠️  Riesgo Alto: {riesgo_alto} hosts')}")
    if riesgo_medio:
        print(f"  {warn(f'🟡 Riesgo Medio: {riesgo_medio} hosts')}")
    print(f"  {ok(f'✅ Riesgo Bajo: {riesgo_bajo} hosts')}")

    # Tabla de fabricantes
    vendors = {}
    for r in resultados:
        v = r.get("vendor", "Desconocido")
        vendors[v] = vendors.get(v, 0) + 1
    if vendors:
        print(f"\n  {titulo('Top Fabricantes:')}")
        for v, cnt in sorted(vendors.items(), key=lambda x: -x[1])[:8]:
            print(f"  {'█' * cnt} {v} ({cnt})")

    separador()
    input(f"  {dim('Enter para continuar...')}")


def _escaneo_rapido():
    """Ping sweep rápido sin escaneo de puertos."""
    from core.lan_vision import discover_lan

    rango = _detectar_rango()
    print(f"\n  {info(f'Ping sweep en: {rango}')}")
    print(f"  {dim('Modo rápido (sin escaneo de puertos)...')}\n")

    separador("HOSTS ACTIVOS")
    print(f"  {'IP':<16} {'MAC':<19} {'Fabricante':<20} {'Hostname'}")
    separador()

    count = [0]
    def on_host(rec):
        count[0] += 1
        print(f"  {rec['ip']:<16} {rec['mac']:<19} {rec['vendor']:<20} {rec['hostname']}")

    discover_lan(rango=rango, scan_ports=False, callback=on_host)

    separador()
    print(f"  {ok(f'Total: {count[0]} hosts activos')}")
    input(f"\n  {dim('Enter para continuar...')}")


def _investigar_host():
    """Investigación profunda de un host específico."""
    from core.lan_vision import _scan_ports_fast, _grab_banner, lookup_oui
    from core.red import hacer_ping

    separador("🔍 INVESTIGAR HOST")
    target = input(f"  {info('IP o hostname del objetivo:')} ").strip()
    if not target:
        return

    # Resolver hostname a IP
    try:
        ip = socket.gethostbyname(target)
    except:
        print(f"  {fallo(f'No se pudo resolver: {target}')}")
        return

    print(f"\n  {info(f'Investigando: {ip}')}")
    online, lat = hacer_ping(ip, count=3)

    if not online:
        print(f"  {fallo('Host sin respuesta (offline o firewall)')}")
        input(f"  {dim('Enter para continuar...')}")
        return

    print(f"  {ok(f'Host activo — Latencia: {lat}ms' if lat else 'Host activo')}")

    # Puertos extendidos
    PUERTOS_EXTENDIDOS = [
        21, 22, 23, 25, 53, 80, 110, 139, 143, 161,
        389, 443, 445, 587, 631, 873, 993, 995, 1433,
        2049, 2375, 2379, 3306, 3389, 5432, 5900, 5985,
        6379, 6443, 8006, 8080, 8291, 8728, 8729, 9200,
        11211, 27017
    ]
    print(f"\n  {info(f'Escaneando {len(PUERTOS_EXTENDIDOS)} puertos...')}")
    puertos_abiertos = _scan_ports_fast(ip, PUERTOS_EXTENDIDOS)

    separador("PUERTOS ABIERTOS")
    PORT_NAMES = {
        21: "FTP", 22: "SSH", 23: "Telnet ⚠️", 25: "SMTP", 53: "DNS",
        80: "HTTP", 110: "POP3", 139: "NetBIOS", 143: "IMAP", 161: "SNMP",
        389: "LDAP", 443: "HTTPS", 445: "SMB ⚠️", 587: "SMTP-TLS", 631: "CUPS",
        873: "rsync", 993: "IMAPS", 995: "POP3S", 1433: "MSSQL ⚠️",
        2049: "NFS", 2375: "Docker API ☠️", 2379: "ETCD", 3306: "MySQL",
        3389: "RDP ⚠️", 5432: "PostgreSQL", 5900: "VNC ⚠️", 5985: "WinRM",
        6379: "Redis", 6443: "K8s API", 8006: "Proxmox", 8080: "HTTP-Alt",
        8291: "Winbox", 8728: "RouterOS API", 8729: "RouterOS API-SSL",
        9200: "Elasticsearch", 11211: "Memcached", 27017: "MongoDB",
    }

    if puertos_abiertos:
        for p in puertos_abiertos:
            nombre = PORT_NAMES.get(p, "Desconocido")
            banner = _grab_banner(ip, p)
            banner_str = f"  → {dim(banner[:60])}" if banner else ""
            nivel = warn if "⚠️" in nombre or "☠️" in nombre else ok
            print(f"  {nivel(f'  {p}/tcp')}  {nombre:<22} {banner_str}")
    else:
        print(f"  {dim('No se detectaron puertos estándar abiertos.')}")

    separador()
    input(f"  {dim('Enter para continuar...')}")


def _threat_hunting_red():
    """Threat Hunting completo en el segmento de red."""
    from core.raptor_eye import scan_network_threats, generar_resumen_riesgo

    rango = _detectar_rango()
    prefijo = ".".join(rango.split(".")[:3])

    print(f"\n  {fallo('🦖 RAPTOR v5.0 — Threat Hunting en ' + rango)}")
    print(f"  {dim('Escaneando 254 hosts con 28 vectores de amenaza...')}\n")

    todos_los_findings = []
    count = [0]

    def on_vuln(entry):
        count[0] += 1
        criticos = entry["criticos"]
        color = fallo if criticos > 0 else warn
        ip_addr = entry["ip"]
        n_threats = len(entry["threats"])
        crit_lbl = fallo(f"{criticos} CRITICOS") if criticos else ""
        print(f"  {color("  WARNING  " + ip_addr)} -- {n_threats} vectores ({crit_lbl})")
        todos_los_findings.extend(entry["threats"])

    separador("HOSTS CON VULNERABILIDADES")
    reporte = scan_network_threats(prefijo, max_hosts=254, callback=on_vuln)

    if not reporte:
        print(f"  {ok('✅ No se detectaron amenazas en la red.')}")
    else:
        separador("RESUMEN DE RIESGO")
        resumen = generar_resumen_riesgo(todos_los_findings)
        print(f"  Nivel global: {resumen['nivel']}")
        print(f"  Score de riesgo: {resumen['score']}")
        print(f"  🔴 CRITICAL: {resumen['conteo']['CRITICAL']}")
        print(f"  🟠 HIGH:     {resumen['conteo']['HIGH']}")
        print(f"  🟡 MEDIUM:   {resumen['conteo']['MEDIUM']}")
        print(f"  🔵 LOW:      {resumen['conteo']['LOW']}")

        separador("TOP AMENAZAS CRÍTICAS")
        criticas = [f for f in todos_los_findings if f["risk"] == "CRITICAL"]
        for f in criticas[:5]:
            print(f"  🔴 Puerto {f['port']:<6} {f['desc']}")
            print(f"     {dim('Fix:')} {f['fix']}")

    separador()
    input(f"  {dim('Enter para continuar...')}")


def _mapa_visual():
    """Genera un mapa ASCII de la red."""
    from core.lan_vision import discover_lan

    rango = _detectar_rango()
    print(f"\n  {info('Generando mapa de red...')}\n")
    resultados = discover_lan(rango=rango, scan_ports=False)

    if not resultados:
        print(f"  {warn('No se encontraron hosts.')}")
        input(f"  {dim('Enter para continuar...')}")
        return

    # Detectar gateway
    gw_ip = None
    try:
        import subprocess, re, platform
        sistema = platform.system().lower()
        if sistema == "windows":
            r = subprocess.run(["ipconfig"], capture_output=True, text=True)
            m = re.search(r"(?:Puerta de enlace|Default Gateway)[^\d]+([\d.]+)", r.stdout, re.IGNORECASE)
        else:
            r = subprocess.run(["ip", "route"], capture_output=True, text=True)
            m = re.search(r"default via ([\d.]+)", r.stdout)
        gw_ip = m.group(1) if m else None
    except:
        pass

    separador("🗺️  MAPA DE RED LOCAL")
    print()
    print(f"         [INTERNET]")
    print(f"              │")
    gw_label = f"[GATEWAY: {gw_ip}]" if gw_ip else "[GATEWAY]"
    print(f"         {gw_label}")
    print(f"              │")
    print(f"         [SWITCH/LAN]")
    print(f"         {'─' * 40}")

    cols = 0
    for host in resultados:
        if host["ip"] == gw_ip:
            continue
        emoji = host["tipo"].split()[0] if host["tipo"] else "💻"
        label = f"{emoji} {host['ip']}"
        if cols == 0:
            print(f"         ", end="")
        print(f"│ {label:<22}", end="")
        cols += 1
        if cols == 3:
            print()
            cols = 0
    if cols > 0:
        print()

    print(f"\n  {ok(f'Total: {len(resultados)} nodos mapeados')}")
    separador()
    input(f"  {dim('Enter para continuar...')}")
