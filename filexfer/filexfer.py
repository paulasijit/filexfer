import os
import json
import uuid
import datetime
import click
import paramiko
from cryptography.fernet import Fernet
from pathlib import Path
from tqdm import tqdm
import tempfile
import shutil

CONFIG_DIR = Path.home() / ".filexfer"
CONFIG_FILE = CONFIG_DIR / "settings.json"
LOG_FILE = CONFIG_DIR / "transfers.json"

def load_config():
    if not CONFIG_FILE.exists():
        return None
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def log_transfer(user_id, token_id, action, remote_path, local_path):
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "user_id": user_id,
        "token_id": token_id,
        "action": action,
        "remote_path": remote_path,
        "local_path": local_path
    }
    logs = []
    if LOG_FILE.exists():
        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)
    logs.append(log_entry)
    with open(LOG_FILE, 'w') as f:
        json.dump(logs, f, indent=4)

def initialize_config():
    config = {
        "user_id": str(uuid.uuid4()),
        "ssh_host": "",
        "ssh_port": 22,
        "ssh_username": "",
        "ssh_password": "",
        "tokens": []
    }
    click.echo("Initializing new configuration...")
    config["ssh_host"] = click.prompt("Enter SSH host")
    config["ssh_port"] = click.prompt("Enter SSH port", type=int, default=22)
    config["ssh_username"] = click.prompt("Enter SSH username")
    config["ssh_password"] = click.prompt("Enter SSH password", hide_input=True)
    save_config(config)
    click.echo(f"Configuration saved to {CONFIG_FILE}")
    return config

def get_sftp_client(config):
    transport = paramiko.Transport((config["ssh_host"], config["ssh_port"]))
    transport.connect(username=config["ssh_username"], password=config["ssh_password"])
    return paramiko.SFTPClient.from_transport(transport)

# def validate_token(config, token_id):
#     for token in config["tokens"]:
#         if token["id"] == token_id:
#             expiry = datetime.datetime.fromisoformat(token["expiry"])
#             if expiry > datetime.datetime.utcnow():
#                 return token
#     return None

def validate_token(config, token_id):
    # Try local validation first
    for token in config["tokens"]:
        if token["id"] == token_id:
            expiry = datetime.datetime.fromisoformat(token["expiry"])
            if expiry > datetime.datetime.utcnow():
                return token

    # If not found locally, check server
    try:
        transport = paramiko.Transport((config["ssh_host"], config["ssh_port"]))
        transport.connect(username=config["ssh_username"], password=config["ssh_password"])
        sftp = paramiko.SFTPClient.from_transport(transport)
        with sftp.open('/root/.filexfer/settings.json', 'r') as f:
            server_config = json.load(f)
        sftp.close()
        transport.close()
        for token in server_config["tokens"]:
            if token["id"] == token_id:
                expiry = datetime.datetime.fromisoformat(token["expiry"])
                if expiry > datetime.datetime.utcnow():
                    return token
    except Exception as e:
        print(f"Error checking server tokens: {e}")
    return None

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

@click.group()
def cli():
    """FileXfer: A secure file transfer CLI tool."""
    pass

@cli.command()
def init():
    """Initialize user configuration."""
    initialize_config()

@cli.command()
@click.argument("bucket_name")
def create_bucket(bucket_name):
    """Create a new bucket."""
    config = load_config()
    if not config:
        click.echo("Please run 'filexfer init' first.")
        return
    try:
        sftp = get_sftp_client(config)
        sftp.mkdir(bucket_name)
        click.echo(f"Bucket '{bucket_name}' created.")
        sftp.close()
    except Exception as e:
        click.echo(f"Error creating bucket: {e}")

@cli.command()
@click.argument("bucket_name")
@click.argument("subfolder_name")
def create_subfolder(bucket_name, subfolder_name):
    """Create a subfolder in a bucket."""
    config = load_config()
    if not config:
        click.echo("Please run 'filexfer init' first.")
        return
    try:
        sftp = get_sftp_client(config)
        path = f"{bucket_name}/{subfolder_name}"
        sftp.mkdir(path)
        click.echo(f"Subfolder '{subfolder_name}' created in bucket '{bucket_name}'.")
        sftp.close()
    except Exception as e:
        click.echo(f"Error creating subfolder: {e}")

@cli.command()
@click.argument("bucket_name")
@click.option("--read", is_flag=True, help="Allow read access")
@click.option("--write", is_flag=True, help="Allow write access")
@click.option("--expiry-days", type=int, default=7, help="Token expiry in days")
def create_token(bucket_name, read, write, expiry_days):
    """Create a Transfer Token for a bucket."""
    if not (read or write):
        click.echo("Must specify at least --read or --write.")
        return
    config = load_config()
    if not config:
        click.echo("Please run 'filexfer init' first.")
        return
    token_id = str(uuid.uuid4())
    key = Fernet.generate_key()
    expiry = (datetime.datetime.utcnow() + datetime.timedelta(days=expiry_days)).isoformat()
    token = {
        "id": token_id,
        "bucket": bucket_name,
        "permissions": {"read": read, "write": write},
        "key": key.decode(),
        "expiry": expiry
    }
    config["tokens"].append(token)
    save_config(config)
    click.echo(f"Transfer Token created: ID={token_id}, Expiry={expiry}")

@cli.command()
@click.argument("token_id")
def revoke_token(token_id):
    """Revoke a Transfer Token."""
    config = load_config()
    if not config:
        click.echo("Please run 'filexfer init' first.")
        return
    config["tokens"] = [t for t in config["tokens"] if t["id"] != token_id]
    save_config(config)
    click.echo(f"Token '{token_id}' revoked.")

@cli.command()
@click.argument("token_id")
@click.argument("remote_path")
@click.argument("local_path")
def download(token_id, remote_path, local_path):
    """Download a file using a Transfer Token."""
    config = load_config()
    if not config:
        click.echo("Please run 'filexfer init' first.")
        return
    token = validate_token(config, token_id)
    if not token or not token["permissions"].get("read"):
        click.echo("Invalid or non-read token.")
        return
    try:
        sftp = get_sftp_client(config)
        remote_full_path = f"{token['bucket']}/{remote_path}"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.enc').name
        file_size = sftp.stat(remote_full_path).st_size
        with sftp.open(remote_full_path, 'rb') as remote_file:
            with open(temp_file, 'wb') as local_temp:
                progress = ProgressFile(local_temp, file_size, f"Downloading {remote_path}")
                shutil.copyfileobj(remote_file, progress)
                progress.close()
        decrypt_file(temp_file, token["key"], local_path)
        os.unlink(temp_file)
        log_transfer(config["user_id"], token_id, "download", remote_full_path, local_path)
        click.echo(f"File downloaded to '{local_path}'.")
        sftp.close()
    except Exception as e:
        click.echo(f"Error downloading file: {e}")

@cli.command()
@click.argument("token_id")
@click.argument("local_path")
@click.argument("remote_path")
def upload(token_id, local_path, remote_path):
    """Upload a file using a Transfer Token."""
    config = load_config()
    if not config:
        click.echo("Please run 'filexfer init' first.")
        return
    print(config, token_id)
    token = validate_token(config, token_id)
    print(token)
    if not token or not token["permissions"].get("write"):
        click.echo("Invalid or non-write token.")
        return
    try:
        sftp = get_sftp_client(config)
        remote_full_path = f"{token['bucket']}/{remote_path}"
        encrypted_file = encrypt_file(local_path, token["key"])
        file_size = os.path.getsize(encrypted_file)
        with open(encrypted_file, 'rb') as local_file:
            with sftp.open(remote_full_path, 'wb') as remote_file:
                progress = ProgressFile(remote_file, file_size, f"Uploading {remote_path}")
                shutil.copyfileobj(local_file, progress)
                progress.close()
        os.unlink(encrypted_file)
        log_transfer(config["user_id"], token_id, "upload", remote_full_path, local_path)
        click.echo(f"File uploaded to '{remote_path}'.")
        sftp.close()
    except Exception as e:
        click.echo(f"Error uploading file: {e}")

if __name__ == "__main__":
    cli()