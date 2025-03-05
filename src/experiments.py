"""
Enhanced experiment framework for logical clocks simulation.
Supports multiple trials and structured configuration.
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, TypedDict, Union


class MachineConfig(TypedDict):
    """Type definition for machine configuration."""
    ticks: int
    port: int
    log_path: str


class ExperimentType(Enum):
    """Types of experiments we can run."""
    CLOCK_RATES = "clock_rates"
    TOPOLOGY = "topology"
    SCALE = "scale"


@dataclass
class Experiment:
    """Experiment configuration."""
    name: str
    description: str
    type: ExperimentType
    machines: Dict[str, MachineConfig]
    trials: int = 1
    base_log_dir: str = "logs"
    timeout: int = 60  # seconds
    
    def get_log_path(self, machine_id: str, trial: int) -> str:
        """Generate log path for a specific machine and trial."""
        return f"{self.base_log_dir}/{machine_id}.{self.name}.trial_{trial}.log"
    
    def get_machine_config_for_trial(self, machine_id: str, trial: int) -> MachineConfig:
        """Get machine configuration for a specific trial."""
        config = self.machines[machine_id].copy()
        config["log_path"] = self.get_log_path(machine_id, trial)
        return config
    
    def get_all_log_paths(self) -> List[str]:
        """Get all log paths for this experiment across all machines and trials."""
        paths = []
        for machine_id in self.machines:
            for trial in range(1, self.trials + 1):
                paths.append(self.get_log_path(machine_id, trial))
        return paths


# Define available experiments
EXPERIMENTS: Dict[str, Experiment] = {
    "baseline": Experiment(
        name="baseline",
        description="Machines running at randomly selected (1 to  6) tickrates, per assignment statemnet",
        type=ExperimentType.CLOCK_RATES,
        machines={
            "A": {"ticks": 3, "port": 50051, "log_path": ""},
            "B": {"ticks": 5, "port": 50052, "log_path": ""},
            "C": {"ticks": 2, "port": 50053, "log_path": ""}
        },
        trials=5,
        timeout=60
    ),

    "fast_clocks": Experiment(
        name="fast_clocks",
        description="Machines running at higher clock rates",
        type=ExperimentType.CLOCK_RATES,
        machines={
            "A": {"ticks": 10, "port": 50051, "log_path": ""},
            "B": {"ticks": 12, "port": 50052, "log_path": ""},
            "C": {"ticks": 8, "port": 50053, "log_path": ""}
        },
        trials=5,
        timeout=60
    ),
    
    "high_variance": Experiment(
        name="high_variance",
        description="Machines with widely varying clock rates",
        type=ExperimentType.CLOCK_RATES,
        machines={
            "A": {"ticks": 1, "port": 50051, "log_path": ""},
            "B": {"ticks": 10, "port": 50052, "log_path": ""},
            "C": {"ticks": 5, "port": 50053, "log_path": ""}
        },
        trials=3
    ),
    
    "five_machines": Experiment(
        name="five_machines",
        description="Simulation with five machines",
        type=ExperimentType.SCALE,
        machines={
            "A": {"ticks": 3, "port": 50051, "log_path": ""},
            "B": {"ticks": 5, "port": 50052, "log_path": ""},
            "C": {"ticks": 2, "port": 50053, "log_path": ""},
            "D": {"ticks": 4, "port": 50054, "log_path": ""},
            "E": {"ticks": 6, "port": 50055, "log_path": ""}
        },
        trials=2
    ),

    "low_internal_prob": Experiment(
        name="low_internal_prob",
        description="Balanced machines with a lower probability of internal events",
        type=ExperimentType.CLOCK_RATES,
        machines={
            "A": {"ticks": 5, "port": 50051, "log_path": "", "internal_event_weight": 2},
            "B": {"ticks": 5, "port": 50052, "log_path": "", "internal_event_weight": 2},
            "C": {"ticks": 5, "port": 50053, "log_path": "", "internal_event_weight": 2}
        },
        trials=5,
        timeout=60
    ),

    "imbalanced_low_internal_prob": Experiment(
        name="imbalanced_low_internal_prob",
        description="Imbalanced machines with a lower probability of internal events, same tickrates as baseline",
        type=ExperimentType.CLOCK_RATES,
        machines={
            "A": {"ticks": 3, "port": 50051, "log_path": "", "internal_event_weight": 2},
            "B": {"ticks": 5, "port": 50052, "log_path": "", "internal_event_weight": 2},
            "C": {"ticks": 2, "port": 50053, "log_path": "", "internal_event_weight": 2}
        },
        trials=5,
        timeout=60
    ),

    "high_internal_prob": Experiment(
        name="high_internal_prob",
        description="Balanced machines with a higher probability of internal events",
        type=ExperimentType.CLOCK_RATES,
        machines={
            "A": {"ticks": 5, "port": 50051, "log_path": "", "internal_event_weight": 17},
            "B": {"ticks": 5, "port": 50052, "log_path": "", "internal_event_weight": 17},
            "C": {"ticks": 5, "port": 50053, "log_path": "", "internal_event_weight": 17}
        },
        trials=5,
        timeout=60
    ),

    "imbalanced_high_internal_prob": Experiment(
        name="imbalanced_high_internal_prob",
        description="Imbalanced machines with a higher probability of internal events, same tickrates as baseline",
        type=ExperimentType.CLOCK_RATES,
        machines={
            "A": {"ticks": 3, "port": 50051, "log_path": "", "internal_event_weight": 17},
            "B": {"ticks": 5, "port": 50052, "log_path": "", "internal_event_weight": 17},
            "C": {"ticks": 2, "port": 50053, "log_path": "", "internal_event_weight": 17}
        },
        trials=5,
        timeout=60
    )
}


def get_experiment(name: str) -> Optional[Experiment]:
    """Get a predefined experiment by name."""
    return EXPERIMENTS.get(name)


def list_experiments() -> List[str]:
    """List all available experiments."""
    return list(EXPERIMENTS.keys())


def get_experiment_config_for_trial(
    experiment_name: str, 
    trial: int = 1
) -> Dict[str, Dict[str, Union[int, str]]]:
    """
    Get the configuration for a specific experiment trial.
    
    Args:
        experiment_name: Name of the experiment
        trial: Trial number (1-based indexing)
        
    Returns:
        Dictionary of machine configurations with trial-specific log paths
    """
    experiment = get_experiment(experiment_name)
    if not experiment:
        return {}
    
    config = {}
    for machine_id in experiment.machines:
        config[machine_id] = experiment.get_machine_config_for_trial(machine_id, trial)
    
    return config
