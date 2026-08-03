import unittest
from unittest.mock import patch

from core.topology import build_topology, render_topology_dot, render_topology_text


class TopologyTests(unittest.TestCase):
    def setUp(self):
        self.devices = [
            {
                "ip": "192.168.1.1",
                "mac": "AA:BB:CC:00:00:01",
                "hostname": "router",
                "vendor": "MikroTik",
                "tipo": "Router",
                "activo": True,
                "puertos": [80, 8291],
                "riesgo": "🟡 MEDIO",
            },
            {
                "ip": "192.168.1.20",
                "mac": "AA:BB:CC:00:00:20",
                "hostname": "servidor",
                "vendor": "VMware",
                "tipo": "Servidor",
                "activo": True,
                "puertos": [22],
            },
        ]

    def discover(self, rango=None, scan_ports=True):
        return self.devices

    def trace(self, target):
        return [
            {"hop": 1, "ip": "192.168.1.1", "hostname": "router", "lat_ms": 1.2, "timeout": False},
            {"hop": 2, "ip": "203.0.113.1", "hostname": "isp-hop", "lat_ms": 12.5, "timeout": False},
        ]

    @staticmethod
    def ping(host, count=1, timeout=2):
        return True, 1.0

    @patch("core.topology.detectar_gateway", return_value="192.168.1.1")
    @patch("core.topology._local_ip", return_value="192.168.1.10")
    def test_merges_lan_and_traceroute_without_inventing_host_links(self, _local, _gateway):
        result = build_topology(
            trace_targets=["198.51.100.20"],
            discover_fn=self.discover,
            traceroute_fn=self.trace,
            ping_fn=self.ping,
        )

        self.assertEqual(result["gateway"], "192.168.1.1")
        self.assertEqual(result["resumen"]["equipos_lan"], 1)
        self.assertGreaterEqual(result["resumen"]["saltos_l3"], 1)
        ips = {node["ip"] for node in result["nodos"]}
        self.assertIn("192.168.1.20", ips)
        self.assertIn("203.0.113.1", ips)

        # No se conecta artificialmente el servidor con el router u otro host LAN.
        node_by_ip = {node["ip"]: node for node in result["nodos"]}
        server_id = node_by_ip["192.168.1.20"]["id"]
        router_id = node_by_ip["192.168.1.1"]["id"]
        self.assertFalse(any(
            {edge["source"], edge["target"]} == {server_id, router_id}
            for edge in result["conexiones"]
        ))

        gateway_edges = [
            edge for edge in result["conexiones"]
            if "default_route" in edge.get("relaciones", [])
        ]
        self.assertTrue(gateway_edges)
        self.assertTrue(gateway_edges[0]["verificado"])

    @patch("core.topology.detectar_gateway", return_value="")
    @patch("core.topology._local_ip", return_value="192.168.1.10")
    def test_timeout_is_not_marked_as_verified(self, _local, _gateway):
        def partial_trace(target):
            return [{"hop": 1, "ip": "192.168.1.1", "lat_ms": None, "timeout": True}]

        result = build_topology(
            trace_targets=["198.51.100.20"],
            discover_fn=lambda **kwargs: [],
            traceroute_fn=partial_trace,
            ping_fn=lambda *args, **kwargs: (False, None),
        )
        trace_edges = [edge for edge in result["conexiones"] if edge["relation"] == "l3_path"]
        self.assertTrue(trace_edges)
        self.assertFalse(trace_edges[0]["verificado"])

    def test_renderers_include_evidence_and_verification(self):
        result = {
            "ts": "now",
            "local": {"ip": "192.168.1.10", "hostname": "noc"},
            "gateway": "192.168.1.1",
            "subred": "192.168.1.0/24",
            "resumen": {"nodos": 1, "conexiones": 0, "conexiones_verificadas": 0},
            "nodos": [{
                "id": "ip:192.168.1.10", "ip": "192.168.1.10", "mac": "", "hostname": "noc",
                "vendor": "Desconocido", "tipo": "Host", "rol": "local", "puertos": [],
                "riesgo": "NO EVALUADO", "evidencia": ["interfaz_local"],
                "verificaciones": ["IP local detectada"], "confianza": "alta",
            }],
            "conexiones": [], "trazas": [], "advertencias": ["Solo evidencia observada."],
        }
        self.assertIn("EQUIPOS DESCUBIERTOS", render_topology_text(result))
        self.assertIn("192.168.1.10", render_topology_dot(result))


if __name__ == "__main__":
    unittest.main()
