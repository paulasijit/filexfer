# FileXfer

FileXfer is a secure, cross-platform command-line tool for transferring files using SFTP (Secure File Transfer Protocol). It allows users to create buckets (folders), organize files in subfolders, generate expiring Transfer Tokens with read/write permissions, and securely transfer files to/from an SSH server. Files are encrypted during transfer, and all actions are logged for auditing. FileXfer is ideal for secure file sharing without relying on cloud services like AWS S3.

## Features

- **Cross-Platform**: Compatible with macOS, Linux, and Windows.
- **Secure Transfers**: Uses SFTP with Fernet encryption for files.
- **Bucket and Subfolder Management**: Organize files on the SSH server.
- **Transfer Tokens**: Expiring tokens with read/write permissions.
- **Transfer Logs**: JSON log of all uploads/downloads.
- **Progress Bar**: Displays transfer progress via `tqdm`.
- **SSH Server Setup**: Script to configure SFTP on Linux.
- **Cost-Free**: Uses your own SSH server, avoiding cloud storage costs.

## Prerequisites

- Python 3.6 or higher.
- An SSH server with SFTP enabled (see platform-specific setup below).
- Internet access for SSH server connectivity.

## Installation

Clone the repository and install FileXfer using `pip`. Follow the instructions for your operating system.

### macOS

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/filexfer.git
   cd filexfer
   ```

2. **Ensure Prerequisites**:
   - Verify Python 3.6+:
     ```bash
     python3 --version
     ```
   - Install `setuptools` if missing:
     ```bash
     python3 -c "import setuptools" || pip install setuptools
     ```
     If `pip` is missing:
     ```bash
     curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
     python3 get-pip.py
     ```

3. **Install FileXfer**:
   ```bash
   pip install .
   ```

4. **Add to PATH (if needed)**:
   If you see a warning about `/Users/youruser/Library/Python/3.x/bin` not in PATH:
   ```bash
   export PATH="$PATH:/Users/youruser/Library/Python/3.9/bin"
   echo 'export PATH="$PATH:/Users/youruser/Library/Python/3.9/bin"' >> ~/.zshrc
   source ~/.zshrc
   ```

5. **Verify Installation**:
   ```bash
   filexfer --help
   ```

### Linux

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/filexfer.git
   cd filexfer
   ```

2. **Ensure Prerequisites**:
   - Verify Python 3.6+:
     ```bash
     python3 --version
     ```
   - Install `setuptools` if missing:
     ```bash
     python3 -c "import setuptools" || pip install setuptools
     ```
     If `pip` is missing:
     ```bash
     curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
     python3 get-pip.py
     ```

3. **Install FileXfer**:
   ```bash
   pip install .
   ```

4. **Add to PATH (if needed)**:
   If you see a warning about `~/.local/bin` not in PATH:
   ```bash
   export PATH="$PATH:$HOME/.local/bin"
   echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc
   source ~/.bashrc
   ```

5. **Verify Installation**:
   ```bash
   filexfer --help
   ```

### Windows

1. **Clone the Repository**:
   - Use Git Bash, WSL, or a Git client:
     ```bash
     git clone https://github.com/yourusername/filexfer.git
     cd filexfer
     ```

2. **Ensure Prerequisites**:
   - Verify Python 3.6+:
     ```bash
     python --version
     ```
   - Install `setuptools` if missing:
     ```bash
     python -c "import setuptools" || pip install setuptools
     ```
     If `pip` is missing:
     ```bash
     curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
     python get-pip.py
     ```

3. **Install FileXfer**:
   ```bash
   pip install .
   ```

4. **Add to PATH (if needed)**:
   If you see a warning about `C:\Python39\Scripts` or `C:\Users\youruser\AppData\Local\Programs\Python\Python39\Scripts` not in PATH:
   - Open **Control Panel > System > Advanced system settings > Environment Variables**.
   - Edit the `Path` variable (user or system) and add the `Scripts` directory.
   - Alternatively, in PowerShell:
     ```powershell
     $env:Path += ";C:\Python39\Scripts"
     ```
     Make it permanent:
     ```powershell
     [Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Python39\Scripts", "User")
     ```

5. **Verify Installation**:
   ```bash
   filexfer --help
   ```

## SSH Server Setup

FileXfer requires an SSH server with SFTP enabled. Follow the instructions for your platform.

### macOS

1. **Enable Built-in SSH Server**:
   - Go to `System Preferences > Sharing > Remote Login` (or `System Settings > General > Sharing`).
   - Enable **Remote Login**.

2. **Create an SFTP User (Optional, for Security)**:
   ```bash
   sudo sysadminctl -addUser filexfer -fullName "FileXfer User" -password "your_secure_password"
   ```

3. **Configure Chrooted SFTP (Optional)**:
   Edit `/etc/ssh/sshd_config`:
   ```bash
   sudo nano /etc/ssh/sshd_config
   ```
   Add:
   ```
   Match User filexfer
       ChrootDirectory /Users/filexfer
       ForceCommand internal-sftp
       AllowTcpForwarding no
   ```
   Set up the directory:
   ```bash
   sudo mkdir /Users/filexfer
   sudo chown filexfer:staff /Users/filexfer
   sudo chmod 700 /Users/filexfer
   ```
   Restart SSH:
   ```bash
   sudo launchctl unload /System/Library/LaunchDaemons/ssh.plist
   sudo launchctl load /System/Library/LaunchDaemons/ssh.plist
   ```

4. **Test SFTP**:
   ```bash
   sftp filexfer@localhost
   ```

### Linux

1. **Run Setup Script**:
   ```bash
   filexfer-setup --username filexfer --password your_secure_password
   ```
   - Installs `openssh-server`, creates an SFTP user, and configures a chrooted directory.
   - Requires `sudo`.

2. **Ensure Port 22 is Open**:
   ```bash
   sudo ufw allow 22
   ```

3. **Test SFTP**:
   ```bash
   sftp filexfer@<server-ip>
   ```

### Windows

1. **Install OpenSSH Server**:
   - Go to `Settings > Apps > Optional features > Add a feature`.
   - Install **OpenSSH Server**.
   - Alternatively, use Windows Subsystem for Linux (WSL2) with Ubuntu and run `filexfer-setup` inside WSL2.

2. **Configure OpenSSH**:
   - Edit `C:\ProgramData\ssh\sshd_config` (requires admin rights).
   - Add:
     ```
     Match User filexfer
         ChrootDirectory C:\Users\filexfer
         ForceCommand internal-sftp
     ```
   - Create the chroot directory:
     ```powershell
     mkdir C:\Users\filexfer
     icacls "C:\Users\filexfer" /setowner filexfer
     icacls "C:\Users\filexfer" /inheritance:r
     ```
   - Restart SSH:
     ```powershell
     net stop sshd
     net start sshd
     ```

3. **Create an SFTP User**:
   ```powershell
   net user filexfer your_secure_password /add
   ```

4. **Test SFTP**:
   ```bash
   sftp filexfer@localhost
   ```

**Note**: For production use, consider a Linux server (local or cloud) for easier SFTP setup.

## Usage

Initialize FileXfer and use the CLI commands to manage buckets, tokens, and file transfers.

1. **Initialize**:
   ```bash
   filexfer init
   ```
   - Enter SSH host (e.g., `localhost` or `192.168.1.100`), port (`22`), username, and password.

2. **Create a Bucket**:
   ```bash
   filexfer create-bucket project1
   ```

3. **Create a Subfolder**:
   ```bash
   filexfer create-subfolder project1 docs
   ```

4. **Create a Transfer Token**:
   ```bash
   filexfer create-token project1 --read --write --expiry-days 10
   ```

5. **Upload a File**:
   ```bash
   filexfer upload <token-id> report.pdf docs/report.pdf
   ```
   - Windows: Use `report.pdf` or `C:\path\to\report.pdf`.

6. **Download a File**:
   ```bash
   filexfer download <token-id> docs/report.pdf report_downloaded.pdf
   ```

7. **Revoke a Token**:
   ```bash
   filexfer revoke-token <token-id>
   ```

8. **View Logs**:
   ```bash
   cat ~/.filexfer/transfers.json  # macOS/Linux
   type %USERPROFILE%\.filexfer\transfers.json  # Windows
   ```

## Example Workflow

```bash
# Set up SSH server (Linux)
filexfer-setup --username filexfer --password mysecurepassword

# Initialize
filexfer init  # e.g., host=192.168.1.100, username=filexfer

# Create bucket and subfolder
filexfer create-bucket project1
filexfer create-subfolder project1 docs

# Create token
filexfer create-token project1 --read --write --expiry-days 10

# Upload file
filexfer upload <token-id> report.pdf docs/report.pdf

# Download file
filexfer download <token-id> docs/report.pdf report_downloaded.pdf

# Revoke token
filexfer revoke-token <token-id>

# Check logs
cat ~/.filexfer/transfers.json  # or type %USERPROFILE%\.filexfer\transfers.json
```

## Troubleshooting

- **Command Not Found**:
  Ensure the Python scripts directory is in PATH (see installation steps).
- **SSH Connection Issues**:
  - Verify server is running: `sudo systemctl status ssh` (Linux) or check `Remote Login` (macOS).
  - Test: `sftp filexfer@<host>`.
  - Ensure port 22 is open: `sudo ufw status` (Linux).
- **Permission Errors**:
  - Verify SSH user has write access to the chroot directory (e.g., `/var/filexfer`).
- **Token Issues**:
  - Check `~/.filexfer/settings.json` (or `%USERPROFILE%\.filexfer\settings.json`) for valid tokens.

## Contributing

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/yourusername/filexfer.git
   cd filexfer
   ```

2. Create a branch:
   ```bash
   git checkout -b feature/your-feature
   ```

3. Make changes, test, and install:
   ```bash
   pip install .
   filexfer --help
   ```

4. Commit and push:
   ```bash
   git commit -m "Add your feature"
   git push origin feature/your-feature
   ```

5. Open a pull request on GitHub.

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT License. See [LICENSE](LICENSE).

## Contact

- Issues: [GitHub Issues](https://github.com/paulasijit/filexfer/issues)
- Email: your.email@example.com
- Discussions: [GitHub Discussions](https://github.com/paulasijit/filexfer/discussions)

---

Thank you for using FileXfer! 🚀