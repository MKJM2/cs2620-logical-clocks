import asyncio
import os
import tempfile
import unittest
import random
from pathlib import Path
import sys

# Ensure proper module import; adjust path as needed.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from machine import machine

# Dummy request to simulate a gRPC message
class DummyRequest:
    def __init__(self, sender_id, logical_time):
        self.sender_id = sender_id
        self.logical_time = logical_time

# Dummy stub to record calls to SendMessage
class DummyStub:
    def __init__(self):
        self.called = False

    async def SendMessage(self, request):
        self.called = True
        # Return a dummy acknowledgement
        class DummyAck:
            pass
        return DummyAck()

class TestMachine(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Patch _setup_server to avoid actual gRPC binding during tests.
        self._original_setup_server = machine._setup_server

        def dummy_setup_server(self_obj, port: int):
            # Instead of binding, set self_obj.server to a dummy with a stub method.
            class DummyServer:
                def add_insecure_port(self, addr):
                    # Return a dummy non-zero port number.
                    return port
            self_obj.server = DummyServer()
        machine._setup_server = dummy_setup_server

        # Create a temporary log file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_path = os.path.join(self.temp_dir.name, "machine.log")
        self.config = {"port": 5000, "ticks": 5, "log_path": self.log_path}
        # Create peers dictionary (simulate other machines)
        self.peers = {"B": {"port": 5001}, "C": {"port": 5002}}
        self.machine = machine("A", self.config, self.peers)

    def tearDown(self):
        # Restore the original _setup_server method
        machine._setup_server = self._original_setup_server
        self.temp_dir.cleanup()

    def test_initialization(self):
        self.assertEqual(self.machine.id, "A")
        self.assertEqual(self.machine.ticks_per_sec, 5)
        self.assertEqual(self.machine.clock, 0)
        # Check that the log file is created and empty
        self.assertTrue(Path(self.log_path).exists())
        self.assertEqual(Path(self.log_path).read_text(), "")

    def test_log_event(self):
        self.machine.clock = 10
        self.machine._log_event("INTERNAL")
        content = Path(self.log_path).read_text()
        self.assertIn("INTERNA", content)
        self.assertIn("10", content)

    async def test_send_message(self):
        dummy_req = DummyRequest("B", 5)
        # Clear the queue before test
        while not self.machine.queue.empty():
            self.machine.queue.get_nowait()
        await self.machine.SendMessage(dummy_req, None)
        queued_msg = await self.machine.queue.get()
        self.assertEqual(queued_msg.sender_id, "B")
        self.assertEqual(queued_msg.logical_time, 5)

    async def test_process_tick_with_message(self):
        # Test when a message is queued
        dummy_req = DummyRequest("B", 5)
        await self.machine.queue.put(dummy_req)
        self.machine.clock = 3
        await self.machine.process_tick()
        # Clock should be max(3, 5) + 1 = 6
        self.assertEqual(self.machine.clock, 6)
        self.assertTrue(self.machine.queue.empty())

    async def test_process_tick_internal_event(self):
        # Test branch when queue is empty and random number leads to an internal event.
        self.machine.queue = asyncio.Queue()  # ensure queue is empty
        self.machine.clock = 0
        # Force random.randint to return a value other than 1, 2, or 3 (e.g. 4)
        original_randint = random.randint
        random.randint = lambda a, b: 4
        try:
            logs = []
            original_log_event = self.machine._log_event
            self.machine._log_event = lambda event_type, target="": logs.append(event_type)
            await self.machine.process_tick()
            self.assertIn("INTERNAL", logs)
        finally:
            random.randint = original_randint
            self.machine._log_event = original_log_event

    async def test_process_tick_send_to_next(self):
        # Test branch when random returns 1 to send a message to the next machine.
        self.machine.queue = asyncio.Queue()
        self.machine.clock = 0
        dummy_stub = DummyStub()
        self.machine.stubs[self.machine.next_machine] = dummy_stub
        original_randint = random.randint
        random.randint = lambda a, b: 1
        try:
            await self.machine.process_tick()
            self.assertTrue(dummy_stub.called)
        finally:
            random.randint = original_randint

    async def test_process_tick_send_to_after_next(self):
        # Test branch when random returns 2 to send a message to the machine after next.
        self.machine.queue = asyncio.Queue()
        self.machine.clock = 0
        dummy_stub = DummyStub()
        self.machine.stubs[self.machine.after_next_machine] = dummy_stub
        original_randint = random.randint
        random.randint = lambda a, b: 2
        try:
            await self.machine.process_tick()
            self.assertTrue(dummy_stub.called)
        finally:
            random.randint = original_randint

    async def test_process_tick_broadcast(self):
        # Test branch when random returns 3 for broadcast.
        self.machine.queue = asyncio.Queue()
        self.machine.clock = 0
        dummy_stub1 = DummyStub()
        dummy_stub2 = DummyStub()
        self.machine.stubs = {"B": dummy_stub1, "C": dummy_stub2}
        original_randint = random.randint
        random.randint = lambda a, b: 3
        try:
            await self.machine.process_tick()
            self.assertTrue(dummy_stub1.called)
            self.assertTrue(dummy_stub2.called)
        finally:
            random.randint = original_randint

if __name__ == "__main__":
    unittest.main()