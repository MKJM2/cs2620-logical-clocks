"""
Predefined experiments for the logical clocks simulation.
Each experiment is a dictionary of machine configuration overrides.
"""

EXPERIMENTS = {
    "fast_clocks": {
        "A": {"ticks": 10},
        "B": {"ticks": 12},
        "C": {"ticks": 8}
    },
    
    "five_machines": {
        "A": {"ticks": 3, "port": 50051, "log_path": "logs/A.log"},
        "B": {"ticks": 5, "port": 50052, "log_path": "logs/B.log"},
        "C": {"ticks": 2, "port": 50053, "log_path": "logs/C.log"},
        "D": {"ticks": 4, "port": 50054, "log_path": "logs/D.log"},
        "E": {"ticks": 6, "port": 50055, "log_path": "logs/E.log"}
    },
    
    "high_variance": {
        "A": {"ticks": 1},
        "B": {"ticks": 10}, 
        "C": {"ticks": 5}
    }
}

def get_experiment(name: str) -> dict:
    """Get a predefined experiment configuration by name."""
    return EXPERIMENTS.get(name, None)

def list_experiments() -> list[str]:
    """List all available experiments."""
    return list(EXPERIMENTS.keys())
