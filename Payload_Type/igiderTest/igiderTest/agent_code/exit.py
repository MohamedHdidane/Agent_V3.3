import sys
import os
import platform
from typing import Dict

def exit(task: Dict) -> Dict:
    """Terminate agent process cleanly across platforms"""
    response = {
        "user_output": "Exiting agent process",
        "completed": True,
        "status": "success"
    }
    
    try:
        # Notify C2 before termination
        C2.post_response(task, response)
        
        # Cross-platform process termination
        if platform.system() == "Windows":
            os._exit(0)  # Immediate termination without cleanup
        else:
            sys.exit(0)  # Clean exit for Unix-like systems
            
    except Exception as e:
        # Fallback forced termination
        os._exit(1)