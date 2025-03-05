## Summary for Experiment: extreme_imbalance

**Description**: Extreme difference in clock rates

### Machine Metrics

| Machine | Clock Rate (avg/max) | Queue Size (avg/max) | Clock Jumps (avg/max) | System Drift (avg/max) | Machine Drift (avg) | Events (I/S/R/B) | Run Duration | Final Clock |
|---------|---------------------|---------------------|---------------------|------------------------|---------------------|-----------------|-------------|------------|
| A | 5.15/23.97 | 84.44/205 | 5.15/29 | 123.09/288.95 | -385.93 | 0.6/0.4/59.0/0.0 | 59.1s | 305 |
| B | 19.69/21.33 | 0.00/0 | 1.00/1 | -8.41/2.00 | 477.27 | 815.8/244.8/0.4/107.0 | 59.3s | 1168 |
| C | 10.12/45.05 | 54.35/118 | 5.07/27 | 242.66/524.78 | -91.33 | 1.0/0.2/117.8/0.0 | 59.1s | 600 |

### Key Observations

* **Maximum drift between machines (avg across trials)**: 863.20 clock ticks
* **Maximum message queue size observed**: 205 messages
* **Maximum clock jump observed**: 29 ticks
* **Average system time drift**: 119.11 ticks
