import asyncio
import random
import time
from pathlib import Path
from typing import Dict
import grpc
from grpc import aio
import sys
import os
from rich.console import Console

from .protos import clock_pb2, clock_pb2_grpc

console = Console()

class machine(clock_pb2_grpc.MachineServiceServicer):
    def __init__(self, machine_id: str, config: dict, peers: dict):
        self.id = machine_id
        self.clock = 0
        self.ticks_per_sec = config['ticks']
        self.log_path = Path(config['log_path'])
        self.peers = peers
        self.queue = asyncio.Queue()
        self.stubs: Dict[str, clock_pb2_grpc.MachineServiceStub] = {}
        self.server = aio.server()
        self._setup_logging()
        self._setup_server(config['port'])
        console.log(f"machine {self.id} initialized with {self.ticks_per_sec} ticks/sec", style="bold blue")

    def _setup_logging(self):
        self.log_path.parent.mkdir(exist_ok=True)
        self.log_path.write_text("")
        console.log(f"machine {self.id}: logging to {self.log_path}", style="green")

    def _setup_server(self, port: int):
        clock_pb2_grpc.add_MachineServiceServicer_to_server(self, self.server)
        self.server.add_insecure_port(f"[::]:{port}")
        console.log(f"machine {self.id}: server set up on port {port}", style="green")

    async def connect_to_peers(self):
        for peer_id, peer_config in self.peers.items():
            if peer_id == self.id:
                continue
            channel = aio.insecure_channel(f"localhost:{peer_config['port']}")
            self.stubs[peer_id] = clock_pb2_grpc.MachineServiceStub(channel)
            console.log(f"machine {self.id}: connected to peer {peer_id} on port {peer_config['port']}", style="cyan")

    async def SendMessage(self, request, context):
        await self.queue.put(request)
        console.log(f"machine {self.id}: received message from {request.sender_id}, logical time {request.logical_time}", style="magenta")
        return clock_pb2.Ack()

    async def run(self):
        console.log(f"machine {self.id}: starting server...", style="bold blue")
        await self.server.start()
        console.log(f"machine {self.id}: server started", style="bold green")
        await self.connect_to_peers()
        try:
            while True:
                start_time = time.time()
                await self.process_tick()
                elapsed = time.time() - start_time
                await asyncio.sleep(max(0, 1 / self.ticks_per_sec - elapsed))
        except asyncio.CancelledError:
            console.log(f"machine {self.id}: shutting down...", style="bold red")
            await self.server.stop(grace=None)

    async def process_tick(self):
        if not self.queue.empty():
            msg = await self.queue.get()
            self.clock = max(self.clock, msg.logical_time) + 1
            self._log_event("RECV", msg.sender_id)
            console.log(f"machine {self.id}: processed message from {msg.sender_id}, clock now {self.clock}", style="magenta")
        else:
            rand_val = random.randint(1, 10)
            self.clock += 1
            if rand_val == 1:
                target_id = "B" if self.id == "A" else "A"
                await self._send_to(target_id)
                console.log(f"machine {self.id}: sent message to {target_id}, clock now {self.clock}", style="cyan")
            elif rand_val == 2:
                await self._send_to("C")
                console.log(f"machine {self.id}: sent message to C, clock now {self.clock}", style="cyan")
            elif rand_val == 3:
                await self._send_broadcast()
                console.log(f"machine {self.id}: broadcast message to all peers, clock now {self.clock}", style="cyan")
            else:
                self._log_event("INTERNAL")
                console.log(f"machine {self.id}: internal event, clock now {self.clock}", style="yellow")

    async def _send_to(self, target_id: str):
        stub = self.stubs.get(target_id)
        if stub:
            await stub.SendMessage(clock_pb2.ClockMessage(
                logical_time=self.clock,
                sender_id=self.id
            ))
            self._log_event("SEND", target_id)

    async def _send_broadcast(self):
        targets = list(self.stubs.keys())
        targets_str = ",".join(targets)
        self._log_event("BROADCAST", targets_str)
        for target_id, stub in self.stubs.items():
            await stub.SendMessage(clock_pb2.ClockMessage(
                logical_time=self.clock,
                sender_id=self.id
            ))

    def _log_event(self, event_type: str, target: str = ""):
        log_line = f"{time.time()}|{self.clock}|{event_type}|{self.queue.qsize()}|{target}\n"
        with open(self.log_path, "a") as f:
            f.write(log_line)

async def start_machine_from_args():
    if len(sys.argv) < 5:
        console.log("usage: python -m src.machine <machine_id> <port> <ticks> <log_path>", style="bold red")
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
    config = {
        "port": port,
        "ticks": ticks,
        "log_path": log_path
    }
    m = machine(machine_id, config, peers)
    await m.run()

if __name__ == "__main__":
    asyncio.run(start_machine_from_args())
