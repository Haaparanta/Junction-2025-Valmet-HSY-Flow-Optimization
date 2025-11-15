# Simulation Engine

Core simulation engine for 24-hour wastewater tunnel optimization. Implements intelligent pump scheduling with minimum runtime constraints, cost optimization, and reinforcement learning models for predictive flow control.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Simulation Engine                          │
│                      (simulator.py)                             │
└────────────────────────────┬────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│    Pump       │    │    Tunnel     │    │   RL Model    │
│   (pump.py)   │    │  (tunnel.py)  │    │ (rl_model.py) │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                     │                     │
        │ Flow/Power          │ Volume/Level        │ Flow Prediction
        │ Calculations        │ Conversions         │ (Transformer)
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   CSV Reader    │
                    │ (csv_reader.py) │
                    │  Data Loading   │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Training      │
                    │   (train.py)    │
                    │  RL Training    │
                    └─────────────────┘
```

## Components

### simulator.py
Main simulation engine running 96 time steps (15-minute intervals) over 24 hours. Implements intelligent pump selection algorithm respecting minimum runtime constraints, tracks water levels, calculates energy costs, and validates constraints. Returns optimized pump schedules and total operational cost.

### pump.py
Pump class modeling individual pump behavior with performance curves. Calculates flow rates based on water level (head), tracks power consumption (400kW big pumps, 250kW small pumps), and maintains usage time statistics. Supports both big and small pump types with different flow characteristics.

### tunnel.py
Tunnel physics module implementing 4-case volume-to-level conversion formulas. Handles water level validation, calculates volumes from levels using piecewise functions for different depth ranges, and provides binary search inverse conversion. Enforces maximum level constraint (14.1m) with penalty costs.


### rl_model.py
Transformer-based reinforcement learning model for predictive flow control. Uses TransformerEncoder architecture to predict optimal flow rates from electricity prices, inflow estimates, and historical pump states. Implements policy gradient learning with action sampling and log probability calculation.

### train.py
Training script for RL model using parallel simulation execution. Processes CSV historical data into training datasets, runs batch simulations with ProcessPoolExecutor for parallelization, and optimizes policy using advantage-weighted policy gradient. Includes data preprocessing and result visualization.

### csv_reader.py
CSV parsing utilities for European number format (comma decimal separator). Handles timestamp parsing, numeric column conversion, and extracts historical state data. Provides helper functions for deriving level-volume relationships and accessing last known system state.


