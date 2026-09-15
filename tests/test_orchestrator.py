import unittest
from unittest.mock import patch

from core.orchestrator import MissionOrchestrator


class OrchestratorInfraTests(unittest.TestCase):
    @patch("core.orchestrator.build_topology")
    def test_infra_mission_is_dispatched_without_mutating_devices(self, build_topology):
        build_topology.return_value = {"nodos": [], "conexiones": []}

        from core.orchestrator import run_orchestrated_task
        result = run_orchestrated_task(
            "INFRA_CHECK", target="192.0.2.1", network="192.0.2.0/24"
        )

        build_topology.assert_called_once_with(
            trace_targets=["192.0.2.1"], rango="192.0.2.0/24", scan_ports=False
        )
        self.assertEqual(result["tipo"], "INFRA_CHECK")
        self.assertEqual(result["topologia"], build_topology.return_value)


class OrchestratorLanTests(unittest.TestCase):
    @patch("core.orchestrator.discover_lan")
    def test_lan_mission_uses_available_discovery_engine(self, discover_lan):
        discover_lan.return_value = [{"ip": "192.0.2.10", "activo": True}]
        orchestrator = MissionOrchestrator(network="192.0.2.0/24")

        result = orchestrator.execute_lan_mission()

        discover_lan.assert_called_once_with("192.0.2.0/24")
        self.assertEqual(result["dispositivos"], discover_lan.return_value)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["activos"], 1)


if __name__ == "__main__":
    unittest.main()
