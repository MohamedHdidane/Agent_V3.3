from mythic_container.MythicCommandBase import *
import json

class LsCommand(CommandBase):
    cmd = "ls"
    needs_admin = False
    help_cmd = "ls [directory]"
    description = "List contents of a directory"
    version = 1
    supported_ui_features = ["file_browser:list"]
    author = "Mythic Developer"
    argument_class = CommandParameter
    attackmapping = ["T1083"]  # File and Directory Discovery
    browser_script = "ls_new"
    attributes = CommandAttributes(
        supported_os=[SupportedOS.Linux, SupportedOS.MacOS, SupportedOS.Windows]
    )
    
    async def create_tasking(self, task: MythicTask) -> MythicTask:
        return task

    async def process_response(self, response: AgentResponse):
        pass