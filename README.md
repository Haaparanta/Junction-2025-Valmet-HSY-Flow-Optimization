# Junction-2025-Valmet-HSY-Flow-Optimization  

Intelligent Flow Optimization by Valmet x HSY  

https://pumptech.surf  
https://pumptech.surf/api/docs  
https://eu.junctionplatform.com/events/junction-2025  
https://www.valmet.com/fi/  
https://www.hsy.fi  

## Project Description  

An intelligent wastewater tunnel flow optimization system that combines reinforcement learning, real-time data integration, and industrial connectivity to minimize operational costs while maintaining system safety. The system optimizes pump scheduling over 24-hour periods by analyzing weather forecasts, electricity prices, and inflow patterns to generate cost-effective pumping strategies. It features a modern web interface for visualizing simulations and an industrial OPC UA integration layer for connecting with PLC/SCADA systems in production environments.

## Backend

https://pumptech.surf/api/docs  

The backend is built with Python and FastAPI, providing REST API endpoints for simulation management and optimization. It automatically fetches real-time weather forecasts from FMI API, electricity prices from Spot-hinta API, and historical inflow patterns from CSV data to feed into the optimization engine. The core simulation engine runs 96 time steps (15-minute intervals) over 24 hours, implementing intelligent pump scheduling algorithms that respect minimum runtime constraints and track water levels, energy costs, and system constraints.   

A Transformer-based reinforcement learning model predicts optimal target flowrates from electricity prices, inflow estimates, and historical pump states using policy gradient learning. The API stores simulation results in SQLite database with in-memory caching for fast access, exposing endpoints for creating simulations, retrieving historical results, and accessing individual data components. An OPC UA integration layer connects the optimization system with PLC/SCADA equipment controllers, enabling bidirectional communication for reading sensor data and writing control commands with safety interlocks. The system supports both advisory mode (recommendations only) and closed-loop mode (automatic control) with configurable safety limits and update intervals. Pump models use performance curves to calculate flow rates based on water level (head) and track power consumption for different pump types (400kW big pumps, 250kW small pumps). The tunnel physics module implements piecewise volume-to-level conversion formulas for different depth ranges with binary search inverse conversion, enforcing maximum level constraints with penalty costs. Training scripts process CSV historical data, run parallel batch simulations, and optimize the policy using advantage-weighted policy gradient learning.

## Frontend

https://pumptech.surf/api/docs  

The frontend is built with SvelteKit and TypeScript, providing an interactive web interface for visualizing and analyzing wastewater tunnel optimization simulations. It features a modern dark-themed UI with Tailwind CSS, displaying simulation history with sortable cards showing metadata like total cost, energy consumption, and timestamps. 

The main simulation detail page provides comprehensive visualization tools including interactive time-series graphs for input data (rain forecasts, electricity prices, inflow estimates) and output data (water levels, pump states, costs). Real-time playback controls allow users to step through the 24-hour simulation timeline, animating pump states, water flow, and system dynamics at 15-minute intervals.

 The pump array visualization shows all 8 pumps with their individual states, flow rates, and performance curves displayed as interactive overlays on pump characteristic diagrams. A water flow animation component visualizes the inflow basin with dynamic water level indicators and flow path animations connecting the basin to the pump array. The performance curve graphs use D3.js and LayerCake for rendering pump characteristic curves with operating point indicators that update as users scrub through the timeline. Interactive tooltips provide detailed information on hover, showing exact values for flow rates, water levels, electricity prices, and costs at any time step. The application uses Svelte's reactive state management with stores and context APIs to manage simulation data flow between components, ensuring smooth updates during timeline navigation. Error handling and loading states are implemented throughout with toast notifications and loading spinners, providing clear feedback during API calls and data fetching operations.
