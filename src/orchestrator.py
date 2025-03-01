import sys
import asyncio
import tomli
import json
from pathlib import Path
import signal
import time
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel

console = Console()

class orchestrator:
    def __init__(self, config_path: str = "config.toml"):
        self.config = self._load_config(config_path)
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self.running = True
        self.start_time = None
        # setup signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handle_exit)

    def _handle_exit(self, signum, frame):
        console.log("[bold red]received shutdown signal...[/]")
        self.running = False

    def _load_config(self, path: str) -> dict:
        with open(path, 'rb') as f:
            return tomli.load(f)['machines']

    async def start_machine(self, machine_id: str):
        config = self.config[machine_id]
        peers = {k: v for k, v in self.config.items() if k != machine_id}

        # create a temporary file for peer info
        peers_file = Path(f"peers_{machine_id}.json")
        with open(peers_file, 'w') as f:
            json.dump(peers, f)

        console.log(f"starting machine {machine_id} with {config['ticks']} ticks/sec", style="bold blue")
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
        peers_file.unlink(missing_ok=True)
        # monitor process output with rich logging
        asyncio.create_task(self._monitor_process_output(machine_id, proc))

    async def _monitor_process_output(self, machine_id: str, proc: asyncio.subprocess.Process):
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            console.log(f"[dim]{machine_id}:[/] {line.decode().strip()}")

    def _peer_env(self, peers: dict) -> dict:
        return {'PEERS': ','.join(f"{k}:{v['port']}" for k, v in peers.items())}

    async def run(self):
        self.start_time = time.time()
        console.rule("[bold green]starting simulation[/]")
        await asyncio.gather(*[self.start_machine(mid) for mid in self.config])
        console.log("[bold green]🚀 all machines running. press ctrl+c to stop.[/]")
        await self._live_monitor()

    async def _live_monitor(self):
        try:
            with Live(self._generate_status_table(), refresh_per_second=2, console=console) as live:
                while self.running:
                    live.update(self._generate_status_table())
                    await asyncio.sleep(0.5)
                await self._shutdown_all_machines()
                live.update(Panel("simulation complete. analyzing logs..."))
                self._analyze_logs()
        except asyncio.CancelledError:
            console.log("[bold red]cancelled![/]")
            await self._shutdown_all_machines()

    def _generate_status_table(self) -> Table:
        table = Table(title=f"logical clocks simulation (running for {int(time.time() - self.start_time)}s)")
        table.add_column("machine")
        table.add_column("ticks/sec")
        table.add_column("events")
        table.add_column("queue size")
        table.add_column("last clock")
        for mid in self.config:
            log_path = Path(self.config[mid]['log_path'])
            ticks = self.config[mid]['ticks']
            if log_path.exists():
                log_lines = log_path.read_text().splitlines()
                event_count = len(log_lines)
                queue_size = "0"
                last_clock = "0"
                if log_lines:
                    parts = log_lines[-1].split('|')
                    if len(parts) >= 4:
                        last_clock = parts[1]
                        queue_size = parts[3]
                table.add_row(f"[bold]{mid}[/]", str(ticks), str(event_count), queue_size, last_clock)
            else:
                table.add_row(mid, str(ticks), "0", "0", "0")
        return table

    async def _shutdown_all_machines(self):
        for mid, proc in self.processes.items():
            if proc.returncode is None:
                console.log(f"terminating machine {mid}...", style="bold yellow")
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass
        for mid, proc in self.processes.items():
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
                console.log(f"machine {mid} terminated", style="bold green")
            except asyncio.TimeoutError:
                console.log(f"[red]machine {mid} didn't terminate, killing...[/]")
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass

    def _analyze_logs(self):
        console.rule("[bold]log analysis")
        max_clocks = {}
        for mid in self.config:
            log_path = Path(self.config[mid]['log_path'])
            if log_path.exists():
                log_lines = log_path.read_text().splitlines()
                if log_lines:
                    clocks = [int(line.split('|')[1]) for line in log_lines]
                    max_clocks[mid] = max(clocks)
        console.log(f"maximum logical clock values: {max_clocks}")
        queue_sizes = {}
        for mid in self.config:
            log_path = Path(self.config[mid]['log_path'])
            if log_path.exists():
                log_lines = log_path.read_text().splitlines()
                if log_lines:
                    qs = [int(line.split('|')[3]) for line in log_lines]
                    if qs:
                        queue_sizes[mid] = sum(qs) / len(qs)
        console.log(f"average queue sizes: {queue_sizes}")
        event_types = {mid: {"internal": 0, "send": 0, "recv": 0, "broadcast": 0} for mid in self.config}
        for mid in self.config:
            log_path = Path(self.config[mid]['log_path'])
            if log_path.exists():
                for line in log_path.read_text().splitlines():
                    parts = line.split('|')
                    if len(parts) >= 3:
                        etype = parts[2].lower()
                        if etype in event_types[mid]:
                            event_types[mid][etype] += 1
        console.log("event type distribution:")
        for mid, events in event_types.items():
            console.log(f"  {mid}: {events}")

async def main():
    orch = orchestrator('config.toml')
    await orch.run()

if __name__ == '__main__':
    asyncio.run(main())
