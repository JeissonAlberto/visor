"""
core/wifi.py — Contexto Wi-Fi local y asociaciones conocidas.

La tabla ARP permite descubrir clientes Wi-Fi dentro de la misma subred, pero no
permite saber por sí sola si un equipo está conectado por cable o radio. Cuando
se dispone de un MikroTik/AP autorizado, se consulta su registration-table para
confirmar MAC, interfaz, señal y tasas del cliente. Nunca se imprimen secretos.
"""

import os
import platform
import re
import subprocess
from typing import Callable

from config.settings import MIKROTIK_HOST, MIKROTIK_USER, MIKROTIK_PASS
from core.mikrotik_agent import _ssh_cmd


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _mac(value: str) -> str:
    return re.sub(r"[^0-9a-f]", "", str(value or "").lower())


def _run(command: list[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return result.stdout or ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _parse_key_value_lines(output: str) -> dict:
    data = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[_clean(key).lower()] = _clean(value)
    return data


def _pick(data: dict, *keys: str) -> str:
    for key in keys:
        value = data.get(key.lower(), "")
        if value:
            return value
    return ""


def local_wifi_context(run_fn: Callable | None = None) -> dict:
    """Devuelve SSID/BSSID y estado de la interfaz Wi-Fi local."""
    runner = run_fn or _run
    system = platform.system().lower()
    raw = ""
    method = "none"
    if system == "windows":
        raw = runner(["netsh", "wlan", "show", "interfaces"])
        method = "netsh"
    elif system == "linux":
        raw = runner(["nmcli", "-t", "-f", "GENERAL.TYPE,GENERAL.CONNECTION,GENERAL.HWADDR,GENERAL.STATE", "device", "show"])
        method = "nmcli"
    data = _parse_key_value_lines(raw)
    # Windows labels are localized; inspect values by their stable field names
    # and keep the raw parser conservative when the OS uses another language.
    result = {
        "disponible": bool(raw.strip()),
        "metodo": method,
        "ssid": _pick(data, "ssid", "general.connection"),
        "bssid": _pick(data, "bssid", "general.hwaddr"),
        "senal": _pick(data, "signal", "signal strength", "señal"),
        "canal": _pick(data, "channel", "canal"),
        "radio": _pick(data, "radio type", "tipo de radio", "general.type"),
        "estado": _pick(data, "state", "estado", "general.state"),
    }
    if system == "linux" and "wifi" in raw.lower():
        result["disponible"] = True
    return result


def _parse_registration_table(raw: str, source: str) -> list[dict]:
    clients = []
    for line in raw.splitlines():
        text = _clean(line)
        if not text or text.upper().startswith("ERROR"):
            continue
        fields = [part.strip() for part in text.split("|")]
        if len(fields) < 2 or not re.search(r"[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}", fields[0]):
            continue
        client = {
            "mac": fields[0].upper(),
            "interfaz": fields[1] if len(fields) > 1 else "",
            "senal": fields[2] if len(fields) > 2 else "",
            "tx_rate": fields[3] if len(fields) > 3 else "",
            "rx_rate": fields[4] if len(fields) > 4 else "",
            "uptime": fields[5] if len(fields) > 5 else "",
            "medio": "wifi",
            "fuente": source,
        }
        clients.append(client)
    return clients


def mikrotik_wifi_clients(host: str | None = None, user: str | None = None,
                          password: str | None = None,
                          ssh_fn: Callable | None = None) -> dict:
    """Consulta asociaciones Wi-Fi solo si el router y la credencial están configurados."""
    router = (host or os.getenv("VISOR_WIFI_ROUTER_HOST") or MIKROTIK_HOST or "").strip()
    username = user or os.getenv("VISOR_MIKROTIK_USER") or MIKROTIK_USER
    secret = password if password is not None else os.getenv("VISOR_MIKROTIK_PASS", MIKROTIK_PASS)
    if not router or "X" in router.upper() or not secret:
        return {
            "disponible": False,
            "fuente": "mikrotik_registration_table",
            "router": router,
            "clientes": [],
            "motivo": "Configura VISOR_WIFI_ROUTER_HOST y VISOR_MIKROTIK_PASS para confirmar asociaciones Wi-Fi.",
        }

    ssh = ssh_fn or _ssh_cmd
    commands = [
        ("routeros_wireless", ':foreach i in=[/interface wireless registration-table find] do={:put ([/interface wireless registration-table get $i mac-address]."|".[/interface wireless registration-table get $i interface]."|".[/interface wireless registration-table get $i signal-strength]."|".[/interface wireless registration-table get $i tx-rate]."|".[/interface wireless registration-table get $i rx-rate]."|".[/interface wireless registration-table get $i uptime])}'),
        ("routeros_wifi", ':foreach i in=[/interface wifi registration-table find] do={:put ([/interface wifi registration-table get $i mac-address]."|".[/interface wifi registration-table get $i interface]."|".[/interface wifi registration-table get $i signal]."|".[/interface wifi registration-table get $i tx-rate]."|".[/interface wifi registration-table get $i rx-rate]."|".[/interface wifi registration-table get $i uptime])}'),
    ]
    clients = []
    for source, command in commands:
        try:
            raw = ssh(router, username, secret, command, timeout=5)
        except Exception:
            raw = ""
        clients.extend(_parse_registration_table(raw, source))

    unique = {}
    for client in clients:
        unique[_mac(client["mac"])] = client
    return {
        "disponible": bool(unique),
        "fuente": "mikrotik_registration_table",
        "router": router,
        "clientes": list(unique.values()),
        "motivo": "" if unique else "No se encontraron asociaciones activas o el modelo no expone registration-table.",
    }


def annotate_wifi_nodes(nodes: list[dict], wifi_data: dict) -> list[dict]:
    """Marca nodos cuya MAC aparece en una tabla de asociación Wi-Fi confirmada."""
    clients = {_mac(c.get("mac")): c for c in wifi_data.get("clientes", []) if c.get("mac")}
    for node in nodes:
        if node.get("rol") == "local":
            continue
        node.setdefault("medio", "lan_no_clasificado")
        if node.get("mac") and _mac(node.get("mac")) in clients:
            client = clients[_mac(node["mac"])]
            node["medio"] = "wifi"
            node["wifi"] = {
                "interfaz": client.get("interfaz", ""),
                "senal": client.get("senal", ""),
                "tx_rate": client.get("tx_rate", ""),
                "rx_rate": client.get("rx_rate", ""),
                "uptime": client.get("uptime", ""),
                "fuente": client.get("fuente", wifi_data.get("fuente", "")),
            }
            node.setdefault("evidencia", []).append("tabla_asociacion_wifi")
            node.setdefault("verificaciones", []).append("Asociación Wi-Fi confirmada por AP/MikroTik")
            node["confianza"] = "alta"
    return nodes
