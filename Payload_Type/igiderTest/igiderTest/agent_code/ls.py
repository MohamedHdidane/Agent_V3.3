import os
import stat
import platform
import json
import time
import pwd
import grp
from pathlib import Path
from typing import Dict, Any
try:
    import xattr  # macOS extended attributes
except ImportError:
    xattr = None

def ls(task: Dict) -> Dict:
    """List directory contents with metadata (cross-platform)"""
    response: Dict[str, Any] = {"file_browser": {}, "completed": True}
    try:
        params = json.loads(task.get("parameters", "{}"))
        path = params.get("path", "").strip() or "."

        # Resolve paths
        path_obj = Path(path).expanduser().resolve()
        if not path_obj.exists():
            return error_response("Path does not exist")

        # Base response structure
        response['file_browser'].update({
            "host": platform.node(),
            "update_deleted": True,
            "success": True,
            "is_file": not path_obj.is_dir(),
            "name": path_obj.name,
            "parent_path": str(path_obj.parent),
            "size": path_obj.stat().st_size,
            "permissions": get_permissions(path_obj),
            "modify_time": int(path_obj.stat().st_mtime * 1000),
            "access_time": int(path_obj.stat().st_atime * 1000),
        })

        # Handle directory listing
        if path_obj.is_dir():
            files_data = []
            for entry in path_obj.iterdir():
                try:
                    entry_stat = entry.stat()
                    files_data.append({
                        "name": entry.name,
                        "is_file": not entry.is_dir(),
                        "size": entry_stat.st_size,
                        "modify_time": int(entry_stat.st_mtime * 1000),
                        "access_time": int(entry_stat.st_atime * 1000),
                        "permissions": get_permissions(entry),
                    })
                except Exception as e:
                    continue  # Skip inaccessible files

            response['file_browser']['files'] = files_data

        # macOS-specific extended attributes
        if platform.system() == "Darwin" and xattr:
            try:
                attrs = xattr.xattr(path_obj)
                response['file_browser']['permissions']['extended'] = {
                    name: base64.b64encode(attrs.get(name)).decode()
                    for name in attrs.list()
                }
            except:
                pass

        # Format output for Mythic
        if params.get('file_browser'):
            response["user_output"] = "added data to file browser"
        else:
            response["user_output"] = json.dumps(response['file_browser'], indent=2)

        return response

    except Exception as e:
        return error_response(f"Error: {str(e)}")

def get_permissions(path: Path) -> Dict:
    """Get cross-platform permission metadata"""
    stat_info = path.stat()
    perms = {
        "posix": oct(stat.S_IMODE(stat_info.st_mode))[-3:],
        "hidden": is_hidden(path),
        "create_time": int(path.stat().st_ctime * 1000),
    }

    try:  # Owner/group info (Unix only)
        perms.update({
            "owner": f"{pwd.getpwuid(stat_info.st_uid).pw_name} ({stat_info.st_uid})",
            "group": f"{grp.getgrgid(stat_info.st_gid).gr_name} ({stat_info.st_gid})"
        })
    except:
        perms.update({"owner": "", "group": ""})

    return perms

def is_hidden(path: Path) -> bool:
    """Check if file is hidden (platform-specific)"""
    if platform.system() == "Windows":
        return bool(os.stat(path).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
    else:
        return path.name.startswith('.') or has_hidden_attribute(path)

def has_hidden_attribute(path: Path) -> bool:
    """Check macOS extended hidden attribute"""
    try:
        if platform.system() == "Darwin" and xattr:
            return b"com.apple.FinderInfo" in xattr.xattr(path)
    except:
        pass
    return False

def error_response(message: str) -> Dict:
    return {
        "user_output": message,
        "completed": True,
        "status": "error"
    }