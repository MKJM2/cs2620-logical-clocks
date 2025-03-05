## Summary for Experiment: progressive

**Description**: Progressively faster machines

### Machine Metrics

| Machine | Clock Rate (avg/max) | Queue Size (avg/max) | Clock Jumps (avg/max) | System Drift (avg/max) | Machine Drift (avg) | Events (I/S/R/B) | Run Duration | Final Clock |
|---------|---------------------|---------------------|---------------------|------------------------|---------------------|-----------------|-------------|------------|
| A | 5.81/24.38 | 2.41/10 | 2.91/15 | 111.79/236.73 | -8.53 | 10.2/3.6/103.0/2.2 | 59.2s | 345 |
| B | 6.02/29.51 | 0.04/1 | 1.51/9 | 60.15/122.11 | 4.07 | 110.8/31.2/80.0/15.0 | 59.3s | 357 |
| C | 6.02/10.86 | 0.00/1 | 1.01/2 | 1.92/4.38 | 4.47 | 209.8/71.6/33.2/39.8 | 59.3s | 358 |

### Key Observations

* **Maximum drift between machines (avg across trials)**: 13.20 clock ticks
* **Maximum message queue size observed**: 10 messages
* **Maximum clock jump observed**: 15 ticks
* **Average system time drift**: 57.95 ticks
