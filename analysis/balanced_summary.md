## Summary for Experiment: balanced

**Description**: All machines running at the same clock rate

### Machine Metrics

| Machine | Clock Rate (avg/max) | Queue Size (avg/max) | Clock Jumps (avg/max) | System Drift (avg/max) | Machine Drift (avg) | Events (I/S/R/B) | Run Duration | Final Clock |
|---------|---------------------|---------------------|---------------------|------------------------|---------------------|-----------------|-------------|------------|
| A | 5.00/8.99 | 0.07/2 | 1.00/2 | 1.29/2.82 | 0.00 | 145.0/45.6/86.0/19.4 | 59.3s | 297 |
| B | 5.00/9.03 | 0.06/2 | 1.00/2 | 1.28/2.84 | 0.00 | 145.2/45.0/81.2/24.6 | 59.3s | 297 |
| C | 5.00/9.03 | 0.05/2 | 1.00/2 | 1.31/2.87 | 0.00 | 150.8/41.4/86.6/17.2 | 59.3s | 297 |

### Key Observations

* **Maximum drift between machines (avg across trials)**: 0.00 clock ticks
* **Maximum message queue size observed**: 2 messages
* **Maximum clock jump observed**: 2 ticks
* **Average system time drift**: 1.29 ticks
