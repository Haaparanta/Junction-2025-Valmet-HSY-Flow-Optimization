# OPC UA Industrial Integration

Industrial-grade OPC UA integration connecting wastewater tunnel optimization with PLC/SCADA systems. Enables real-time sensor data reading, optimization result publishing, and bidirectional pump control with safety interlocks.

## Architecture

```
┌─────────────────┐
│   PLC/SCADA     │  (Physical equipment controllers)
│   Equipment     │
└────────┬────────┘
         │ OPC UA Client
         │ (reads sensors, writes commands)
         ▼
┌─────────────────────────────────────┐
│   OPC UA Server (This System)       │
│  ┌──────────────────────────────┐   │
│  │  OPC UA Node Address Space   │   │
│  │  - Water Level L1 (read)     │   │
│  │  - Pump States (read/write)  │   │
│  │  - Optimization Results      │   │
│  │  - Commands (write)          │   │
│  └──────────────────────────────┘   │
└────────┬────────────────────────────┘
         │
         │ Internal API calls
         ▼
┌─────────────────────────────────────┐
│   FastAPI Backend                   │
│  ┌──────────────────────────────┐   │
│  │  Simulation Engine           │   │
│  │  - Runs optimization         │   │
│  │  - Generates pump strategy   │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

## Components

### `opcua_server.py`
OPC UA server exposing optimization results and system state. Creates address space with tunnel variables (water level, volume, inflow), pump objects (state, flow, power, recommendations), and optimization results (strategy, cost, timestamp). Handles node updates and subscriptions for real-time data publishing.

### `opcua_client.py`
OPC UA client connecting to PLC/SCADA systems. Reads sensor data (water levels, pump states, flow rates) via subscriptions and direct reads. Writes pump commands in closed-loop mode. Supports connection management, subscriptions, and fallback to mock mode when disconnected.

### `control_loop.py`
Main control loop managing bidirectional communication with safety interlocks. Periodically reads sensors, checks safety conditions (water level limits, minimum runtime), triggers optimizations, and executes control commands. Supports advisory and closed-loop modes with runtime tracking.

### `opcua_bridge.py`
Bridge connecting FastAPI backend with OPC UA system. Syncs simulation results to OPC UA server nodes. Reads sensor data for simulations. Provides pump control methods (single/multiple) with safety checks. Manages lifecycle (start/stop) of server, client, and control loop.

### `config.py`
Configuration management with environment variable support. Defines server endpoints, PLC connections, control modes (advisory/closed-loop), safety limits (max water level, min pump runtime), and update intervals. Provides `from_env()` method for easy deployment configuration.
