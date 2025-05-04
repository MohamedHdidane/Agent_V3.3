from mythic_payloadtype_container.PayloadBuilder import *
import asyncio
import os
import tempfile
import shutil
import zipfile
import base64
import subprocess
import sys
import uuid
from distutils.dir_util import copy_tree
import json

class igiderTest(PayloadType):
    name = "igiderTest"
    file_extension = "bin"
    author = "igider"
    supported_os = [
        SupportedOS.Linux,
        SupportedOS.MacOS,
        SupportedOS.Windows
    ]
    wrapper = False
    wrapped_payloads = []
    note = "A simple agent that can run the 'ls' command"
    supports_dynamic_loading = False
    build_parameters = [
        BuildParameter(
            name="output_type",
            parameter_type=BuildParameterType.ChooseOne,
            description="Choose the output format",
            choices=["binary", "python"],
            default_value="binary",
            required=False
        ),
    ]
    c2_profiles = ["http"]
    
    async def build(self) -> BuildResponse:
        # Create the build response
        resp = BuildResponse(status=BuildStatus.Error)
        
        try:
            # Create a temporary build directory
            build_dir = tempfile.mkdtemp()
            agent_dir = os.path.join(build_dir, "agent")
            os.makedirs(agent_dir, exist_ok=True)
            
            # Copy agent code to build directory
            agent_code_dir = os.path.join(self.agent_code_path, "base")
            shutil.copy(os.path.join(agent_code_dir, "main_agent.py"), os.path.join(agent_dir, "main_agent.py"))
            
            # Copy command implementations
            commands_dir = os.path.join(agent_dir, "commands")
            os.makedirs(commands_dir, exist_ok=True)
            
            # Copy ls command implementation
            shutil.copy(os.path.join(self.agent_code_path, "ls.py"), os.path.join(commands_dir, "ls.py"))
            
            # Create __init__.py files for Python packages
            with open(os.path.join(agent_dir, "__init__.py"), "w") as f:
                f.write("")
            with open(os.path.join(commands_dir, "__init__.py"), "w") as f:
                f.write("")
            
            # Create a launcher script
            with open(os.path.join(agent_dir, "launcher.py"), "w") as f:
                f.write("""
import asyncio
import os
import sys
from main_agent import BaseAgent
from commands.ls import ls_command

# Import C2 profile based on build configuration
from c2profile import C2Profile

async def main():
    # Initialize the agent
    agent = BaseAgent()
    
    # Register commands
    agent.register_command("ls", ls_command)
    
    # Setup C2 profile
    c2_profile = C2Profile()
    agent.set_c2_profile(c2_profile)
    
    # Start the agent
    await agent.start()

if __name__ == "__main__":
    asyncio.run(main())
""")
            
            # Create C2 profile loader
            c2_dir = os.path.join(agent_dir, "c2profile")
            os.makedirs(c2_dir, exist_ok=True)
            with open(os.path.join(c2_dir, "__init__.py"), "w") as f:
                f.write("")
            
            # Process C2 profiles
            for c2 in self.c2info:
                profile_name = c2.get_c2profile()["name"]
                c2_code_path = os.path.join(self.agent_code_path, "c2_profiles", f"{profile_name}.py")
                
                if os.path.exists(c2_code_path):
                    # Copy C2 code
                    shutil.copy(c2_code_path, os.path.join(c2_dir, f"{profile_name}.py"))
                    
                    # Create C2 profile loader
                    with open(os.path.join(c2_dir, "c2profile.py"), "w") as f:
                        f.write(f"""
# Import the appropriate C2 profile
from c2profile.{profile_name} import {profile_name.capitalize()}Profile

class C2Profile({profile_name.capitalize()}Profile):
    def __init__(self):
        # C2 configuration from build parameters
        config = {json.dumps(c2.get_parameters_dict())}
        super().__init__(config)
""")
            
            # Decide on output format
            output_type = self.get_parameter("output_type")
            
            if output_type == "binary":
                # Use PyInstaller to create a binary
                if sys.platform == "win32":
                    python_executable = "python"
                else:
                    python_executable = "python3"
                
                # Create PyInstaller spec file
                spec_file = os.path.join(build_dir, "agent.spec")
                with open(spec_file, "w") as f:
                    f.write(f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{os.path.join(agent_dir, "launcher.py").replace("\\", "/")}'],
    pathex=['{agent_dir.replace("\\", "/")}'],
    binaries=[],
    datas=[],
    hiddenimports=['asyncio'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='igiderTest',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False
)
""")
                
                # Run PyInstaller
                proc = await asyncio.create_subprocess_shell(
                    f"{python_executable} -m PyInstaller --onefile --clean {spec_file}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=build_dir
                )
                stdout, stderr = await proc.communicate()
                
                if proc.returncode != 0:
                    resp.build_stderr = f"Failed to build binary: {stderr.decode()}"
                    return resp
                
                # Get the output file
                if sys.platform == "win32":
                    output_file = os.path.join(build_dir, "dist", "igiderTest.exe")
                else:
                    output_file = os.path.join(build_dir, "dist", "igiderTest")
                
                if not os.path.exists(output_file):
                    resp.build_stderr = f"Failed to find output file at {output_file}"
                    return resp
                
                # Read the binary and return it
                with open(output_file, "rb") as f:
                    file_data = f.read()
                
                resp.payload = file_data
                resp.build_message = "Successfully built binary payload"
                resp.status = BuildStatus.Success