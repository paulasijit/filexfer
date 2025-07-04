import paramiko
import socket
import threading
import json
import datetime
from .utils import load_config, save_config, log_transfer

class FileXferServer(paramiko.ServerInterface):
    def __init__(self, config):
        self.config = config

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL if username == "filexfer" and password == "filexfer" else paramiko.AUTH_FAILED

    def check_channel_exec_request(self, channel, command):
        command = command.decode().strip()
        response = self.handle_command(command)
        channel.send(json.dumps(response).encode() + b"\n")
        channel.close()
        return True

    def handle_command(self, command):
        parts = command.split(maxsplit=1)
        if not parts:
            return {"error": "No command provided"}
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        if cmd == "init_server":
            if load_config(is_server=True):
                return {"error": "Server already initialized"}
            config = json.loads(args)
            client_key = save_config(config, is_server=True)
            return {"message": "Server initialized", "client_key": client_key}
        elif cmd == "get_config":
            config = load_config(is_server=True)
            if not config:
                return {"error": "Server not initialized"}
            config_stub = {k: v for k, v in config.items() if k != "tokens"}
            return {"config": config_stub}
        elif cmd == "validate_token" and args:
            token_id = args
            config = load_config(is_server=True)
            for token in config["tokens"]:
                if token["id"] == token_id:
                    expiry = datetime.datetime.fromisoformat(token["expiry"])
                    if expiry > datetime.datetime.utcnow():
                        return {"token": token}
            return {"error": "Invalid or expired token"}
        elif cmd == "create_token" and args:
            token_data = json.loads(args)
            config = load_config(is_server=True)
            config["tokens"].append(token_data)
            save_config(config, is_server=True)
            return {"message": f"Token {token_data['id']} created"}
        elif cmd == "revoke_token" and args:
            token_id = args
            config = load_config(is_server=True)
            config["tokens"] = [t for t in config["tokens"] if t["id"] != token_id]
            save_config(config, is_server=True)
            return {"message": f"Token {token_id} revoked"}
        elif cmd == "log_transfer" and args:
            log_data = json.loads(args)
            log_transfer(log_data["user_id"], log_data["token_id"], log_data["action"], log_data["remote_path"], log_data["local_path"])
            return {"message": "Transfer logged"}
        elif cmd == "create_bucket" and args:
            bucket_name = args
            config = load_config(is_server=True)
            transport = paramiko.Transport((config["ssh_host"], config["ssh_port"]))
            transport.connect(username=config["ssh_username"], password=config["ssh_password"])
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.mkdir(bucket_name)
            sftp.close()
            transport.close()
            return {"message": f"Bucket {bucket_name} created"}
        elif cmd == "create_subfolder" and args:
            bucket_name, subfolder_name = args.split(maxsplit=1)
            config = load_config(is_server=True)
            transport = paramiko.Transport((config["ssh_host"], config["ssh_port"]))
            transport.connect(username=config["ssh_username"], password=config["ssh_password"])
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.mkdir(f"{bucket_name}/{subfolder_name}")
            sftp.close()
            transport.close()
            return {"message": f"Subfolder {subfolder_name} created in bucket {bucket_name}"}
        return {"error": "Unknown command"}

def run_server(host="0.0.0.0", port=2222):
    config = load_config(is_server=True)
    if not config:
        print("Server not initialized. Run 'filexfer init-server' first.")
        return
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"FileXfer server running on {host}:{port}")
    while True:
        client_socket, addr = server_socket.accept()
        transport = paramiko.Transport(client_socket)
        transport.add_server_key(paramiko.RSAKey.generate(2048))
        server = FileXferServer(config)
        transport.start_server(server=server)
        channel = transport.accept(20)
        if channel:
            threading.Thread(target=transport.run).start()