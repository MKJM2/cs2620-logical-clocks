import sys
import asyncio
import tomli
import json
from pathlib import Path
from typing import Dict, List
import signal
import time
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel

console = Console()

class Orchestrator:
    def __init__(self, config_path: str = "config.toml"):
        self.config = self._load_config(config_path)
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        self.running = True
        self.start_time = None
        # Setup signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handle_exit)

    def _handle_exit(self, signum, frame):
        console.print("\n[bold red]Shutting down all machines...[/]")
        self.running = False
        # Signal will be processed in the main loop

    def _load_config(self, path: str) -> Dict:
        with open(path, 'rb') as f:
            return tomli.load(f)['machines']

    async def start_machine(self, machine_id: str):
        config = self.config[machine_id]
        peers = {k: v for k, v in self.config.items() if k != machine_id}
        
        # Create a temporary file for peer info
        peers_file = Path(f"peers_{machine_id}.json")
        with open(peers_file, 'w') as f:
            json.dump(peers, f)
        
        # Start the process
        console.print(f"Starting machine {machine_id} with {config['ticks']} ticks/sec")
        proc = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'src.machine',
            machine_id,
            str(config['port']),
            str(config['ticks']),
            config['log_path'],
            env={**self._peer_env(peers)},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        self.processes[machine_id] = proc
        
        # Clean up the temporary file
        peers_file.unlink(missing_ok=True)
        
        # Start a task to monitor process output
        asyncio.create_task(self._monitor_process_output(machine_id, proc))

    async def _monitor_process_output(self, machine_id: str, proc: asyncio.subprocess.Process):
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            console.print(f"[dim]{machine_id}:[/] {line.decode().strip()}")

    def _peer_env(self, peers: Dict) -> Dict:
        return {'PEERS': ','.join(
            f"{k}:{v['port']}" for k, v in peers.items()
        )}

    async def run(self):
        self.start_time = time.time()
        
        # Start all machines
        await asyncio.gather(*[
            self.start_machine(machine_id)
            for machine_id in self.config
        ])
        
        console.print("[bold green]🚀 All machines running. Press Ctrl+C to stop.[/]")
        
        # Monitor the logs in real-time
        await self._live_monitor()

    async def _live_monitor(self):
        try:
            with Live(self._generate_status_table(), refresh_per_second=2) as live:
                while self.running:
                    live.update(self._generate_status_table())
                    await asyncio.sleep(0.5)
                
                # Graceful shutdown
                await self._shutdown_all_machines()
                live.update(Panel("Simulation complete. Analyzing logs..."))
                self._analyze_logs()
                
        except asyncio.CancelledError:
            console.print("[bold red]Cancelled![/]")
            await self._shutdown_all_machines()

    def _generate_status_table(self) -> Table:
        table = Table(title=f"Logical Clocks Simulation (Running for {int(time.time() - self.start_time)}s)")
        table.add_column("Machine")
        table.add_column("Ticks/sec")
        table.add_column("Events")
        table.add_column("Queue Size")
        table.add_column("Last Clock")
        
        for machine_id in self.config:
            log_path = Path(self.config[machine_id]['log_path'])
            ticks = self.config[machine_id]['ticks']
            
            if log_path.exists():
                log_lines = log_path.read_text().splitlines()
                event_count = len(log_lines)
                
                queue_size = "0"
                last_clock = "0"
                if log_lines:
                    last_line = log_lines[-1]
                    parts = last_line.split('|')
                    if len(parts) >= 4:
                        last_clock = parts[1]
                        queue_size = parts[3]
                
                table.add_row(
                    f"[bold]{machine_id}[/]",
                    str(ticks),
                    str(event_count),
                    queue_size,
                    last_clock
                )
            else:
                table.add_row(machine_id, str(ticks), "0", "0", "0")
                
        return table

    async def _shutdown_all_machines(self):
        # Ask all processes to terminate
        for machine_id, proc in self.processes.items():
            if proc.returncode is None:  # Still running
                console.print(f"Terminating machine {machine_id}...")
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass  # Process already terminated
        
        # Wait for processes to terminate
        for machine_id, proc in self.processes.items():
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
                console.print(f"Machine {machine_id} terminated")
            except asyncio.TimeoutError:
                console.print(f"[red]Machine {machine_id} didn't terminate, killing...[/]")
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass  # Process already terminated

    def _analyze_logs(self):
        """Analyze the logs after the simulation completes"""
        console.rule("[bold]Log Analysis")
        
        # Calculate max logical clock values for each machine
        max_clocks = {}
        for machine_id in self.config:
            log_path = Path(self.config[machine_id]['log_path'])
            if log_path.exists():
                log_lines = log_path.read_text().splitlines()
                if log_lines:
                    clocks = [int(line.split('|')[1]) for line in log_lines]
                    max_clocks[machine_id] = max(clocks)
        
        console.print(f"Maximum logical clock values: {max_clocks}")
        
        # Calculate average queue sizes
        queue_sizes = {}
        for machine_id in self.config:
            log_path = Path(self.config[machine_id]['log_path'])
            if log_path.exists():
                log_lines = log_path.read_text().splitlines()
                if log_lines:
                    queue_sizes_list = [int(line.split('|')[3]) for line in log_lines]
                    if queue_sizes_list:
                        queue_sizes[machine_id] = sum(queue_sizes_list) / len(queue_sizes_list)
        
        console.print(f"Average queue sizes: {queue_sizes}")
        
        # Event type distribution
        event_types = {machine_id: {"INTERNAL": 0, "SEND": 0, "RECV": 0, "BROADCAST": 0} 
                       for machine_id in self.config}
        
        for machine_id in self.config:
            log_path = Path(self.config[machine_id]['log_path'])
            if log_path.exists():
                log_lines = log_path.read_text().splitlines()
                for line in log_lines:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        event_type = parts[2]
                        if event_type in event_types[machine_id]:
                            event_types[machine_id][event_type] += 1
        
        console.print("Event type distribution:")
        for machine_id, events in event_types.items():
            console.print(f"  {machine_id}: {events}")

async def main():
    orchestrator = Orchestrator('config.toml')
    await orchestrator.run()

if __name__ == '__main__':
    asyncio.run(main())
