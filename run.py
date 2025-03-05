#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path

VENV_DIR: Path = Path(".venv").resolve()


def get_venv_python() -> Path:
    if sys.platform.startswith("win"):
        return VENV_DIR / "Scripts" / "python.exe"
    else:
        return VENV_DIR / "bin" / "python"

def run_command(cmd: list[str], env: dict | None = None, timeout: int | None = None) -> None:
    print("running:", " ".join(map(str, cmd)))
    try:
        subprocess.run(cmd, check=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"Command timed out after {timeout} seconds")
        raise


def run_experiment(experiment_name: str, extra_args: list[str]) -> None:
    venv_python: Path = get_venv_python()
    
    try:
        # Get experiment configuration including trials and timeout
        result = subprocess.run(
            [str(venv_python), "-c", 
             f"from src.experiments import get_experiment; "
             f"exp = get_experiment('{experiment_name}'); "
             f"print(f'{{exp.trials}},{{exp.timeout}}' if exp else '0,0')"],
            capture_output=True,
            text=True,
            check=True
        )
        
        trials_and_timeout = result.stdout.strip().split(',')
        num_trials = int(trials_and_timeout[0])
        timeout = int(trials_and_timeout[1])
        
        if num_trials <= 0:
            print(f"Error: Experiment '{experiment_name}' not found")
            sys.exit(1)
        
        print(f"Running experiment '{experiment_name}' with {num_trials} trials (timeout: {timeout}s)...")
        
        # Run each trial
        for trial in range(1, num_trials + 1):
            print(f"\n=== Trial {trial}/{num_trials} ===")
            cmd = [
                str(venv_python), 
                "-m", 
                "src.orchestrator", 
                "--experiment", 
                experiment_name,
                "--trial", 
                str(trial)
            ] + extra_args
            
            # Start the orchestrator process
            process = subprocess.Popen(cmd)
            
            try:
                # Wait for the process to finish, with timeout
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                print(f"\nTimeout reached ({timeout}s). Terminating orchestrator...")
                # Send SIGTERM to trigger the orchestrator's graceful shutdown
                process.terminate()
                try:
                    # Give it a bit of time to clean up
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("Orchestrator didn't terminate gracefully, forcing...")
                    process.kill()
            
            # Ensure the process is terminated
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            
        # After all trials, run analysis
        print("\n=== Analyzing Results ===")
        subprocess.run([
            str(venv_python), 
            "-m", 
            "src.analyze", 
            "--experiment", 
            experiment_name
        ], check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"Error running experiment: {e}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nExperiment interrupted")
        sys.exit(1)

def setup_project() -> None:
    if not VENV_DIR.exists():
        print("creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)

    venv_python: Path = get_venv_python()

    # attempt to upgrade pip; if pip is missing, bootstrap with ensurepip
    try:
        run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
    except subprocess.CalledProcessError:
        print("pip not found; bootstrapping pip with ensurepip...")
        run_command([str(venv_python), "-m", "ensurepip", "--upgrade"])
        run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])

    # install required packages: uv, mypy, and ruff
    run_command([str(venv_python), "-m", "pip", "install", "uv", "mypy", "ruff"])

    # uninstall previous installation if it exists
    try:
        run_command(
            [str(venv_python), "-m", "uv", "pip", "uninstall", "cs2620-logical-clocks"]
        )
    except subprocess.CalledProcessError:
        print("previous installation not found; skipping uninstall.")

    # install package in editable mode with UV_PREVIEW enabled
    env = os.environ.copy()
    env["UV_PREVIEW"] = "1"
    run_command([str(venv_python), "-m", "uv", "pip", "install", "-e", "."], env=env)

def run_project(extra_args: list[str]) -> None:
    venv_python: Path = get_venv_python()
    try:
        run_command([str(venv_python), "-m", "src.orchestrator"] + extra_args)
    except KeyboardInterrupt:
        sys.exit(0)

def run_lint() -> None:
    venv_python: Path = get_venv_python()
    run_command([str(venv_python), "-m", "ruff", "check"])

def run_type() -> None:
    venv_python: Path = get_venv_python()
    run_command([str(venv_python), "-m", "mypy", "src"])

def main() -> None:
    parser = argparse.ArgumentParser(description="Project setup and execution utility.")
    parser.add_argument(
        "command",
        choices=["setup", "run", "lint", "type", "check", "all", "test", "experiment", "analyze"],
        nargs="?",
        default="run",
        help="command to execute: setup, run, lint, type, check, all, test, experiment, or analyze",
    )
    parser.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="additional arguments to pass to the underlying command",
    )
    args = parser.parse_args()

    if args.command == "setup":
        setup_project()
    elif args.command == "run":
        run_project(args.extra_args)
    elif args.command == "lint":
        run_lint()
    elif args.command == "type":
        run_type()
    elif args.command == "check":
        run_lint()
        run_type()
    elif args.command == "all":
        setup_project()
        run_lint()
        run_type()
        run_project(args.extra_args)
    elif args.command == "test":
        run_tests(args.extra_args)
    elif args.command == "experiment":
        if not args.extra_args:
            print("Error: Experiment name required")
            print("Available experiments:")
            run_command([str(get_venv_python()), "-m", "src.analyze", "--list"])
            sys.exit(1)
        experiment_name = args.extra_args[0]
        run_experiment(experiment_name, args.extra_args[1:])
    elif args.command == "analyze":
        venv_python: Path = get_venv_python()
        if not args.extra_args:
            run_command([str(venv_python), "-m", "src.analyze", "--list"])
        else:
            run_command([str(venv_python), "-m", "src.analyze"] + args.extra_args)

if __name__ == "__main__":
    main()

