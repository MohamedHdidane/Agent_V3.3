import mythic_container
import asyncio
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("igiderTest")

async def main():
    try:
        logger.info("Starting igiderTest Mythic agent handler...")
        # Start the mythic container service
        await mythic_container.mythic_service.start_services()
        # Just hang out forever
        while True:
            await asyncio.sleep(30)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())