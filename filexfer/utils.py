import json
from pathlib import Path
from cryptography.fernet import Fernet
import paramiko
import os
from tqdm import tqdm

CONFIG_DIR = Path.home() / ".filexfer"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
TRANSFER_LOG = CONFIG_DIR / "transfers.json"
SSH_KEY_FILE = CONFIG_DIR / "key"
FERNET_KEY_FILE = CONFIG_DIR / "fernet_key"

def save_config(config, is_server=False):
    CONFIG_DIR.mkdir(exist_ok=True)
    try:
        key = Fernet.generate_key()
        fernet = Fernet(key)
        config_data = config.copy()
        
        if is_server:
            # Generate or regenerate RSA key if invalid or missing
            try:
                paramiko.RSAKey.from_private_key_file(str(SSH_KEY_FILE))
            except Exception:
                rsa_key = paramiko.RSAKey.generate(bits=2048)
                with open(SSH_KEY_FILE, 'w') as f:
                    f.write(rsa_key.get_private_key().decode())
                os.chmod(SSH_KEY_FILE, 0o600)
                
            config_data["ssh_host"] = fernet.encrypt(config["ssh_host"].encode()).decode()
            config_data["ssh_username"] = fernet.encrypt(config["ssh_username"].encode()).decode()
            config_data["ssh_password"] = fernet.encrypt(config["ssh_password"].encode()).decode()
            config_data["ssh_port"] = fernet.encrypt(str(config["ssh_port"]).encode()).decode()
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(config_data, f, indent=2)
            os.chmod(SETTINGS_FILE, 0o600)
            
            with open(FERNET_KEY_FILE, 'wb') as f:
                f.write(key)
            os.chmod(FERNET_KEY_FILE, 0o600)
            return key.decode()
        return None
    except Exception as e:
        raise Exception(f"Failed to save config: {e}")

def load_config(is_server=False):
    try:
        if not SETTINGS_FILE.exists():
            return None
        with open(SETTINGS_FILE, 'r') as f:
            config = json.load(f)
        if is_server:
            with open(FERNET_KEY_FILE, 'rb') as f:
                key = f.read()
            fernet = Fernet(key)
            config["ssh_host"] = fernet.decrypt(config["ssh_host"].encode()).decode()
            config["ssh_username"] = fernet.decrypt(config["ssh_username"].encode()).decode()
            config["ssh_password"] = fernet.decrypt(config["ssh_password"].encode()).decode()
            config["ssh_port"] = int(fernet.decrypt(config["ssh_port"].encode()).decode())
        return config
    except Exception as e:
        raise Exception(f"Failed to load config: {e}")

def log_transfer(entry):
    try:
        CONFIG_DIR.mkdir(exist_ok=True)
        transfers = []
        if TRANSFER_LOG.exists():
            with open(TRANSFER_LOG, 'r') as f:
                try:
                    transfers = json.load(f)
                except json.JSONDecodeError:
                    transfers = []
        transfers.append(entry)
        with open(TRANSFER_LOG, 'w') as f:
            json.dump(transfers, f, indent=2)
        os.chmod(TRANSFER_LOG, 0o600)
    except Exception as e:
        raise Exception(f"Failed to log transfer: {e}")

def encrypt_file(input_path, key):
    try:
        fernet = Fernet(key)
        with open(input_path, 'rb') as f:
            data = f.read()
        encrypted_data = fernet.encrypt(data)
        output_path = input_path + '.enc'
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
        return output_path
    except Exception as e:
        raise Exception(f"Failed to encrypt file: {e}")

def decrypt_file(input_path, key, output_path):
    try:
        fernet = Fernet(key)
        with open(input_path, 'rb') as f:
            encrypted_data = f.read()
        decrypted_data = fernet.decrypt(encrypted_data)
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
    except Exception as e:
        raise Exception(f"Failed to decrypt file: {e}")
    
class ProgressFile:
    def __init__(self, fileobj, size, desc):
        self.fileobj = fileobj
        self.size = size
        self.progress = tqdm(total=size, unit='B', unit_scale=True, desc=desc)

    def read(self, size=-1):
        data = self.fileobj.read(size)
        self.progress.update(len(data))
        return data

    def write(self, data):
        self.fileobj.write(data)
        self.progress.update(len(data))

    def close(self):
        self.progress.close()
        self.fileobj.close()