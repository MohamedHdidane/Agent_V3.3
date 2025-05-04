import os
import json
from typing import Dict, List, Optional

async def ls_command(command_data: Dict) -> str:
    """
    List directory contents
    Arguments:
        path (str): The directory path to list (defaults to current directory)
    """
    # Extract the path from command arguments
    args = command_data.get("arguments", {})
    path = args.get("path", ".")
    
    try:
        # List directory contents
        entries = []
        with os.scandir(path) as scan_entries:
            for entry in scan_entries:
                # Get file stats
                try:
                    stats = entry.stat()
                    
                    # Format the entry info
                    entry_info = {
                        "name": entry.name,
                        "is_dir": entry.is_dir(),
                        "size": stats.st_size,
                        "permissions": oct(stats.st_mode)[-3:],  # Last 3 digits of permission octal
                        "modified": stats.st_mtime,
                        "path": os.path.join(path, entry.name)
                    }
                    entries.append(entry_info)
                except Exception as e:
                    # Handle permission errors for specific files
                    entries.append({
                        "name": entry.name,
                        "error": str(e),
                        "path": os.path.join(path, entry.name)
                    })
        
        # Sort entries (directories first, then files)
        entries.sort(key=lambda x: (0 if x.get("is_dir", False) else 1, x["name"].lower()))
        
        # Return JSON formatted result
        result = {
            "path": os.path.abspath(path),
            "entries": entries,
            "total": len(entries)
        }
        
        return json.dumps(result)
    
    except Exception as e:
        return json.dumps({
            "error": f"Error listing directory {path}: {str(e)}"
        })