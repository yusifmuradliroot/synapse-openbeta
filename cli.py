import os
import sys
import json
from pathlib import Path

WORKSPACE_DIR = Path.home() / ".synapse"
CONFIG_PATH = WORKSPACE_DIR / "config.json"
MEMORY_PATH = WORKSPACE_DIR / "memory.json"
HISTORY_PATH = WORKSPACE_DIR / "history.json"

DEFAULT_CONFIG = {
    "default_provider": "nvidia",
    "providers": {
        "nvidia": {
            "api_key": "YOUR_NVIDIA_KEY",
            "model": "nvidia/nemotron-3-ultra-550b-a55b",
            "api_url": "https://integrate.api.nvidia.com/v1/chat/completions"
        },
        "cohere": {
            "api_key": "YOUR_COHERE_KEY",
            "model": "command-r-08-2024",
            "api_url": "https://api.cohere.com/v1/chat"
        },
        "openrouter": {
            "api_key": "YOUR_OPENROUTER_KEY",
            "model": "meta-llama/llama-3.1-8b-instruct:free",
            "api_url": "https://openrouter.ai/api/v1/chat/completions"
        }
    }
}

def init_workspace():
    if not WORKSPACE_DIR.exists():
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[+] Created workspace: {WORKSPACE_DIR}")
    
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        print(f"[+] Created default config: {CONFIG_PATH}")
        print("[!] Please edit config.json with your API keys before running.")
    
    if not MEMORY_PATH.exists():
        MEMORY_PATH.write_text("[]", encoding="utf-8")
        
    if not HISTORY_PATH.exists():
        HISTORY_PATH.write_text(json.dumps({"summary": "", "recent": [], "chat_counter": 0}, indent=2), encoding="utf-8")

def run():
    init_workspace()
    
    if not CONFIG_PATH.exists():
        sys.exit("[Error] config.json missing.")
    
    cfg_content = CONFIG_PATH.read_text(encoding="utf-8").strip()
    if not cfg_content:
        sys.exit("[Error] config.json is empty.")
        
    os.chdir(WORKSPACE_DIR)
    
    from synapse.main import TerminalChat
    TerminalChat(base_dir=WORKSPACE_DIR).run()

if __name__ == "__main__":
    run()
