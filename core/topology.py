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
from typing import Callable, Iterable

from core.health import traceroute as _traceroute
from core.lan_vision import discover_lan, lookup_oui
from core.red import detectar_gateway, hacer_ping


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
    }
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

    # Escaneo LAN: cada resultado trae la ficha técnica disponible del equipo.
    lan_devices = []
    try:
        lan_devices = discover(rango=rango, scan_ports=scan_ports) or []
    except TypeError:
        # Compatibilidad con motores antiguos que no aceptan argumentos nombrados.
        lan_devices = discover(rango, scan_ports) or []
    except Exception as exc:
        lan_error = f"No se pudo completar el descubrimiento LAN: {exc}"
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
        },
        "evidencia": {
            "descubrimiento_lan": discovery_note,
            "metodo": ["ARP", "ICMP", "ruta por defecto", "traceroute", "DNS inverso", "puertos TCP comunes"],
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
        f"Nodos: {summary.get('nodos', 0)} | Conexiones: {summary.get('conexiones', 0)} | Verificadas: {summary.get('conexiones_verificadas', 0)}",
        "",
        "EQUIPOS DESCUBIERTOS",
        "-" * 72,
    ]
    for node in topology.get("nodos", []):
        ports = ", ".join(str(p) for p in node.get("puertos", [])) or "—"
        checks = "; ".join(node.get("verificaciones", [])) or "—"
        evidence = ", ".join(node.get("evidencia", [])) or "—"
        lines.extend([
            f"[{node.get('rol', 'host').upper()}] {node.get('ip', '—')} — {node.get('tipo', 'Host')}",
            f"  Hostname: {node.get('hostname') or '—'} | MAC: {node.get('mac') or '—'} | Fabricante: {node.get('vendor') or '—'}",
            f"  Puertos: {ports} | Riesgo: {node.get('riesgo', '—')} | Confianza: {node.get('confianza', '—')}",
            f"  Evidencia: {evidence}",
            f"  Verificación: {checks}",
        ])
    lines.extend(["", "CONEXIONES OBSERVADAS", "-" * 72])
    by_id = {n["id"]: n for n in topology.get("nodos", [])}
    for edge in topology.get("conexiones", []):
        source = by_id.get(edge["source"], {}).get("ip", edge["source"])
        target = by_id.get(edge["target"], {}).get("ip", edge["target"])
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


def save_topology_reports(topology: dict, directory: Path | None = None) -> dict:
    """Guarda JSON, TXT y DOT; devuelve solo rutas locales generadas."""
    out_dir = Path(directory or REPORTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = {
        "json": out_dir / f"topology_{stamp}.json",
        "txt": out_dir / f"topology_{stamp}.txt",
        "dot": out_dir / f"topology_{stamp}.dot",
    }
    paths["json"].write_text(json.dumps(topology, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["txt"].write_text(render_topology_text(topology), encoding="utf-8")
    paths["dot"].write_text(render_topology_dot(topology), encoding="utf-8")
    return {key: str(path) for key, path in paths.items()}
