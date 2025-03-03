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


def run_command(cmd: list[str], env: dict | None = None) -> None:
    print("running:", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True, env=env)


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


def run_project() -> None:
    venv_python: Path = get_venv_python()
    run_command([str(venv_python), "-m", "src.orchestrator"])


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
        choices=["setup", "run", "lint", "type", "all"],
        nargs="?",
        default="run",
        help="command to execute: setup, run, lint, type, or all (lint & type then run)",
    )
    args = parser.parse_args()

    if args.command == "setup":
        setup_project()
    elif args.command == "run":
        setup_project()
        run_project()
    elif args.command == "lint":
        setup_project()
        run_lint()
    elif args.command == "type":
        setup_project()
        run_type()
    elif args.command == "all":
        setup_project()
        run_lint()
        run_type()
        run_project()


if __name__ == "__main__":
    main()
