#!/usr/bin/env python3
import mythic_container
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - [%(levelname)s] %(message)s"
)

# Import our payload type
import igiderTest

# Start the mythic container
mythic_container.mythic_service.start_and_run_forever()