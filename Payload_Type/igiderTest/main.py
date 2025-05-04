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
from igiderTest.igiderTest.agent_functions import *

# Start the mythic container
mythic_container.mythic_service.start_and_run_forever()