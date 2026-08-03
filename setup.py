from setuptools import setup, find_packages
from pathlib import Path

VERSION = "3.0.0"

setup(
    name="synapse-ai",
    version=VERSION,
    description="Synapse AI v3.0.0 - Modular CLI/GUI with Synapsis Middleware",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[],
    entry_points={"console_scripts": ["synapse=synapse.main:main"]}
)
