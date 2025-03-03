import asyncio
import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import Dict

from grpc import aio

from .protos import clock_pb2, clock_pb2_grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class machine(clock_pb2_grpc.MachineServiceServicer):
    def __init__(self, machine_id: str, config: dict, peers: dict):
        self.id = machine_id
        self.logger = logging.getLogger(f"machine-{machine_id}")
        self.clock = 0
        self.ticks_per_sec = config["ticks"]
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
            channel = aio.insecure_channel(f"localhost:{peer_config['port']}")
            self.stubs[peer_id] = clock_pb2_grpc.MachineServiceStub(channel)
            self.logger.info(f"connected to peer {peer_id} on port {peer_config['port']}")

    async def SendMessage(self, request, context):
        await self.queue.put(request)
        self.logger.info(f"received message from {request.sender_id}, logical time {request.logical_time}")
        return clock_pb2.Ack()

    async def run(self):
        self.logger.info("starting server...")
        await self.server.start()
        self.logger.info("server started")
        await self.connect_to_peers()
        try:
            interval = 1.0 / self.ticks_per_sec
            next_tick = time.monotonic()  # More precise timing
            
            while True:
                await self.process_tick()
                
                # Maintain exact tick intervals
                now = time.monotonic()
                next_tick += interval
                sleep_time = next_tick - now
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            self.logger.info("shutting down...")
            await self.server.stop(grace=None)
    
    async def process_tick(self):
        if not self.queue.empty():
            msg = await self.queue.get()
            self.clock = max(self.clock, msg.logical_time) + 1
            self._log_event("RECV", msg.sender_id)
            self.logger.info(f"processed message from {msg.sender_id}, clock now {self.clock}")
        else:
            rand_val = random.randint(1, 10)
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
        logging.error("usage: python -m src.machine <machine_id> <port> <ticks> <log_path>")
        sys.exit(1)
    machine_id = sys.argv[1]
    port = int(sys.argv[2])
    ticks = int(sys.argv[3])
    log_path = sys.argv[4]
    peers = {}
    if "PEERS" in os.environ:
        peers_str = os.environ["PEERS"]
        for peer in peers_str.split(","):
            if peer:
                peer_id, peer_port = peer.split(":")
                peers[peer_id] = {"port": int(peer_port)}
    config = {"port": port, "ticks": ticks, "log_path": log_path}
    m = machine(machine_id, config, peers)
    await m.run()


if __name__ == "__main__":
    asyncio.run(start_machine_from_args())
