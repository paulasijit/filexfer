import socket
import json
import paramiko
from cryptography.fernet import Fernet
from pathlib import Path
import datetime
import os
from .utils import load_config, save_config, log_transfer

CONFIG_DIR = Path.home() / ".filexfer"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
SSH_KEY_FILE = CONFIG_DIR / "key"

def handle_client(client_socket, config):
    try:
        command = client_socket.recv(1024).decode().strip()
        parts = command.split(" ", 1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        response = {}

        if cmd == "init_server":
            config_data = json.loads(args)
            client_key = save_config(config_data, is_server=True)
            response = {"message": "Server initialized", "client_key": client_key}
        elif cmd == "get_config":
            config_data = load_config(is_server=True)
            response = {"config": config_data}
        elif cmd == "create_bucket":
            bucket = args
            sftp = paramiko.SFTPClient.from_transport(paramiko.Transport((config["ssh_host"], config["ssh_port"])))
            sftp.connect(username=config["ssh_username"], password=config["ssh_password"])
            sftp.mkdir(bucket)
            sftp.close()
            response = {"message": f"Bucket '{bucket}' created"}
        elif cmd == "create_subfolder":
            bucket, subfolder = args.split(" ", 1)
            sftp = paramiko.SFTPClient.from_transport(paramiko.Transport((config["ssh_host"], config["ssh_port"])))
            sftp.connect(username=config["ssh_username"], password=config["ssh_password"])
            sftp.mkdir(f"{bucket}/{subfolder}")
            sftp.close()
            response = {"message": f"Subfolder '{subfolder}' created in bucket '{bucket}'"}
        elif cmd == "create_token":
            token = json.loads(args)
            config_data = load_config(is_server=True)
            config_data["tokens"].append(token)
            save_config(config_data, is_server=True)
            response = {"message": f"Token created: {token['id']}"}
        elif cmd == "validate_token":
            token_id = args
            config_data = load_config(is_server=True)
            token = next((t for t in config_data["tokens"] if t["id"] == token_id and datetime.datetime.fromisoformat(t["expiry"]) > datetime.datetime.utcnow()), None)
            response = {"token": token}
        elif cmd == "revoke_token":
            token_id = args
            config_data = load_config(is_server=True)
            config_data["tokens"] = [t for t in config_data["tokens"] if t["id"] != token_id]
            save_config(config_data, is_server=True)
            response = {"message": f"Token '{token_id}' revoked"}
        elif cmd == "log_transfer":
            log_entry = json.loads(args)
            log_transfer(log_entry)
            response = {"message": "Transfer logged"}
        else:
            response = {"error": "Unknown command"}

        client_socket.send(json.dumps(response).encode())
    except Exception as e:
        client_socket.send(json.dumps({"error": str(e)}).encode())
    finally:
        client_socket.close()

def run_server():
    host = "0.0.0.0"
    port = 2222
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Filexfer server running on {host}:{port}")

    config = load_config(is_server=True)
    if not config:
        print("Server not initialized. Run 'filexfer init-server' first.")
        return

    ssh_server = paramiko.ServerInterface()
    while True:
        try:
            client_socket, addr = server_socket.accept()
            transport = paramiko.Transport(client_socket)
            transport.add_server_key(paramiko.RSAKey(filename=str(SSH_KEY_FILE)))
            transport.start_server(server=ssh_server)
            channel = transport.accept(20)
            if channel is None:
                continue
            handle_client(channel, config)
        except Exception as e:
            print(f"Server error: {e}")

def stop_server():
    """Stop the FileXfer server by terminating the process using port 2222."""
    import subprocess
    try:
        # Find the PID using port 2222
        result = subprocess.run(['lsof', '-i', ':2222'], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        pid = None
        for line in lines[1:]:  # Skip header
            if 'filexfer' in line:  # Ensure it's a Python process
                pid = line.split()[1]  # PID is second column
                break
        if pid:
            subprocess.run(['kill', '-9', pid])
            print(f"Filexfer server (PID: {pid}) stopped")
        else:
            print("No FileXfer server process found on port 2222")
    except Exception as e:
        print(f"Error stopping server: {e}")

if __name__ == "__main__":
    run_server()