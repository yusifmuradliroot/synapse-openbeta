from setuptools import setup, find_packages

setup(
    name="synapse-ai-cli",
    version="1.0.0",
    description="Synapse AI Terminal Client with Multi-Provider Support",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "synapse=synapse.cli:run"
        ]
    }
)
