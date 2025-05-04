from mythic_container.PayloadBuilder import *
from mythic_container.MythicCommandBase import *
import asyncio
import os
import sys
import tempfile
import base64
import uuid

class IgiderTest(PayloadType):
    name = "igiderTest"
    file_extension = "bin"
    author = "Mythic Developer"
    supported_os = [
        SupportedOS.Linux,
        SupportedOS.MacOS,
        SupportedOS.Windows
    ]
    wrapper = False
    wrapped_payloads = []
    note = "A simple Mythic agent written in Python for educational purposes"
    supports_dynamic_loading = False
    build_parameters = [
        BuildParameter(
            name="version",
            parameter_type=BuildParameterType.String,
            description="Choose a specific version to build",
            default_value="1.0",
            required=False
        ),
        BuildParameter(
            name="debug",
            parameter_type=BuildParameterType.Boolean,
            description="Enable debug output",
            default_value=False,
            required=False
        )
    ]
    c2_profiles = ["http"]
    translation_container = None
    
    async def build(self) -> BuildResponse:
        # This function will be called to build the payload
        try:
            agent_code_path = os.path.join(self.agent_code_path, "base", "main_agent.py")
            with open(agent_code_path, 'r') as f:
                main_code = f.read()

            # Handle C2 profile configuration
            if "http" in self.c2info:
                c2_code_path = os.path.join(self.agent_code_path, "c2_profiles", "http.py")
                with open(c2_code_path, 'r') as f:
                    c2_code = f.read()
                
                # Replace placeholders with actual C2 information
                http_config = self.c2info["http"]
                callback_host = http_config.get("callback_host", "127.0.0.1")
                callback_port = http_config.get("callback_port", "8080")
                
                c2_code = c2_code.replace("{{CALLBACK_HOST}}", callback_host)
                c2_code = c2_code.replace("{{CALLBACK_PORT}}", str(callback_port))
                
                # Combine the code
                combined_code = f"{c2_code}\n\n{main_code}"
                
                # Handle build parameters
                if self.get_parameter("debug"):
                    combined_code = combined_code.replace("DEBUG = False", "DEBUG = True")
                
                version = self.get_parameter("version", "1.0")
                combined_code = combined_code.replace("{{VERSION}}", version)
                
                # Now compile this into a "binary" (we'll just encode it for the demo)
                payload_data = base64.b64encode(combined_code.encode()).decode()
                
                # Return success with our constructed payload
                return BuildResponse(status=BuildStatus.Success, payload=payload_data)
            else:
                return BuildResponse(status=BuildStatus.Error, error="No HTTP C2 profile configuration provided")
                
        except Exception as e:
            return BuildResponse(status=BuildStatus.Error, error=f"Error building payload: {str(e)}")