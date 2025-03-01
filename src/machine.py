import asyncio
import random
import time
from pathlib import Path
from typing import Dict, List
import grpc
from grpc import aio
import sys

from .protos import clock_pb2, clock_pb2_grpc

class Machine(clock_pb2_grpc.MachineServiceServicer):
    def __init__(self, machine_id: str, config: Dict, peers: Dict):
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
        print(f"Machine {self.id} initialized with {self.ticks_per_sec} ticks/sec")

    def _setup_logging(self):
        self.log_path.parent.mkdir(exist_ok=True)
        self.log_path.write_text("")  # Clear previous logs
        print(f"Machine {self.id}: Logging to {self.log_path}")

    def _setup_server(self, port: int):
        clock_pb2_grpc.add_MachineServiceServicer_to_server(self, self.server)
        self.server.add_insecure_port(f'[::]:{port}')
        print(f"Machine {self.id}: Server set up on port {port}")

    async def connect_to_peers(self):
        for peer_id, peer_config in self.peers.items():
            if peer_id == self.id:
                continue
            channel = aio.insecure_channel(f'localhost:{peer_config["port"]}')
            self.stubs[peer_id] = clock_pb2_grpc.MachineServiceStub(channel)
            print(f"Machine {self.id}: Connected to peer {peer_id} on port {peer_config['port']}")

    async def SendMessage(self, request, context):
        await self.queue.put(request)
        print(f"Machine {self.id}: Received message from {request.sender_id}, logical time {request.logical_time}")
        return clock_pb2.Ack()

    async def run(self):
        await self.server.start()
        print(f"Machine {self.id}: Server started")
        await self.connect_to_peers()
        
        try:
            while True:
                start_time = time.time()
                await self.process_tick()
                elapsed = time.time() - start_time
                await asyncio.sleep(max(0, 1/self.ticks_per_sec - elapsed))
        except asyncio.CancelledError:
            print(f"Machine {self.id}: Shutting down...")
            await self.server.stop(grace=None)

    async def process_tick(self):
        if not self.queue.empty():
            msg = await self.queue.get()
            self.clock = max(self.clock, msg.logical_time) + 1
            self._log_event('RECV', msg.sender_id)
            print(f"Machine {self.id}: Processed message from {msg.sender_id}, clock now {self.clock}")
        else:
            rand_val = random.randint(1, 10)
            self.clock += 1
            
            if rand_val == 1:
                target_id = 'B' if self.id == 'A' else 'A'
                await self._send_to(target_id)
                print(f"Machine {self.id}: Sent message to {target_id}, clock now {self.clock}")
            elif rand_val == 2:
                await self._send_to('C')
                print(f"Machine {self.id}: Sent message to C, clock now {self.clock}")
            elif rand_val == 3:
                await self._send_broadcast()
                print(f"Machine {self.id}: Broadcast message to all peers, clock now {self.clock}")
            else:
                self._log_event('INTERNAL')
                print(f"Machine {self.id}: Internal event, clock now {self.clock}")

    async def _send_to(self, target_id: str):
        stub = self.stubs.get(target_id)
        if stub:
            await stub.SendMessage(clock_pb2.ClockMessage(
                logical_time=self.clock,
                sender_id=self.id
            ))
            self._log_event('SEND', target_id)

    async def _send_broadcast(self):
        # Only increment clock once for a broadcast event
        targets = list(self.stubs.keys())
        targets_str = ",".join(targets)
        self._log_event('BROADCAST', targets_str)
        
        # Now send to each target without incrementing the clock again
        for target_id, stub in self.stubs.items():
            await stub.SendMessage(clock_pb2.ClockMessage(
                logical_time=self.clock,
                sender_id=self.id
            ))

    def _log_event(self, event_type: str, target: str = ''):
        log_line = f"{time.time()}|{self.clock}|{event_type}|{self.queue.qsize()}|{target}\n"
        with open(self.log_path, 'a') as f:
            f.write(log_line)

async def start_machine_from_args():
    if len(sys.argv) < 5:
        print("Usage: python -m src.machine <machine_id> <port> <ticks> <log_path>")
        sys.exit(1)
        
    machine_id = sys.argv[1]
    port = int(sys.argv[2])
    ticks = int(sys.argv[3])
    log_path = sys.argv[4]
    
    # Parse peers from environment variable
    peers = {}
    if 'PEERS' in os.environ:
        peers_str = os.environ['PEERS']
        for peer in peers_str.split(','):
            if peer:
                peer_id, peer_port = peer.split(':')
                peers[peer_id] = {"port": int(peer_port)}
    
    config = {
        "port": port,
        "ticks": ticks,
        "log_path": log_path
    }
    
    machine = Machine(machine_id, config, peers)
    await machine.run()

if __name__ == '__main__':
    import os
    asyncio.run(start_machine_from_args())
