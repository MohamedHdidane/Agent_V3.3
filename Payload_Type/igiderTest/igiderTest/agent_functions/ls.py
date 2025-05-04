from mythic_container.MythicCommandBase import *
import json
from typing import Dict, List, Tuple, Optional

class LsCommand(CommandBase):
    cmd = "ls"
    needs_admin = False
    help_cmd = "ls [path]"
    description = "List directory contents"
    version = 1
    supported_ui_features = ["file_browser:list"]
    author = "igider"
    attackmapping = ["T1083"]
    argument_class = CommandParameter
    browser_script = BrowserScript(script_name="ls_new", author="igider")
    
    async def create_go_tasking(self, taskData: MythicCommandBase.PTTaskMessageAllData) -> MythicCommandBase.PTTaskCreateTaskingMessageResponse:
        response = MythicCommandBase.PTTaskCreateTaskingMessageResponse(
            TaskID=taskData.Task.ID,
            Success=True,
        )
        
        # Get the path argument, if any
        path = taskData.args.get_arg("path")
        if not path:
            path = "."  # Default to current directory
        
        # Save the path as a parameter
        response.DisplayParams = f"{path}"
        
        # Create JSON task data
        task_data = {
            "command": "ls",
            "arguments": {
                "path": path
            }
        }
        
        response.TaskData = json.dumps(task_data).encode()
        return response
    
    async def process_response(self, response: bytes, task: PTTaskMessageAllData) -> PTTaskProcessResponseMessageResponse:
        resp = PTTaskProcessResponseMessageResponse(TaskID=task.Task.ID, Success=True)
        
        try:
            response_data = json.loads(response.decode())
            
            # Process file listing for Mythic file browser
            if "entries" in response_data:
                # Convert the response to a Mythic file browser format
                file_browser_data = []
                
                for entry in response_data["entries"]:
                    file_data = {
                        "name": entry.get("name", ""),
                        "is_file": not entry.get("is_dir", False),
                        "size": entry.get("size", 0),
                        "permissions": {
                            "octal": entry.get("permissions", "000")
                        },
                        "modify_time": entry.get("modified", 0),
                        "full_path": entry.get("path", "")
                    }
                    file_browser_data.append(file_data)
                
                # Process the file browser data through Mythic API
                if len(file_browser_data) > 0:
                    resp.ProcessResponse = json.dumps(
                        {"files": file_browser_data, "parent_path": response_data.get("path", "")}
                    ).encode()
                    
                    await MythicCommandBase.MythicCmdBase.register_file_browser(self, task, 
                                                                                file_browser_data, 
                                                                                response_data.get("path", ""))
            
            if "error" in response_data:
                resp.UserOutput = f"Error: {response_data['error']}"
            else:
                # Format a nice output for the user
                output = [f"Directory listing for {response_data.get('path', '')}:"]
                output.append(f"Total: {response_data.get('total', 0)} entries\n")
                
                # Column headers
                output.append(f"{'Type':<5} {'Permissions':<10} {'Size':<10} {'Name':<30}")
                output.append("-" * 60)
                
                # Add each entry
                for entry in response_data.get("entries", []):
                    entry_type = "D" if entry.get("is_dir", False) else "F"
                    name = entry.get("name", "")
                    perms = entry.get("permissions", "000")
                    size = entry.get("size", 0)
                    
                    output.append(f"{entry_type:<5} {perms:<10} {size:<10} {name:<30}")
                
                resp.UserOutput = "\n".join(output)
        
        except Exception as e:
            resp.UserOutput = f"Error processing response: {str(e)}\n{response.decode()}"
            resp.Success = False
        
        return resp

    async def create_tasking(self, task: MythicCommandBase.PTTaskMessageAllData) -> MythicCommandBase.PTTaskCreateTaskingMessageResponse:
        """
        Create a task for listing directory contents
        """
        # Get arguments
        args = task.args.get_arg_value_dict()
        
        # Get the path argument, or default to current directory
        path = args.get("path", ".")
        
        response = MythicCommandBase.PTTaskCreateTaskingMessageResponse(
            TaskID=task.Task.ID,
            Success=True,
            DisplayParams=f"Listing contents of {path}"
        )
        
        # Create command JSON
        command_data = {
            "command": "ls",
            "arguments": {
                "path": path
            }
        }
        
        response.TaskData = json.dumps(command_data).encode()
        return response