"""Standalone example of OPC UA server without FastAPI integration."""
import asyncio
import logging
from opc_ua import OPCUAServer, OPCUAConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run standalone OPC UA server example."""
    # Create configuration
    config = OPCUAConfig(
        server_endpoint="opc.tcp://0.0.0.0:4840",
        server_name="Wastewater Tunnel Optimization Server",
        control_mode="advisory"  # Read-only recommendations
    )
    
    # Create and start server
    server = OPCUAServer(config)
    
    # Start server in background task
    server_task = asyncio.create_task(server.start())
    
    # Wait a bit for server to initialize
    await asyncio.sleep(2)
    
    # Update some example values
    logger.info("Updating example values...")
    await server.update_water_level(5.2)
    await server.update_volume(12500.0)
    await server.update_inflow(150.0)
    
    # Update pump recommendations
    await server.update_pump_recommendation("1.1", True)
    await server.update_pump_recommendation("1.2", True)
    await server.update_pump_recommendation("1.3", False)
    
    # Update optimization results
    from datetime import datetime
    pump_strategy = {
        "1.1": [True] * 96,
        "1.2": [True] * 96,
        "1.3": [False] * 96,
        "1.4": [False] * 96,
        "2.1": [False] * 96,
        "2.2": [True] * 96,
        "2.3": [False] * 96,
        "2.4": [False] * 96,
    }
    await server.update_optimization_results(
        pump_strategy,
        total_cost=1250.50,
        timestamp=datetime.now()
    )
    
    logger.info("OPC UA server is running. Connect with an OPC UA client to:")
    logger.info(f"  Endpoint: {config.server_endpoint}")
    logger.info("  Example nodes:")
    logger.info("    - ns=2;s=WaterLevel_L1")
    logger.info("    - ns=2;s=Pump_1_1.RecommendedState")
    logger.info("    - ns=2;s=Optimization.TotalCost")
    logger.info("\nPress Ctrl+C to stop...")
    
    try:
        # Keep running
        await server_task
    except KeyboardInterrupt:
        logger.info("Stopping server...")
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())

