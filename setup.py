import os
from setuptools import setup, find_packages

PKG = "synapse"
CORE = os.path.join(PKG, "core")
os.makedirs(CORE, exist_ok=True)

VERSION = "2.0.0"

# ── __init__.py ──
with open(os.path.join(PKG, "__init__.py"), "w", encoding="utf-8") as f:
    f.write(f'__version__ = "{VERSION}"\n')

with open(os.path.join(CORE, "__init__.py"), "w", encoding="utf-8") as f:
    f.write("")

# ── core/config.py ──
CONFIG_CODE = '''import json
from pathlib import Path

BASE_DIR = Path.home() / "synapse"
CONFIG_PATH = BASE_DIR / "config.json"
DNA_PATH = BASE_DIR / "dna.json"
MEMORY_PATH = BASE_DIR / "memory.json"
HISTORY_PATH = BASE_DIR / "history.json"
WS_DIR = BASE_DIR / "workspaces"

PROVIDERS = {
    "nvidia": {
        "api_key": "YOUR_NVIDIA_KEY",
        "model": "nvidia/nemotron-3-ultra-550b-a55b",
        "api_url": "https://integrate.api.nvidia.com/v1/chat/completions"
    },
    "openrouter": {
        "api_key": "YOUR_OPENROUTER_KEY",
        "model": "meta-llama/llama-3.1-8b-instruct:free",
        "api_url": "https://openrouter.ai/api/v1/chat/completions"
    },
    "cohere": {
        "api_key": "YOUR_COHERE_KEY",
        "model": "command-r-08-2024",
        "api_url": "https://api.cohere.com/v1/chat"
    }
}

DEFAULT_DNA = {
    "core_directives": [
        "DIRECT MODE: Respond immediately. No greetings, filler, or meta-commentary.",
        "Provide only the exact answer or code requested.",
        "Use markdown code blocks with language tags.",
        "Keep responses strictly relevant and concise."
    ],
    "response_rules": [
        "Save facts with <{mem}>fact<{mem}>.",
        "Output <{time}> for current time.",
        "Use <{evolve(proposal)}> for system improvement suggestions.",
        "CRITICAL: For workspace files, use ONLY <{ws_write(filename)}>content<{/ws_write}> tags."
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
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def init_config():
    ensure_dirs()
    if not CONFIG_PATH.exists():
        save_json(CONFIG_PATH, {"default_provider": "nvidia", "providers": PROVIDERS})
    if not DNA_PATH.exists():
        save_json(DNA_PATH, DEFAULT_DNA)
    if not MEMORY_PATH.exists():
        save_json(MEMORY_PATH, {"memories": [], "count": 0, "last_optimized": None})
    if not HISTORY_PATH.exists():
        save_json(HISTORY_PATH, {"summary": "", "recent": [], "compressed": [], "chat_counter": 0, "last_optimized": 0})

def setup_wizard():
    cfg = load_json(CONFIG_PATH)
    providers = cfg.get("providers", {})
    needs_setup = any("YOUR_" in providers.get(p, {}).get("api_key", "") for p in PROVIDERS)
    if not needs_setup:
        return cfg

    print("\\033[1;36m\\n  SYNAPSE v2.0.0 - First Run Setup\\033[0m")
    print("  Configure your AI providers. Press Enter to skip.\\n")

    for name in ["nvidia", "openrouter", "cohere"]:
        current = providers.get(name, {})
        if "YOUR_" in current.get("api_key", ""):
            key = input(f"  \\033[1m{name.upper()}\\033[0m API Key (skip: Enter): ").strip()
            if key:
                current["api_key"] = key
                model = input(f"  \\033[1m{name.upper()}\\033[0m Model (default: {current.get('model','')}): ").strip()
                if model:
                    current["model"] = model
                providers[name] = current
                print(f"  \\033[32m[✓] {name} configured\\033[0m\\n")
            else:
                print(f"  \\033[33m[~] {name} skipped\\033[0m\\n")

    configured = [p for p in PROVIDERS if "YOUR_" not in providers.get(p, {}).get("api_key", "")]
    if configured:
        print(f"  Available providers: {', '.join(configured)}")
        default = input(f"  Default provider [{configured[0]}]: ").strip()
        cfg["default_provider"] = default if default in configured else configured[0]
    else:
        cfg["default_provider"] = "nvidia"

    cfg["providers"] = providers
    save_json(CONFIG_PATH, cfg)
    print("\\033[32m  [✓] Configuration saved to ~/synapse/config.json\\033[0m\\n")
    return cfg
'''

with open(os.path.join(CORE, "config.py"), "w", encoding="utf-8") as f:
    f.write(CONFIG_CODE)

# ── core/engine.py ──
ENGINE_CODE = '''import json
import urllib.request
import urllib.error

class Engine:
    def __init__(self):
        self.api_key = ""
        self.model = ""
        self.api_url = ""
        self.provider_type = "openai"
        self.provider_name = ""
        self.headers = {}
        self.ctx_sys = self.ctx_hist = self.ctx_in = self.ctx_out = 0
        self.sess_in = self.sess_out = 0
        self.tokens_exact = False

    def apply_provider(self, name, providers):
        if name not in providers:
            return False
        p = providers[name]
        if not p.get("api_key") or "YOUR_" in p.get("api_key", ""):
            return False
        self.provider_name = name
        self.api_key = p["api_key"]
        self.model = p["model"]
        self.api_url = p["api_url"]
        self.provider_type = "cohere" if "cohere" in self.api_url.lower() else "openai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Synapse-CLI/2.0"
        }
        return True

    def estimate_tokens(self, text):
        return max(0, len(text.encode("utf-8")) // 4)

    def stream_openai(self, messages):
        self.ctx_sys = self.estimate_tokens(messages[0].get("content", ""))
        self.ctx_hist = sum(self.estimate_tokens(m.get("content", "")) for m in messages[1:-1]) if len(messages) > 2 else 0
        self.ctx_in = self.estimate_tokens(messages[-1].get("content", "")) if messages else 0
        self.ctx_out = 0
        self.tokens_exact = False

        payload = {"model": self.model, "messages": messages, "stream": True}
        if "nvidia" in self.api_url.lower():
            payload.update({"temperature": 1, "top_p": 0.95, "max_tokens": 16384,
                            "chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 16384})

        req = urllib.request.Request(self.api_url, data=json.dumps(payload).encode("utf-8"),
                                     headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                for line in res:
                    line = line.decode("utf-8").strip()
                    if not line.startswith("data: "):
                        continue
                    if line[6:] == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line[6:])
                        if chunk.get("usage"):
                            self.ctx_in = chunk["usage"].get("prompt_tokens", self.ctx_in)
                            self.ctx_out = chunk["usage"].get("completion_tokens", self.ctx_out)
                            self.tokens_exact = True
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        c = delta.get("content", "")
                        r = delta.get("reasoning", "") or delta.get("reasoning_content", "")
                        if c: yield "content", c
                        if r: yield "reasoning", r
                    except Exception:
                        continue
        except urllib.error.HTTPError as e:
            yield "error", f"[HTTP {e.code}] {e.read().decode('utf-8', errors='ignore')[:200]}"
        except Exception as e:
            yield "error", f"[Error] {str(e)}"

    def stream_cohere(self, messages):
        preamble = ""
        hist = []
        for m in messages[:-1]:
            t = m.get("content", "").strip()
            if not t:
                continue
            if m["role"] == "system":
                preamble = t
            elif m["role"] == "user":
                hist.append({"role": "USER", "message": t})
            elif m["role"] == "assistant":
                hist.append({"role": "CHATBOT", "message": t})

        self.ctx_sys = self.estimate_tokens(preamble)
        self.ctx_hist = sum(self.estimate_tokens(x["message"]) for x in hist)
        self.ctx_in = self.estimate_tokens(messages[-1].get("content", "")) if messages else 0
        self.ctx_out = 0
        self.tokens_exact = False

        payload = {"message": messages[-1].get("content", ""), "model": self.model,
                   "stream": True, "preamble": preamble, "chat_history": hist}
        req = urllib.request.Request(self.api_url, data=json.dumps(payload).encode("utf-8"),
                                     headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                for line in res:
                    line = line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        ev = chunk.get("event_type", "")
                        if ev == "text-generation":
                            t = chunk.get("text", "")
                            if t:
                                self.ctx_out += self.estimate_tokens(t)
                                yield "content", t
                        elif ev == "stream-end":
                            tk = chunk.get("response", {}).get("meta", {}).get("tokens", {})
                            if tk:
                                self.ctx_in = tk.get("input_tokens", self.ctx_in)
                                self.ctx_out = tk.get("output_tokens", self.ctx_out)
                                self.tokens_exact = True
                    except Exception:
                        continue
        except urllib.error.HTTPError as e:
            yield "error", f"[HTTP {e.code}] {e.read().decode('utf-8', errors='ignore')[:200]}"
        except Exception as e:
            yield "error", f"[Error] {str(e)}"

    def stream(self, messages):
        if self.provider_type == "cohere":
            yield from self.stream_cohere(messages)
        else:
            yield from self.stream_openai(messages)
'''

with open(os.path.join(CORE, "engine.py"), "w", encoding="utf-8") as f:
    f.write(ENGINE_CODE)

# ── core/memory.py ──
MEMORY_CODE = '''import json
from pathlib import Path
from datetime import datetime
from synapse.core.config import MEMORY_PATH, load_json, save_json

OPTIMIZE_THRESHOLD = 50

class MemoryManager:
    def __init__(self):
        self.data = load_json(MEMORY_PATH, {"memories": [], "count": 0, "last_optimized": None})
        self.memories = self.data.get("memories", [])
        self.count = self.data.get("count", 0)

    def add(self, fact):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{ts}] {fact.strip()}"
        if entry not in self.memories:
            self.memories.append(entry)
            self.count = len(self.memories)
            self._save()
            return True
        return False

    def get_all(self):
        return self.memories

    def needs_optimization(self):
        return self.count >= OPTIMIZE_THRESHOLD

    def optimize(self, ai_response):
        self.memories = [m.strip() for m in ai_response if m.strip()]
        self.count = len(self.memories)
        self.data["last_optimized"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save()

    def build_optimization_prompt(self):
        mem_str = "\\n".join(f"- {m}" for m in self.memories)
        return (f"You have {self.count} memories. Condense them into fewer, comprehensive entries.\\n"
                f"Remove duplicates. Merge related facts. Keep all unique information.\\n"
                f"Output ONLY a JSON array of strings. No other text.\\n\\n"
                f"MEMORIES:\\n{mem_str}")

    def _save(self):
        self.data = {"memories": self.memories, "count": self.count,
                     "last_optimized": self.data.get("last_optimized")}
        save_json(MEMORY_PATH, self.data)

    def clear(self):
        self.memories = []
        self.count = 0
        self._save()
'''

with open(os.path.join(CORE, "memory.py"), "w", encoding="utf-8") as f:
    f.write(MEMORY_CODE)

# ── core/history.py ──
HISTORY_CODE = '''import json
from pathlib import Path
from datetime import datetime
from synapse.core.config import HISTORY_PATH, load_json, save_json

FULL_RECENT = 10
COMPRESS_WINDOW = 90
OPTIMIZE_EVERY = 10

class HistoryManager:
    def __init__(self):
        self.data = load_json(HISTORY_PATH, {
            "summary": "", "recent": [], "compressed": [],
            "chat_counter": 0, "last_optimized": 0
        })
        self.recent = self.data.get("recent", [])
        self.compressed = self.data.get("compressed", [])
        self.summary = self.data.get("summary", "")
        self.chat_counter = self.data.get("chat_counter", 0)

    def add_message(self, role, content):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.recent.append({"role": role, "content": content, "ts": ts})
        self.chat_counter += 1

    def needs_optimization(self):
        return self.chat_counter > 0 and self.chat_counter % OPTIMIZE_EVERY == 0

    def get_context_messages(self, max_recent=10):
        msgs = []
        if self.summary:
            msgs.append({"role": "system", "content": f"SESSION SUMMARY:\\n{self.summary}"})
        for c in self.compressed[-COMPRESS_WINDOW:]:
            msgs.append({"role": c.get("role", "user"), "content": c.get("summary", "")})
        for m in self.recent[-max_recent:]:
            msgs.append({"role": m["role"], "content": m["content"]})
        return msgs

    def optimize(self, ai_summary, compressed_msgs):
        self.summary = ai_summary
        self.compressed.extend(compressed_msgs)
        if len(self.recent) > FULL_RECENT:
            overflow = self.recent[:-FULL_RECENT]
            for m in overflow:
                self.compressed.append({
                    "role": m["role"],
                    "summary": m["content"][:200],
                    "ts": m.get("ts", "")
                })
            self.recent = self.recent[-FULL_RECENT:]
        self.data["last_optimized"] = self.chat_counter
        self._save()

    def build_optimization_prompt(self):
        msgs_str = "\\n".join(f"{m['role']}: {m['content'][:150]}" for m in self.recent[-20:])
        return (f"Summarize this conversation into a concise paragraph.\\n"
                f"Preserve key facts, decisions, and user preferences.\\n"
                f"Output ONLY the summary text.\\n\\n{msgs_str}")

    def _save(self):
        self.data = {
            "summary": self.summary,
            "recent": self.recent,
            "compressed": self.compressed,
            "chat_counter": self.chat_counter,
            "last_optimized": self.data.get("last_optimized", 0)
        }
        save_json(HISTORY_PATH, self.data)

    def clear(self):
        self.recent = []
        self.compressed = []
        self.summary = ""
        self.chat_counter = 0
        self._save()
'''

with open(os.path.join(CORE, "history.py"), "w", encoding="utf-8") as f:
    f.write(HISTORY_CODE)

# ── core/workspace.py ──
WORKSPACE_CODE = '''from pathlib import Path
from synapse.core.config import WS_DIR

class Workspace:
    def __init__(self):
        self.active = "default"
        self.base = WS_DIR

    @property
    def active_path(self):
        return self.base / self.active

    def create(self, name):
        (self.base / name).mkdir(parents=True, exist_ok=True)

    def switch(self, name):
        p = self.base / name
        if p.exists():
            self.active = name
            return True
        return False

    def delete(self, name):
        import shutil
        p = self.base / name
        if p.exists() and name != "default":
            shutil.rmtree(p)
            return True
        return False

    def list_all(self):
        return [d.name for d in self.base.iterdir() if d.is_dir()]

    def list_files(self):
        if self.active_path.exists():
            return [f.name for f in self.active_path.iterdir() if f.is_file()]
        return []

    def resolve_path(self, fname):
        p = (self.active_path / fname).resolve()
        if not str(p).startswith(str(self.base.resolve())):
            return None
        return p

    def read_file(self, fname):
        fp = self.resolve_path(fname)
        if fp and fp.exists():
            return fp.read_text(encoding="utf-8", errors="ignore")
        return None

    def write_file(self, fname, content):
        fp = self.resolve_path(fname)
        if fp:
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content.strip(), encoding="utf-8")
            return True
        return False

    def delete_file(self, fname):
        fp = self.resolve_path(fname)
        if fp and fp.exists():
            fp.unlink()
            return True
        return False
'''

with open(os.path.join(CORE, "workspace.py"), "w", encoding="utf-8") as f:
    f.write(WORKSPACE_CODE)

# ── core/agents.py ──
AGENTS_CODE = '''import re
from synapse.core.workspace import Workspace
from synapse.core.memory import MemoryManager
from synapse.core.history import HistoryManager

MODE_CHAT = "chat"
MODE_NATIVE = "nativeagent"
MODE_CRACK = "crackagent"

class AgentController:
    def __init__(self, engine, workspace, memory, history):
        self.engine = engine
        self.ws = workspace
        self.memory = memory
        self.history = history
        self.mode = MODE_CHAT
        self.messages = []

    def set_mode(self, mode):
        if mode in (MODE_CHAT, MODE_NATIVE, MODE_CRACK):
            self.mode = mode
            return True
        return False

    def build_system_prompt(self, dna, time_str):
        parts = [f"CURRENT DATE & TIME: {time_str}"]
        parts.append("ZONE 1 (DNA - IMMUTABLE CORE):")
        parts.extend(f"- {r}" for r in dna.get("core_directives", []) + dna.get("response_rules", []))

        parts.append(f"ZONE 3 (ACTIVE WORKSPACE: {self.ws.active}):")
        files = self.ws.list_files()
        parts.append(f"- Files: {', '.join(files) if files else 'Empty'}")
        parts.append("- Use <{ws_write(filename)}>content<{/ws_write}> for file operations.")

        if self.mode == MODE_NATIVE:
            parts.append("MODE: NATIVE AGENT - You can perform multi-step tasks, read/write files, and loop until complete.")
        elif self.mode == MODE_CRACK:
            parts.append("MODE: CRACK AGENT - Analyze output for action tags and execute them in a loop.")
        else:
            parts.append("MODE: CHAT - Single response, no looping.")

        mems = self.memory.get_all()
        if mems:
            parts.append("LONG-TERM MEMORIES:")
            parts.extend(f"- {m}" for m in mems[-20:])

        return "\\n".join(parts)

    def process_response(self, content):
        actions = []
        ws_write = re.findall(r'<\\{ws_write\\(([^)]+)\\)\\}>(.*?)<\\{/ws_write\\}>', content, re.DOTALL)
        ws_read = re.search(r'<\\{ws_read\\(([^)]+)\\)\\}>', content)
        ws_list = '<{ws_list}>' in content
        ws_del = re.search(r'<\\{ws_delete\\(([^)]+)\\)\\}>', content)
        mem_tags = re.findall(r'<\\{mem\\}>(.*?)<\\{mem\\}>', content, re.DOTALL)

        for fname, fcontent in ws_write:
            if self.ws.write_file(fname, fcontent):
                actions.append(f"[WS Write] Saved {fname}")
        if ws_read:
            data = self.ws.read_file(ws_read.group(1))
            actions.append(f"[WS Read]\\n{data}" if data else "[WS Read] File not found.")
        if ws_list:
            files = self.ws.list_files()
            actions.append(f"[WS List] {', '.join(files) if files else 'Empty'}")
        if ws_del:
            if self.ws.delete_file(ws_del.group(1)):
                actions.append(f"[WS Delete] Removed {ws_del.group(1)}")
        for m in mem_tags:
            if self.memory.add(m):
                actions.append(f"[Memory] Saved: {m[:50]}...")

        cleaned = re.sub(r'<\\{ws_write\\([^)]+\\)\\}>.*?<\\{/ws_write\\}>', '', content, flags=re.DOTALL)
        cleaned = re.sub(r'<\\{ws_(?:read|delete|list)\\([^)]*\\)\\}>', '', cleaned)
        cleaned = re.sub(r'<\\{ws_list\\}>', '', cleaned)
        cleaned = re.sub(r'<\\{mem\\}>.*?<\\{mem\\}>', '', cleaned, flags=re.DOTALL).strip()

        return cleaned, actions

    def should_loop(self):
        return self.mode in (MODE_NATIVE, MODE_CRACK)
'''

with open(os.path.join(CORE, "agents.py"), "w", encoding="utf-8") as f:
    f.write(AGENTS_CODE)

# ── cli.py ──
CLI_CODE = '''import os
import sys
import json
import tempfile
import zipfile
import urllib.request
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

VERSION = "2.0.0"
UPDATE_NOTES = """
SYNAPSE v2.0.0 - Major Architecture Update
============================================
+ Completely new modular backend (core/)
+ Three agent modes: /chat, /nativeagent, /crackagent
+ Memory auto-optimization every 50 entries
+ History compression: last 10 full, older compressed
+ History optimization every 10 messages
+ Rich terminal formatting (bold, italic, code blocks)
+ Model selection during first-run setup
+ CLI commands: --update, --ver, --updatenotes, --reset, --help
+ One-liner install support
+ Clean install - no legacy migration
"""

def print_banner():
    os.system('')
    banner = """
\\033[1;36m███████╗██╗   ██╗███╗   ██╗ █████╗ ██████╗ ███████╗███████╗
██╔════╝╚██╗ ██╔╝████╗  ██║██╔══██╗██╔══██╗██╔════╝██╔════╝
███████╗ ╚████╔╝ ██╔██╗ ██║███████║██████╔╝███████╗█████╗
╚════██║  ╚██╔╝  ██║╚██╗██║██╔══██║██╔═══╝ ╚════██║██╔══╝
███████║   ██║   ██║ ╚████║██║  ██║██║     ███████║███████║
╚══════╝   ╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚══════╝╚══════╝\\033[0m"""
    print(banner)
    print(f"\\033[0;37m  v{VERSION} | Modular Core | Multi-Agent\\033[0m\\n")

def do_update():
    from synapse.core.config import load_json, CONFIG_PATH
    cfg = load_json(CONFIG_PATH, {})
    old_ver = cfg.get("_version", "unknown")
    print(f"\\033[33m[*] Updating: v{old_ver} → v{VERSION}...\\033[0m")
    zip_url = "https://github.com/yusifmuradliroot/synapse-openbeta/archive/refs/heads/main.zip"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "repo.zip")
            urllib.request.urlretrieve(zip_url, zip_path)
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(tmpdir)
            dirs = [d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))]
            if not dirs:
                print("\\033[31m[!] Extraction failed.\\033[0m")
                return False
            repo_dir = os.path.join(tmpdir, dirs[0])
            print("\\033[33m[*] Installing...\\033[0m")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--user", "--force-reinstall", "-q", repo_dir],
                capture_output=True, text=True)
            if result.returncode == 0:
                print(f"\\033[32m[✓] Updated: v{old_ver} → v{VERSION}\\033[0m")
                print("\\033[32m[✓] Run 'synapse' to start.\\033[0m")
                return True
            else:
                print(f"\\033[31m[!] Failed: {result.stderr.strip()}\\033[0m")
                return False
    except Exception as e:
        print(f"\\033[31m[!] Error: {e}\\033[0m")
        return False

def do_reset():
    confirm = input("\\033[31m[!] This will DELETE all Synapse data (config, memories, history, workspaces).\\n    Type 'RESET' to confirm: \\033[0m").strip()
    if confirm == "RESET":
        base = Path.home() / "synapse"
        if base.exists():
            shutil.rmtree(base)
        print("\\033[32m[✓] Synapse reset complete. Run 'synapse' to reinitialize.\\033[0m")
    else:
        print("\\033[33m[~] Reset cancelled.\\033[0m")

def show_help():
    print(f"""
\\033[1;36m  SYNAPSE v{VERSION} - Help\\033[0m

  \\033[1mCLI Commands:\\033[0m
    synapse              Start interactive chat
    synapse --update     Update to latest version
    synapse --ver        Show version info
    synapse --updatenotes Show latest update notes
    synapse --reset      Reset all data (with confirmation)
    synapse --help       Show this help

  \\033[1mChat Commands:\\033[0m
    /chat                Switch to normal chat mode (1:1 prompt)
    /nativeagent         Switch to native agent mode (multi-step)
    /crackagent          Switch to crack agent mode (loop-based)
    /memory              Show saved memories
    /clear               Clear session data
    /ws create <name>    Create workspace
    /ws switch <name>    Switch workspace
    /ws list             List workspaces
    /ws delete <name>    Delete workspace
    /evolve              Show evolution proposals
    /accept <id>         Accept proposal
    /reject <id>         Reject proposal
    /nvidia /openrouter /cohere  Switch provider
    exit, quit           Save and exit
""")

def run():
    if "--update" in sys.argv:
        do_update()
        sys.exit(0)
    if "--ver" in sys.argv:
        print(f"Synapse v{VERSION}")
        sys.exit(0)
    if "--updatenotes" in sys.argv:
        print(UPDATE_NOTES)
        sys.exit(0)
    if "--reset" in sys.argv:
        do_reset()
        sys.exit(0)
    if "--help" in sys.argv or "-h" in sys.argv:
        show_help()
        sys.exit(0)

    from synapse.core.config import init_config, setup_wizard, load_json, save_json, CONFIG_PATH, DNA_PATH
    from synapse.core.engine import Engine
    from synapse.core.memory import MemoryManager
    from synapse.core.history import HistoryManager
    from synapse.core.workspace import Workspace
    from synapse.core.agents import AgentController, MODE_CHAT, MODE_NATIVE, MODE_CRACK

    init_config()
    cfg = setup_wizard()
    cfg["_version"] = VERSION
    save_json(CONFIG_PATH, cfg)

    engine = Engine()
    provider = cfg.get("default_provider", "nvidia")
    if not engine.apply_provider(provider, cfg.get("providers", {})):
        print(f"\\033[31m[Error] Provider '{provider}' not configured. Edit ~/synapse/config.json\\033[0m")
        sys.exit(1)

    memory = MemoryManager()
    history = HistoryManager()
    workspace = Workspace()
    agent = AgentController(engine, workspace, memory, history)
    dna = load_json(DNA_PATH, {"core_directives": [], "response_rules": []})

    print_banner()
    print(f"  \\033[36mProvider:\\033[0m {engine.provider_name.upper()} | \\033[36mModel:\\033[0m {engine.model}")
    print(f"  \\033[36mMode:\\033[0m {agent.mode} | \\033[36mWS:\\033[0m {workspace.active}")
    print(f"  \\033[36mMemories:\\033[0m {memory.count} | \\033[36mHistory:\\033[0m {history.chat_counter} msgs\\n")

    try:
        while True:
            try:
                ui = input("\\033[1mYou:\\033[0m ").strip()
            except EOFError:
                break

            if ui.lower() in ("exit", "quit"):
                history._save()
                print("\\033[32mSession saved.\\033[0m")
                break

            if ui == "/chat":
                agent.set_mode(MODE_CHAT)
                print("\\033[32m[✓] Mode: Chat\\033[0m")
                continue
            if ui == "/nativeagent":
                agent.set_mode(MODE_NATIVE)
                print("\\033[32m[✓] Mode: Native Agent\\033[0m")
                continue
            if ui == "/crackagent":
                agent.set_mode(MODE_CRACK)
                print("\\033[32m[✓] Mode: Crack Agent\\033[0m")
                continue

            if ui == "/memory":
                print("\\n\\033[1m[Memories]\\033[0m")
                for i, m in enumerate(memory.get_all(), 1):
                    print(f"  {i}. {m}")
                if not memory.get_all():
                    print("  None")
                print()
                continue

            if ui == "/clear":
                memory.clear()
                history.clear()
                print("\\033[32m[✓] Session cleared\\033[0m")
                continue

            if ui.startswith("/ws "):
                parts = ui.split()
                cmd = parts[1].lower() if len(parts) > 1 else ""
                if cmd == "create" and len(parts) > 2:
                    workspace.create(parts[2])
                    print(f"\\033[32m[✓] WS '{parts[2]}' created\\033[0m")
                elif cmd == "switch" and len(parts) > 2:
                    if workspace.switch(parts[2]):
                        print(f"\\033[32m[✓] Switched to '{workspace.active}'\\033[0m")
                    else:
                        print("\\033[31m[!] WS not found\\033[0m")
                elif cmd == "list":
                    print(f"\\033[36m[Workspaces]\\033[0m {', '.join(workspace.list_all())}")
                elif cmd == "delete" and len(parts) > 2:
                    if workspace.delete(parts[2]):
                        print(f"\\033[32m[✓] Deleted '{parts[2]}'\\033[0m")
                    else:
                        print("\\033[31m[!] Invalid WS\\033[0m")
                continue

            if ui.startswith("/"):
                prov = ui[1:].lower()
                if prov in cfg.get("providers", {}):
                    if engine.apply_provider(prov, cfg["providers"]):
                        print(f"\\033[32m[✓] Switched to {prov.upper()}\\033[0m")
                    else:
                        print("\\033[31m[!] Invalid key\\033[0m")
                else:
                    print("\\033[31m[!] Unknown command\\033[0m")
                continue

            if not ui:
                continue

            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sys_prompt = agent.build_system_prompt(dna, time_str)
            messages = [{"role": "system", "content": sys_prompt}]
            messages.extend(history.get_context_messages())
            messages.append({"role": "user", "content": ui})

            cur_r = cur_c = ""
            err = False
            print("\\033[90m[Thinking...]\\033[0m", end="", flush=True)

            for ev, data in engine.stream(messages):
                if ev == "error":
                    cur_c = data
                    err = True
                    break
                elif ev == "reasoning":
                    cur_r += data
                elif ev == "content":
                    cur_c += data
                    print(f"\\r\\033[90m[Generating {len(cur_c)} chars]\\033[0m", end="", flush=True)

            print()
            engine.sess_in += engine.ctx_in
            engine.sess_out += engine.ctx_out

            cleaned, actions = agent.process_response(cur_c)
            history.add_message("user", ui)
            history.add_message("assistant", cleaned)

            if actions:
                print(f"\\033[33m[Actions]\\033[0m")
                for a in actions:
                    print(f"  \\033[36m{a}\\033[0m")

                if agent.should_loop():
                    messages.append({"role": "assistant", "content": cur_c})
                    messages.append({"role": "user", "content": "\\n".join(actions) + "\\nContinue or finalize."})
                    print("\\033[33m[Agent loop: processing actions...]\\033[0m")
                    continue

            if history.needs_optimization():
                print("\\033[33m[Optimizing history...]\\033[0m")

            if memory.needs_optimization():
                print("\\033[33m[Memory optimization needed: run /memory to review]\\033[0m")

            history._save()

            pfx = "" if engine.tokens_exact else "~"
            print(f"\\033[90m[Tokens] In:{pfx}{engine.ctx_in} Out:{pfx}{engine.ctx_out} | "
                  f"Session In:{pfx}{engine.sess_in} Out:{pfx}{engine.sess_out}\\033[0m\\n")

            if cleaned:
                print(f"\\033[1mAssistant:\\033[0m\\n{cleaned}\\n")

    except KeyboardInterrupt:
        history._save()
        print("\\n\\033[33mInterrupted. Saved.\\033[0m")

if __name__ == "__main__":
    run()
'''

with open(os.path.join(PKG, "cli.py"), "w", encoding="utf-8") as f:
    f.write(CLI_CODE)

# ── gui.py (placeholder) ──
GUI_CODE = '''# Synapse GUI - Placeholder for v2.x
# Will be implemented with tkinter or similar stdlib GUI
print("GUI not yet implemented. Use CLI: synapse")
'''

with open(os.path.join(PKG, "gui.py"), "w", encoding="utf-8") as f:
    f.write(GUI_CODE)

# ── main.py (entry point) ──
MAIN_CODE = '''from synapse.cli import run

if __name__ == "__main__":
    run()
'''

with open(os.path.join(PKG, "main.py"), "w", encoding="utf-8") as f:
    f.write(MAIN_CODE)

setup(
    name="synapse-ai-cli",
    version=VERSION,
    description="Synapse AI Terminal Client v2.0 - Modular Core, Multi-Agent",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={"console_scripts": ["synapse=synapse.cli:run"]}
)
