from setuptools import setup, find_packages

setup(
    name="filexfer",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.3",
        "paramiko>=2.10.4",
        "cryptography>=36.0.0",
        "tqdm>=4.64.0",
        "setuptools>=40.0.0"
    ],
    entry_points={
        "console_scripts": [
            "filexfer = filexfer.filexfer:cli",
            "filexfer-setup = filexfer.setup_ssh:setup_ssh_server"
        ]
    },
    author="Asijit Paul",
    author_email="asijit1610@gmail.com",
    description="A secure file transfer CLI tool using SFTP",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/filexfer",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)