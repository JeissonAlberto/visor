import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from core.topology import render_topology_drawio, save_topology_reports


class DrawioTopologyTests(unittest.TestCase):
    def sample(self):
        return {
            "nodos": [
                {"id": "ip:192.168.1.10", "ip": "192.168.1.10", "tipo": "Estación", "rol": "local", "medio": "wifi", "wifi": {"senal": "-54dBm"}},
                {"id": "ip:192.168.1.1", "ip": "192.168.1.1", "tipo": "Gateway", "rol": "gateway", "medio": "lan_no_clasificado"},
            ],
            "conexiones": [{
                "source": "ip:192.168.1.10", "target": "ip:192.168.1.1",
                "relation": "default_route", "evidencia": ["icmp"], "verificado": True,
            }],
        }

    def test_generates_valid_drawio_xml(self):
        xml = render_topology_drawio(self.sample())
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, "mxfile")
        self.assertIsNotNone(root.find('.//mxCell[@id="node_0"]'))
        self.assertIsNotNone(root.find('.//mxCell[@id="edge_0"]'))

    def test_saves_drawio_alongside_other_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = save_topology_reports(self.sample(), Path(directory))
            self.assertIn("drawio", paths)
            self.assertTrue(Path(paths["drawio"]).exists())


if __name__ == "__main__":
    unittest.main()
