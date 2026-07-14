"""
ui/menu_infraestructura.py — Módulo de Infraestructura L3 para Visor v5.0
Jasol Group · Ing. Jeisson Alberto Sarmiento · Saravena, Arauca, Colombia
Integra: MikroTik Telemetry + Proxmox VE API
"""

from core.colores import (
    separador, titulo, info, ok, fallo, warn, dim, resaltar, naranja, azul
)
from config.settings import (
    MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS,
    PROXMOX_HOST, PROXMOX_USER, PROXMOX_PASS
)


def _barra(pct: float, width: int = 20) -> str:
    """Genera una barra de progreso visual."""
    filled = int((pct or 0) / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    color = ok if pct < 60 else (warn if pct < 85 else fallo)
    return f"[{color(bar)}] {pct}%"


def menu_infraestructura():
    """Menú principal del módulo de infraestructura."""
    while True:
        separador("🖥️  INFRAESTRUCTURA L3 — Jasol Group")
        print(f"  {resaltar('1.')} 📡  MikroTik — Telemetría en Vivo")
        print(f"  {resaltar('2.')} 🖥️   Proxmox  — Estado de Nodos y VMs")
        print(f"  {resaltar('3.')} 🔗  Conexión — Verificar Conectividad de Equipos")
        print(f"  {resaltar('0.')} ←   Volver al Menú Principal")
        separador()

        op = input(f"\n  {info('Elige una opción:')} ").strip().upper()

        if   op == "1": _menu_mikrotik()
        elif op == "2": _menu_proxmox()
        elif op == "3": _menu_connect()
        elif op == "0": break
        else:
            print(f"\n  {warn('Opción inválida.')}")


def _menu_mikrotik():
    from core.mikrotik_agent import get_mikrotik_info, get_interfaces_traffic, get_active_clients

    separador("📡 MikroTik RouterOS — Telemetría en Vivo")
    host = input(f"  {info('IP del MikroTik')} [{MIKROTIK_HOST}]: ").strip() or MIKROTIK_HOST
    user = input(f"  {info('Usuario')} [{MIKROTIK_USER}]: ").strip() or MIKROTIK_USER
    pwd  = input(f"  {info('Password')}: ").strip() or MIKROTIK_PASS

    print(f"\n  {naranja('Conectando a')} {resaltar(host)}...\n")
    data = get_mikrotik_info(host, user, pwd)

    if not data.get("online"):
        print(f"  {fallo('Sin conexión:')} {data.get('error', 'Host inaccesible')}")
        print(f"  {dim('Verifica que SSH esté habilitado: /ip service set ssh disabled=no')}")
        input(f"\n  {dim('Enter para continuar...')}")
        return

    # Datos del sistema
    separador(f"✅ {data.get('identity', host)}")
    print(f"  {resaltar('RouterOS Version:')} {data.get('ros_version', '—')}")
    print(f"  {resaltar('Uptime:')}           {data.get('uptime', '—')}")

    cpu = data.get("cpu_load")
    if cpu is not None:
        print(f"  {resaltar('CPU:')}             {_barra(cpu)}")

    mem_pct = data.get("mem_used_pct")
    if mem_pct is not None:
        print(f"  {resaltar('Memoria:')}         {_barra(mem_pct)}  ({data.get('mem_free_mb')} MB libres de {data.get('mem_total_mb')} MB)")

    temp = data.get("temperature")
    if temp is not None:
        t_color = ok if temp < 55 else (warn if temp < 70 else fallo)
        print(f"  {resaltar('Temperatura:')}     {t_color(str(temp) + '°C')}")

    # Tráfico de interfaces
    print(f"\n  {titulo('INTERFACES — TRÁFICO EN VIVO')}")
    print(f"  {naranja('Midiendo tráfico (puede tardar ~3s)...')}")
    interfaces = get_interfaces_traffic(host, user, pwd)

    if interfaces:
        print(f"\n  {'INTERFAZ':<22} {'RX (Mbps)':>12} {'TX (Mbps)':>12}")
        print(f"  {dim('─'*48)}")
        for iface in interfaces:
            rx_c = ok if iface['rx_mbps'] < 500 else warn
            tx_c = ok if iface['tx_mbps'] < 500 else warn
            print(f"  {iface['name']:<22} {rx_c(str(iface['rx_mbps'])):>20} {tx_c(str(iface['tx_mbps'])):>20}")
    else:
        print(f"  {warn('No se pudo obtener tráfico de interfaces.')}")
        print(f"  {dim('Asegúrate de que el usuario SSH tiene permisos de lectura.')}")

    # Clientes DHCP
    clients = get_active_clients(host, user, pwd)
    print(f"\n  {resaltar('Clientes DHCP Activos:')} {ok(str(clients))}")

    separador()
    input(f"  {dim('Enter para continuar...')}")


def _menu_proxmox():
    from core.proxmox_agent import get_nodes_status, get_vms_status, ping_proxmox

    separador("🖥️  Proxmox VE — Estado del Cluster")
    host       = input(f"  {info('IP del Proxmox')} [{PROXMOX_HOST}]: ").strip() or PROXMOX_HOST
    token_id   = input(f"  {info('Token ID')} [root@pam!visor]: ").strip() or "root@pam!visor"
    token_sec  = input(f"  {info('Token Secret')}: ").strip()

    print(f"\n  {naranja('Consultando API Proxmox en')} {resaltar(host+':8006')}...\n")

    if not ping_proxmox(host):
        print(f"  {fallo('No se puede conectar al puerto 8006 de Proxmox.')}")
        print(f"  {dim('Verifica: Datacenter > API Tokens > Crea un token para Visor')}")
        input(f"\n  {dim('Enter para continuar...')}")
        return

    nodes = get_nodes_status(host, token_id, token_sec)

    if nodes and nodes[0].get("error"):
        print(f"  {fallo('Error de autenticación:')} {nodes[0]['error']}")
        print(f"  {dim('Crea un token: Datacenter > Permissions > API Tokens')}")
        input(f"\n  {dim('Enter para continuar...')}")
        return

    for node in nodes:
        status_c = ok("ONLINE") if node.get("status") == "online" else fallo("OFFLINE")
        separador(f"NODO: {node['node']}  [{status_c}]  Uptime: {node.get('uptime_h', '—')}h")

        cpu = node.get("cpu_pct", 0)
        mem = node.get("mem_pct", 0)
        print(f"  {resaltar('CPU:')}      {_barra(cpu)}")
        print(f"  {resaltar('Memoria:')} {_barra(mem)}  ({node.get('mem_used_gb')} GB / {node.get('mem_total_gb')} GB)")
        print(f"  {resaltar('Disco:')}   {node.get('disk_used_gb')} GB / {node.get('disk_total_gb')} GB")

        # VMs del nodo
        print(f"\n  {titulo('MÁQUINAS VIRTUALES')}")
        vms = get_vms_status(host, node["node"], token_id, token_sec)
        if vms:
            print(f"  {'VMID':<8} {'NOMBRE':<20} {'ESTADO':<12} {'CPU%':>6} {'MEM(MB)':>10} {'UPTIME':>10}")
            print(f"  {dim('─'*70)}")
            for vm in vms:
                s_c = ok if vm["status"] == "running" else fallo
                print(f"  {str(vm['vmid']):<8} {vm['name']:<20} {s_c(vm['status']):<20} "
                      f"{str(vm['cpu_pct']):>6} {str(vm['mem_mb']):>10} {str(vm['uptime_h'])+'h':>10}")
        else:
            print(f"  {dim('No se encontraron VMs o no hay permisos suficientes.')}")

    separador()
    input(f"  {dim('Enter para continuar...')}")


def _menu_connect():
    """Verifica la conectividad con todos los equipos configurados."""
    import socket
    from core.red import hacer_ping
    from core.mikrotik_agent import ping_mikrotik
    from core.proxmox_agent import ping_proxmox

    separador("🔗 VERIFICACIÓN DE CONECTIVIDAD — Jasol Group")
    print(f"  {dim('Verificando acceso a todos los equipos de infraestructura...')}\n")

    equipos = [
        ("MikroTik Core",   MIKROTIK_HOST, "ssh",     22),
        ("Proxmox VE",      PROXMOX_HOST,  "https",   8006),
    ]

    print(f"  {'EQUIPO':<22} {'HOST':<18} {'PROTO':<8} {'ESTADO'}")
    print(f"  {dim('─'*60)}")

    for nombre, host, proto, port in equipos:
        if host and "X" not in host:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                res = s.connect_ex((host, port))
                s.close()
                estado = ok("  ONLINE  ") if res == 0 else fallo(" OFFLINE ")
            except:
                estado = fallo(" ERROR   ")
        else:
            estado = warn("  NO CONF ")
        print(f"  {nombre:<22} {host:<18} {proto.upper():<8} [{estado}]")

    print(f"\n  {dim('Para configurar las IPs reales, edita: config/settings.py')}")
    separador()
    input(f"  {dim('Enter para continuar...')}")
