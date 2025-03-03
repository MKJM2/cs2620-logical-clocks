import asyncio
import json
import os
import signal
import sys
import time
import argparse
from pathlib import Path

import tomli
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

console = Console()


class orchestrator:
    def __init__(self, config_path: str = "config.toml", verbose: bool = False):
        self.config = self._load_config(config_path)
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self.running = True
        self.start_time = None
        self.verbose = verbose
        # setup signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handle_exit)

    def _handle_exit(self, signum, frame):
        console.log("[bold red]received shutdown signal...[/]")
        self.running = False

    def _load_config(self, path: str) -> dict:
        with open(path, "rb") as f:
            return tomli.load(f)["machines"]

    async def start_machine(self, machine_id: str):
        config = self.config[machine_id]
        peers = {k: v for k, v in self.config.items() if k != machine_id}

        # create a temporary file for peer info
        peers_file = Path(f"peers_{machine_id}.json")
        with open(peers_file, "w") as f:
            json.dump(peers, f)

        console.log(
            f"starting machine {machine_id} with {config['ticks']} ticks/sec",
            style="bold blue",
        )
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "src.machine",
            machine_id,
            str(config["port"]),
            str(config["ticks"]),
            config["log_path"],
            env={**os.environ, **self._peer_env(peers)},
            stdout=asyncio.subprocess.PIPE if self.verbose else asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE if self.verbose else asyncio.subprocess.DEVNULL,
        )
        self.processes[machine_id] = proc
        peers_file.unlink(missing_ok=True)
        
        # Only monitor process output in verbose mode
        if self.verbose:
            asyncio.create_task(self._monitor_process_output(machine_id, proc))

    async def _monitor_process_output(
        self, machine_id: str, proc: asyncio.subprocess.Process
    ):
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            console.log(f"[dim]{machine_id}:[/] {line.decode().strip()}")

    def _peer_env(self, peers: dict) -> dict:
        return {"PEERS": ",".join(f"{k}:{v['port']}" for k, v in peers.items())}

    async def run(self):
        self.start_time = time.time()
        console.rule("[bold green]starting simulation[/]")
        await asyncio.gather(*[self.start_machine(mid) for mid in self.config])
        console.log("[bold green]🚀 all machines running. press ctrl+c to stop.[/]")
        await self._live_monitor()

    async def _live_monitor(self):
        try:
            with Live(
                self._generate_status_table(), refresh_per_second=10, console=console
            ) as live:
                while self.running:
                    live.update(self._generate_status_table())
                    await asyncio.sleep(0.1)
                await self._shutdown_all_machines()
                live.update(Panel("simulation complete. analyzing logs..."))
                self._analyze_logs()
        except asyncio.CancelledError:
            console.log("[bold red]cancelled![/]")
            await self._shutdown_all_machines()
    
    def _generate_status_table(self) -> Table:
        # Calculate average logical clock across all machines for drift calculation
        all_clocks = {}
        for mid in self.config:
            log_path = Path(self.config[mid]["log_path"])
            if log_path.exists() and log_path.stat().st_size > 0:
                log_lines = log_path.read_text().splitlines()
                if log_lines:
                    all_clocks[mid] = int(log_lines[-1].split("|")[1])
        
        avg_clock = sum(all_clocks.values()) / max(1, len(all_clocks))
        
        # Create the table with new metrics
        table = Table(
            title=f"logical clocks simulation (running for {int(time.time() - self.start_time)}s)"
        )
        table.add_column("Machine")
        table.add_column("Ticks/sec")
        table.add_column("Clock Value")
        table.add_column("Clock Rate")
        table.add_column("Clock Drift")
        table.add_column("Max Jump")
        table.add_column("Events %")
        
        for mid in self.config:
            log_path = Path(self.config[mid]["log_path"])
            ticks = self.config[mid]["ticks"]
            
            if not log_path.exists() or log_path.stat().st_size == 0:
                table.add_row(mid, str(ticks), "0", "0.0", "0", "0", "N/A")
                continue
                
            log_lines = log_path.read_text().splitlines()
            if not log_lines:
                table.add_row(mid, str(ticks), "0", "0.0", "0", "0", "N/A")
                continue
                
            # Parse log entries
            timestamps = []
            clock_values = []
            event_types = {"internal": 0, "send": 0, "recv": 0, "broadcast": 0}
            queue_sizes = []
            
            for line in log_lines:
                parts = line.split("|")
                if len(parts) >= 4:
                    timestamps.append(float(parts[0]))
                    clock_values.append(int(parts[1]))
                    event_type = parts[2].lower()
                    if event_type in event_types:
                        event_types[event_type] += 1
                    queue_sizes.append(int(parts[3]))
            
            # Calculate metrics
            last_clock = clock_values[-1]
            clock_drift = last_clock - avg_clock
            
            # Calculate clock jumps (differences between consecutive values)
            clock_jumps = [j - i for i, j in zip(clock_values[:-1], clock_values[1:])]
            max_jump = max(clock_jumps) if clock_jumps else 0
            
            # Calculate clock rate (logical clock ticks per second of real time)
            if len(timestamps) >= 2:
                elapsed_time = timestamps[-1] - timestamps[0]
                clock_change = clock_values[-1] - clock_values[0]
                clock_rate = clock_change / max(0.1, elapsed_time)  # Avoid division by zero
            else:
                clock_rate = 0
                
            # Calculate event distribution
            total_events = sum(event_types.values())
            event_dist = ""
            if total_events > 0:
                event_dist = f"{event_types['internal']*100/total_events:.0f}/"
                event_dist += f"{event_types['send']*100/total_events:.0f}/"
                event_dist += f"{event_types['recv']*100/total_events:.0f}/"
                event_dist += f"{event_types['broadcast']*100/total_events:.0f}"
                
            # Add row to table with all metrics
            table.add_row(
                f"[bold]{mid}[/]",
                str(ticks),
                str(last_clock),
                f"{clock_rate:.1f}",
                f"{clock_drift:+.1f}",
                str(max_jump),
                event_dist  # I%/S%/R%/B%
            )
            
        return table

    def _analyze_logs(self):
        console.rule("[bold]log analysis")
        
        # Prepare dictionaries for metrics
        max_clocks = {}
        avg_queue_sizes = {}
        max_queue_sizes = {}
        clock_rates = {}
        max_jumps = {}
        event_types = {
            mid: {"internal": 0, "send": 0, "recv": 0, "broadcast": 0}
            for mid in self.config
        }
        
        for mid in self.config:
            log_path = Path(self.config[mid]["log_path"])
            if not log_path.exists() or log_path.stat().st_size == 0:
                continue
                
            log_lines = log_path.read_text().splitlines()
            if not log_lines:
                continue
                
            # Parse logs for analysis
            timestamps = []
            clock_values = []
            queue_sizes = []
            
            for line in log_path.read_text().splitlines():
                parts = line.split("|")
                if len(parts) >= 4:
                    timestamps.append(float(parts[0]))
                    clock_values.append(int(parts[1]))
                    event_type = parts[2].lower()
                    if event_type in event_types[mid]:
                        event_types[mid][event_type] += 1
                    queue_sizes.append(int(parts[3]))
                    
            # Calculate metrics
            if clock_values:
                max_clocks[mid] = max(clock_values)
                
                # Calculate jumps in clock values
                clock_jumps = [j - i for i, j in zip(clock_values[:-1], clock_values[1:])]
                if clock_jumps:
                    max_jumps[mid] = max(clock_jumps)
                else:
                    max_jumps[mid] = 0
                    
                # Calculate average and max queue sizes
                if queue_sizes:
                    avg_queue_sizes[mid] = sum(queue_sizes) / len(queue_sizes)
                    max_queue_sizes[mid] = max(queue_sizes)
                    
                # Calculate clock rate
                if len(timestamps) >= 2:
                    elapsed_time = timestamps[-1] - timestamps[0]
                    clock_change = clock_values[-1] - clock_values[0]
                    clock_rates[mid] = clock_change / max(0.1, elapsed_time)
                else:
                    clock_rates[mid] = 0
        
        # Print analysis results
        console.log(f"Maximum logical clock values: {max_clocks}")
        console.log(f"Maximum single-step clock jumps: {max_jumps}")
        console.log(f"Average clock rates (ticks/sec): {clock_rates}")
        console.log(f"Average queue sizes: {avg_queue_sizes}")
        console.log(f"Maximum queue sizes: {max_queue_sizes}")
        
        # Calculate the drift between machines
        if len(max_clocks) >= 2:
            max_drift = max(max_clocks.values()) - min(max_clocks.values())
            console.log(f"Maximum clock drift between machines: {max_drift}")
        
        # Print event type distribution
        console.log("Event type distribution:")
        for mid, events in event_types.items():
            total = sum(events.values())
            if total > 0:
                percentages = {k: f"{v*100/total:.1f}%" for k, v in events.items()}
                console.log(f"  {mid}: {percentages}")

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

async def main():
    parser = argparse.ArgumentParser(description="Logical clock simulation orchestrator")
    parser.add_argument('-v', '--verbose', action='store_true', 
                        help='Enable verbose output from machine processes')
    parser.add_argument('-c', '--config', default="config.toml",
                        help='Path to configuration file (default: config.toml)')
    args = parser.parse_args()
    
    orch = orchestrator(args.config, verbose=args.verbose)
    await orch.run()


if __name__ == "__main__":
    asyncio.run(main())
