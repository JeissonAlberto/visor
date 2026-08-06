"""
core/topology.py — Descubrimiento y verificación de topología para Visor.

Construye un mapa conservador a partir de evidencias observables:
- ARP + ping para vecinos L2 de la estación de análisis.
- Ruta por defecto para identificar el gateway local.
- Traceroute para la cadena L3 hacia uno o varios destinos.
- Puertos y nombres obtenidos durante el descubrimiento LAN.

Importante: ARP demuestra vecindad en la LAN, no el puerto físico del switch.
Traceroute demuestra el camino L3 observado, no una conexión física exacta.
El reporte conserva esas limitaciones para evitar inventar enlaces.
"""

from datetime import datetime
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import xml.etree.ElementTree as ET
from typing import Callable, Iterable

from core.health import traceroute as _traceroute
from core.lan_vision import discover_lan, lookup_oui
from core.red import detectar_gateway, hacer_ping
from core.wifi import annotate_wifi_nodes, local_wifi_context, mikrotik_wifi_clients


DEFAULT_TRACE_TARGET = "8.8.8.8"
REPORTS_DIR = Path(__file__).parent.parent / "reports"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _local_ip() -> str:
    """Obtiene la IP de salida sin transmitir tráfico de aplicación."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((DEFAULT_TRACE_TARGET, 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return ""
    finally:
        sock.close()


def _safe_ip(value: str) -> str:
    try:
        return str(ipaddress.ip_address(value))
    except (ValueError, TypeError):
        return ""


def _same_subnet(ip_a: str, ip_b: str, prefix: int = 24) -> bool:
    try:
        net = ipaddress.ip_network(f"{ip_a}/{prefix}", strict=False)
        return ipaddress.ip_address(ip_b) in net
    except ValueError:
        return False


def _node_id(ip: str, mac: str = "") -> str:
    """ID estable: MAC cuando existe; IP como fallback."""
    normalized_mac = re.sub(r"[^0-9A-Fa-f]", "", mac or "").lower()
    if normalized_mac and normalized_mac not in {"000000000000", "ffffffffffff"}:
        return f"mac:{normalized_mac}"
    return f"ip:{ip}"


def _merge_values(old: list, new: Iterable) -> list:
    result = list(old or [])
    for item in new or []:
        if item not in result:
            result.append(item)
    return result


def _new_node(ip: str, **kwargs) -> dict:
    node = {
        "id": _node_id(ip, kwargs.get("mac", "")),
        "ip": ip,
        "mac": kwargs.get("mac", ""),
        "hostname": kwargs.get("hostname", ""),
        "vendor": kwargs.get("vendor", "Desconocido"),
        "tipo": kwargs.get("tipo", "Host"),
        "rol": kwargs.get("rol", "host"),
        "activo": kwargs.get("activo", True),
        "puertos": sorted(set(kwargs.get("puertos", []) or [])),
        "latencia_ms": kwargs.get("latencia_ms"),
        "riesgo": kwargs.get("riesgo", "NO EVALUADO"),
        "evidencia": list(kwargs.get("evidencia", []) or []),
        "verificaciones": list(kwargs.get("verificaciones", []) or []),
        "confianza": kwargs.get("confianza", "media"),
        "medio": kwargs.get("medio", "lan_no_clasificado"),
    }
    if kwargs.get("wifi"):
        node["wifi"] = kwargs["wifi"]
    return node


def _merge_node(nodes_by_id: dict, node: dict) -> dict:
    """Fusiona IP/MAC repetidas sin perder evidencias ni atributos."""
    # Primero intenta encontrar por IP para unir un hop con un host LAN.
    existing = None
    for candidate in nodes_by_id.values():
        if node.get("ip") and candidate.get("ip") == node.get("ip"):
            existing = candidate
            break
        if node.get("mac") and candidate.get("mac") == node.get("mac"):
            existing = candidate
            break

    if existing is None:
        nodes_by_id[node["id"]] = node
        return node

    for key in ("evidencia", "verificaciones"):
        existing[key] = _merge_values(existing.get(key, []), node.get(key, []))
    for key in ("puertos",):
        existing[key] = sorted(set(existing.get(key, []) + node.get(key, [])))
    for key in ("mac", "hostname", "vendor", "tipo", "rol", "riesgo"):
        if node.get(key) not in (None, "", "—", "Desconocido", "NO EVALUADO", "host"):
            if existing.get(key) in (None, "", "—", "Desconocido", "NO EVALUADO", "host"):
                existing[key] = node[key]
    if node.get("latencia_ms") is not None:
        existing["latencia_ms"] = node["latencia_ms"]
    if node.get("confianza") == "alta":
        existing["confianza"] = "alta"
    return existing


def _edge_key(source: str, target: str) -> tuple[str, str]:
    return tuple(sorted((source, target)))


def _add_edge(edges_by_key: dict, source: dict, target: dict, relation: str,
              evidence: Iterable[str], verified: bool, confidence: str,
              note: str = "") -> None:
    if source["id"] == target["id"]:
        return
    key = _edge_key(source["id"], target["id"])
    edge = edges_by_key.get(key)
    if edge is None:
        edge = {
            "source": source["id"],
            "target": target["id"],
            "relation": relation,
            "relaciones": [relation],
            "evidencia": [],
            "verificado": bool(verified),
            "confianza": confidence,
            "notas": [],
        }
        edges_by_key[key] = edge
    edge["relaciones"] = _merge_values(edge.get("relaciones", [edge["relation"]]), [relation])
    edge["relation"] = " + ".join(edge["relaciones"])
    edge["evidencia"] = _merge_values(edge["evidencia"], evidence)
    edge["verificado"] = edge["verificado"] and bool(verified)
    if confidence == "alta" or edge["confianza"] == "alta":
        edge["confianza"] = "alta"
    if note and note not in edge["notas"]:
        edge["notas"].append(note)


def _resolve_target(target: str) -> tuple[str, str]:
    ip = _safe_ip(target)
    if ip:
        return ip, target
    try:
        return socket.gethostbyname(target), target
    except OSError:
        return target, target


def build_topology(
    trace_targets: Iterable[str] | None = None,
    rango: str | None = None,
    scan_ports: bool = True,
    discover_fn: Callable | None = None,
    traceroute_fn: Callable | None = None,
    ping_fn: Callable | None = None,
    wifi_provider: Callable | None = None,
) -> dict:
    """Descubre una topología basada únicamente en conexiones verificables.

    Las funciones se pueden inyectar para pruebas y para integrar otros motores
    de descubrimiento sin acoplar el generador de topología al hardware.
    """
    discover = discover_fn or discover_lan
    trace = traceroute_fn or _traceroute
    ping = ping_fn or hacer_ping
    local_ip = _local_ip()
    gateway = detectar_gateway() or ""
    subnet = rango or ""
    if not subnet and local_ip:
        try:
            subnet = str(ipaddress.ip_network(f"{local_ip}/24", strict=False))
        except ValueError:
            subnet = ""

    nodes_by_id: dict[str, dict] = {}
    edges_by_key: dict[tuple[str, str], dict] = {}

    local = _new_node(
        local_ip or "local",
        hostname=socket.gethostname(),
        tipo="Estación de análisis",
        rol="local",
        evidencia=["interfaz_local"],
        verificaciones=["IP local detectada" if local_ip else "IP local no determinada"],
        confianza="alta" if local_ip else "media",
    )
    _merge_node(nodes_by_id, local)

    # Contexto Wi-Fi: se consulta el sistema local y, si está configurado,
    # la tabla de asociaciones del MikroTik/AP autorizado.
    local_wifi = local_wifi_context()
    wifi_error = ""
    try:
        wifi_data = (wifi_provider() if wifi_provider else mikrotik_wifi_clients()) or {}
    except Exception:
        # Wi-Fi/AP telemetry is optional: a failed provider must not abort the
        # LAN and traceroute portions of the topology report.
        wifi_data = {}
        wifi_error = "No se pudo consultar la telemetría Wi-Fi opcional."
    if not isinstance(wifi_data, dict):
        wifi_data = {}
        wifi_error = "El proveedor de telemetría Wi-Fi devolvió un formato inválido."
    wifi_data.setdefault("local", local_wifi)
    raw_wifi_clients = wifi_data.get("clientes", [])
    if isinstance(raw_wifi_clients, list):
        wifi_clients = [client for client in raw_wifi_clients if isinstance(client, dict)]
        if len(wifi_clients) != len(raw_wifi_clients) and not wifi_error:
            wifi_error = "Se ignoraron registros Wi-Fi con formato inválido."
    else:
        wifi_clients = []
        if not wifi_error:
            wifi_error = "El proveedor de telemetría Wi-Fi devolvió clientes inválidos."
    # Keep downstream annotators on the validated representation.
    wifi_data["clientes"] = wifi_clients
    if local_wifi.get("disponible") and local_wifi.get("ssid"):
        local["medio"] = "wifi"
        local["wifi"] = local_wifi

    # Escaneo LAN: cada resultado trae la ficha técnica disponible del equipo.
    lan_devices = []
    try:
        lan_devices = discover(rango=rango, scan_ports=scan_ports) or []
    except TypeError:
        # Compatibilidad con motores antiguos que no aceptan argumentos nombrados.
        try:
            lan_devices = discover(rango, scan_ports) or []
        except Exception:
            lan_error = "No se pudo completar el descubrimiento LAN."
        else:
            lan_error = ""
    except Exception:
        # El escaneo LAN es una fuente opcional de evidencia; no debe impedir
        # que se emita el resto del informe (gateway, Wi-Fi y ruta L3).
        lan_error = "No se pudo completar el descubrimiento LAN."
    else:
        lan_error = ""

    for raw in lan_devices:
        if not isinstance(raw, dict) or not raw.get("ip"):
            continue
        ip = str(raw["ip"])
        mac = raw.get("mac", "") or ""
        node = _new_node(
            ip,
            mac=mac,
            hostname=raw.get("hostname", ""),
            vendor=raw.get("vendor") or lookup_oui(mac),
            tipo=raw.get("tipo", "Host"),
            rol="gateway" if ip == gateway else "lan_host",
            activo=raw.get("activo", True),
            puertos=raw.get("puertos", []),
            latencia_ms=raw.get("latencia_ms", raw.get("latencia")),
            riesgo=raw.get("riesgo", "NO EVALUADO"),
            evidencia=["icmp" if raw.get("activo", True) else "descubrimiento"]
                      + (["arp"] if mac and mac != "—" else []),
            verificaciones=["Respuesta ICMP" if raw.get("activo", True) else "Detectado sin ICMP"],
            confianza="alta" if mac and mac != "—" else "media",
        )
        node = _merge_node(nodes_by_id, node)
        _add_edge(
            edges_by_key, local, node, "l2_adjacent",
            ["arp", "misma_subred"] if mac and mac != "—" else ["misma_subred"],
            bool(mac and mac != "—"),
            "alta" if mac and mac != "—" else "media",
            "ARP prueba vecindad L2; no identifica el puerto físico del switch.",
        )

    if lan_error:
        discovery_note = lan_error
    else:
        discovery_note = f"{len(lan_devices)} registros devueltos por el descubrimiento LAN."

    # Gateway: lo añadimos aunque el ping-sweep no lo haya devuelto.
    gateway_node = None
    if gateway:
        gateway_node = next((n for n in nodes_by_id.values() if n.get("ip") == gateway), None)
        if gateway_node is None:
            gateway_node = _new_node(
                gateway,
                hostname="",
                tipo="Gateway / Router",
                rol="gateway",
                evidencia=["ruta_por_defecto"],
                verificaciones=[],
                confianza="alta",
            )
            gateway_node = _merge_node(nodes_by_id, gateway_node)
        else:
            gateway_node["rol"] = "gateway"
            gateway_node["evidencia"] = _merge_values(gateway_node["evidencia"], ["ruta_por_defecto"])
        try:
            reachable, latency = ping(gateway, count=2, timeout=2)
        except Exception:
            reachable, latency = False, None
        gateway_node["verificaciones"].append("Gateway responde ICMP" if reachable else "Gateway no responde ICMP")
        gateway_node["activo"] = bool(gateway_node.get("activo") or reachable)
        if latency is not None:
            gateway_node["latencia_ms"] = latency
        _add_edge(
            edges_by_key, local, gateway_node, "default_route",
            ["ruta_por_defecto"] + (["icmp"] if reachable else []),
            bool(reachable or gateway_node.get("mac") not in ("", "—")),
            "alta" if reachable else "media",
            "La ruta por defecto identifica el gateway L3 local.",
        )

    # Clientes Wi-Fi confirmados por la tabla del AP/MikroTik pueden aparecer
    # aunque no respondan al ping-sweep. Se conserva su MAC y telemetría radio.
    wifi_clients = wifi_data.get("clientes", []) or []
    known_macs = {re.sub(r"[^0-9a-f]", "", n.get("mac", "").lower())
                  for n in nodes_by_id.values() if n.get("mac")}
    for client in wifi_clients:
        client_mac = re.sub(r"[^0-9a-f]", "", client.get("mac", "").lower())
        if not client_mac or client_mac in known_macs:
            continue
        wifi_node = _new_node(
            client.get("ip", ""),
            mac=client.get("mac", ""),
            hostname=client.get("hostname", ""),
            vendor=lookup_oui(client.get("mac", "")),
            tipo="Cliente Wi-Fi",
            rol="wifi_client",
            activo=True,
            medio="wifi",
            wifi={k: client.get(k, "") for k in ("interfaz", "senal", "tx_rate", "rx_rate", "uptime", "fuente")},
            evidencia=["tabla_asociacion_wifi"],
            verificaciones=["Asociación Wi-Fi confirmada por AP/MikroTik"],
            confianza="alta",
        )
        _merge_node(nodes_by_id, wifi_node)

    annotate_wifi_nodes(list(nodes_by_id.values()), wifi_data)
    wifi_router = wifi_data.get("router", "")
    wifi_anchor = next((n for n in nodes_by_id.values() if n.get("ip") == wifi_router), None)
    if wifi_anchor is None and gateway and wifi_clients:
        wifi_anchor = next((n for n in nodes_by_id.values() if n.get("ip") == gateway), None)
    if wifi_anchor:
        for wifi_node in nodes_by_id.values():
            if wifi_node.get("medio") == "wifi" and wifi_node["id"] != wifi_anchor["id"]:
                _add_edge(
                    edges_by_key, wifi_anchor, wifi_node, "wifi_association",
                    ["tabla_asociacion_wifi"], True, "alta",
                    "Asociación confirmada por la tabla del AP/MikroTik; no implica un puerto físico.",
                )

    targets = list(trace_targets or [DEFAULT_TRACE_TARGET])
    traces = []
    for target in targets:
        resolved_target, display_target = _resolve_target(str(target))
        try:
            hops = trace(str(target)) or []
        except Exception as exc:
            hops = []
            trace_error = str(exc)
        else:
            trace_error = ""
        trace_record = {
            "destino": display_target,
            "ip_destino": resolved_target,
            "saltos": hops,
            "error": trace_error,
        }
        traces.append(trace_record)

        previous = local
        observed_hops = []
        for hop in hops:
            if not isinstance(hop, dict):
                continue
            hop_ip = _safe_ip(hop.get("ip", ""))
            if not hop_ip or hop_ip == "0.0.0.0":
                continue
            hop_node = _new_node(
                hop_ip,
                hostname=hop.get("hostname") or "",
                tipo="Salto L3",
                rol="route_hop",
                latencia_ms=hop.get("lat_ms"),
                evidencia=["traceroute"],
                verificaciones=["Respuesta de traceroute" if not hop.get("timeout") else "Traceroute parcial"],
                confianza="alta" if not hop.get("timeout") else "media",
            )
            hop_node = _merge_node(nodes_by_id, hop_node)
            observed_hops.append(hop_node)
            _add_edge(
                edges_by_key, previous, hop_node, "l3_path",
                ["traceroute"],
                not bool(hop.get("timeout")),
                "alta" if not hop.get("timeout") else "media",
                "Camino L3 observado; no equivale a un enlace físico.",
            )
            previous = hop_node

        if resolved_target and _safe_ip(resolved_target):
            target_node = next((n for n in nodes_by_id.values() if n.get("ip") == resolved_target), None)
            if target_node is None:
                target_node = _new_node(
                    resolved_target,
                    hostname=display_target if display_target != resolved_target else "",
                    tipo="Destino trazado",
                    rol="trace_target",
                    evidencia=["destino_traceroute"],
                    verificaciones=[],
                    confianza="alta",
                )
                target_node = _merge_node(nodes_by_id, target_node)
            target_node["evidencia"] = _merge_values(target_node["evidencia"], ["destino_traceroute"])
            if observed_hops:
                _add_edge(
                    edges_by_key, observed_hops[-1], target_node, "l3_path",
                    ["traceroute_destino"],
                    bool(hops and not hops[-1].get("timeout", False)),
                    "alta" if hops and not hops[-1].get("timeout", False) else "media",
                    "Último salto observado antes del destino.",
                )
            else:
                # Si no hubo saltos pero el destino responde, la conexión se verifica por ICMP.
                try:
                    reachable, latency = ping(resolved_target, count=2, timeout=2)
                except Exception:
                    reachable, latency = False, None
                target_node["verificaciones"].append("Destino responde ICMP" if reachable else "Destino sin respuesta ICMP")
                if latency is not None:
                    target_node["latencia_ms"] = latency
                _add_edge(
                    edges_by_key, local, target_node, "reachability",
                    ["icmp"], bool(reachable), "media",
                    "No se observó una cadena de saltos; solo se verificó alcanzabilidad.",
                )

    nodes = sorted(nodes_by_id.values(), key=lambda n: (n.get("rol") != "local", n.get("ip", "")))
    edges = sorted(edges_by_key.values(), key=lambda e: (e["source"], e["target"]))
    warnings = [
        "La topología representa evidencias L2/L3 observadas desde este equipo.",
        "No se infieren conexiones entre dos hosts LAN si no existe evidencia directa.",
        "Un salto con timeout no se marca como enlace verificado.",
    ]
    if wifi_error:
        warnings.append(wifi_error)
    return {
        "ts": _now(),
        "local": {"ip": local_ip, "hostname": socket.gethostname()},
        "gateway": gateway,
        "subred": subnet,
        "nodos": nodes,
        "conexiones": edges,
        "trazas": traces,
        "resumen": {
            "nodos": len(nodes),
            "conexiones": len(edges),
            "conexiones_verificadas": sum(1 for e in edges if e["verificado"]),
            "equipos_lan": sum(1 for n in nodes if n["rol"] == "lan_host"),
            "saltos_l3": sum(1 for n in nodes if n["rol"] == "route_hop"),
            "equipos_wifi": sum(1 for n in nodes if n.get("medio") == "wifi" and n["rol"] != "local"),
        },
        "wifi": wifi_data,
        "evidencia": {
            "descubrimiento_lan": discovery_note,
            "metodo": ["ARP", "ICMP", "ruta por defecto", "traceroute", "DNS inverso", "puertos TCP comunes", "tabla de asociación Wi-Fi si está configurada"],
        },
        "advertencias": warnings,
    }


def render_topology_text(topology: dict) -> str:
    """Genera un reporte legible, incluyendo la ficha de cada nodo."""
    summary = topology.get("resumen", {})
    lines = [
        "VISOR — TOPOLOGÍA VERIFICADA",
        "=" * 72,
        f"Fecha: {topology.get('ts', '—')}",
        f"Estación: {topology.get('local', {}).get('hostname', '—')} ({topology.get('local', {}).get('ip', '—')})",
        f"Gateway: {topology.get('gateway') or 'No detectado'}",
        f"Subred: {topology.get('subred') or 'No determinada'}",
        f"Nodos: {summary.get('nodos', 0)} | Conexiones: {summary.get('conexiones', 0)} | Verificadas: {summary.get('conexiones_verificadas', 0)} | Wi-Fi: {summary.get('equipos_wifi', 0)}",
        "",
        "EQUIPOS DESCUBIERTOS",
        "-" * 72,
    ]
    for node in topology.get("nodos", []):
        ports = ", ".join(str(p) for p in node.get("puertos", [])) or "—"
        checks = "; ".join(node.get("verificaciones", [])) or "—"
        evidence = ", ".join(node.get("evidencia", [])) or "—"
        wifi = node.get("wifi", {})
        wifi_info = ""
        if node.get("medio") == "wifi":
            wifi_info = f" | Wi-Fi: interfaz={wifi.get('interfaz', '—')} señal={wifi.get('senal', '—')}"
        lines.extend([
            f"[{node.get('rol', 'host').upper()}] {node.get('ip') or 'IP no asociada'} — {node.get('tipo', 'Host')}",
            f"  Hostname: {node.get('hostname') or '—'} | MAC: {node.get('mac') or '—'} | Fabricante: {node.get('vendor') or '—'}",
            f"  Puertos: {ports} | Medio: {node.get('medio', '—')} | Riesgo: {node.get('riesgo', '—')} | Confianza: {node.get('confianza', '—')}{wifi_info}",
            f"  Evidencia: {evidence}",
            f"  Verificación: {checks}",
        ])
    lines.extend(["", "CONEXIONES OBSERVADAS", "-" * 72])
    by_id = {n["id"]: n for n in topology.get("nodos", [])}
    for edge in topology.get("conexiones", []):
        source = by_id.get(edge["source"], {}).get("ip") or edge["source"]
        target = by_id.get(edge["target"], {}).get("ip") or edge["target"]
        status = "VERIFICADA" if edge.get("verificado") else "PARCIAL / NO VERIFICADA"
        evidence = ", ".join(edge.get("evidencia", []))
        lines.append(f"{source} -> {target} | {edge.get('relation')} | {status} | {evidence}")
        for note in edge.get("notas", []):
            lines.append(f"  Nota: {note}")
    lines.extend(["", "LIMITACIONES", "-" * 72])
    lines.extend(f"- {warning}" for warning in topology.get("advertencias", []))
    return "\n".join(lines) + "\n"


def _dot_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def render_topology_dot(topology: dict) -> str:
    """Exporta Graphviz DOT sin ejecutar comandos externos."""
    lines = ["graph visor_topology {", "  rankdir=LR;", "  graph [fontname=Arial];", "  node [shape=box, fontname=Arial];"]
    for node in topology.get("nodos", []):
        label = f"{node.get('ip', '—')}\\n{node.get('tipo', 'Host')}\\n{node.get('hostname') or '—'}"
        shape = "doubleoctagon" if node.get("rol") == "local" else ("diamond" if node.get("rol") == "gateway" else "box")
        lines.append(f'  "{_dot_escape(node["id"])}" [label="{_dot_escape(label)}", shape={shape}];')
    for edge in topology.get("conexiones", []):
        style = "solid" if edge.get("verificado") else "dashed"
        label = f"{edge.get('relation', '')}\\n{','.join(edge.get('evidencia', []))}"
        lines.append(f'  "{_dot_escape(edge["source"])}" -- "{_dot_escape(edge["target"])}" [label="{_dot_escape(label)}", style={style}];')
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_topology_drawio(topology: dict) -> str:
    """Exporta una topología profesional y editable para diagrams.net/draw.io.

    El diseño separa LAN/Wi-Fi de la ruta WAN/L3, conserva las evidencias en
    cada enlace y agrega una leyenda para que el diagrama no confunda una ruta
    observada con un enlace físico.
    """
    root = ET.Element("mxfile", {
        "host": "app.diagrams.net",
        "modified": datetime.now().isoformat(timespec="seconds"),
        "agent": "Visor NOC Command Suite",
        "version": "24.7.17",
        "type": "device",
    })
    diagram = ET.SubElement(root, "diagram", {"id": "visor-topology", "name": "Visor NOC — Topología profesional"})
    graph = ET.SubElement(diagram, "mxGraphModel", {
        "dx": "1600", "dy": "900", "grid": "1", "gridSize": "10",
        "guides": "1", "tooltips": "1", "connect": "1", "arrows": "1",
        "fold": "1", "page": "1", "pageScale": "1", "pageWidth": "1600",
        "pageHeight": "900", "math": "0", "shadow": "0",
    })
    graph_root = ET.SubElement(graph, "root")
    ET.SubElement(graph_root, "mxCell", {"id": "0"})
    ET.SubElement(graph_root, "mxCell", {"id": "1", "parent": "0"})

    summary = topology.get("resumen", {})
    title = "VISOR NOC COMMAND SUITE — TOPOLOGÍA VERIFICADA"
    subtitle = (
        f"{topology.get('ts', '—')}  |  Subred: {topology.get('subred') or 'no determinada'}  |  "
        f"Nodos: {summary.get('nodos', len(topology.get('nodos', [])))}  |  "
        f"Wi-Fi confirmado: {summary.get('equipos_wifi', 0)}"
    )
    title_cell = ET.SubElement(graph_root, "mxCell", {
        "id": "title", "value": f"{title}\\n{subtitle}",
        "style": "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=18;fontStyle=1;fontColor=#17324D;",
        "vertex": "1", "parent": "1",
    })
    ET.SubElement(title_cell, "mxGeometry", {"x": "40", "y": "25", "width": "1450", "height": "55", "as": "geometry"})

    def add_lane(cell_id: str, label: str, x: int, y: int, width: int, height: int, fill: str) -> None:
        lane = ET.SubElement(graph_root, "mxCell", {
            "id": cell_id, "value": label,
            "style": f"swimlane;html=1;rounded=1;startSize=30;horizontal=1;fillColor={fill};strokeColor=#B7C5D3;fontColor=#17324D;fontStyle=1;",
            "vertex": "1", "parent": "1",
        })
        ET.SubElement(lane, "mxGeometry", {"x": str(x), "y": str(y), "width": str(width), "height": str(height), "as": "geometry"})

    add_lane("lane_lan", "LAN / WI-FI — VECINDAD LOCAL", 40, 105, 520, 420, "#F6FAFE")
    add_lane("lane_wan", "WAN / RUTA L3 — CAMINO OBSERVADO", 590, 105, 900, 420, "#FAFAFA")

    nodes = topology.get("nodos", [])
    cell_ids: dict[str, str] = {}
    local_nodes = [n for n in nodes if n.get("rol") == "local"]
    gateways = [n for n in nodes if n.get("rol") == "gateway"]
    wifi_nodes = [n for n in nodes if n.get("medio") == "wifi" and n.get("rol") != "local"]
    route_nodes = [n for n in nodes if n.get("rol") == "route_hop"]
    other_nodes = [n for n in nodes if n not in local_nodes + gateways + wifi_nodes + route_nodes]
    positions: dict[str, tuple[int, int]] = {}
    for i, node in enumerate(local_nodes):
        positions[node.get("id", str(i))] = (70, 185 + i * 125)
    for i, node in enumerate(gateways):
        positions[node.get("id", str(i))] = (340, 185 + i * 125)
    for i, node in enumerate(wifi_nodes):
        positions[node.get("id", str(i))] = (70 + (i % 2) * 245, 380 + (i // 2) * 115)
    for i, node in enumerate(other_nodes):
        positions[node.get("id", str(i))] = (70 + (i % 2) * 245, 380 + (i // 2) * 115)
    for i, node in enumerate(route_nodes):
        positions[node.get("id", str(i))] = (620 + i * 165, 205)

    for index, node in enumerate(nodes):
        node_id = node.get("id", str(index))
        cell_id = f"node_{index}"
        cell_ids[node_id] = cell_id
        ip = node.get("ip") or "IP no asociada"
        medium = node.get("medio", "lan_no_clasificado")
        medium_label = "Wi-Fi confirmado" if medium == "wifi" else ("LAN / medio no clasificado" if medium == "lan_no_clasificado" else medium)
        lines = [ip, f"{node.get('tipo', 'Host')}  ·  {node.get('rol', 'host')}"]
        if node.get("hostname"):
            lines.append(str(node["hostname"]))
        lines.append(medium_label)
        if node.get("mac"):
            lines.append(f"MAC: {node['mac']}")
        if node.get("wifi", {}).get("senal"):
            lines.append(f"Señal: {node['wifi']['senal']}")
        monitor = node.get("monitorizacion", {})
        if monitor:
            loss = monitor.get("perdida_pct", "—")
            avg = monitor.get("promedio_ms", "—")
            lines.append(f"ICMP: {loss}% pérdida / {avg} ms")
        evidence = node.get("evidencia", [])
        if evidence:
            lines.append("Evidencia: " + ", ".join(evidence[:3]))
        label = "\\n".join(lines)
        if node.get("rol") == "local":
            style = "shape=ellipse;whiteSpace=wrap;html=1;fillColor=#E8F1FB;strokeColor=#2878C8;strokeWidth=2;fontColor=#17324D;align=left;spacingLeft=10;"
        elif node.get("rol") == "gateway":
            style = "shape=rhombus;whiteSpace=wrap;html=1;fillColor=#FFF4CE;strokeColor=#D6A300;strokeWidth=2;fontColor=#5D4800;align=left;spacingLeft=10;"
        elif medium == "wifi":
            style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#E8F7EE;strokeColor=#178A44;strokeWidth=2;fontColor=#14532D;align=left;spacingLeft=10;"
        elif node.get("rol") == "route_hop":
            style = "shape=hexagon;whiteSpace=wrap;html=1;fillColor=#EEF1F4;strokeColor=#67727E;fontColor=#26323D;align=left;spacingLeft=10;"
        else:
            style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#7B8794;fontColor=#26323D;align=left;spacingLeft=10;"
        if "ALTO" in str(node.get("riesgo", "")):
            style += "strokeColor=#C0392B;"
        cell = ET.SubElement(graph_root, "mxCell", {
            "id": cell_id, "value": label, "style": style,
            "vertex": "1", "parent": "1",
        })
        x, y = positions.get(node_id, (70 + (index % 5) * 220, 550 + (index // 5) * 110))
        width = 220 if node.get("rol") != "route_hop" else 150
        ET.SubElement(cell, "mxGeometry", {"x": str(x), "y": str(y), "width": str(width), "height": "92", "as": "geometry"})

    for index, edge in enumerate(topology.get("conexiones", [])):
        source = cell_ids.get(edge.get("source"))
        target = cell_ids.get(edge.get("target"))
        if not source or not target:
            continue
        relation = edge.get("relation", "")
        evidence = ", ".join(edge.get("evidencia", []))
        label = relation + (f"\\n{evidence}" if evidence else "")
        if "wifi" in relation:
            color = "#178A44"
        elif "l3" in relation:
            color = "#3978C4"
        elif "default_route" in relation:
            color = "#B88700"
        else:
            color = "#59636E"
        style = f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2;strokeColor={color};fontColor=#26323D;"
        style += "dashed=0;" if edge.get("verificado") else "dashed=1;strokeWidth=1;"
        cell = ET.SubElement(graph_root, "mxCell", {
            "id": f"edge_{index}", "value": label, "style": style,
            "edge": "1", "parent": "1", "source": source, "target": target,
        })
        ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})

    legend_text = (
        "LEYENDA\\n"
        "━━  Conexión verificada\\n"
        "- -  Conexión parcial / no verificada\\n"
        "Azul: estación local   Amarillo: gateway   Verde: Wi-Fi confirmado   Gris: salto L3\\n"
        "La ruta L3 es un camino observado; no representa cableado físico."
    )
    legend = ET.SubElement(graph_root, "mxCell", {
        "id": "legend", "value": legend_text,
        "style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#F3F6F9;strokeColor=#B7C5D3;fontColor=#405465;align=left;spacingLeft=12;verticalAlign=middle;",
        "vertex": "1", "parent": "1",
    })
    ET.SubElement(legend, "mxGeometry", {"x": "40", "y": "580", "width": "1050", "height": "105", "as": "geometry"})

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", short_empty_elements=True) + "\n"

def save_topology_reports(topology: dict, directory: Path | None = None) -> dict:
    """Guarda JSON, TXT, DOT y DRAWIO; devuelve solo rutas locales generadas."""
    out_dir = Path(directory or REPORTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "json": out_dir / f"topology_{stamp}.json",
        "txt": out_dir / f"topology_{stamp}.txt",
        "dot": out_dir / f"topology_{stamp}.dot",
        "drawio": out_dir / f"topology_{stamp}.drawio",
    }
    paths["json"].write_text(json.dumps(topology, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["txt"].write_text(render_topology_text(topology), encoding="utf-8")
    paths["dot"].write_text(render_topology_dot(topology), encoding="utf-8")
    paths["drawio"].write_text(render_topology_drawio(topology), encoding="utf-8")
    return {key: str(path) for key, path in paths.items()}
