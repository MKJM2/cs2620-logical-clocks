import asyncio
import os
import signal
import tempfile
import unittest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from orchestrator import orchestrator

# Dummy classes for simulating a subprocess
class DummyStream:
    async def readline(self):
        return b''

class DummyProcess:
    def __init__(self):
        self.stdout = DummyStream()
        self.stderr = DummyStream()
        self.returncode = 0

    async def wait(self):
        return 0

class TestOrchestrator(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Create a temporary config file with a sample TOML content
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "config.toml")
        config_content = """
[machines]
A = {port = 5000, ticks = 5, log_path = "a.log"}
B = {port = 5001, ticks = 10, log_path = "b.log"}
"""
        with open(self.config_path, "w") as f:
            f.write(config_content)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_config(self):
        orch = orchestrator(config_path=self.config_path)
        self.assertIn("A", orch.config)
        self.assertIn("B", orch.config)
        self.assertEqual(orch.config["A"]["ticks"], 5)
        self.assertEqual(orch.config["B"]["port"], 5001)

    def test_apply_config_overrides(self):
        base_config = {
            "A": {"port": 5000, "ticks": 5, "log_path": "a.log"}
        }
        overrides = {
            "A": {"ticks": 10},
            "B": {"port": 5001, "ticks": 8, "log_path": "b.log"}
        }
        orch = orchestrator(config_path=self.config_path)
        orch.config = base_config
        orch._apply_config_overrides(orch.config, overrides)
        self.assertEqual(orch.config["A"]["ticks"], 10)
        self.assertEqual(orch.config["B"]["port"], 5001)

    def test_peer_env(self):
        orch = orchestrator(config_path=self.config_path)
        peers = {
            "A": {"port": 5000},
            "B": {"port": 5001}
        }
        env = orch._peer_env(peers)
        self.assertIn("PEERS", env)
        # Since dict ordering might vary, check that both substrings are present.
        self.assertIn("A:5000", env["PEERS"])
        self.assertIn("B:5001", env["PEERS"])

    def test_handle_exit(self):
        orch = orchestrator(config_path=self.config_path)
        self.assertTrue(orch.running)
        orch._handle_exit(signal.SIGINT, None)
        self.assertFalse(orch.running)

    async def test_start_machine(self):
        orch = orchestrator(config_path=self.config_path, verbose=True)
        # Monkey-patch asyncio.create_subprocess_exec to return a dummy process.
        async def dummy_create_subprocess_exec(*args, **kwargs):
            return DummyProcess()

        original_create = asyncio.create_subprocess_exec
        asyncio.create_subprocess_exec = dummy_create_subprocess_exec
        try:
            await orch.start_machine("A")
            self.assertIn("A", orch.processes)
        finally:
            asyncio.create_subprocess_exec = original_create

if __name__ == "__main__":
    unittest.main()