import glob
import os
import importlib.util
from pathlib import Path
import sys

# Get absolute path to this __init__.py
current_path = Path(__file__).parent.resolve()
agent_functions_dir = current_path / "agent_functions"

# Add parent directory to Python path (critical for Docker imports)
sys.path.insert(0, str(current_path.parent.parent))

# Clear any existing cached modules (Mythic hot-reload safety)
importlib.invalidate_caches()

# Dynamically import all command modules
for py_file in agent_functions_dir.glob("*.py"):
    if py_file.name == "__init__.py":
        continue
        
    module_name = py_file.stem
    spec = importlib.util.spec_from_file_location(
        f"igiderTest.agent_functions.{module_name}", 
        py_file
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Add commands to global namespace (Mythic expects this)
    for attr in dir(module):
        if not attr.startswith("__"):
            globals()[attr] = getattr(module, attr)

# Mythic requires this explicit export
__all__ = [name for name in globals() if not name.startswith("__")]