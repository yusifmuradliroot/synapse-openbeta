import os
import sys
from setuptools import setup

PKG_DIR = "synapse"
os.makedirs(PKG_DIR, exist_ok=True)

with open(os.path.join(PKG_DIR, "__init__.py"), "w", encoding="utf-8") as f:
    f.write("# Synapse AI CLI\n")

CLI_CODE = '''
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
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    if not MEMORY_PATH.exists():
        MEMORY_PATH.write_text("[]", encoding="utf-8")
    if not HISTORY_PATH.exists():
        HISTORY_PATH.write_text(json.dumps({"summary": "", "recent": [], "chat_counter": 0}, indent=2), encoding="utf-8")

def run():
    init_workspace()
    if not CONFIG_PATH.exists():
        sys.exit("[Error] config.json missing.")
    cfg = CONFIG_PATH.read_text(encoding="utf-8").strip()
    if not cfg:
        sys.exit("[Error] config.json is empty.")
    os.chdir(WORKSPACE_DIR)
    from synapse.main import TerminalChat
    TerminalChat(base_dir=WORKSPACE_DIR).run()

if __name__ == "__main__":
    run()
'''

with open(os.path.join(PKG_DIR, "cli.py"), "w", encoding="utf-8") as f:
    f.write(CLI_CODE.strip() + "\n")

MAIN_CODE = '''
import json
import sys
import os
import re
import platform
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stdin.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

BANNER = """
\\033[1;36m███████╗██╗   ██╗███╗   ██╗ █████╗ ██████╗ ███████╗███████╗
██╔════╝╚██╗ ██╔╝████╗  ██║██╔══██╗██╔══██╗██╔════╝██╔════╝
███████╗ ╚████╔╝ ██╔██╗ ██║███████║██████╔╝███████╗█████╗  
╚════██║  ╚██╔╝  ██║╚██╗██║██╔══██║██╔═══╝ ╚════██║██╔══╝  
███████║   ██║   ██║ ╚████║██║  ██║██║     ███████║███████║
╚══════╝   ╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚══════╝╚══════╝\\033[0m
"""

class TerminalChat:
    def __init__(self, base_dir=None, max_active_history=12):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.config_path = self.base_dir / "config.json"
        self.memory_path = self.base_dir / "memory.json"
        self.history_path = self.base_dir / "history.json"
        self.platform_name = platform.system().lower()
        self.is_termux = "TERMUX_VERSION" in os.environ
        self.max_active_history = max_active_history
        self.config_data = self._load_config()
        self.current_provider = self.config_data.get("default_provider", "nvidia")
        self._apply_provider_config(self.current_provider)
        self.memories = self._load_memories()
        self.history_data = self._load_history()
        self.chat_counter = self.history_data.get("chat_counter", 0)
        self.messages = self._build_initial_context()
        self.last_user = ""
        self.last_assistant = ""
        self.last_reasoning = ""
        self.ctx_sys = 0
        self.ctx_hist = 0
        self.ctx_in = 0
        self.ctx_out = 0
        self.sess_in = 0
        self.sess_out = 0
        self.tokens_exact = False

    def _get_time(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _load_config(self):
        if not self.config_path.exists():
            sys.exit("[Error] config.json not found.")
        content = self.config_path.read_text(encoding="utf-8").strip()
        if not content:
            sys.exit("[Error] config.json is empty.")
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            sys.exit(f"[Error] Invalid JSON: {e}")

    def _apply_provider_config(self, provider_name):
        providers = self.config_data.get("providers", {})
        if provider_name not in providers:
            print(f"[Error] Provider '{provider_name}' not found.")
            return False
        p_cfg = providers[provider_name]
        if not p_cfg.get("api_key") or "YOUR_" in p_cfg.get("api_key", ""):
            print(f"[Error] API key missing for '{provider_name}'. Update config.json.")
            return False
        self.current_provider = provider_name
        self.api_key = p_cfg["api_key"]
        self.model = p_cfg["model"]
        self.api_url = p_cfg["api_url"]
        self.provider_type = "cohere" if "cohere" in self.api_url.lower() else "openai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"Synapse-CLI/1.0 ({self.platform_name}{'-termux' if self.is_termux else ''})"
        }
        return True

    def _load_memories(self):
        if self.memory_path.exists():
            try:
                data = json.loads(self.memory_path.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
            except Exception:
                return []
        return []

    def _save_memories(self):
        self.memory_path.write_text(json.dumps(self.memories, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_history(self):
        if self.history_path.exists():
            try:
                data = json.loads(self.history_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    if not isinstance(data.get("recent"), list):
                        data["recent"] = []
                    return data
            except Exception:
                pass
        return {"summary": "", "recent": [], "chat_counter": 0}

    def _save_history(self):
        self.history_data["chat_counter"] = self.chat_counter
        self.history_path.write_text(json.dumps(self.history_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _build_system_prompt(self):
        base = f"DIRECT MODE: Respond immediately. No greetings, filler, apologies, or meta-commentary. Provide only the exact answer or code requested.\\nCURRENT DATE & TIME: {self._get_time()}"
        if self.memories:
            base += f"\\nMEMORIES (ALWAYS CONSIDER):\\n- " + "\\n- ".join(self.memories)
        base += "\\nRULES:\\n1. Save facts with <{mem}>fact<{mem}>.\\n2. Use markdown code blocks.\\n3. Keep responses concise.\\n4. Output <{time}> for current time."
        return base

    def _update_system_context(self):
        self.messages[0]["content"] = self._build_system_prompt()

    def _build_initial_context(self):
        ctx = [{"role": "system", "content": self._build_system_prompt()}]
        if self.history_data.get("summary"):
            ctx.append({"role": "system", "content": f"PREVIOUS SESSION SUMMARY:\\n{self.history_data['summary']}"})
        for msg in self.history_data.get("recent", [])[-self.max_active_history:]:
            if isinstance(msg, dict):
                ctx.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        return ctx

    def _estimate_tokens(self, text):
        return max(0, len(text.encode('utf-8')) // 4)

    def _manage_context(self):
        while sum(self._estimate_tokens(m.get("content", "")) for m in self.messages) > 6000 and len(self.messages) > 3:
            self.messages.pop(1)

    def _clear_screen(self):
        sys.stdout.write("\\033[H\\033[J")
        sys.stdout.flush()

    def _format_code_blocks(self, text):
        def repl(m):
            lang = m.group(1).strip().upper() or "CODE"
            return f"\\n\\033[1;37m╔═══ {lang} ═══╗\\033[0m\\n{m.group(2)}\\n\\033[1;37m╚══════════════╝\\033[0m\\n"
        return re.sub(r'```(\\w*)\\n(.*?)```', repl, text, flags=re.DOTALL).replace('```', '\\n\\033[1;37m[ CODE ]\\033[0m\\n')

    def _stream_openai(self, prompt):
        self.ctx_sys = self._estimate_tokens(self.messages[0].get("content", ""))
        self.ctx_hist = sum(self._estimate_tokens(m.get("content", "")) for m in self.messages[1:-1]) if len(self.messages) > 2 else 0
        self.ctx_in = self._estimate_tokens(prompt) if prompt else 0
        self.ctx_out = 0
        self.tokens_exact = False
        payload_data = {"model": self.model, "messages": self.messages, "stream": True}
        if "nvidia" in self.api_url.lower():
            payload_data.update({"temperature": 1, "top_p": 0.95, "max_tokens": 16384, "chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 16384})
        req = urllib.request.Request(self.api_url, data=json.dumps(payload_data).encode("utf-8"), headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                for line in res:
                    line = line.decode("utf-8").strip()
                    if not line.startswith("data: "): continue
                    if line[6:] == "[DONE]": break
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
                    except json.JSONDecodeError: continue
        except urllib.error.HTTPError as e: yield "error", f"[HTTP {e.code}] {e.read().decode('utf-8', errors='ignore')}"
        except urllib.error.URLError as e: yield "error", f"[Network] {e.reason}"
        except Exception as e: yield "error", f"[Error] {str(e)}"

    def _stream_cohere(self, prompt):
        preamble, chat_history = "", []
        for msg in self.messages[:-1]:
            txt = msg.get("content", "").strip()
            if not txt: continue
            if msg["role"] == "system": preamble = txt
            elif msg["role"] == "user": chat_history.append({"role": "USER", "message": txt})
            elif msg["role"] == "assistant": chat_history.append({"role": "CHATBOT", "message": txt})
        self.ctx_sys = self._estimate_tokens(preamble)
        self.ctx_hist = sum(self._estimate_tokens(m["message"]) for m in chat_history)
        self.ctx_in = self._estimate_tokens(prompt) if prompt else 0
        self.ctx_out = 0
        self.tokens_exact = False
        payload = json.dumps({"message": prompt, "model": self.model, "stream": True, "preamble": preamble, "chat_history": chat_history}).encode("utf-8")
        req = urllib.request.Request(self.api_url, data=payload, headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                for line in res:
                    line = line.decode("utf-8").strip()
                    if not line: continue
                    try:
                        chunk = json.loads(line)
                        ev = chunk.get("event_type", "")
                        if ev == "text-generation":
                            t = chunk.get("text", "")
                            if t:
                                self.ctx_out += self._estimate_tokens(t)
                                yield "content", t
                        elif ev == "stream-end":
                            tk = chunk.get("response", {}).get("meta", {}).get("tokens", {})
                            if tk:
                                self.ctx_in = tk.get("input_tokens", self.ctx_in)
                                self.ctx_out = tk.get("output_tokens", self.ctx_out)
                                self.tokens_exact = True
                    except json.JSONDecodeError: continue
        except urllib.error.HTTPError as e: yield "error", f"[HTTP {e.code}] {e.read().decode('utf-8', errors='ignore')}"
        except urllib.error.URLError as e: yield "error", f"[Network] {e.reason}"
        except Exception as e: yield "error", f"[Error] {str(e)}"

    def _stream_request(self, prompt=None):
        if prompt: self.messages.append({"role": "user", "content": prompt})
        self._manage_context()
        yield from (self._stream_cohere(prompt) if self.provider_type == "cohere" else self._stream_openai(prompt))

    def _render_live(self, reasoning_text, content_text, is_complete=False, status=""):
        self._clear_screen()
        print(BANNER)
        pfx = "" if self.tokens_exact else "~"
        print(f"\\033[1;37m{'='*62}\\033[0m")
        print(f"\\033[36m[Context] Sys: {pfx}{self.ctx_sys} | Hist: {pfx}{self.ctx_hist} | In: {pfx}{self.ctx_in} | Out: {pfx}{self.ctx_out}\\033[0m")
        print(f"\\033[33m[Session] Total In: {pfx}{self.sess_in} | Total Out: {pfx}{self.sess_out}\\033[0m")
        print(f"\\033[1;37m{'='*62}\\033[0m")
        print(f"You: {self.last_user}")
        if reasoning_text:
            print(f"\\n\\033[90m[Thinking]\\033[0m\\n\\033[90m{reasoning_text}\\033[0m\\n\\033[90m{'-'*62}\\033[0m")
        print(f"\\nAssistant: {self._format_code_blocks(content_text.replace('<{time}>', self._get_time()))}", end="" if not is_complete else "\\n")
        if status: print(f"\\n\\033[33m[{status}]\\033[0m")
        if not is_complete: sys.stdout.flush()

    def run(self):
        self._clear_screen()
        print(BANNER)
        print(f"Env: {self.platform_name}{' (Termux)' if self.is_termux else ''} | Python {platform.python_version()} | Provider: {self.current_provider.upper()} | Model: {self.model}")
        print("Commands: 'exit', 'quit', '/memory', '/clear', '/nvidia', '/cohere', '/openrouter'")
        print(f"Memories: {len(self.memories)} | History msgs: {len(self.history_data.get('recent', []))}\\n")
        try:
            while True:
                try: user_in = input("You: ").strip()
                except EOFError: break
                if user_in.lower() in ("exit", "quit"):
                    self._save_history()
                    self._clear_screen()
                    print("Session saved. Ended.")
                    break
                if user_in.lower() == "/memory":
                    print("\\n[Saved Memories]")
                    for i, m in enumerate(self.memories, 1) if self.memories else print("None"): print(f"{i}. {m}")
                    print(); continue
                if user_in.lower() == "/clear":
                    self.memories, self.history_data, self.chat_counter, self.sess_in, self.sess_out = [], {"summary": "", "recent": [], "chat_counter": 0}, 0, 0, 0
                    self._save_memories(); self._save_history()
                    self.messages = [{"role": "system", "content": self._build_system_prompt()}]
                    print("\\n\\033[32m[✓ All data cleared]\\033[0m"); continue
                if user_in.startswith("/"):
                    prov = user_in[1:].lower()
                    if prov in self.config_data.get("providers", {}):
                        if self._apply_provider_config(prov):
                            self._update_system_context()
                            print(f"\\n\\033[32m[✓ Switched to {prov.upper()} | Model: {self.model}]\\033[0m")
                        else: print(f"\\n\\033[31m[Error] Failed to switch.\\033[0m")
                    else: print(f"\\n\\033[31m[Error] Unknown provider.\\033[0m")
                    continue
                if not user_in: continue
                self._update_system_context()
                self.last_user = user_in
                cur_r, cur_c, err = "", "", False
                for ev, data in self._stream_request(user_in):
                    if ev == "error": cur_c, err = data, True; break
                    elif ev == "reasoning": cur_r += data; self._render_live(cur_r, cur_c)
                    elif ev == "content": cur_c += data; self._render_live(cur_r, cur_c)
                self.sess_in += self.ctx_in; self.sess_out += self.ctx_out
                new_mems = re.findall(r'<\\{mem\\}>(.*?)<\\{mem\\}>', cur_c, re.DOTALL)
                cleaned = re.sub(r'<\\{mem\\}>.*?<\\{mem\\}>', '', cur_c, flags=re.DOTALL).strip()
                status = ""
                if new_mems and not err:
                    ts = self._get_time()
                    for m in new_mems:
                        mc = f"[{ts}] {m.strip()}"
                        if mc not in self.memories: self.memories.append(mc)
                    self._save_memories(); self._update_system_context(); status = "Memory updated & injected"
                if not err and cleaned:
                    self.messages.append({"role": "assistant", "content": cleaned})
                    ts = self._get_time()
                    self.history_data["recent"].extend([{"role": "user", "content": user_in, "ts": ts}, {"role": "assistant", "content": cleaned, "ts": ts}])
                    self.chat_counter += 1; self._save_history()
                self._render_live(cur_r, cleaned, is_complete=True, status=status)
                self.last_assistant, self.last_reasoning = cleaned, cur_r
        except KeyboardInterrupt:
            self._save_history()
            self._clear_screen()
            print("\\nInterrupted. Session saved.")

if __name__ == "__main__":
    TerminalChat().run()
'''

with open(os.path.join(PKG_DIR, "main.py"), "w", encoding="utf-8") as f:
    f.write(MAIN_CODE.strip() + "\n")

setup(
    name="synapse-ai-cli",
    version="1.0.0",
    description="Synapse AI Terminal Client",
    packages=["synapse"],
    python_requires=">=3.8",
    entry_points={"console_scripts": ["synapse=synapse.cli:run"]}
)
