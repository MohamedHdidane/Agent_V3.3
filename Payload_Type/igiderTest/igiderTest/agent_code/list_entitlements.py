import ctypes
import json
import plistlib
import platform
from typing import Dict, List

try:
    from AppKit import NSWorkspace, NSRunningApplication
    from Foundation import NSData, NSPropertyListSerialization, NSMakeRange
except ImportError:
    NSWorkspace = None

# macOS security constants
CS_OPS_IDENT = 7
CS_OPS_ENTITLEMENTS_BLOB = 12

class ProcessEntitlements:
    def __init__(self):
        self.libc = ctypes.CDLL('/usr/lib/system/libsystem_kernel.dylib')
        self._setup_ctypes()

    def _setup_ctypes(self):
        self.libc.csops.argtypes = [
            ctypes.c_int,    # pid
            ctypes.c_uint,   # ops
            ctypes.c_void_p, # useraddr
            ctypes.c_size_t  # usersize
        ]
        self.libc.csops.restype = ctypes.c_int
        
        self.libc.malloc.argtypes = [ctypes.c_size_t]
        self.libc.malloc.restype = ctypes.c_void_p
        
        self.libc.free.argtypes = [ctypes.c_void_p]

    def get_entitlements(self, pid: int) -> Dict:
        """Retrieve entitlements for a process using low-level macOS APIs"""
        buffer_size = 512000
        buffer = self.libc.malloc(buffer_size)
        
        try:
            result = self.libc.csops(
                pid,
                CS_OPS_ENTITLEMENTS_BLOB,
                buffer,
                buffer_size
            )
            
            if result != 0:
                return {}
            
            ns_data = NSData.dataWithBytes_length_(buffer, buffer_size)
            plist_data = NSData.dataWithData_(ns_data)
            
            plist, _, error = NSPropertyListSerialization.propertyListWithData_options_format_error_(
                plist_data,
                0,
                None,
                None
            )
            
            if error:
                return {}
                
            return plist
        finally:
            self.libc.free(buffer)

def list_entitlements(task: Dict) -> Dict:
    try:
        if platform.system() != 'Darwin':
            return {
                "user_output": "Entitlements are only available on macOS",
                "completed": True,
                "status": "error"
            }

        pe = ProcessEntitlements()
        params = json.loads(task.get("parameters", "{}"))
        output = []

        if params.get("pid", -1) == -1:
            workspace = NSWorkspace.sharedWorkspace()
            for app in workspace.runningApplications():
                try:
                    entitlements = pe.get_entitlements(app.processIdentifier())
                    output.append({
                        "pid": app.processIdentifier(),
                        "bundle": app.bundleIdentifier(),
                        "bundleURL": app.bundleURL().path() if app.bundleURL() else "",
                        "bin_path": app.executableURL().path() if app.executableURL() else "",
                        "name": app.localizedName(),
                        "entitlements": entitlements
                    })
                except Exception:
                    continue
        else:
            pid = int(params["pid"])
            entitlements = pe.get_entitlements(pid)
            output.append({
                "pid": pid,
                "bundle": "",
                "bundleURL": "",
                "bin_path": "",
                "name": "",
                "entitlements": entitlements
            })

        return {
            "user_output": json.dumps(output, indent=2),
            "completed": True
        }

    except Exception as e:
        return {
            "user_output": str(e),
            "completed": True,
            "status": "error"
        }