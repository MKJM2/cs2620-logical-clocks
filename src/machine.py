import asyncio
import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import Dict

import grpc
from grpc import aio

from .protos import clock_pb2, clock_pb2_grpc

### Logging configuration for immediate flushing to orchestrator parent

class FlushStreamHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
    force=True
)

# Remove preexisting handlers (if any) and install our flush-capable one.
root_logger = logging.getLogger()
root_logger.handlers.clear()
handler = FlushStreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

# Make sure the output is flushed when `--verbose` flag is present
sys.stdout.reconfigure(line_buffering=True)


class machine(clock_pb2_grpc.MachineServiceServicer):
    def __init__(self, machine_id: str, config: dict, peers: dict):
        self.id = machine_id
        self.logger = logging.getLogger(f"machine-{machine_id}")
        self.clock = 0
        self.ticks_per_sec = config["ticks"]
        self.internal_event_weight = config.get("internal_event_weight", 7)
        self.log_path = Path(config["log_path"])
        self.peers = peers
        self.queue = asyncio.Queue()
        self.stubs: Dict[str, clock_pb2_grpc.MachineServiceStub] = {}
        self.server = aio.server()

        # Node topology of our machines according to config file
        self.all_machine_ids = sorted([self.id] + list(peers.keys()))
        self.my_position = self.all_machine_ids.index(self.id)
        self.total_machines = len(self.all_machine_ids)
        self.next_machine = self.all_machine_ids[(self.my_position + 1) % self.total_machines]
        self.after_next_machine = self.all_machine_ids[(self.my_position + 2) % self.total_machines]

        self._setup_logging()
        self._setup_server(config["port"])
        self.logger.info(f"initialized with {self.ticks_per_sec} ticks/sec")

    def _setup_logging(self):
        self.log_path.parent.mkdir(exist_ok=True)
        self.log_path.write_text("")
        self.logger.info(f"logging to {self.log_path}")

    def _setup_server(self, port: int):
        clock_pb2_grpc.add_MachineServiceServicer_to_server(self, self.server)
        self.server.add_insecure_port(f"[::]:{port}")
        self.logger.info(f"server set up on port {port}")

    async def connect_to_peers(self):
        for peer_id, peer_config in self.peers.items():
            if peer_id == self.id:
                continue

            for attempt in range(3):
                try:
                    channel = aio.insecure_channel(f"localhost:{peer_config['port']}")
                    stub = clock_pb2_grpc.MachineServiceStub(channel)
                    # Optionally perform a simple RPC (if available) here to check health.
                    # For now, we assume if we can create the stub without exception,
                    # the connection will eventually be established.
                    self.stubs[peer_id] = stub
                    self.logger.info(f"connected to peer {peer_id} on port {peer_config['port']}")
                    break
                except grpc.aio.AioRpcError as e:
                    self.logger.warning(f"failed to connect to {peer_id}, attempt {attempt}: {e}")
                    await asyncio.sleep(0.5)
            else:
                self.logger.error(f"Could not connect to peer {peer_id}")

    async def SendMessage(self, request, context):
        await self.queue.put(request)
        self.logger.info(f"received message from {request.sender_id}, logical time {request.logical_time}")
        return clock_pb2.Ack()

    async def run(self):
        self.logger.info("starting server...")
        await self.server.start()
        await asyncio.sleep(0.5)  # Simple, but prevents race conditions w/ other machines
        self.logger.info("server started")
        await self.connect_to_peers()
        try:
            interval = 1.0 / self.ticks_per_sec
            while True:
                start = time.monotonic()
                await self.process_tick()
                elapsed = time.monotonic() - start
                await asyncio.sleep(max(0, interval - elapsed))

        except asyncio.CancelledError:
            self.logger.info("shutting down...")
            await self.server.stop(grace=1)
            await self.server.wait_for_termination()

    async def process_tick(self):
        if not self.queue.empty():
            msg = await self.queue.get()
            self.clock = max(self.clock, msg.logical_time) + 1
            self._log_event("RECV", msg.sender_id)
            self.logger.info(f"processed message from {msg.sender_id}, clock now {self.clock}")
        else:
            rand_val = random.randint(1, 3 + self.internal_event_weight)
            self.clock += 1

            if rand_val == 1:  # Send to the next machine
                await self._send_to(self.next_machine)
                self.logger.info(f"sent message to {self.next_machine} (next), clock now {self.clock}")
            elif rand_val == 2:  # Send to the machine after next
                await self._send_to(self.after_next_machine)
                self.logger.info(f"sent message to {self.after_next_machine} (after next), clock now {self.clock}")
            elif rand_val == 3:  # Broadcast to all peers
                await self._send_broadcast()
                self.logger.info(f"broadcast message to all peers, clock now {self.clock}")
            else:  # Internal event
                self._log_event("INTERNAL")
                self.logger.info(f"internal event, clock now {self.clock}")

    async def _send_to(self, target_id: str):
        stub = self.stubs.get(target_id)
        if stub:
            await stub.SendMessage(
                clock_pb2.ClockMessage(logical_time=self.clock, sender_id=self.id)
            )
            self._log_event("SEND", target_id)

    async def _send_broadcast(self):
        targets = list(self.stubs.keys())
        targets_str = ",".join(targets)
        self._log_event("BROADCAST", targets_str)
        for _target_id, stub in self.stubs.items():
            await stub.SendMessage(
                clock_pb2.ClockMessage(logical_time=self.clock, sender_id=self.id)
            )

    def _log_event(self, event_type: str, target: str = ""):
        log_line = (
            f"{time.time()}|{self.clock}|{event_type}|{self.queue.qsize()}|{target}\n"
        )
        with open(self.log_path, "a") as f:
            f.write(log_line)


async def start_machine_from_args():
    if len(sys.argv) < 5:
        logging.error("usage: python -m src.machine <machine_id> <port> <ticks> <log_path> <internal_event_weight>")
        sys.exit(1)
    machine_id = sys.argv[1]
    port = int(sys.argv[2])
    ticks = int(sys.argv[3])
    log_path = sys.argv[4]
    internal_event_weight = int(sys.argv[5])
    peers = {}
    if "PEERS" in os.environ:
        peers_str = os.environ["PEERS"]
        for peer in peers_str.split(","):
            if peer:
                peer_id, peer_port = peer.split(":")
                peers[peer_id] = {"port": int(peer_port)}
    config = {"port": port, "ticks": ticks, "log_path": log_path, "internal_event_weight": internal_event_weight}
    m = machine(machine_id, config, peers)
    await m.run()


if __name__ == "__main__":
    asyncio.run(start_machine_from_args())
