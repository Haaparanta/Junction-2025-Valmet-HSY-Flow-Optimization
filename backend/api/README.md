# Simulation API

FastAPI REST API for wastewater tunnel system optimization. Manages 24-hour pump scheduling simulations with real-time weather, electricity pricing, and inflow data to minimize operational costs.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                     │
│                         (main.py)                               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌────────────────┐    ┌────────────────┐
│  Data Fetcher │    │   Simulator    │    │   Storage      │
│ (data_fetcher)│    │  (external)    │    │  (storage.py)  │
└───────┬───────┘    └────────┬───────┘    └────────┬───────┘
        │                     │                     │
        │ FMI API             │                     │
        │ Spot-hinta API      │                     │
        │ CSV Data            │                     │
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │    Database     │
                    │  (database.py)  │
                    │   SQLite DB     │
                    └─────────────────┘
```

## Components

### main.py
FastAPI application with REST endpoints for simulation management. Handles POST /simulate to create new simulations, GET endpoints for retrieving simulation data, and converts Simulator results to API responses. Includes CORS middleware and comprehensive error handling.

### models.py
Pydantic models defining request/response DTOs. Includes SimulationRequest, SimulationResponse, PumpData, and specialized response models for individual data endpoints. Ensures type safety and automatic API documentation generation.

### database.py
SQLite database layer for persistent simulation storage. Manages tables for simulations, inputs, outputs, and pump data. Provides CRUD operations and query functions for retrieving simulation data by ID or listing all simulations with metadata.


### storage.py
In-memory storage layer providing backward compatibility and fast access to recent simulations. Dual-writes to both memory and database, with graceful fallback if database operations fail. Maintains simulation history list.


### data_fetcher.py
External data integration service fetching real-time weather forecasts from FMI API, electricity prices from Spot-hinta API, and historical patterns from CSV files. Includes downsampling logic for 10-minute to 15-minute intervals and fallback mechanisms.


