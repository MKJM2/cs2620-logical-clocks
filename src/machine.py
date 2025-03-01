import asyncio
import random
import time
from pathlib import Path
from typing import Dict
import grpc
from grpc import aio

from protos import clock_pb2, clock_pb2_grpc

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

    def _setup_logging(self):
        self.log_path.parent.mkdir(exist_ok=True)
        self.log_path.write_text("")  # Clear previous logs

    def _setup_server(self, port: int):
        clock_pb2_grpc.add_MachineServiceServicer_to_server(self, self.server)
        self.server.add_insecure_port(f'[::]:{port}')

    async def connect_to_peers(self):
        for peer_id, peer_config in self.peers.items():
            if peer_id == self.id:
                continue
            channel = aio.insecure_channel(f'localhost:{peer_config["port"]}')
            self.stubs[peer_id] = clock_pb2_grpc.MachineServiceStub(channel)

    async def SendMessage(self, request, context):
        await self.queue.put(request)
        return clock_pb2.Ack()

    async def run(self):
        await self.server.start()
        await self.connect_to_peers()
        
        while True:
            start_time = time.time()
            await self.process_tick()
            elapsed = time.time() - start_time
            await asyncio.sleep(max(0, 1/self.ticks_per_sec - elapsed))

    async def process_tick(self):
        if not self.queue.empty():
            msg = await self.queue.get()
            self.clock = max(self.clock, msg.logical_time) + 1
            self._log_event('RECV', msg.sender_id)
        else:
            rand_val = random.randint(1, 10)
            self.clock += 1
            
            if rand_val == 1:
                await self._send_to('B' if self.id == 'A' else 'A')
            elif rand_val == 2:
                await self._send_to('C')
            elif rand_val == 3:
                await self._send_broadcast()
            else:
                self._log_event('INTERNAL')

    async def _send_to(self, target_id: str):
        stub = self.stubs.get(target_id)
        if stub:
            await stub.SendMessage(clock_pb2.ClockMessage(
                logical_time=self.clock,
                sender_id=self.id
            ))
            self._log_event('SEND', target_id)

    async def _send_broadcast(self):
        for target_id in self.stubs:
            await self._send_to(target_id)

    def _log_event(self, event_type: str, target: str = ''):
        log_line = f"{time.time()}|{self.clock}|{event_type}|{self.queue.qsize()}|{target}\n"
        with open(self.log_path, 'a') as f:
            f.write(log_line)
