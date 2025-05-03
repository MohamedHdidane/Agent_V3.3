import json
import platform
import subprocess
from typing import Dict, List
import psutil

try:
    from AppKit import NSWorkspace, NSRunningApplication  # macOS only
except ImportError:
    NSWorkspace = None

def list_apps(task: Dict) -> Dict:
    """List running applications/processes with metadata"""
    try:
        processes = []
        system = platform.system()

        if system == "Darwin" and NSWorkspace:
            processes = get_mac_apps()
        else:
            processes = get_generic_processes()

        return {
            "user_output": json.dumps(processes, indent=2),
            "processes": processes,
            "completed": True
        }
    except Exception as e:
        return {
            "user_output": str(e),
            "completed": True,
            "status": "error"
        }

def get_mac_apps() -> List[Dict]:
    """macOS-specific app enumeration using PyObjC"""
    apps = []
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        info = {
            "frontMost": app.isActive(),
            "hidden": app.isHidden(),
            "bundle": app.bundleIdentifier(),
            "bundleURL": app.bundleURL().path() if app.bundleURL() else "",
            "bin_path": app.executableURL().path() if app.executableURL() else "",
            "process_id": app.processIdentifier(),
            "name": app.localizedName(),
            "architecture": get_arch_mac(app)
        }
        apps.append(info)
    return apps

def get_generic_processes() -> List[Dict]:
    """Cross-platform process enumeration"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'exe', 'username']):
        try:
            info = {
                "name": proc.info['name'],
                "process_id": proc.info['pid'],
                "bin_path": proc.info['exe'] or "",
                "architecture": get_architecture(proc.info['exe']),
                "frontMost": False,  # Not available generically
                "hidden": False,
                "bundle": "",
                "bundleURL": ""
            }
            processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes

def get_arch_mac(app: NSRunningApplication) -> str:
    """Detect macOS executable architecture"""
    arch_map = {
        0x01000000 | 7: "x86",
        0x01000000 | 18: "PPC",
        0x01000000 | 16777223: "x64",
        0x01000000 | 16777234: "x64_PPC",
        0x01000000 | 16777228: "ARM64"
    }
    return arch_map.get(app.executableArchitecture(), "unknown")

def get_architecture(exe_path: str) -> str:
    """Cross-platform architecture detection"""
    if not exe_path:
        return "unknown"
    
    try:
        if platform.system() == "Windows":
            return get_pe_architecture(exe_path)
        else:
            return get_unix_architecture(exe_path)
    except Exception:
        return "unknown"

def get_unix_architecture(path: str) -> str:
    """Use file command for Unix-like systems"""
    try:
        output = subprocess.check_output(['file', '-b', path], 
                    stderr=subprocess.DEVNULL).decode().lower()
        if 'x86-64' in output: return 'x64'
        if 'i386' in output: return 'x86'
        if 'arm64' in output: return 'ARM64'
        return "unknown"
    except FileNotFoundError:
        return "unknown"

def get_pe_architecture(path: str) -> str:
    """Windows PE file analysis"""
    try:
        import pefile  # Requires pip install pefile
        pe = pefile.PE(path)
        machine = pe.FILE_HEADER.Machine
        if machine == 0x8664: return 'x64'
        if machine == 0x14c: return 'x86'
        return "unknown"
    except ImportError:
        return "unknown"
    except Exception:
        return "unknown"