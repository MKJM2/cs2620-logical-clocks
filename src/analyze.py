#!/usr/bin/env python3
"""
Analyze logs from logical clock experiments.
Generates visualizations and summary tables.
"""
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
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
    
    # Add system time drift (logical clock - expected clock based on tick rate)
    # This estimates drift from "real time" progression
    experiment = get_experiment(experiment_name)
    if experiment and machine_id in experiment.machines:
        ticks_per_sec = experiment.machines[machine_id]["ticks"]
        expected_clock = df["relative_time"] * ticks_per_sec
        df["system_drift"] = df["clock"] - expected_clock
    else:
        df["system_drift"] = np.nan
    
    return df


def load_experiment_data(experiment_name: str) -> pd.DataFrame:
    """
    Load all log data for a specific experiment across all trials.
    
    Args:
        experiment_name: Name of the experiment
        
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
        avg_jump = clock_jumps.mean() if not clock_jumps.empty else 0
        
        # Calculate system drift
        system_drift = group["system_drift"]
        avg_system_drift = system_drift.mean() if not system_drift.empty else 0
        max_system_drift = system_drift.max() if not system_drift.empty else 0
        
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
            "avg_jump": avg_jump,
            "avg_system_drift": avg_system_drift,
            "max_system_drift": max_system_drift,
            "internal_events": internal_events,
            "send_events": send_events,
            "recv_events": recv_events,
            "broadcast_events": broadcast_events,
            "total_events": total_events,
            "final_clock": group["clock"].iloc[-1],
            "run_duration": group["relative_time"].iloc[-1]
        })
    
    metrics_df = pd.DataFrame(metrics)
    
    # Add inter-machine drift calculation (difference from average clock)
    # Group by trial to compare machines within the same trial
    for trial in metrics_df["trial"].unique():
        trial_df = metrics_df[metrics_df["trial"] == trial]
        avg_final_clock = trial_df["final_clock"].mean()
        
        # Update the DataFrame with the drift values
        for idx, row in trial_df.iterrows():
            metrics_df.loc[idx, "drift_from_avg"] = row["final_clock"] - avg_final_clock
    
    return metrics_df


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
    
    # Use named aggregations so that each aggregated column is scalar
    summary = metrics_df.groupby("machine_id").agg(
        avg_clock_rate=("avg_clock_rate", "mean"),
        max_clock_rate=("max_clock_rate", "mean"),
        avg_queue_size=("avg_queue_size", "mean"),
        max_queue_size=("max_queue_size", "max"),
        max_jump=("max_jump", "max"),
        avg_jump=("avg_jump", "mean"),
        avg_system_drift=("avg_system_drift", "mean"),
        max_system_drift=("max_system_drift", "max"),
        drift_from_avg_mean=("drift_from_avg", "mean"),
        drift_from_avg_min=("drift_from_avg", "min"),
        drift_from_avg_max=("drift_from_avg", "max"),
        internal_events=("internal_events", "mean"),
        send_events=("send_events", "mean"),
        recv_events=("recv_events", "mean"),
        broadcast_events=("broadcast_events", "mean"),
        total_events=("total_events", "mean"),
        final_clock=("final_clock", "mean"),
        run_duration=("run_duration", "mean"),
    ).reset_index()
    
    experiment = get_experiment(experiment_name)
    description = experiment.description if experiment else "Unknown experiment"
    
    # Format table
    markdown = f"## Summary for Experiment: {experiment_name}\n\n"
    markdown += f"**Description**: {description}\n\n"
    markdown += "### Machine Metrics\n\n"
    markdown += (
        "| Machine | Clock Rate (avg/max) | Queue Size (avg/max) | Clock Jumps (avg/max) "
        "| System Drift (avg/max) | Machine Drift (avg) | Events (I/S/R/B) | Run Duration | Final Clock |\n"
    )
    markdown += (
        "|---------|---------------------|---------------------|---------------------|"
        "------------------------|---------------------|-----------------|-------------|------------|\n"
    )
    
    for _, row in summary.iterrows():
        events = (
            f"{row['internal_events']:.1f}/"
            f"{row['send_events']:.1f}/"
            f"{row['recv_events']:.1f}/"
            f"{row['broadcast_events']:.1f}"
        )
        clock_rates = f"{row['avg_clock_rate']:.2f}/{row['max_clock_rate']:.2f}"
        queue_sizes = f"{row['avg_queue_size']:.2f}/{row['max_queue_size']:.0f}"
        jumps = f"{row['avg_jump']:.2f}/{row['max_jump']:.0f}"
        system_drift = f"{row['avg_system_drift']:.2f}/{row['max_system_drift']:.2f}"
        machine_drift = f"{row['drift_from_avg_mean']:.2f}"
        
        markdown += (
            f"| {row['machine_id']} | {clock_rates} | {queue_sizes} | {jumps} | "
            f"{system_drift} | {machine_drift} | {events} | "
            f"{row['run_duration']:.1f}s | {row['final_clock']:.0f} |\n"
        )
    
    # Add overall experiment analysis
    markdown += "\n### Key Observations\n\n"
    
    # Calculate overall metrics
    max_drift_between_machines = (
        metrics_df.groupby("trial")["final_clock"].max()
        - metrics_df.groupby("trial")["final_clock"].min()
    )
    avg_max_drift = max_drift_between_machines.mean()
    max_queue_size = metrics_df["max_queue_size"].max()
    max_jump_overall = metrics_df["max_jump"].max()
    avg_system_drift = metrics_df["avg_system_drift"].mean()
    
    markdown += f"* **Maximum drift between machines (avg across trials)**: {avg_max_drift:.2f} clock ticks\n"
    markdown += f"* **Maximum message queue size observed**: {max_queue_size:.0f} messages\n"
    markdown += f"* **Maximum clock jump observed**: {max_jump_overall:.0f} ticks\n"
    markdown += f"* **Average system time drift**: {avg_system_drift:.2f} ticks\n"
    
    return markdown


def calculate_time_series_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate time-series metrics for visualization.
    Groups data into 1-second intervals (time windows) 
    aggregated by machine and trial, and then computes
    the average clock across all machines for each trial/time_window.
    
    Args:
        df: DataFrame with raw log data
        
    Returns:
        DataFrame with aggregated metrics per time window.
    """
    if df.empty:
        return pd.DataFrame()
    
    # Create 1-second time windows based on relative time.
    df["time_window"] = (df["relative_time"] // 1).astype(int)
    
    # Group by machine_id, trial, and time_window and calculate aggregations.
    grouped = df.groupby(["machine_id", "trial", "time_window"])
    time_series = grouped.agg({
        "clock": ["mean", "min", "max"],
        "queue_size": ["mean", "max"],
        "clock_diff": ["mean", "max"],
        "system_drift": ["mean", "min", "max"],
        "timestamp": "mean"  # representative timestamp for this window
    }).reset_index()
    
    # Flatten the multi-level columns.
    time_series.columns = [
        "_".join(col).strip("_") if isinstance(col, tuple) else col
        for col in time_series.columns
    ]
    
    # Compute the average clock value per trial and time window across all machines.
    avg_clocks = (
        time_series.groupby(["trial", "time_window"])["clock_mean"]
        .mean()
        .reset_index()
        .rename(columns={"clock_mean": "avg_clock_all_machines"})
    )
    
    # Merge the average clock values back onto the aggregated DataFrame using both keys.
    time_series = pd.merge(time_series, avg_clocks, on=["trial", "time_window"], how="left")
    
    # Calculate the drift from the average clock for each observation.
    time_series["drift_from_avg"] = time_series["clock_mean"] - time_series["avg_clock_all_machines"]
    
    return time_series

def plot_clock_drift_over_time(time_series: pd.DataFrame, experiment_name: str, save_dir: Path) -> None:
    """
    Plot min/avg/max clock drifts over time with error bars.
    
    Args:
        time_series: DataFrame with time-series metrics
        experiment_name: Name of the experiment
        save_dir: Directory to save plots
    """
    if time_series.empty:
        console.log(f"[bold yellow]No data to plot for experiment: {experiment_name}[/]")
        return
    
    save_dir.mkdir(exist_ok=True, parents=True)
    
    # Only use the first trial for this plot to keep it clean
    trial = time_series['trial'].min()
    trial_data = time_series[time_series['trial'] == trial]
    
    plt.figure(figsize=(12, 8))
    
    # Color mapping for machines
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    machines = sorted(trial_data['machine_id'].unique())
    machine_colors = {m: colors[i % len(colors)] for i, m in enumerate(machines)}
    
    for machine_id in machines:
        machine_data = trial_data[trial_data['machine_id'] == machine_id]
        
        # Skip if no data
        if machine_data.empty:
            continue
            
        x = machine_data['time_window']
        y = machine_data['drift_from_avg']
        
        plt.plot(x, y, label=f"Machine {machine_id}", color=machine_colors[machine_id], linewidth=2)
    
    plt.title(f"Logical Clock Drift Between Machines - {experiment_name} (Trial {trial})", fontsize=14)
    plt.xlabel("Time (seconds)", fontsize=12)
    plt.ylabel("Drift from Average Clock (ticks)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()
    
    # Save plot
    plot_path = save_dir / f"{experiment_name}_clock_drift_between_machines.png"
    plt.savefig(plot_path, dpi=150)
    console.log(f"[green]Saved plot: {plot_path}[/]")
    plt.close()


def plot_system_drift_over_time(time_series: pd.DataFrame, experiment_name: str, save_dir: Path) -> None:
    """
    Plot drift from system time over time.
    
    Args:
        time_series: DataFrame with time-series metrics
        experiment_name: Name of the experiment
        save_dir: Directory to save plots
    """
    if time_series.empty:
        return
    
    save_dir.mkdir(exist_ok=True, parents=True)
    
    # Only use the first trial for this plot to keep it clean
    trial = time_series['trial'].min()
    trial_data = time_series[time_series['trial'] == trial]
    
    plt.figure(figsize=(12, 8))
    
    # Color mapping for machines
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    machines = sorted(trial_data['machine_id'].unique())
    machine_colors = {m: colors[i % len(colors)] for i, m in enumerate(machines)}
    
    for machine_id in machines:
        machine_data = trial_data[trial_data['machine_id'] == machine_id]
        
        # Skip if no data
        if machine_data.empty or machine_data['system_drift_mean'].isnull().all():
            continue
            
        x = machine_data['time_window']
        y = machine_data['system_drift_mean']
        y_min = machine_data['system_drift_min']
        y_max = machine_data['system_drift_max']
        
        plt.plot(x, y, label=f"Machine {machine_id}", color=machine_colors[machine_id], linewidth=2)
        plt.fill_between(x, y_min, y_max, color=machine_colors[machine_id], alpha=0.2)
    
    plt.title(f"Logical Clock Drift from System Time - {experiment_name} (Trial {trial})", fontsize=14)
    plt.xlabel("Time (seconds)", fontsize=12)
    plt.ylabel("Drift from System Time (ticks)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()
    
    # Save plot
    plot_path = save_dir / f"{experiment_name}_system_time_drift.png"
    plt.savefig(plot_path, dpi=150)
    console.log(f"[green]Saved plot: {plot_path}[/]")
    plt.close()


def plot_jumps_over_time(time_series: pd.DataFrame, experiment_name: str, save_dir: Path) -> None:
    """
    Plot logical clock jumps over time.
    
    Args:
        time_series: DataFrame with time-series metrics
        experiment_name: Name of the experiment
        save_dir: Directory to save plots
    """
    if time_series.empty:
        return
    
    save_dir.mkdir(exist_ok=True, parents=True)
    
    # Only use the first trial for this plot to keep it clean
    trial = time_series['trial'].min()
    trial_data = time_series[time_series['trial'] == trial]
    
    plt.figure(figsize=(12, 8))
    
    # Color mapping for machines
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    machines = sorted(trial_data['machine_id'].unique())
    machine_colors = {m: colors[i % len(colors)] for i, m in enumerate(machines)}
    
    for machine_id in machines:
        machine_data = trial_data[trial_data['machine_id'] == machine_id]
        
        # Skip if no data
        if machine_data.empty:
            continue
            
        x = machine_data['time_window']
        y_avg = machine_data['clock_diff_mean']
        y_max = machine_data['clock_diff_max']
        
        plt.plot(x, y_avg, label=f"Machine {machine_id} (Avg)", color=machine_colors[machine_id], linewidth=2)
        plt.plot(x, y_max, label=f"Machine {machine_id} (Max)", color=machine_colors[machine_id], 
                linestyle='--', linewidth=1.5, alpha=0.8)
    
    plt.title(f"Logical Clock Jumps - {experiment_name} (Trial {trial})", fontsize=14)
    plt.xlabel("Time (seconds)", fontsize=12)
    plt.ylabel("Clock Jump Size (ticks)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()
    
    # Save plot
    plot_path = save_dir / f"{experiment_name}_clock_jumps.png"
    plt.savefig(plot_path, dpi=150)
    console.log(f"[green]Saved plot: {plot_path}[/]")
    plt.close()


def plot_queue_sizes_over_time(
    time_series: pd.DataFrame, experiment_name: str, save_dir: Path
) -> None:
    """
    Plot message queue sizes over time.
    
    Args:
        time_series: DataFrame with time-series metrics.
        experiment_name: Name of the experiment.
        save_dir: Directory to save plots.
    """
    if time_series.empty:
        console.log(f"[bold yellow]No data to plot for experiment: {experiment_name}[/]")
        return

    save_dir.mkdir(exist_ok=True, parents=True)
    
    # Only use the first trial for this plot to keep it clean.
    trial = time_series["trial"].min()
    trial_data = time_series[time_series["trial"] == trial]
    
    plt.figure(figsize=(12, 8))
    
    # Color mapping for machines.
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
    machines = sorted(trial_data["machine_id"].unique())
    machine_colors = {m: colors[i % len(colors)] for i, m in enumerate(machines)}
    
    for machine_id in machines:
        machine_data = trial_data[trial_data["machine_id"] == machine_id]
        if machine_data.empty:
            continue
        
        plt.plot(
            machine_data["time_window"],
            machine_data["queue_size_mean"],
            label=f"Machine {machine_id}",
            color=machine_colors[machine_id],
            linewidth=2,
        )
        # Use the max as error (this is a simplistic error bound)
        plt.fill_between(
            machine_data["time_window"],
            machine_data["queue_size_mean"] - machine_data["queue_size_max"],
            machine_data["queue_size_mean"] + machine_data["queue_size_max"],
            color=machine_colors[machine_id],
            alpha=0.2,
        )
    
    plt.title(
        f"Message Queue Sizes Over Time - {experiment_name} (Trial {trial})", fontsize=14
    )
    plt.xlabel("Time (seconds)", fontsize=12)
    plt.ylabel("Queue Size", fontsize=12)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    plot_path = save_dir / f"{experiment_name}_queue_sizes_over_time.png"
    plt.savefig(plot_path, dpi=150)
    console.log(f"[green]Saved plot: {plot_path}[/]")
    plt.close()


def analyze_experiment(experiment_name: str, output_dir: Path) -> None:
    """
    Analyze an experiment using time series metrics and generate refined visualizations.
    
    Args:
        experiment_name: Name of the experiment to analyze.
        output_dir: Directory to save analysis results.
    """
    console.log(f"[bold blue]Analyzing experiment: {experiment_name}[/]")
    
    # Load raw data.
    df = load_experiment_data(experiment_name)
    if df.empty:
        console.log(f"[bold red]No data found for experiment: {experiment_name}[/]")
        return
    
    # Calculate aggregated metrics.
    metrics_df = calculate_metrics(df)
    summary_markdown = generate_summary_table(metrics_df, experiment_name)
    console.log(Markdown(summary_markdown))
    
    # Save summary to file.
    summary_file = output_dir / f"{experiment_name}_summary.md"
    summary_file.write_text(summary_markdown)
    console.log(f"[green]Saved summary: {summary_file}[/]")
    
    # Calculate time series metrics.
    ts_df = calculate_time_series_metrics(df)
    
    # Create plots directory.
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(exist_ok=True, parents=True)
    
    # Plot clock drift between machines over time.
    plot_clock_drift_over_time(ts_df, experiment_name, plots_dir)
    # Plot drift of clocks from system time over time.
    plot_system_drift_over_time(ts_df, experiment_name, plots_dir)
    # Plot clock jumps over time.
    plot_jumps_over_time(ts_df, experiment_name, plots_dir)
    # Plot queue sizes over time.
    plot_queue_sizes_over_time(ts_df, experiment_name, plots_dir)


def main() -> None:
    """Main function for analysis script."""
    parser = argparse.ArgumentParser(
        description="Analyze logical clock simulation logs"
    )
    parser.add_argument(
        "--experiment", "-e", help="Experiment to analyze"
    )
    parser.add_argument(
        "--all", "-a", action="store_true", help="Analyze all experiments"
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="List available experiments"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="analysis",
        help="Output directory for analysis results",
    )
    
    args = parser.parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    if args.list:
        console.log("[bold]Available experiments:[/]")
        for name in list_experiments():
            experiment = get_experiment(name)
            console.log(
                f"  [green]{name}[/]: {experiment.description} "
                f"({experiment.trials} trials, timeout {experiment.timeout}s)"
            )
        return
    
    if args.all:
        for name in list_experiments():
            analyze_experiment(name, output_dir)
    elif args.experiment:
        analyze_experiment(args.experiment, output_dir)
    else:
        console.log("[bold yellow]No experiment specified. Use --experiment or --all.[/]")
        console.log("Available experiments:")
        for name in list_experiments():
            experiment = get_experiment(name)
            console.log(
                f"  [green]{name}[/]: {experiment.description} "
                f"({experiment.trials} trials, timeout {experiment.timeout}s)"
            )


if __name__ == "__main__":
    main()
