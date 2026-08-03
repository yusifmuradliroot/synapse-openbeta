import json
from pathlib import Path

BASE_DIR = Path.home() / "synapse"
CONFIG_PATH = BASE_DIR / "config.json"
DNA_PATH = BASE_DIR / "dna.json"
MEMORY_PATH = BASE_DIR / "memory.json"
HISTORY_PATH = BASE_DIR / "history.json"
WS_DIR = BASE_DIR / "workspaces"

PROVIDERS = {
    "nvidia": {"api_key": "YOUR_NVIDIA_KEY", "model": "nvidia/nemotron-3-ultra-550b-a55b", "api_url": "https://integrate.api.nvidia.com/v1/chat/completions"},
    "openrouter": {"api_key": "YOUR_OPENROUTER_KEY", "model": "meta-llama/llama-3.1-8b-instruct:free", "api_url": "https://openrouter.ai/api/v1/chat/completions"},
    "cohere": {"api_key": "YOUR_COHERE_KEY", "model": "command-r-08-2024", "api_url": "https://api.cohere.com/v1/chat"}
}

DEFAULT_DNA = {
    "core_directives": [
        "DIRECT MODE: No greetings, filler, or meta-commentary.",
        "Provide only exact answers or code.",
        "Use markdown code blocks.",
        "Be strictly relevant and concise."
    ],
    "response_rules": [
        "Save facts with <{mem}>fact<{mem}>.",
        "Output <{time}> for time.",
        "CRITICAL: Workspace files ONLY via <{ws_write(f)}>content<{/ws_write}>."
    ],
    "immutable": True
}

def ensure_dirs():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    WS_DIR.mkdir(parents=True, exist_ok=True)
    (WS_DIR / "default").mkdir(exist_ok=True)

def load_json(path, default=None):
    if not Path(path).exists():
        return default
    try:
        c = Path(path).read_text(encoding="utf-8").strip()
        return json.loads(c) if c else default
    except Exception:
        return default

def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def init_config():
    ensure_dirs()
    if not CONFIG_PATH.exists():
        save_json(CONFIG_PATH, {"default_provider": "nvidia", "providers": PROVIDERS, "default_interface": "cli"})
    if not DNA_PATH.exists():
        save_json(DNA_PATH, DEFAULT_DNA)
    if not MEMORY_PATH.exists():
        save_json(MEMORY_PATH, {"memories": [], "total_chars": 0})
    if not HISTORY_PATH.exists():
        save_json(HISTORY_PATH, {"compressed_3": "", "ultra_10": "", "recent": [], "total_chars": 0})

def setup_wizard():
    cfg = load_json(CONFIG_PATH, {"default_provider": "nvidia", "providers": PROVIDERS, "default_interface": "cli"})
    if cfg is None:
        cfg = {"default_provider": "nvidia", "providers": PROVIDERS, "default_interface": "cli"}
    providers = cfg.get("providers", {})
    needs = any("YOUR_" in providers.get(p, {}).get("api_key", "") for p in PROVIDERS)
    if not needs:
        return cfg

    print("\033[1;36m\n  SYNAPSE v3.0.0 - Setup\033[0m")
    print("  Configure providers. Enter to skip.\n")
    for name in ["nvidia", "openrouter", "cohere"]:
        cur = providers.get(name, {})
        if "YOUR_" in cur.get("api_key", ""):
            k = input(f"  \033[1m{name.upper()}\033[0m Key (skip: Enter): ").strip()
            if k:
                cur["api_key"] = k
                m = input(f"  \033[1m{name.upper()}\033[0m Model (default: {cur.get('model','')}): ").strip()
                if m:
                    cur["model"] = m
                providers[name] = cur
                print(f"  \033[32m[✓] {name} set\033[0m\n")
            else:
                print(f"  \033[33m[~] {name} skipped\033[0m\n")
    ok = [p for p in PROVIDERS if "YOUR_" not in providers.get(p, {}).get("api_key", "")]
    cfg["default_provider"] = ok[0] if ok else "nvidia"
    cfg["providers"] = providers
    iface = input("  Default Interface [cli/gui]: ").strip().lower()
    cfg["default_interface"] = iface if iface in ("cli", "gui") else "cli"
    save_json(CONFIG_PATH, cfg)
    print("\033[32m  [✓] Saved to ~/synapse/config.json\033[0m\n")
    return cfg
