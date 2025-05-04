"""
Implementation of the 'ls' command for the igidertest agent.
This is used by the main agent to list directory contents.
"""
import os
import stat
from datetime import datetime

def list_directory(path="."):
    """List contents of a directory with detailed information."""
    results = []
    
    try:
        # Convert relative path to absolute
        abs_path = os.path.abspath(path)
        
        # Check if directory exists
        if not os.path.exists(abs_path):
            return {"error": f"Path does not exist: {abs_path}"}
        
        # Check if it's a directory
        if not os.path.isdir(abs_path):
            return {"error": f"Path is not a directory: {abs_path}"}
        
        # List directory contents
        for item in os.listdir(abs_path):
            item_path = os.path.join(abs_path, item)
            try:
                stats = os.stat(item_path)
                
                # Format permissions similar to ls -l
                mode = stats.st_mode
                perms = ""
                perms += "d" if stat.S_ISDIR(mode) else "-"
                perms += "r" if mode & stat.S_IRUSR else "-"
                perms += "w" if mode & stat.S_IWUSR else "-"
                perms += "x" if mode & stat.S_IXUSR else "-"
                perms += "r" if mode & stat.S_IRGRP else "-"
                perms += "w" if mode & stat.S_IWGRP else "-"
                perms += "x" if mode & stat.S_IXGRP else "-"
                perms += "r" if mode & stat.S_IROTH else "-"
                perms += "w" if mode & stat.S_IWOTH else "-"
                perms += "x" if mode & stat.S_IXOTH else "-"
                
                file_info = {
                    "name": item,
                    "path": item_path,
                    "size": stats.st_size,
                    "permissions": perms,
                    "is_directory": os.path.isdir(item_path),
                    "modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "accessed": datetime.fromtimestamp(stats.st_atime).strftime("%Y-%m-%d %H:%M:%S"),
                }
                
                results.append(file_info)
                
            except Exception as e:
                # Skip files we can't access
                continue
                
        return {
            "success": True,
            "path": abs_path,
            "items": results
        }
        
    except Exception as e:
        return {"error": str(e)}