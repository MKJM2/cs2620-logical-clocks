## Summary for Experiment: high_variance

**Description**: Machines with widely varying clock rates (10x difference)

### Machine Metrics

| Machine | Clock Rate (avg/max) | Queue Size (avg/max) | Clock Jumps (avg/max) | System Drift (avg/max) | Machine Drift (avg) | Events (I/S/R/B) | Run Duration | Final Clock |
|---------|---------------------|---------------------|---------------------|------------------------|---------------------|-----------------|-------------|------------|
| A | 4.23/16.98 | 41.07/98 | 4.23/20 | 94.28/206.93 | -224.93 | 0.8/0.2/59.0/0.0 | 59.1s | 251 |
| B | 9.89/70.62 | 0.06/2 | 1.99/16 | 144.57/292.24 | 111.07 | 135.8/33.0/108.8/18.2 | 59.2s | 587 |
| C | 9.92/10.36 | 0.00/0 | 1.00/1 | -1.35/1.04 | 113.87 | 385.4/118.4/35.4/50.2 | 59.3s | 589 |

### Key Observations

* **Maximum drift between machines (avg across trials)**: 338.80 clock ticks
* **Maximum message queue size observed**: 98 messages
* **Maximum clock jump observed**: 20 ticks
* **Average system time drift**: 79.16 ticks
