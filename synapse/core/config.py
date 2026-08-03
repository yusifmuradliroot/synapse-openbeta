import json
from pathlib import Path

BASE_DIR = Path.home() / "synapse"
CONTEXT_PATH = BASE_DIR / "context.json"
DNA_PATH = BASE_DIR / "dna.json"
MEMORY_PATH = BASE_DIR / "memory.json"
HISTORY_PATH = BASE_DIR / "history.json"
WS_DIR = BASE_DIR / "workspaces"

DEFAULT_CONTEXT = {
    "version": "4.0.0",
    "interface": "gui",
    "active_provider": "nvidia",
    "providers": {
        "nvidia": {"api_key": "YOUR_NVIDIA_KEY", "model": "nvidia/nemotron-3-ultra-550b-a55b", "api_url": "https://integrate.api.nvidia.com/v1/chat/completions"},
        "openrouter": {"api_key": "YOUR_OPENROUTER_KEY", "model": "google/gemini-2.0-flash-001", "api_url": "https://openrouter.ai/api/v1/chat/completions"},
        "cohere": {"api_key": "YOUR_COHERE_KEY", "model": "command-r-08-2024", "api_url": "https://api.cohere.com/v1/chat"}
    },
    "modes": {
        "chat": {"temperature": 0.5, "top_p": 0.9, "max_tokens": 2048, "reasoning_budget": 1024, "system_hint": "Short, direct answers. Max 5 sentences."},
        "code": {"temperature": 0.1, "top_p": 0.95, "max_tokens": 4096, "reasoning_budget": 2048, "system_hint": "Output ONLY code. No explanations unless critical."},
        "agent": {"temperature": 0.7, "top_p": 0.95, "max_tokens": 8192, "reasoning_budget": 4096, "system_hint": "Full autonomous. Plan, execute, verify, fix."}
    },
    "agent": {"max_loops": 25, "auto_verify": True, "plan_first": True, "max_cmd_timeout": 30},
    "context": {"max_messages": 15, "max_code_files": 10, "auto_summarize": True},
    "gui": {"theme": "dark", "font_size": 14, "show_thinking": True, "show_tokens": True}
}

DEFAULT_DNA = {
    "core_directives": ["DIRECT MODE: No greetings, filler, or meta-commentary.", "Provide only exact answers or code.", "Use markdown code blocks.", "Be strictly relevant and concise."],
    "response_rules": ["Save facts with <{mem}>fact<{mem}>.", "Workspace files ONLY via <{ws_write(f)}>content<{/ws_write}>."],
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

def load_context():
    ctx = load_json(CONTEXT_PATH, None)
    if ctx is None:
        ctx = DEFAULT_CONTEXT.copy()
        save_json(CONTEXT_PATH, ctx)
    for k, v in DEFAULT_CONTEXT.items():
        if k not in ctx:
            ctx[k] = v
    return ctx

def save_context(ctx):
    save_json(CONTEXT_PATH, ctx)

def init_config():
    ensure_dirs()
    load_context()
    if not DNA_PATH.exists():
        save_json(DNA_PATH, DEFAULT_DNA)
    if not MEMORY_PATH.exists():
        save_json(MEMORY_PATH, {"memories": [], "total_chars": 0})
    if not HISTORY_PATH.exists():
        save_json(HISTORY_PATH, {"compressed_3": "", "ultra_10": "", "recent": [], "total_chars": 0})

def setup_wizard():
    ctx = load_context()
    providers = ctx.get("providers", {})
    needs = any("YOUR_" in providers.get(p, {}).get("api_key", "") for p in providers)
    if not needs:
        return ctx
    print("\033[1;36m\n  SYNAPSE v4.0.0 - Setup\033[0m\n")
    for name in providers:
        cur = providers[name]
        if "YOUR_" in cur.get("api_key", ""):
            k = input("  \033[1m" + name.upper() + "\033[0m Key (skip: Enter): ").strip()
            if k:
                cur["api_key"] = k
                print("  \033[32m[OK]\033[0m")
            else:
                print("  \033[33m[~] skipped\033[0m")
    ok = [p for p in providers if "YOUR_" not in providers[p].get("api_key", "")]
    if ok:
        ctx["active_provider"] = ok[0]
    save_context(ctx)
    return ctx
