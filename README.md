# Swarm Intelligence Simulation (SwarmSim)

A modular pygame simulation to compare different intelligence strategies (brains) for swarm agents. The simulation features two teams (RED and BLUE) of agents that move on a grid, each controlled by a selectable "brain". The simulation collects metrics such as team sizes and entropy over time, and visualizes them in real-time graphs.

## Features

- Three distinct agent brains:
  - **ChaosBrain**: Moves randomly.
  - **SwarmBrain**: Prefers empty spaces and avoids frontiers.
  - **ZMQBrainLike**: Uses attraction, threat, and frontier fields to make decisions.
- **Flag mechanic**: A single yellow pixel at the center represents a flag. When a team's agent captures the flag (moves onto it), that team gains the flag holder status. While a team does NOT hold the flag, their agents' movements are impaired with added randomness, simulating reduced coordination. The flag respawns after a delay.
- Real-time visualization of the grid and agent movements.
- Real-time graphs tracking:
  - Number of RED agents
  - Number of BLUE agents
  - Entropy (a measure of field activity)
- On-screen display of current brains, slopes (trends), flag holder, and an interpretation of the system state.
- Interactive brain switching:
  - Press `Z` to change the RED team's brain.
  - Press `M` to change the BLUE team's brain.
- Data collection: Press `S` to save the current history (agent counts and entropy) to a CSV file.
- Automatic screenshots and data logging: Every 30 seconds (configurable), the simulation saves a screenshot and the history data to timestamped files in the `screenshots/` and `data/` directories.

## Dependencies

- Python 3.x
- Pygame
- NumPy

Install dependencies with:
```bash
pip install pygame numpy
```

## How to Run

Navigate to the swamsim directory and run:
```bash
python swarm.py
```

## Controls

- `Z`: Cycle through brains for the RED team.
- `M`: Cycle through brains for the BLUE team.
- `S`: Save the current history data to a CSV file (saved in the `data/` directory).
- `ESC` or close window: Exit the simulation.

## Data Collection

When you press `S`, or when the automatic interval triggers, the simulation saves the following data to a CSV file:
- Frame (time step)
- RED agent count
- BLUE agent count
- Entropy value

The file is saved in the `data/` directory with a timestamp in the filename (e.g., `swarmsim_data_20260601_132834.csv`).

Screenshots are saved as PNG files in the `screenshots/` directory with timestamps.

## Project Structure

- `agents.py`: Base Agent class (used in both the main simulation and potentially other modules).
- `config.py`: Configuration constants (grid size, colors, etc.).
- `grid.py`: Field update functions (attraction, threat, frontier).
- `swarm.py`: Main simulation loop, pygame rendering, brain definitions, and data handling.
- `README.md`: This file.

## Notes

- The simulation uses a fixed grid size (120x120) with a cell size of 5 pixels.
- The maximum history length for graphs is 200 frames (configurable via `MAX_HISTORY` in swarm.py).
- The entropy measure is the mean of the three fields (attraction, threat, frontier).
- Flag respawn delay is set to 500 frames (~8.3 seconds at 60 FPS).
- Automatic screenshot and data interval is set to 1800 frames (~30 seconds at 60 FPS).

## Future Ideas

- Save data automatically after each run or at regular intervals.
- Export data in multiple formats (JSON, Excel).
- Add more brain types or allow custom brain scripts.
- Implement team-based scoring or victory conditions.
- Add parameters to brains for evolutionary tuning.

---
*Built with pygame and numpy for exploring swarm intelligence dynamics.*