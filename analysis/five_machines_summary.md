## Summary for Experiment: five_machines

**Description**: Increased scale with five machines

### Machine Metrics

| Machine | Clock Rate (avg/max) | Queue Size (avg/max) | Clock Jumps (avg/max) | System Drift (avg/max) | Machine Drift (avg) | Events (I/S/R/B) | Run Duration | Final Clock |
|---------|---------------------|---------------------|---------------------|------------------------|---------------------|-----------------|-------------|------------|
| A | 5.03/23.96 | 0.06/2 | 1.68/10 | 60.88/123.57 | -1.08 | 71.0/20.2/78.6/8.2 | 59.2s | 299 |
| B | 5.03/22.39 | 0.02/1 | 1.26/6 | 31.78/64.22 | -0.68 | 118.4/35.0/69.6/14.0 | 59.2s | 299 |
| C | 5.08/10.07 | 0.02/1 | 1.02/2 | 3.45/9.84 | 2.32 | 158.6/44.6/71.0/21.8 | 59.3s | 302 |
| D | 5.05/22.33 | 0.06/2 | 1.27/7 | 32.37/67.20 | -0.08 | 102.0/29.8/91.6/13.6 | 59.2s | 300 |
| E | 5.04/22.82 | 0.16/2 | 1.68/10 | 61.32/127.47 | -0.48 | 61.2/15.8/93.4/7.6 | 59.2s | 299 |

### Key Observations

* **Maximum drift between machines (avg across trials)**: 3.60 clock ticks
* **Maximum message queue size observed**: 2 messages
* **Maximum clock jump observed**: 10 ticks
* **Average system time drift**: 37.96 ticks
