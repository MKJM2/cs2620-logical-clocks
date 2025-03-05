Design decisions:

Please look at our engineering notebook for a timeline of our design decisions. It is written in more detail there. But here is a summary of our design decisions.

The first main decision we made was using processes instead of threads to simulate each machine. This seems to align with the assignment description to use communication protocols. We want to enforce separation because we want to limit the address space sharing. Also, using processes fits the purpose of the assignment more as it resemebles separate machines more than threads. To this end, we spawn 3 processes to model each machine. We modularized the code accordingly.

For communication between machines, we chose gRPC over other protocols due to its strong support for distributed systems and clean interface for remote procedure calls. Each machine runs a gRPC server and connects to its peers as a client, allowing for message passing that closely resembles network communication in real distributed systems. We implemented an asynchronous approach using asyncio to handle concurrency effectively, allowing each machine to maintain its own internal clock rate while still responding to incoming messages at network speed.

The third key design decision was our approach to experimentation and analysis. We created a framework that allows us to define multiple experiment configurations with different parameters (clock rates, machine counts, trial durations) and run them systematically. For data collection, we implemented a structured logging system where each machine writes time-stamped events to its own log file. We then built analysis tools that process these logs to calculate metrics such as clock drift, queue sizes, and event distributions, generating both numerical summaries and visualizations to help us understand the behavior of logical clocks under different conditions.

Experiment Observation:

1. Bottleneck Experiment

    Setup: Machine A has a significantly lower tick count (1) compared to Machines B and C (8 each).
    Observations:
        Queue Sizes: Machine A consistently exhibits much larger average and maximum queue sizes compared to B and C. This is the MOST pronounced trend.
        Event Distribution: Machine A spends almost all its time receiving messages (high "recv" percentage), while B and C spend most of their time on internal events.
        Clock Rates: The average clock rates for B and C are much higher than A, as expected.
        Clock Drifts: The maximum clock drift between machines is relatively high.
    Expectations:
        The observations largely match expectations. The bottleneck at Machine A causes messages to queue up, leading to high "recv" events and lower clock progression. B and C, running much faster, generate more internal events and send messages that A can't process quickly enough.

2. Progressive Experiment

    Setup: Machines have progressively increasing tick counts (A: 2, B: 4, C: 6).
    Observations:
        Queue Sizes: Machine A tends to have slightly larger queue sizes than B and C, but the differences are much smaller than in the "bottleneck" experiment.
        Event Distribution: Machine A has a high "recv" percentage, while C has a high "internal" percentage. B falls in between.
        Clock Rates: The average clock rates are relatively close, but C is slightly higher than B, which is slightly higher than A.
        Clock Drifts: The maximum clock drift between machines is relatively low.
    Expectations:
        The observations generally align with expectations. The progressive increase in tick counts leads to a more balanced system than the "bottleneck" scenario. Machine A still receives more messages, but the queue buildup is less severe.

3. Five Machines Experiment

    Setup: Five machines with relatively similar tick counts (A: 3, B: 4, C: 5, D: 4, E: 3).
    Observations:
        Queue Sizes: Machines A and E tend to have slightly larger queue sizes than B, C, and D.
        Event Distribution: Machines A and E have higher "recv" percentages, while B, C, and D have higher "internal" percentages.
        Clock Rates: The average clock rates are relatively close across all machines.
        Clock Drifts: The maximum clock drift between machines is very low.
    Expectations:
        The observations are mostly as expected. With similar tick counts, the system is relatively balanced, leading to low clock drifts. The slight differences in queue sizes and event distributions might be due to network topology or random variations in message sending.

General Trends and Correlations

    Tick Count and Queue Size: There's a strong negative correlation between a machine's tick count and its average queue size. Machines with lower tick counts tend to have larger queues.
    Tick Count and Event Distribution: There's a correlation between a machine's tick count and its event distribution. Machines with lower tick counts tend to have higher "recv" percentages, while machines with higher tick counts tend to have higher "internal" percentages.
    Queue Size and "recv" Events: There's a strong positive correlation between a machine's average queue size and its "recv" event percentage.
    Clock Drift and Tick Count Variance: Experiments with higher variance in tick counts (e.g., "bottleneck") tend to have higher maximum clock drifts between machines.
    System Time Drift: The average system time drift seems to be influenced by the overall clock rates in the system. Experiments with higher tick counts tend to have higher average system time drifts.

Areas for Further Investigation

    Network Topology: The current analysis doesn't account for network topology. It would be interesting to explore how different network configurations (e.g., star, ring, mesh) affect the observed metrics.
    Message Sending Probabilities: The current analysis assumes uniform message sending probabilities. It would be valuable to investigate how non-uniform probabilities affect queue sizes, clock drifts, and event distributions.
    Longer Simulation Runs: Running the simulations for longer durations could reveal long-term trends and stability properties of the logical clocks.

Overall, the observations from your experiments provide valuable insights into the behavior of logical clocks under different conditions. The trends generally match my expectations, but there are also some interesting nuances that warrant further investigation.