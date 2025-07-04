from setuptools import setup, find_packages

setup(
    name="filexfer",
    version="0.1.0",
    description="A secure file transfer tool with client and server functionality",
    author="Asijit Paul",
    author_email="asijit1610@gmail.com",
    url="https://github.com/paulasijit/filexfer",
    packages=["filexfer"],
    py_modules=["client", "server", "utils"],
    install_requires=[
        "click>=8.0.0",
        "paramiko>=2.10.0",
        "cryptography>=36.0.0",
        "tqdm>=4.60.0",
    ],
    entry_points={
        "console_scripts": [
            "filexfer = filexfer.client:cli",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)