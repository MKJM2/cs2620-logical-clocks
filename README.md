# CS2620 Logical Clocks

A simulation of distributed systems with logical clocks. This project models multiple machines running at different clock rates, communicating via messages, and implementing Lamport's logical clocks.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) - Python package manager
- gRPC tools

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/cs2620-logical-clocks.git
   cd cs2620-logical-clocks
   ```

2. Install the package in development mode:
   ```bash
   UV_PREVIEW=1 uv pip install -e .
   ```

## Usage

Run the orchestrator to start the simulation:

```bash
python -m src.orchestrator
```

The orchestrator will:
- Create multiple virtual machines
- Assign random clock rates to each
- Establish communication channels between them
- Start the logical clock simulation

Press Ctrl+C to stop the simulation.

## Regenerating Protocol Buffers

If you modify the Protocol Buffer definitions, you'll need to regenerate the Python files:

```bash
python -m grpc_tools.protoc -I src/protos --python_out=src/protos --grpc_python_out=src/protos src/protos/clock.proto
```

After generating the files, you must fix the imports in `clock_pb2_grpc.py`:
1. Open `src/protos/clock_pb2_grpc.py`
2. Change `import clock_pb2 as clock__pb2` to `from . import clock_pb2 as clock__pb2`

Alternatively, use the provided build script:
```bash
python build_protos.py
```

## Development

### Code Formatting and Linting

Format and lint your code using Ruff:

```bash
uv run ruff check .
uv run ruff format .
```

### Type Checking

Check type annotations using MyPy:

```bash
uv run mypy src
```

## Project Structure

- `src/` - Main source code
  - `orchestrator.py` - Manages the overall simulation
  - `machine.py` - Individual machine implementation
  - `protos/` - Protocol Buffer definitions for gRPC communication
- `config.toml` - Configuration file

## Configuration

Edit `config.toml` to adjust simulation parameters:
- Number of machines
- Clock rate ranges (#TODO)
- Message probabilities (#TODO)
- Run duration (#TODO)

## Lab Notebook

Observations from running the simulation will be documented in `NOTEBOOK.md`, including:
- Logical clock value jumps
- Clock drift between machines
- Queue length analysis
- Effects of varying parameters
