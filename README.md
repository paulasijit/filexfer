# FileXfer: Secure File Transfer Tool

FileXfer is a simple, secure tool for transferring files between your computer and a server using SSH. It uses a client-server model where the server manages file storage and the client handles file uploads, downloads, and more. Files are encrypted for security, and a unique client key ensures safe access to the server without storing sensitive data on your computer.

This guide explains how to set up the FileXfer server on Linux and the client on Linux, macOS, or Windows. Follow the steps carefully, and you’ll be transferring files in no time!

## Prerequisites

- **Server**: A Linux machine (e.g., Ubuntu) with SSH access and Python 3.6 or later.
- **Client**: A computer running Linux, macOS, or Windows with Python 3.6 or later.
- **Client Key**: A key provided by the server administrator to initialize the client (you’ll get this after setting up the server).

## Server Setup (Linux Only)

The server runs on a Linux machine (e.g., a cloud server like `XX.XX.XXX.XXX`) and handles file storage and client requests. Follow these steps to set it up.

### Step 1: Log in to Your Linux Server
Connect to your server using SSH. Replace `root@XX.XX.XXX.XXX` with your server’s address and username.
```bash
ssh root@XX.XX.XXX.XXX
```

### Step 2: Install FileXfer
1. Clone or download the `filexfer` project to your server:
   ```bash
   git clone https://github.com/paulasijit/filexfer.git
   cd filexfer
   ```
2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install FileXfer:
   ```bash
   pip install .
   ```

### Step 3: Initialize the Server
Run the initialization command to set up the server with your SSH details:
```bash
filexfer init-server
```
You’ll be prompted to enter:
- **SSH Host**: Your server’s address (e.g., `XX.XX.XXX.XXX`).
- **SSH Port**: Usually `22` (press Enter for default).
- **SSH Username**: Your SSH username (e.g., `asijitp`).
- **SSH Password**: Your SSH password (e.g., `Asijit@1999`).

Example output:
```
Server initialized
Client key: gAAAAAB...
```
**Save the client key** (starts with `gAAAAAB...`). You’ll need to share it securely with anyone using the client (e.g., via encrypted email).

### Step 4: Start the Server
Run the server in the background:
```bash
filexfer server &
```
The server will start on port `2222`. You’ll see:
```
FileXfer server running on 0.0.0.0:2222
```

### Step 5: Open Port 2222
Allow connections to port `2222`:
```bash
sudo ufw allow 2222
```

### Step 6: Verify Server Setup
Check that the server’s configuration is created:
```bash
ls -l /root/.filexfer/
```
You should see `settings.json` (encrypted credentials) and `key`. Later, `transfers.json` will appear when files are transferred.

## Client Setup

The client runs on your computer (Linux, macOS, or Windows) and lets you upload, download, or manage files on the server. You need the `client_key` from the server setup.

### Linux Client Setup
1. **Clone or Download FileXfer**:
   ```bash
   git clone https://github.com/paulasijit/filexfer.git
   cd filexfer
   ```
2. **Create and Activate Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
   If `python3` doesn’t work, try `python`.
3. **Install FileXfer**:
   ```bash
   pip install .
   ```
4. **Initialize the Client**:
   ```bash
   filexfer init
   ```
   Enter the `client_key` provided by the server administrator. Example:
   ```
   Enter client key: gAAAAAB...
   Client initialized with server configuration
   ```
5. **Verify Setup**:
   Check that the client key is saved:
   ```bash
   cat ~/.filexfer/client_key
   ```

### macOS Client Setup
1. **Clone or Download FileXfer**:
   ```bash
   git clone https://github.com/paulasijit/filexfer.git
   cd filexfer
   ```
   You may need `git` installed. Install it with:
   ```bash
   xcode-select --install
   ```
2. **Create and Activate Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
   Ensure Python 3 is installed (run `python3 --version`). If not, install it using Homebrew:
   ```bash
   brew install python
   ```
3. **Install FileXfer**:
   ```bash
   pip install .
   ```
4. **Initialize the Client**:
   ```bash
   filexfer init
   ```
   Enter the `client_key` provided by the server administrator.
5. **Verify Setup**:
   ```bash
   cat ~/.filexfer/client_key
   ```

### Windows Client Setup
1. **Clone or Download FileXfer**:
   Download the `filexfer` project from GitHub (https://github.com/paulasijit/filexfer) and extract it, or use Git:
   ```cmd
   git clone https://github.com/paulasijit/filexfer.git
   cd filexfer
   ```
   Install Git from https://git-scm.com if needed.
2. **Create and Activate Virtual Environment**:
   Open Command Prompt (or PowerShell) and run:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```
   Ensure Python 3 is installed (run `python --version`). If not, download it from https://www.python.org.
3. **Install FileXfer**:
   ```cmd
   pip install .
   ```
4. **Initialize the Client**:
   ```cmd
   filexfer init
   ```
   Enter the `client_key` provided by the server administrator.
5. **Verify Setup**:
   ```cmd
   type %USERPROFILE%\.filexfer\client_key
   ```

## Using FileXfer

Once the server and client are set up, you can use these commands to manage files.

### Create a Bucket
A bucket is like a folder on the server:
```bash
filexfer create-bucket project1
```

### Create a Subfolder
Add a subfolder inside a bucket:
```bash
filexfer create-subfolder project1 documents
```

### Create a Transfer Token
Generate a token to allow specific actions (read, write, delete):
```bash
filexfer create-token project1 --write --delete
```
This creates a token for writing and deleting in `project1`. Copy the token ID (e.g., `550e8400-e29b-41d4-a716-446655440000`).

### Upload a File
Upload a file to the server:
```bash
filexfer upload <token_id> ~/Downloads/file.txt documents/file.txt
```
Replace `<token_id>` with the token ID from `create-token`.

### Download a File
Download a file from the server:
```bash
filexfer download <token_id> documents/file.txt ~/Downloads/file.txt
```

### Delete a File
Delete a file from the server:
```bash
filexfer delete <token_id> documents/file.txt
```

### Upload a Folder
Upload a folder and its contents:
```bash
filexfer upload-folder <token_id> ~/myfolder documents/myfolder
```

### Delete a Folder
Delete a folder and its contents:
```bash
filexfer delete-folder <token_id> documents/myfolder
```

### Revoke a Token
Revoke a token to disable it:
```bash
filexfer revoke-token <token_id>
```

## Troubleshooting

- **Server not running**:
  Check if the server is running:
  ```bash
  ssh root@XX.XX.XXX.XXX 'ps aux | grep filexfer'
  ```
  Restart it if needed:
  ```bash
  filexfer server &
  ```
- **Client can’t connect**:
  Ensure port `2222` is open:
  ```bash
  ssh root@XX.XX.XXX.XXX 'sudo ufw status'
  ```
  Open it if needed:
  ```bash
  sudo ufw allow 2222
  ```
- **No transfers.json file**:
  Check the server’s log file:
  ```bash
  ssh root@XX.XX.XXX.XXX 'cat /root/.filexfer/transfers.json'
  ```
  Ensure the `/root/.filexfer` directory has correct permissions:
  ```bash
  ssh root@XX.XX.XXX.XXX
  chmod 700 /root/.filexfer
  ```
  Run a test upload and check again.
- **Invalid client key**:
  Verify the `client_key` with the server administrator. Re-run:
  ```bash
  filexfer init
  ```
- **Command errors**:
  Run the command again and note the error message. For example:
  ```bash
  filexfer upload <token_id> ~/Downloads/file.txt documents/file.txt
  ```

## Security Notes
- The server stores all sensitive data (SSH credentials) in an encrypted file (`/root/.filexfer/settings.json`).
- Clients only store a `client_key`, which is safe and cannot be used to access sensitive data without the server.
- Share the `client_key` securely (e.g., via encrypted email).
- For production, consider using SSH keys instead of a hardcoded username/password for the server (port `2222`).

## Contributing
File issues or submit pull requests at https://github.com/paulasijit/filexfer.