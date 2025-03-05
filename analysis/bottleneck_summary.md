## Summary for Experiment: bottleneck

**Description**: One slow machine with faster peers - potential message queue buildup

### Machine Metrics

| Machine | Clock Rate (avg/max) | Queue Size (avg/max) | Clock Jumps (avg/max) | System Drift (avg/max) | Machine Drift (avg) | Events (I/S/R/B) | Run Duration | Final Clock |
|---------|---------------------|---------------------|---------------------|------------------------|---------------------|-----------------|-------------|------------|
| A | 3.14/11.38 | 46.10/112 | 3.15/14 | 61.85/156.93 | -196.47 | 1.0/0.0/59.0/0.0 | 59.1s | 187 |
| B | 8.10/14.49 | 0.01/1 | 1.02/2 | 4.45/29.92 | 98.33 | 283.8/74.0/80.2/34.2 | 59.3s | 481 |
| C | 8.09/14.50 | 0.01/1 | 1.02/2 | 4.46/28.98 | 98.13 | 285.8/76.4/70.8/39.4 | 59.3s | 481 |

### Key Observations

* **Maximum drift between machines (avg across trials)**: 294.80 clock ticks
* **Maximum message queue size observed**: 112 messages
* **Maximum clock jump observed**: 14 ticks
* **Average system time drift**: 23.58 ticks
