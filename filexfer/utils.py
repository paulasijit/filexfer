import os
import json
import datetime
from cryptography.fernet import Fernet
from pathlib import Path
import tempfile
from tqdm import tqdm

CONFIG_DIR = Path("/root/.filexfer") if os.geteuid() == 0 else Path.home() / ".filexfer"
CONFIG_FILE = CONFIG_DIR / "settings.json"
KEY_FILE = CONFIG_DIR / "key"
LOG_FILE = CONFIG_DIR / "transfers.json"

def load_config(is_server=False):
    if not CONFIG_FILE.exists() or not KEY_FILE.exists():
        return None
    with open(KEY_FILE, 'rb') as f:
        key = f.read()
    fernet = Fernet(key)
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    config["ssh_host"] = fernet.decrypt(config["ssh_host"].encode()).decode()
    config["ssh_username"] = fernet.decrypt(config["ssh_username"].encode()).decode()
    config["ssh_password"] = fernet.decrypt(config["ssh_password"].encode()).decode()
    config["ssh_port"] = int(fernet.decrypt(config["ssh_port"].encode()).decode())
    return config

def save_config(config, is_server=False):
    CONFIG_DIR.mkdir(exist_ok=True)
    if not KEY_FILE.exists():
        key = Fernet.generate_key()
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        os.chmod(KEY_FILE, 0o600)
    with open(KEY_FILE, 'rb') as f:
        key = f.read()
    fernet = Fernet(key)
    encrypted_config = config.copy()
    encrypted_config["ssh_host"] = fernet.encrypt(config["ssh_host"].encode()).decode()
    encrypted_config["ssh_username"] = fernet.encrypt(config["ssh_username"].encode()).decode()
    encrypted_config["ssh_password"] = fernet.encrypt(config["ssh_password"].encode()).decode()
    encrypted_config["ssh_port"] = fernet.encrypt(str(config["ssh_port"]).encode()).decode()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(encrypted_config, f, indent=4)
    os.chmod(CONFIG_FILE, 0o600)
    return key.decode() if is_server else None

def log_transfer(user_id, token_id, action, remote_path, local_path):
    try:
        CONFIG_DIR.mkdir(exist_ok=True)
        logs = []
        if LOG_FILE.exists():
            with open(LOG_FILE, 'r') as f:
                logs = json.load(f)
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "user_id": user_id,
            "token_id": token_id,
            "action": action,
            "remote_path": remote_path,
            "local_path": local_path
        }
        logs.append(log_entry)
        with open(LOG_FILE, 'w') as f:
            json.dump(logs, f, indent=4)
        os.chmod(LOG_FILE, 0o600)
    except Exception as e:
        print(f"Error logging transfer: {e}")

def encrypt_file(input_path, key):
    fernet = Fernet(key)
    with open(input_path, 'rb') as f:
        data = f.read()
    encrypted = fernet.encrypt(data)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.enc')
    with open(temp_file.name, 'wb') as f:
        f.write(encrypted)
    return temp_file.name

def decrypt_file(input_path, key, output_path):
    fernet = Fernet(key)
    with open(input_path, 'rb') as f:
        encrypted = f.read()
    decrypted = fernet.decrypt(encrypted)
    with open(output_path, 'wb') as f:
        f.write(decrypted)

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