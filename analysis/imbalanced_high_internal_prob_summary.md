## Summary for Experiment: imbalanced_high_internal_prob

**Description**: Imbalanced machines with a higher probability of internal events, same tickrates as baseline

### Machine Metrics

| Machine | Clock Rate (avg/max) | Queue Size (avg/max) | Clock Jumps (avg/max) | System Drift (avg/max) | Machine Drift (avg) | Events (I/S/R/B) | Run Duration | Final Clock |
|---------|---------------------|---------------------|---------------------|------------------------|---------------------|-----------------|-------------|------------|
| A | 4.90/52.72 | 0.00/1 | 1.64/23 | 55.59/117.41 | -2.93 | 126.0/14.8/29.8/7.2 | 59.1s | 290 |
| B | 4.98/7.06 | 0.00/1 | 1.00/2 | 0.41/1.77 | 2.67 | 237.4/26.2/19.8/12.0 | 59.2s | 296 |
| C | 4.95/46.04 | 0.05/2 | 2.48/32 | 83.94/176.75 | 0.27 | 68.2/6.2/41.6/3.0 | 59.1s | 294 |

### Key Observations

* **Maximum drift between machines (avg across trials)**: 5.60 clock ticks
* **Maximum message queue size observed**: 2 messages
* **Maximum clock jump observed**: 32 ticks
* **Average system time drift**: 46.65 ticks
