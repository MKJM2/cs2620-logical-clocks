#!/usr/bin/env python3
"""
Analyze logs from logical clock experiments.
Generates visualizations and summary tables.
"""
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from src.experiments import (Experiment, ExperimentType, get_experiment,
                            list_experiments)

console = Console()


def parse_log_file(log_path: Path) -> pd.DataFrame:
    """
    Parse a log file into a pandas DataFrame.
    
    Log format: timestamp|logical_clock|event_type|queue_size|target
    """
    if not log_path.exists():
        console.log(f"[bold red]Log file not found: {log_path}[/]")
        return pd.DataFrame()
    
    # Extract machine ID and experiment info from filename
    filename_parts = log_path.name.split(".")
    machine_id = filename_parts[0]
    experiment_name = filename_parts[1] if len(filename_parts) > 1 else "unknown"
    trial = int(re.search(r"trial_(\d+)", log_path.name).group(1)) if "trial_" in log_path.name else 0
    
    # Read log file
    data = []
    with open(log_path, "r") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 4:
                timestamp = float(parts[0])
                clock = int(parts[1])
                event_type = parts[2].lower()
                queue_size = int(parts[3])
                target = parts[4] if len(parts) > 4 else ""
                
                data.append({
                    "timestamp": timestamp,
                    "clock": clock,
                    "event_type": event_type,
                    "queue_size": queue_size,
                    "target": target,
                    "machine_id": machine_id,
                    "experiment": experiment_name,
                    "trial": trial
                })
    
    if not data:
        console.log(f"[bold yellow]No data found in log file: {log_path}[/]")
        return pd.DataFrame()
    
    # Create DataFrame and add derived columns
    df = pd.DataFrame(data)
    df["time_diff"] = df["timestamp"].diff()
    df["clock_diff"] = df["clock"].diff()
    df["clock_rate"] = df["clock_diff"] / df["time_diff"].replace(0, np.nan)
    
    # Add relative time (seconds since start)
    df["relative_time"] = df["timestamp"] - df["timestamp"].iloc[0]
    
    return df


def load_experiment_data(experiment_name: str) -> pd.DataFrame:
    """
    Load all log data for a specific experiment across all trials.
    
    Args:
        experiment_name: Name of the experiment to load
        
    Returns:
        DataFrame containing all log data
    """
    experiment = get_experiment(experiment_name)
    if not experiment:
        console.log(f"[bold red]Experiment not found: {experiment_name}[/]")
        return pd.DataFrame()
    
    # Get all log paths
    log_paths = [Path(path) for path in experiment.get_all_log_paths()]
    
    # Check if logs exist
    existing_logs = [path for path in log_paths if path.exists()]
    if not existing_logs:
        console.log(f"[bold red]No log files found for experiment: {experiment_name}[/]")
        return pd.DataFrame()
    
    # Parse logs and concatenate
    dfs = [parse_log_file(path) for path in existing_logs]
    df = pd.concat(dfs, ignore_index=True)
    
    # Sort by timestamp
    df = df.sort_values("timestamp")
    
    return df


def calculate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate additional metrics from the log data."""
    if df.empty:
        return df
    
    # Group by machine, experiment, and trial
    grouped = df.groupby(["machine_id", "experiment", "trial"])
    
    metrics = []
    for (machine_id, experiment, trial), group in grouped:
        # Calculate metrics for this group
        avg_clock_rate = group["clock_rate"].mean()
        max_clock_rate = group["clock_rate"].max()
        avg_queue_size = group["queue_size"].mean()
        max_queue_size = group["queue_size"].max()
        
        # Calculate clock jumps
        clock_jumps = group["clock_diff"].dropna()
        max_jump = clock_jumps.max() if not clock_jumps.empty else 0
        
        # Calculate event counts
        event_counts = group["event_type"].value_counts()
        internal_events = event_counts.get("internal", 0)
        send_events = event_counts.get("send", 0)
        recv_events = event_counts.get("recv", 0)
        broadcast_events = event_counts.get("broadcast", 0)
        total_events = len(group)
        
        metrics.append({
            "machine_id": machine_id,
            "experiment": experiment,
            "trial": trial,
            "avg_clock_rate": avg_clock_rate,
            "max_clock_rate": max_clock_rate,
            "avg_queue_size": avg_queue_size,
            "max_queue_size": max_queue_size,
            "max_jump": max_jump,
            "internal_events": internal_events,
            "send_events": send_events,
            "recv_events": recv_events,
            "broadcast_events": broadcast_events,
            "total_events": total_events,
            "final_clock": group["clock"].iloc[-1]
        })
    
    return pd.DataFrame(metrics)


def generate_summary_table(metrics_df: pd.DataFrame, experiment_name: str) -> str:
    """
    Generate a markdown summary table from metrics.
    
    Args:
        metrics_df: DataFrame containing metrics
        experiment_name: Name of the experiment
        
    Returns:
        Markdown-formatted table
    """
    if metrics_df.empty:
        return f"No data available for experiment: {experiment_name}"
    
    # Group by machine_id and calculate average across trials
    summary = metrics_df.groupby("machine_id").agg({
        "avg_clock_rate": "mean",
        "max_clock_rate": "mean",
        "avg_queue_size": "mean",
        "max_queue_size": "max",
        "max_jump": "max",
        "internal_events": "mean",
        "send_events": "mean",
        "recv_events": "mean",
        "broadcast_events": "mean",
        "total_events": "mean",
        "final_clock": "mean"
    }).reset_index()
    
    # Format table
    markdown = f"## Summary for Experiment: {experiment_name}\n\n"
    markdown += "| Machine | Avg Clock Rate | Max Clock Rate | Avg Queue Size | Max Queue Size | Max Jump | Events (I/S/R/B) | Final Clock |\n"
    markdown += "|---------|---------------|---------------|---------------|---------------|----------|-----------------|-------------|\n"
    
    for _, row in summary.iterrows():
        events = f"{row['internal_events']:.1f}/{row['send_events']:.1f}/{row['recv_events']:.1f}/{row['broadcast_events']:.1f}"
        markdown += f"| {row['machine_id']} | {row['avg_clock_rate']:.2f} | {row['max_clock_rate']:.2f} | {row['avg_queue_size']:.2f} | {row['max_queue_size']:.0f} | {row['max_jump']:.0f} | {events} | {row['final_clock']:.0f} |\n"
    
    return markdown


def plot_clock_progression(df: pd.DataFrame, experiment_name: str, save_dir: Path) -> None:
    """
    Plot logical clock progression over time for each machine.
    
    Args:
        df: DataFrame containing log data
        experiment_name: Name of the experiment
        save_dir: Directory to save plots
    """
    if df.empty:
        console.log(f"[bold yellow]No data to plot for experiment: {experiment_name}[/]")
        return
    
    save_dir.mkdir(exist_ok=True, parents=True)
    
    # Plot clock values over time for each trial
    for trial in df["trial"].unique():
        trial_df = df[df["trial"] == trial]
        
        plt.figure(figsize=(10, 6))
        
        for machine_id in sorted(trial_df["machine_id"].unique()):
            machine_df = trial_df[trial_df["machine_id"] == machine_id]
            plt.plot(machine_df["relative_time"], machine_df["clock"], 
                    label=f"Machine {machine_id}")
        
        plt.title(f"Logical Clock Progression - {experiment_name} (Trial {trial})")
        plt.xlabel("Time (seconds)")
        plt.ylabel("Logical Clock Value")
        plt.legend()
        plt.grid(True)
        
        # Save plot
        plot_path = save_dir / f"{experiment_name}_trial_{trial}_clock_progression.png"
        plt.savefig(plot_path)
        console.log(f"[green]Saved plot: {plot_path}[/]")
        plt.close()


def plot_queue_sizes(df: pd.DataFrame, experiment_name: str, save_dir: Path) -> None:
    """
    Plot queue sizes over time for each machine.
    
    Args:
        df: DataFrame containing log data
        experiment_name: Name of the experiment
        save_dir: Directory to save plots
    """
    if df.empty:
        return
    
    save_dir.mkdir(exist_ok=True, parents=True)
    
    # Plot queue sizes over time for each trial
    for trial in df["trial"].unique():
        trial_df = df[df["trial"] == trial]
        
        plt.figure(figsize=(10, 6))
        
        for machine_id in sorted(trial_df["machine_id"].unique()):
            machine_df = trial_df[trial_df["machine_id"] == machine_id]
            plt.plot(machine_df["relative_time"], machine_df["queue_size"], 
                     label=f"Machine {machine_id}")
        
        plt.title(f"Message Queue Size - {experiment_name} (Trial {trial})")
        plt.xlabel("Time (seconds)")
        plt.ylabel("Queue Size")
        plt.legend()
        plt.grid(True)
        
        # Save plot
        plot_path = save_dir / f"{experiment_name}_trial_{trial}_queue_sizes.png"
        plt.savefig(plot_path)
        console.log(f"[green]Saved plot: {plot_path}[/]")
        plt.close()


def plot_event_distribution(metrics_df: pd.DataFrame, experiment_name: str, save_dir: Path) -> None:
    """
    Plot event type distribution for each machine.
    
    Args:
        metrics_df: DataFrame containing metrics
        experiment_name: Name of the experiment
        save_dir: Directory to save plots
    """
    if metrics_df.empty:
        return
    
    save_dir.mkdir(exist_ok=True, parents=True)
    
    # Group by machine and average across trials
    summary = metrics_df.groupby("machine_id").agg({
        "internal_events": "mean",
        "send_events": "mean",
        "recv_events": "mean",
        "broadcast_events": "mean"
    }).reset_index()
    
    # Prepare data for plotting
    machines = summary["machine_id"]
    events = ["Internal", "Send", "Receive", "Broadcast"]
    data = np.array([
        summary["internal_events"],
        summary["send_events"],
        summary["recv_events"],
        summary["broadcast_events"]
    ])
    
    # Create plot
    plt.figure(figsize=(12, 7))
    
    # Create the bar chart
    bottom = np.zeros(len(machines))
    for i, event_type in enumerate(events):
        plt.bar(machines, data[i], bottom=bottom, label=event_type)
        bottom += data[i]
    
    plt.title(f"Event Distribution - {experiment_name}")
    plt.xlabel("Machine")
    plt.ylabel("Number of Events")
    plt.legend()
    
    # Save plot
    plot_path = save_dir / f"{experiment_name}_event_distribution.png"
    plt.savefig(plot_path)
    console.log(f"[green]Saved plot: {plot_path}[/]")
    plt.close()


def analyze_experiment(experiment_name: str, save_dir: Path) -> None:
    """
    Analyze an experiment and generate visualizations.
    
    Args:
        experiment_name: Name of the experiment
        save_dir: Directory to save output
    """
    console.log(f"[bold blue]Analyzing experiment: {experiment_name}[/]")
    
    # Load data
    df = load_experiment_data(experiment_name)
    if df.empty:
        console.log(f"[bold red]No data found for experiment: {experiment_name}[/]")
        return
    
    # Calculate metrics
    metrics_df = calculate_metrics(df)
    
    # Generate summary table
    summary_table = generate_summary_table(metrics_df, experiment_name)
    console.log(Markdown(summary_table))
    
    # Save summary table to file
    summary_path = save_dir / f"{experiment_name}_summary.md"
    summary_path.write_text(summary_table)
    console.log(f"[green]Saved summary: {summary_path}[/]")
    
    # Generate plots
    plots_dir = save_dir / "plots"
    plots_dir.mkdir(exist_ok=True, parents=True)
    
    plot_clock_progression(df, experiment_name, plots_dir)
    plot_queue_sizes(df, experiment_name, plots_dir)
    plot_event_distribution(metrics_df, experiment_name, plots_dir)


def main() -> None:
    """Main entry point for the analysis script."""
    parser = argparse.ArgumentParser(description="Analyze logical clock simulation logs")
    parser.add_argument("--experiment", "-e", help="Experiment to analyze")
    parser.add_argument("--all", "-a", action="store_true", help="Analyze all experiments")
    parser.add_argument("--list", "-l", action="store_true", help="List available experiments")
    parser.add_argument("--output", "-o", default="analysis", help="Output directory")
    
    args = parser.parse_args()
    
    if args.list:
        console.log("[bold]Available experiments:[/]")
        for name in list_experiments():
            experiment = get_experiment(name)
            console.log(f"  [green]{name}[/]: {experiment.description} ({experiment.trials} trials)")
        return
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    if args.all:
        # Analyze all experiments
        for name in list_experiments():
            analyze_experiment(name, output_dir)
    elif args.experiment:
        # Analyze specific experiment
        analyze_experiment(args.experiment, output_dir)
    else:
        console.log("[bold yellow]No experiment specified. Use --experiment or --all.[/]")
        console.log("[bold]Available experiments:[/]")
        for name in list_experiments():
            experiment = get_experiment(name)
            console.log(f"  [green]{name}[/]: {experiment.description} ({experiment.trials} trials)")


if __name__ == "__main__":
    main()
