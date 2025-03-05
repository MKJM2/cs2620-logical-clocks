## Summary for Experiment: long_running

**Description**: Extended run to observe long-term behavior

### Machine Metrics

| Machine | Clock Rate (avg/max) | Queue Size (avg/max) | Clock Jumps (avg/max) | System Drift (avg/max) | Machine Drift (avg) | Events (I/S/R/B) | Run Duration | Final Clock |
|---------|---------------------|---------------------|---------------------|------------------------|---------------------|-----------------|-------------|------------|
| A | 5.09/27.99 | 0.11/3 | 1.70/10 | 186.88/378.56 | -0.56 | 204.7/59.3/244.0/28.7 | 179.2s | 912 |
| B | 5.09/10.09 | 0.01/2 | 1.02/2 | 9.09/21.14 | 0.44 | 516.0/151.3/157.3/68.3 | 179.2s | 913 |
| C | 5.09/27.91 | 0.03/3 | 1.28/8 | 97.97/200.26 | 0.11 | 351.3/112.0/206.0/45.7 | 179.2s | 913 |

### Key Observations

* **Maximum drift between machines (avg across trials)**: 1.33 clock ticks
* **Maximum message queue size observed**: 3 messages
* **Maximum clock jump observed**: 10 ticks
* **Average system time drift**: 97.98 ticks
