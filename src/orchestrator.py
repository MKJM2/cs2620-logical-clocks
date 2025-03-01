import asyncio
import tomli
from pathlib import Path
from typing import Dict
import signal
from rich.console import Console
from machine import Machine

console = Console()

class Orchestrator:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.processes: Dict[str, asyncio.subprocess.Process] = {}

    def _load_config(self, path: str) -> Dict:
        with open(path, 'rb') as f:
            return tomli.load(f)['machines']

    async def start_machine(self, machine_id: str):
        config = self.config[machine_id]
        peers = {k:v for k,v in self.config.items() if k != machine_id}
        
        proc = await asyncio.create_subprocess_exec(
            'python', '-m', 'src.machine',
            machine_id,
            str(config['port']),
            str(config['ticks']),
            config['log_path'],
            env={**self._peer_env(peers)}
        )
        self.processes[machine_id] = proc

    def _peer_env(self, peers: Dict) -> Dict:
        return {'PEERS': ','.join(
            f"{k}:{v['port']}" for k,v in peers.items()
        )}

    async def run(self):
        await asyncio.gather(*[
            self.start_machine(machine_id)
            for machine_id in self.config
        ])
        
        console.print("🚀 All machines running. Press Ctrl+C to stop.", style="bold green")
        await self.monitor_logs()

    async def monitor_logs(self):
        try:
            while True:
                await asyncio.sleep(5)
                self._print_log_summary()
        except asyncio.CancelledError:
            self._print_log_summary()

    def _print_log_summary(self):
        console.rule("Current Status")
        for machine_id in self.config:
            log_path = Path(self.config[machine_id]['log_path'])
            if log_path.exists():
                console.print(f"[bold]{machine_id}:[/] {len(log_path.read_text().splitlines())} events")

async def main():
    orchestrator = Orchestrator('configs/machines.toml')
    await orchestrator.run()

if __name__ == '__main__':
    asyncio.run(main())
