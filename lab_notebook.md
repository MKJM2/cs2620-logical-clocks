Summary of Design Decisions:

The first main decision we made was using processes instead of threads to simulate each machine. This seems to align with the assignment description to use communication protocols. We want to enforce separation because we want to limit the address space sharing. Also, using processes fits the purpose of the assignment more as it resemebles separate machines more than threads. To this end, we spawn 3 processes to model each machine. We modularized the code accordingly.

For communication between machines, we chose gRPC over other protocols due to its strong support for distributed systems and clean interface for remote procedure calls. Each machine runs a gRPC server and connects to its peers as a client, allowing for message passing that closely resembles network communication in real distributed systems. We implemented an asynchronous approach using asyncio to handle concurrency effectively, allowing each machine to maintain its own internal clock rate while still responding to incoming messages at network speed.

The third key design decision was our approach to experimentation and analysis. We created a framework that allows us to define multiple experiment configurations with different parameters (clock rates, machine counts, trial durations) and run them systematically. For data collection, we implemented a structured logging system where each machine writes time-stamped events to its own log file. We then built analysis tools that process these logs to calculate metrics such as clock drift, queue sizes, and event distributions, generating both numerical summaries and visualizations to help us understand the behavior of logical clocks under different conditions.

Experiment design:
0. Baseline - 3 machines at a randomly selected tick rate (1 to 6)
1. Balanced - all machines at the same tick rate
2. High Variance - machines with tick rates varying by 10x
3. Fast Ticks - all machines running at high rates
4. Bottleneck - one slow machine with faster peers
5. Progressive - gradually increasing tick rates
6. Five Machines - testing with more nodes. We were curious to see this.
7. Long Running - extended duration to observe long-term behavior
8. Extreme Imbalance - extreme differences in ticks rates
9. Varying internal events probability. Especially we wanted to see the jumps and drifts and test our hypothesis that if all the machines have high internal events probability will have higher jumps and drifts while if all the machines have low internal event probability, there will be lower jumps and drifts.

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


Here is our step by step design decisions and experiment setups
## Date: March 1st 2025 (Michal)

Created the repository and began exploring potential approaches to implementing the distributed system model. After reading through the assignment prompt, I understand we need to:

To get started, I'm exploring gRPC for inter-machine communication. This seems like a good fit since it's designed for distributed systems and provides a clean way to handle remote procedure calls between our virtual machines. I created the initial project structure and set up some basic proto definitions for our message format. Also later on Ed, it was suggested by James Waldo.

- Created the repository with initial README
- Set up the basic project structure
- Created the initial proto file for gRPC communication
- Wrote a bare-bones orchestrator to start thinking about machine coordination
- Generated the Python code from the proto definitions

TODOs:
- Implement the virtual machine class
- Set up the networking between machines
- Implement logical clock updates
- Create the event handling logic
- Set up the logging system

Questions:
- Should we implement some kind of GUI to visualize the system state?
- What's the best way to handle the random events described in the spec?
- Should we implement threads instead of processes? Ask OH or Ed.



## Date: March 1st 2025 (Natnael)

I took a look at Michal's initial implementation with gRPC and it looks like a good approach. I focused on making sure our environment setup works across different operating systems since I'm on Windows and Michal is on macOS. 

We discussed our design approach and decided to structure the project with these main components:
1. `orchestrator.py` - Manages the overall simulation, starts machines, monitors progress
2. `machine.py` - Implements the virtual machine logic, including clock updates and message handling
3. `protos/` - Contains the gRPC protocol definitions

Fixed some issues with environment variable passing on Windows, which was causing some configuration problems. The way Windows handles environment variables differs from Unix systems, so I had to add special case handling.

Today:
- Fixed ENV passing issue on Windows OS
- Reviewed the gRPC implementation
- Discussed design decisions with Michal

TODOs:
- Implement proper logging for each machine
- Work on the message queue implementation
- Figure out how we'll analyze the logs after experiments run

qns:
- How should we structure the experiment configurations for consistent results?
- How to ensure our virtual machines properly simulate the randomized behavior specified in the assignment?

## Date: March 2nd 2025 (Michal)

Focused on improving our project's foundation. I added comprehensive logging to each machine, so we can track events, clock updates, and queue states. Each machine now writes to its own log file in a structured format that will be easy to parse later for analysis.

I also updated the README with more detailed instructions and added support for rich console output to make monitoring the simulations easier. The rich library gives us nice formatting and tables in the terminal.

Additionally, I started working on the asyncio implementation to handle the concurrency aspects more cleanly. Each machine will run in its own async task, which should make the simulation more accurate.

Today:
- Added comprehensive logging for each machine
- Updated README with better documentation
- Added rich for better terminal output
- Started implementing asyncio for concurrency handling

TODOs:
- Complete the event generation logic
- Implement the message queue processing
- Set up experiment configuration
- Create scripts to run experiments with different parameters

## Date: March 2nd 2025 (Natnael)

worked on refining our machine implementation today. After discussing the assignment requirements with Michal, I realized we need to be careful about how we handle the timing aspects. Each machine needs to run at its own clock rate, but we need to make sure the network queue operates independently of that rate.

implemented the message queue for each machine using asyncio.Queue, which handles the concurrent access nicely. When a machine receives a message via gRPC, it's added to the queue. Then, on each clock tick (which happens at the configured rate), the machine checks the queue and processes one message if available.

For the event generation, I implemented the random event logic as specified in the assignment:
- Random number from 1-10
- If 1: Send to next machine
- If 2: Send to after next machine
- If 3: Broadcast to all peers
- If 4-10: Internal event

Today:
- Implemented message queue using asyncio.Queue
- Coded the event generation logic
- Added clock update rules

TODOs:
- Test the implementation with multiple machines
- Set up configuration for different experiments
- Think about how to analyze the logs effectively

Qns for OH:
- Is our approach to simulating different clock speeds correct?
- How should we handle machine initialization to ensure they all start correctly?

## Date: March 3rd 2025 (Michal)

Made good progress today! I focused on getting our orchestrator working properly. Since we're simulating multiple machines on a single physical machine, I restructured the code to make this more efficient and reliable:

1. The orchestrator now starts each virtual machine as a separate process
2. Each machine gets its configuration (port, tick rate, etc.) from the orchestrator
3. Machines establish connections with peers after starting up
4. The orchestrator monitors all machines and displays their status in a real-time table

I also fixed some formatting issues and made sure all the machines can communicate correctly. The system is now working end-to-end, but I need to do more testing to ensure the logical clock updates are working as expected.

Today:
- Fixed formatting issues
- Improved the orchestrator to manage machine processes
- Added real-time status monitoring
- Ensured proper inter-machine communication

TODOs:
- Test the system with various configurations
- Implement automated experiments
- Create analysis tools for the logs

## Date: March 3rd 2025 (Natnael)

I focused on testing our implementation and making sure the messages between machines are properly handled. I found and fixed a few issues:

1. The clock update rules weren't being applied correctly in some cases
2. There was a race condition during machine startup that could cause connection failures
3. Some events weren't being logged properly

I also started thinking about how we'll analyze the results. We need to examine:
- Clock drift between machines
- Impact of different clock rates on message queue sizes
- Patterns in logical clock jumps

I'm working on a plan for the experiments we need to run. Based on the assignment, we should test:
1. Default configuration with 3 machines at varied clock rates
2. Configuration with smaller variation in clock rates
3. Configuration with smaller probability of internal events

Today:
- Fixed bugs in message handling and clock updates
- Resolved race conditions in machine startup
- Started planning experiment configurations

TODOs:
- Implement experiment configurations
- Create analysis scripts
- Run initial experiments and analyze results

## Date: March 4th 2025 (Michal)

Made significant progress today! I created an `experiments.py` script to define and run different experiment configurations. Each experiment specifies:
- Number and configuration of machines
- Clock rates for each machine
- Number of trials to run
- Duration of each trial

This will allow us to systematically test different scenarios and compare results. I also reworked the routing code to make machine topology more flexible, which will help us try different network configurations.

I then created a PR with these changes, and we merged it into the main branch. We're now ready to start running experiments and collecting data.

Today:
- Implemented the experiments.py script
- Reworked orchestrator and machine code
- Set up configurations for different experiments
- Created unified experiment runner

TODOs:
- Run all the experiment configurations
- Create visualization code for the results
- Analyze the patterns in the data

## Date: March 4th 2025 (Natnael)

worked on improving our experiment infrastructure. I made some local changes to enhance how we collect and process data. Specifically:

1. Made sure log directories are properly created
2. Added metadata to log files to track which experiment and trial they belong to
3. Fixed an issue with machine IDs in the logs
4. Improved error handling during experiment runs

I also merged with Michal's latest changes and tested the updated code. Everything seems to be working well, and we should be ready to start collecting meaningful data.

Today:
- Improved log file handling
- Added metadata to logs
- Fixed machine ID issues
- Tested merged code from Michal's PR

TODOs:
- Run the initial batch of experiments
- Start developing the analysis code
- Think about visualizations for the report

## Date: March 4th 2025 (Michal)

I focused on setting up the experiment runner today. I modified the orchestrator to handle multiple trials automatically, with proper cleanup between runs. This will let us collect statistically significant data.

I defined several experiment configurations:
1. Balanced - all machines at the same clock rate
2. High Variance - machines with clock rates varying by 10x
3. Fast Clocks - all machines running at high rates
4. Bottleneck - one slow machine with faster peers
5. Progressive - gradually increasing clock rates
6. Five Machines - testing with more nodes
7. Long Running - extended duration to observe long-term behavior
8. Extreme Imbalance - extreme differences in clock rates
9. Varying internal events probability,
will do more

Each experiment is designed to test a specific aspect of the system. I've set up the runner to execute each experiment with multiple trials and collect all the logs.

Today:
- Added experiments.py script
- Set up multiple experiment configurations
- Modified orchestrator to handle multiple trials
- Created cleanup mechanisms between runs

TODOs:
- Run all experiments
- Create analysis tools for processing the logs
- Generate visualizations

## Date: March 4th 2025 (Natnael)

Tested our experiment framework and found a few issues that needed fixing:

1. Some edge cases were causing log parsing errors
2. There was a bug in the clock drift calculation
3. The machine connection logic sometimes failed with larger topologies

fixed these issues and also created tests to verify our core functionality. The tests focus on:
- Orchestrator initialization and configuration
- Machine message handling
- Clock update logic
- Event generation

now have better confidence in our implementation as we prepare to run the experiments.

Today:
- Fixed bugs in experiment framework
- Created tests for orchestrator and machine classes
- Verified clock update logic
- Improved error handling

TODOs:
- Complete testing of all components
- Run experiments and collect data
- Help with analysis code

## Date: March 4th 2025 (Michal)

I focused on creating the analysis code. I implemented a comprehensive script that:
1. Parses all experiment logs
2. Calculates metrics for each machine and trial
3. Generates visualizations
4. Creates summary tables

The metrics we're calculating include:
- Clock rates (average and maximum)
- Queue sizes (average and maximum)
- Clock jumps (average and maximum)
- System time drift
- Machine drift (difference between machines)
- Event type distribution

I've also added code to generate several plots:
- Clock drift between machines over time
- System time drift over time
- Clock jumps over time
- Queue sizes over time
- Event type distribution


Today:
- Implemented analysis.py script
- Added metrics calculation
- Created visualization code
- Generated summary tables

TODOs:
- Run experiments with all configurations
- Analyze results and identify patterns
- Write up findings for the report

## Date: March 5th 2025 (Natnael)

I focused on testing our entire pipeline. I ran several of our experiment configurations and made sure everything is working properly:

1. Data collection is working correctly
2. Logs are being properly generated
3. Analysis script can process all the logs
4. Visualizations are being generated

I found and fixed a few minor issues:
- Some log files weren't being closed properly
- There was an error in the event count calculation
- Some edge cases in the visualization code

After running the tests, I'm confident that our system is working as expected and we're ready to run all the experiments and collect the data for our report.

Today:
- Tested the entire pipeline
- Fixed issues with log handling
- Corrected event count calculation
- Added more tests

TODOs:
- Complete all experiment runs
- Finalize the analysis
- Prepare for demo day

## Date: March 5th 2025 (Michal)

I ran additional experiments to gather more data and refined our analysis approach.

The results as follows. will do more in the lab notebook:
1. In the balanced configuration, all machines stay perfectly synchronized
2. In the high variance configuration, we see significant clock drift and queue buildup
3. The bottleneck configuration shows how a slow machine affects the entire system
4. The long-running experiment demonstrates how drift tends to stabilize over time

I've created comprehensive summary documents for each experiment with key observations and metrics. These will be helpful for our presentation.

Some key findings:
- Logical clocks effectively maintain causal ordering despite different physical clock rates
- Message queue sizes can grow dramatically when there's a large disparity in clock rates
- Clock jumps are larger and more frequent in imbalanced systems
- The drift between machines tends to reach an equilibrium in longer-running experiments

Today:
- Ran more experiments
- Refined analysis
- Created summary documents
- Prepared for the demo

Final TODOs:
- Polish our presentation for demo day
- Document any remaining observations
- Prepare to answer questions about our design decisions
- Recheck project reqs