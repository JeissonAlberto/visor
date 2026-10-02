import contextlib
import io
import unittest
from concurrent.futures import Future
from unittest.mock import patch

from core.orchestrator import MissionOrchestrator, _spinner_task


class SpinnerTaskTests(unittest.TestCase):
    def test_worker_exception_does_not_print_sensitive_exception_text(self):
        future = Future()
        future.set_exception(RuntimeError("api_key=do-not-leak"))
        output = io.StringIO()

        with patch("core.orchestrator.time.time", side_effect=AssertionError("wall clock used")):
            with contextlib.redirect_stdout(output):
                result = _spinner_task("agent", future, timeout=1)

        self.assertIsNone(result)
        self.assertIn("RuntimeError (detalle omitido)", output.getvalue())
        self.assertNotIn("do-not-leak", output.getvalue())

    def test_timeout_uses_monotonic_clock_and_cancels_pending_future(self):
        future = Future()
        output = io.StringIO()

        with patch("core.orchestrator.time.monotonic", side_effect=[100.0, 102.0]):
            with patch("core.orchestrator.time.time", side_effect=AssertionError("wall clock used")):
                with contextlib.redirect_stdout(output):
                    result = _spinner_task("agent", future, timeout=1)

        self.assertIsNone(result)
        self.assertTrue(future.cancelled())
        self.assertIn("TIMEOUT (1s)", output.getvalue())


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
