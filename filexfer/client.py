import os
import json
import uuid
import datetime
import click
import paramiko
from pathlib import Path
import shutil
from cryptography.fernet import Fernet
from .utils import encrypt_file, decrypt_file, ProgressFile

CONFIG_DIR = Path.home() / ".filexfer"
CLIENT_KEY_FILE = CONFIG_DIR / "client_key"
SERVER_HOST = "45.79.122.246"
SERVER_PORT = 2222

def save_client_key(client_key):
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CLIENT_KEY_FILE, 'w') as f:
        f.write(client_key)
    os.chmod(CLIENT_KEY_FILE, 0o600)

def load_client_key():
    if not CLIENT_KEY_FILE.exists():
        return None
    with open(CLIENT_KEY_FILE, 'r') as f:
        return f.read()

def send_server_command(command):
    transport = paramiko.Transport((SERVER_HOST, SERVER_PORT))
    transport.connect(username="filexfer", password="filexfer")
    channel = transport.open_session()
    channel.exec_command(command)
    response = json.loads(channel.recv(1024).decode())
    channel.close()
    transport.close()
    if "error" in response:
        raise Exception(response["error"])
    return response

def get_sftp_client(config):
    transport = paramiko.Transport((config["ssh_host"], config["ssh_port"]))
    transport.connect(username=config["ssh_username"], password=config["ssh_password"])
    return paramiko.SFTPClient.from_transport(transport)

def validate_token(token_id):
    response = send_server_command(f"validate_token {token_id}")
    return response.get("token")

def load_config():
    client_key = load_client_key()
    if not client_key:
        return None
    response = send_server_command("get_config")
    config = response["config"]
    fernet = Fernet(client_key.encode())
    config["ssh_host"] = fernet.decrypt(config["ssh_host"].encode()).decode()
    config["ssh_username"] = fernet.decrypt(config["ssh_username"].encode()).decode()
    config["ssh_password"] = fernet.decrypt(config["ssh_password"].encode()).decode()
    config["ssh_port"] = int(fernet.decrypt(config["ssh_port"].encode()).decode())
    return config

def upload_folder_recursive(sftp, local_path, remote_path, token):
    local_path = Path(local_path)
    remote_base = f"{token['bucket']}/{remote_path.lstrip('/')}"
    try:
        sftp.mkdir(remote_base)
    except:
        pass
    for item in local_path.iterdir():
        remote_item = f"{remote_base}/{item.name}"
        if item.is_file():
            encrypted_file = encrypt_file(str(item), token["key"])
            file_size = os.path.getsize(encrypted_file)
            with open(encrypted_file, 'rb') as local_file:
                with sftp.open(remote_item, 'wb') as remote_file:
                    progress = ProgressFile(remote_file, file_size, f"Uploading {remote_item}")
                    shutil.copyfileobj(local_file, progress)
                    progress.close()
            os.unlink(encrypted_file)
        elif item.is_dir():
            upload_folder_recursive(sftp, item, remote_item[len(token['bucket'])+1:], token)

def delete_recursive(sftp, remote_path, token):
    if remote_path.rstrip('/') == token['bucket']:
        raise ValueError(f"Cannot delete bucket '{token['bucket']}' from client")
    parent = '/'.join(remote_path.rstrip('/').split('/')[:-1])
    if parent == token['bucket']:
        raise ValueError(f"Cannot delete server-created subfolder '{remote_path}'")
    try:
        stat = sftp.stat(remote_path)
        if stat.st_mode & 0o040000:
            for item in sftp.listdir(remote_path):
                delete_recursive(sftp, f"{remote_path}/{item}", token)
            sftp.rmdir(remote_path)
        else:
            sftp.remove(remote_path)
    except:
        pass

@click.group()
def cli():
    """FileXfer: A secure file transfer CLI tool."""
    pass

@cli.command()
@click.option("--client-key", prompt=True, help="Client key provided by server administrator")
def init(client_key):
    """Initialize client with server-provided client key."""
    save_client_key(client_key)
    try:
        config = load_config()
        if not config:
            click.echo("Failed to fetch configuration from server. Check client key or server status.")
            return
        click.echo("Client initialized with server configuration")
    except Exception as e:
        click.echo(f"Error initializing client: {e}")

@cli.command()
@click.option("--ssh-host", prompt=True)
@click.option("--ssh-port", prompt=True, type=int, default=22)
@click.option("--ssh-username", prompt=True)
@click.option("--ssh-password", prompt=True, hide_input=True)
def init_server(ssh_host, ssh_port, ssh_username, ssh_password):
    """Initialize server with SSH configuration (run on server only)."""
    config = {
        "user_id": str(uuid.uuid4()),
        "ssh_host": ssh_host,
        "ssh_port": ssh_port,
        "ssh_username": ssh_username,
        "ssh_password": ssh_password,
        "tokens": []
    }
    response = send_server_command(f"init_server {json.dumps(config)}")
    click.echo(response["message"])
    click.echo(f"Client key: {response['client_key']}")

@cli.command()
def server():
    """Start the FileXfer server."""
    from .server import run_server
    run_server()

@cli.command()
@click.argument("bucket_name")
def create_bucket(bucket_name):
    """Create a new bucket."""
    response = send_server_command(f"create_bucket {bucket_name}")
    click.echo(response["message"])

@cli.command()
@click.argument("bucket_name")
@click.argument("subfolder_name")
def create_subfolder(bucket_name, subfolder_name):
    """Create a subfolder in a bucket."""
    response = send_server_command(f"create_subfolder {bucket_name} {subfolder_name}")
    click.echo(response["message"])

@cli.command()
@click.argument("bucket_name")
@click.option("--read", is_flag=True, help="Allow read access")
@click.option("--write", is_flag=True, help="Allow write access")
@click.option("--delete", is_flag=True, help="Allow delete access")
@click.option("--expiry-days", type=int, default=7, help="Token expiry in days")
def create_token(bucket_name, read, write, delete, expiry_days):
    """Create a Transfer Token for a bucket."""
    if not (read or write or delete):
        click.echo("Must specify at least --read, --write, or --delete.")
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
        "permissions": {"read": read, "write": write, "delete": delete},
        "key": key.decode(),
        "expiry": expiry
    }
    response = send_server_command(f"create_token {json.dumps(token)}")
    click.echo(response["message"])

@cli.command()
@click.argument("token_id")
def revoke_token(token_id):
    """Revoke a Transfer Token."""
    response = send_server_command(f"revoke_token {token_id}")
    click.echo(response["message"])

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
    token = validate_token(token_id)
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
        send_server_command(f"log_transfer {json.dumps({'user_id': config['user_id'], 'token_id': token_id, 'action': 'download', 'remote_path': remote_full_path, 'local_path': local_path})}")
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
    token = validate_token(token_id)
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
        send_server_command(f"log_transfer {json.dumps({'user_id': config['user_id'], 'token_id': token_id, 'action': 'upload', 'remote_path': remote_full_path, 'local_path': local_path})}")
        click.echo(f"File uploaded to '{remote_path}'.")
        sftp.close()
    except Exception as e:
        click.echo(f"Error uploading file: {e}")

@cli.command()
@click.argument("token_id")
@click.argument("remote_path")
def delete(token_id, remote_path):
    """Delete a file using a Transfer Token."""
    config = load_config()
    if not config:
        click.echo("Please run 'filexfer init' first.")
        return
    token = validate_token(token_id)
    if not token or not token["permissions"].get("delete"):
        click.echo("Invalid or non-delete token.")
        return
    try:
        sftp = get_sftp_client(config)
        remote_full_path = f"{token['bucket']}/{remote_path}"
        if remote_full_path.rstrip('/') == token['bucket']:
            click.echo(f"Error: Cannot delete bucket '{token['bucket']}' from client")
            return
        parent = '/'.join(remote_full_path.rstrip('/').split('/')[:-1])
        if parent == token['bucket']:
            click.echo(f"Error: Cannot delete server-created subfolder '{remote_path}'")
            return
        sftp.remove(remote_full_path)
        send_server_command(f"log_transfer {json.dumps({'user_id': config['user_id'], 'token_id': token_id, 'action': 'delete', 'remote_path': remote_full_path, 'local_path': None})}")
        click.echo(f"File '{remote_path}' deleted.")
        sftp.close()
    except Exception as e:
        click.echo(f"Error deleting file: {e}")

@cli.command()
@click.argument("token_id")
@click.argument("local_path")
@click.argument("remote_path")
def upload_folder(token_id, local_path, remote_path):
    """Upload a folder recursively using a Transfer Token."""
    config = load_config()
    if not config:
        click.echo("Please run 'filexfer init' first.")
        return
    token = validate_token(token_id)
    if not token or not token["permissions"].get("write"):
        click.echo("Invalid or non-write token.")
        return
    try:
        sftp = get_sftp_client(config)
        upload_folder_recursive(sftp, local_path, remote_path, token)
        remote_full_path = f"{token['bucket']}/{remote_path}"
        send_server_command(f"log_transfer {json.dumps({'user_id': config['user_id'], 'token_id': token_id, 'action': 'upload_folder', 'remote_path': remote_full_path, 'local_path': local_path})}")
        click.echo(f"Folder uploaded to '{remote_path}'.")
        sftp.close()
    except Exception as e:
        click.echo(f"Error uploading folder: {e}")

@cli.command()
@click.argument("token_id")
@click.argument("remote_path")
def delete_folder(token_id, remote_path):
    """Delete a folder recursively using a Transfer Token."""
    config = load_config()
    if not config:
        click.echo("Please run 'filexfer init' first.")
        return
    token = validate_token(token_id)
    if not token or not token["permissions"].get("delete"):
        click.echo("Invalid or non-delete token.")
        return
    try:
        sftp = get_sftp_client(config)
        remote_full_path = f"{token['bucket']}/{remote_path}"
        delete_recursive(sftp, remote_full_path, token)
        send_server_command(f"log_transfer {json.dumps({'user_id': config['user_id'], 'token_id': token_id, 'action': 'delete_folder', 'remote_path': remote_full_path, 'local_path': None})}")
        click.echo(f"Folder '{remote_path}' deleted.")
        sftp.close()
    except Exception as e:
        click.echo(f"Error deleting folder: {e}")

if __name__ == "__main__":
    cli()