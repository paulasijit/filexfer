import subprocess
import click
import os
import sys
from pathlib import Path

@click.command()
@click.option("--username", default="filexfer", help="Username for SFTP user")
@click.option("--password", prompt=True, hide_input=True, help="Password for SFTP user")
@click.option("--home-dir", default="/var/filexfer", help="Home directory for SFTP user")
def setup_ssh_server(username, password, home_dir):
    """Set up an SSH server for FileXfer."""
    try:
        # Update and install OpenSSH
        click.echo("Installing OpenSSH server...")
        subprocess.run(["sudo", "apt-get", "update"], check=True)
        subprocess.run(["sudo", "apt-get", "install", "-y", "openssh-server"], check=True)

        # Create user
        click.echo(f"Creating user '{username}'...")
        subprocess.run(["sudo", "useradd", "-m", "-d", home_dir, "-s", "/bin/false", username], check=True)
        subprocess.run(["sudo", "passwd", username], input=password.encode(), check=True)

        # Create home directory and set permissions
        click.echo(f"Setting up home directory '{home_dir}'...")
        Path(home_dir).mkdir(exist_ok=True, parents=True)
        subprocess.run(["sudo", "chown", f"{username}:{username}", home_dir], check=True)
        subprocess.run(["sudo", "chmod", "700", home_dir], check=True)

        # Configure SSH for SFTP
        sshd_config = f"""
Match User {username}
    ChrootDirectory {home_dir}
    ForceCommand internal-sftp
    AllowTcpForwarding no
    X11Forwarding no
"""
        with open("/tmp/sshd_config_append", "w") as f:
            f.write(sshd_config)
        subprocess.run(["sudo", "tee", "-a", "/etc/ssh/sshd_config"], input=sshd_config.encode(), check=True)
        os.unlink("/tmp/sshd_config_append")

        # Restart SSH service
        click.echo("Restarting SSH service...")
        subprocess.run(["sudo", "systemctl", "restart", "ssh"], check=True)

        click.echo(f"SSH server configured! Use username '{username}' and home directory '{home_dir}' in filexfer.")
        click.echo("Ensure port 22 is open in your firewall.")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error during setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_ssh_server()