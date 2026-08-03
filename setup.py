import os
from setuptools import setup

PKG_DIR = "synapse"
os.makedirs(PKG_DIR, exist_ok=True)

with open(os.path.join(PKG_DIR, "__init__.py"), "w", encoding="utf-8") as f:
    f.write("# Synapse AI CLI\n")

CLI_CODE = '''import os
import sys
import json
import tempfile
import zipfile
import urllib.request
import subprocess
import shutil
from pathlib import Path

WORKSPACE_DIR = Path.home() / "synapse"
OLD_WORKSPACE_DIR = Path.home() / ".synapse"
CONFIG_PATH = WORKSPACE_DIR / "config.json"
DNA_PATH = WORKSPACE_DIR / "dna.json"
EVOLUTION_PATH = WORKSPACE_DIR / "evolution.json"
MEMORY_PATH = WORKSPACE_DIR / "memory.json"
HISTORY_PATH = WORKSPACE_DIR / "history.json"
WS_DIR = WORKSPACE_DIR / "workspaces"

DEFAULT_CONFIG = {
    "default_provider": "nvidia",
    "providers": {
        "nvidia": {"api_key": "YOUR_NVIDIA_KEY", "model": "nvidia/nemotron-3-ultra-550b-a55b", "api_url": "https://integrate.api.nvidia.com/v1/chat/completions"},
        "cohere": {"api_key": "YOUR_COHERE_KEY", "model": "command-r-08-2024", "api_url": "https://api.cohere.com/v1/chat"},
        "openrouter": {"api_key": "YOUR_OPENROUTER_KEY", "model": "meta-llama/llama-3.1-8b-instruct:free", "api_url": "https://openrouter.ai/api/v1/chat/completions"}
    }
}

DEFAULT_DNA = {
    "core_directives": [
        "DIRECT MODE: Respond immediately. No greetings, filler, apologies, or meta-commentary.",
        "Provide only the exact answer or code requested.",
        "Always use markdown code blocks with language tags.",
        "Keep responses strictly relevant and concise."
    ],
    "response_rules": [
        "Save facts with <{mem}>fact<{mem}>.",
        "Output <{time}> for current time.",
        "Use <{evolve(proposal)}> to suggest system improvements (requires user approval).",
        "CRITICAL: For workspace files, NEVER output JSON. You MUST use ONLY these tags: <{ws_write(filename)}>content<{/ws_write}>."
    ],
    "immutable": True
}

DEFAULT_EVOLUTION = {"proposals": [], "accepted_rules": []}

def do_update():
    print("\\033[33m[*] Fetching latest version from GitHub...\\033[0m")
    zip_url = "https://github.com/yusifmuradliroot/synapse-openbeta/archive/refs/heads/main.zip"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "repo.zip")
            urllib.request.urlretrieve(zip_url, zip_path)
            with zipfile.ZipFile(zip_path, 'r') as z: z.extractall(tmpdir)
            dirs = [d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))]
            if not dirs: print("\\033[31m[!] Extraction failed.\\033[0m"); return False
            repo_dir = os.path.join(tmpdir, dirs[0])
            print("\\033[33m[*] Installing update...\\033[0m")
            result = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--force-reinstall", "-q", repo_dir], capture_output=True, text=True)
            if result.returncode == 0: print("\\033[32m[✓] Update successful! Run 'synapse' again.\\033[0m"); return True
            else: print(f"\\033[31m[!] Install failed: {result.stderr.strip()}\\033[0m"); return False
    except Exception as e: print(f"\\033[31m[!] Update error: {e}\\033[0m"); return False

def migrate_data():
    if OLD_WORKSPACE_DIR.exists() and not WORKSPACE_DIR.exists():
        print("\\033[33m[*] Migrating data from ~/.synapse to ~/synapse...\\033[0m")
        try:
            shutil.copytree(OLD_WORKSPACE_DIR, WORKSPACE_DIR)
            print("\\033[32m[✓] Migration complete. Your settings, memories, and workspaces are preserved.\\033[0m")
        except Exception as e:
            print(f"\\033[31m[!] Migration warning: {e}\\033[0m")

def init_workspace():
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    WS_DIR.mkdir(parents=True, exist_ok=True)
    (WS_DIR / "default").mkdir(exist_ok=True)
    if not CONFIG_PATH.exists(): CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    if not DNA_PATH.exists(): DNA_PATH.write_text(json.dumps(DEFAULT_DNA, indent=2), encoding="utf-8")
    if not EVOLUTION_PATH.exists(): EVOLUTION_PATH.write_text(json.dumps(DEFAULT_EVOLUTION, indent=2), encoding="utf-8")
    if not MEMORY_PATH.exists(): MEMORY_PATH.write_text("[]", encoding="utf-8")
    if not HISTORY_PATH.exists(): HISTORY_PATH.write_text(json.dumps({"summary": "", "recent": [], "chat_counter": 0}, indent=2), encoding="utf-8")

def run():
    if "--update" in sys.argv: do_update(); sys.exit(0)
    migrate_data()
    init_workspace()
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    providers = cfg.get("providers", {})
    needs_setup = any("YOUR_" in providers.get(p, {}).get("api_key", "") for p in ["nvidia", "openrouter", "cohere"])
    if needs_setup:
        print("\\n[!] First run. Configure API keys. (Empty to skip)\\n")
        for p in ["nvidia", "openrouter", "cohere"]:
            if "YOUR_" in providers[p].get("api_key", ""):
                k = input(f"Enter {p.upper()} API Key: ").strip()
                if k: providers[p]["api_key"] = k
        configured = [p for p in ["nvidia", "openrouter", "cohere"] if "YOUR_" not in providers[p].get("api_key", "")]
        if configured: cfg["default_provider"] = configured[0]
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        print("[✓] Saved.\\n")
    os.chdir(WORKSPACE_DIR)
    from synapse.main import TerminalChat
    TerminalChat(base_dir=WORKSPACE_DIR).run()

if __name__ == "__main__":
    run()
'''

with open(os.path.join(PKG_DIR, "cli.py"), "w", encoding="utf-8") as f:
    f.write(CLI_CODE)

MAIN_CODE = '''import json
import sys
import os
import re
import platform
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

os.system('')
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stdin.reconfigure(encoding='utf-8')
    except AttributeError: pass

BANNER = """
\\033[1;36m███████╗██╗   ██╗███╗   ██╗ █████╗ ██████╗ ███████╗███████╗
██╔════╝╚██╗ ██╔╝████╗  ██║██╔══██╗██╔══██╗██╔════╝██╔════╝
███████╗ ╚████╔╝ ██╔██╗ ██║███████║██████╔╝███████╗█████╗  
╚════██║  ╚██╔╝  ██║╚██╗██║██╔══██║██╔═══╝ ╚════██║██╔══╝  
███████║   ██║   ██║ ╚████║██║  ██║██║     ███████║███████║
╚══════╝   ╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚══════╝╚══════╝\\033[0m
"""

class TerminalChat:
    def __init__(self, base_dir=None, max_active_history=10):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.cfg_path = self.base_dir / "config.json"
        self.dna_path = self.base_dir / "dna.json"
        self.evo_path = self.base_dir / "evolution.json"
        self.mem_path = self.base_dir / "memory.json"
        self.hist_path = self.base_dir / "history.json"
        self.ws_dir = self.base_dir / "workspaces"
        self.active_ws = "default"
        
        self.platform_name = platform.system().lower()
        self.is_termux = "TERMUX_VERSION" in os.environ
        self.max_active_history = max_active_history
        
        self.model = self.api_key = self.api_url = ""
        self.provider_type = "openai"
        self.headers = {}
        
        self.config_data = self._load_json(self.cfg_path)
        self.dna = self._load_json(self.dna_path)
        self.evolution = self._load_json(self.evo_path)
        self.memories = self._load_json(self.mem_path) or []
        self.history_data = self._load_json(self.hist_path) or {"summary": "", "recent": [], "chat_counter": 0}
        self.chat_counter = self.history_data.get("chat_counter", 0)
        
        self.current_provider = self.config_data.get("default_provider", "nvidia")
        if not self._apply_provider(self.current_provider):
            sys.exit(f"[Error] Provider '{self.current_provider}' invalid. Update config.json.")
            
        self.messages = self._build_context()
        self.last_user = self.last_assistant = self.last_reasoning = ""
        self.ctx_sys = self.ctx_hist = self.ctx_in = self.ctx_out = 0
        self.sess_in = self.sess_out = 0
        self.tokens_exact = False

    def _load_json(self, p):
        if not Path(p).exists(): return None
        try: return json.loads(Path(p).read_text(encoding="utf-8"))
        except: return None

    def _save_json(self, p, data):
        Path(p).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _apply_provider(self, name):
        provs = self.config_data.get("providers", {})
        if name not in provs: return False
        p = provs[name]
        if not p.get("api_key") or "YOUR_" in p.get("api_key", ""): return False
        self.current_provider = name
        self.api_key, self.model, self.api_url = p["api_key"], p["model"], p["api_url"]
        self.provider_type = "cohere" if "cohere" in self.api_url.lower() else "openai"
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "User-Agent": "Synapse-CLI/1.0"}
        return True

    def _get_time(self): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _build_context(self):
        dna_rules = self.dna.get("core_directives", []) + self.dna.get("response_rules", [])
        evo_rules = self.evolution.get("accepted_rules", [])
        ws_files = []
        ws_p = self.ws_dir / self.active_ws
        if ws_p.exists():
            ws_files = [f.name for f in ws_p.iterdir() if f.is_file()]
        
        prompt_parts = [f"CURRENT DATE & TIME: {self._get_time()}"]
        prompt_parts.append("ZONE 1 (DNA - IMMUTABLE CORE):")
        prompt_parts.extend(f"- {r}" for r in dna_rules)
        if evo_rules:
            prompt_parts.append("ZONE 2 (EVOLUTION - ACCEPTED UPGRADES):")
            prompt_parts.extend(f"- {r}" for r in evo_rules)
        prompt_parts.append(f"ZONE 3 (ACTIVE WORKSPACE: {self.active_ws}):")
        prompt_parts.append(f"- Files: {', '.join(ws_files) if ws_files else 'Empty'}")
        prompt_parts.append("- STRICT RULE: To create/edit files, you MUST use ONLY this format:")
        prompt_parts.append("  <{ws_write(filename)}>\\nFULL_FILE_CONTENT\\n<{/ws_write}>")
        prompt_parts.append("- DO NOT output JSON. DO NOT use markdown for the tags. Write files one by one.")
        if self.memories:
            prompt_parts.append("LONG-TERM MEMORIES:")
            prompt_parts.extend(f"- {m}" for m in self.memories)
            
        ctx = [{"role": "system", "content": "\\n".join(prompt_parts)}]
        if self.history_data.get("summary"):
            ctx.append({"role": "system", "content": f"PREVIOUS SESSION SUMMARY:\\n{self.history_data['summary']}"})
        for m in self.history_data.get("recent", [])[-self.max_active_history:]:
            if isinstance(m, dict): ctx.append({"role": m.get("role","user"), "content": m.get("content","")})
        return ctx

    def _update_context(self): self.messages[0]["content"] = self._build_context()[0]["content"]

    def _estimate_tokens(self, t): return max(0, len(t.encode('utf-8')) // 4)

    def _trim_context(self):
        while sum(self._estimate_tokens(m.get("content","")) for m in self.messages) > 6000 and len(self.messages) > 3:
            self.messages.pop(1)

    def _clear(self): sys.stdout.write("\\033[H\\033[J"); sys.stdout.flush()

    def _fmt_code(self, text):
        def repl(m):
            lang = m.group(1).strip().upper() or "CODE"
            return f"\\n\\033[1;37m╔═══ {lang} ═══╗\\033[0m\\n{m.group(2)}\\n\\033[1;37m╚══════════════╝\\033[0m\\n"
        return re.sub(r'```(\\w*)\\n(.*?)```', repl, text, flags=re.DOTALL).replace('```', '\\n\\033[1;37m[ CODE ]\\033[0m\\n')

    def _stream_openai(self, prompt):
        self.ctx_sys = self._estimate_tokens(self.messages[0].get("content",""))
        self.ctx_hist = sum(self._estimate_tokens(m.get("content","")) for m in self.messages[1:-1]) if len(self.messages)>2 else 0
        self.ctx_in = self._estimate_tokens(prompt) if prompt else 0
        self.ctx_out = 0; self.tokens_exact = False
        payload = {"model": self.model, "messages": self.messages, "stream": True}
        if "nvidia" in self.api_url.lower():
            payload.update({"temperature":1,"top_p":0.95,"max_tokens":16384,"chat_template_kwargs":{"enable_thinking":True},"reasoning_budget":16384})
        req = urllib.request.Request(self.api_url, data=json.dumps(payload).encode("utf-8"), headers=self.headers, method="POST")
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
                        delta = chunk.get("choices",[{}])[0].get("delta",{})
                        c = delta.get("content",""); r = delta.get("reasoning","") or delta.get("reasoning_content","")
                        if c: yield "content", c
                        if r: yield "reasoning", r
                    except: continue
        except urllib.error.HTTPError as e: yield "error", f"[HTTP {e.code}]"
        except Exception as e: yield "error", f"[Error] {str(e)}"

    def _stream_cohere(self, prompt):
        preamble, hist = "", []
        for m in self.messages[:-1]:
            t = m.get("content","").strip()
            if not t: continue
            if m["role"]=="system": preamble=t
            elif m["role"]=="user": hist.append({"role":"USER","message":t})
            elif m["role"]=="assistant": hist.append({"role":"CHATBOT","message":t})
        self.ctx_sys = self._estimate_tokens(preamble)
        self.ctx_hist = sum(self._estimate_tokens(x["message"]) for x in hist)
        self.ctx_in = self._estimate_tokens(prompt) if prompt else 0
        self.ctx_out = 0; self.tokens_exact = False
        payload = {"message":prompt,"model":self.model,"stream":True,"preamble":preamble,"chat_history":hist}
        req = urllib.request.Request(self.api_url, data=json.dumps(payload).encode("utf-8"), headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                for line in res:
                    line = line.decode("utf-8").strip()
                    if not line: continue
                    try:
                        chunk = json.loads(line)
                        ev = chunk.get("event_type","")
                        if ev=="text-generation":
                            t = chunk.get("text","")
                            if t: self.ctx_out += self._estimate_tokens(t); yield "content", t
                        elif ev=="stream-end":
                            tk = chunk.get("response",{}).get("meta",{}).get("tokens",{})
                            if tk: self.ctx_in=tk.get("input_tokens",self.ctx_in); self.ctx_out=tk.get("output_tokens",self.ctx_out); self.tokens_exact=True
                    except: continue
        except urllib.error.HTTPError as e: yield "error", f"[HTTP {e.code}]"
        except Exception as e: yield "error", f"[Error] {str(e)}"

    def _stream(self, prompt=None):
        if prompt: self.messages.append({"role":"user","content":prompt})
        self._trim_context()
        yield from (self._stream_cohere(prompt) if self.provider_type=="cohere" else self._stream_openai(prompt))

    def _render(self, reason, content, complete=False, status=""):
        self._clear()
        print(BANNER)
        print(f"\\033[0;37m  v1.2.3 | DNA / Evolution / Workspace\\033[0m")
        pfx = "" if self.tokens_exact else "~"
        print(f"\\033[1;37m{'='*62}\\033[0m")
        print(f"\\033[36m[Context] Sys:{pfx}{self.ctx_sys} Hist:{pfx}{self.ctx_hist} In:{pfx}{self.ctx_in} Out:{pfx}{self.ctx_out}\\033[0m")
        print(f"\\033[33m[Session] In:{pfx}{self.sess_in} Out:{pfx}{self.sess_out} | WS:{self.active_ws}\\033[0m")
        print(f"\\033[1;37m{'='*62}\\033[0m")
        print(f"You: {self.last_user}")
        if reason: print(f"\\n\\033[90m[Thinking]\\033[0m\\n\\033[90m{reason}\\033[0m\\n\\033[90m{'-'*62}\\033[0m")
        print(f"\\nAssistant: {self._fmt_code(content.replace('<{time}>', self._get_time()))}", end="" if not complete else "\\n")
        if status: print(f"\\n\\033[33m[{status}]\\033[0m")
        if not complete: sys.stdout.flush()

    def _ws_path(self, fname):
        p = (self.ws_dir / self.active_ws / fname).resolve()
        if not str(p).startswith(str(self.ws_dir.resolve())): return None
        return p

    def run(self):
        self._clear()
        print(BANNER)
        print(f"\\033[0;37m  v1.2.3 | DNA / Evolution / Workspace\\033[0m")
        print(f"Env: {self.platform_name}{' (Termux)' if self.is_termux else ''} | Python {platform.python_version()}")
        print(f"Provider: {self.current_provider.upper()} | Model: {self.model} | WS: {self.active_ws}")
        print("Commands: exit, quit, /memory, /clear, /ws, /evolve, /accept <id>, /reject <id>, /nvidia, /cohere, /openrouter")
        print(f"Memories: {len(self.memories)} | History: {len(self.history_data.get('recent',[]))}\\n")
        
        try:
            while True:
                try: ui = input("You: ").strip()
                except EOFError: break
                if ui.lower() in ("exit","quit"):
                    self._save_json(self.hist_path, self.history_data)
                    self._clear(); print("Session saved."); break
                if ui.lower()=="/memory":
                    print("\\n[Memories]"); [print(f"{i}. {m}") for i,m in enumerate(self.memories,1)] if self.memories else print("None"); print(); continue
                if ui.lower()=="/clear":
                    self.memories, self.history_data, self.chat_counter, self.sess_in, self.sess_out = [], {"summary":"","recent":[],"chat_counter":0}, 0, 0, 0
                    self._save_json(self.mem_path,self.memories); self._save_json(self.hist_path,self.history_data)
                    self.messages=self._build_context(); print("\\n\\033[32m[✓ Cleared]\\033[0m"); continue
                if ui.lower().startswith("/ws "):
                    parts=ui.split(); cmd=parts[1].lower() if len(parts)>1 else ""
                    if cmd=="create" and len(parts)>2:
                        (self.ws_dir/parts[2]).mkdir(parents=True,exist_ok=True); print(f"\\n[✓ WS '{parts[2]}' created]"); continue
                    if cmd=="switch" and len(parts)>2:
                        p=self.ws_dir/parts[2]
                        if p.exists(): self.active_ws=parts[2]; self._update_context(); print(f"\\n[✓ Switched to '{self.active_ws}']")
                        else: print("\\n[!] WS not found"); continue
                    if cmd=="list":
                        ws=[d.name for d in self.ws_dir.iterdir() if d.is_dir()]; print(f"\\n[Workspaces] {', '.join(ws)}"); continue
                    if cmd=="delete" and len(parts)>2:
                        import shutil; p=self.ws_dir/parts[2]
                        if p.exists() and p.name!="default": shutil.rmtree(p); print(f"\\n[✓ Deleted '{parts[2]}']")
                        else: print("\\n[!] Invalid WS"); continue
                if ui.lower()=="/evolve":
                    props=self.evolution.get("proposals",[])
                    print("\\n[Evolution Proposals]")
                    for p in props: print(f"ID:{p['id']} | {p['proposal'][:60]}... | Status:{p['status']}")
                    if not props: print("None"); print(); continue
                if ui.lower().startswith("/accept ") or ui.lower().startswith("/reject "):
                    action, pid = ui.split()[0][1:], ui.split()[1]
                    props=self.evolution.get("proposals",[])
                    for p in props:
                        if str(p["id"])==pid:
                            p["status"]="accepted" if action=="accept" else "rejected"
                            if action=="accept": self.evolution.setdefault("accepted_rules",[]).append(p["proposal"])
                            self._save_json(self.evo_path, self.evolution); self._update_context()
                            print(f"\\n[✓ Proposal {pid} {action}ed]"); break
                    continue
                if ui.startswith("/"):
                    prov=ui[1:].lower()
                    if prov in self.config_data.get("providers",{}):
                        if self._apply_provider(prov): self._update_context(); print(f"\\n\\033[32m[✓ Switched to {prov.upper()}]\\033[0m")
                        else: print("\\n\\033[31m[!] Invalid key\\033[0m")
                    else: print("\\n\\033[31m[!] Unknown provider\\033[0m")
                    continue
                if not ui: continue

                self._update_context()
                self.last_user=ui; cur_r=cur_c=""; err=False
                for ev, data in self._stream(ui):
                    if ev=="error": cur_c=data; err=True; break
                    elif ev=="reasoning": cur_r+=data; self._render(cur_r, cur_c)
                    elif ev=="content": cur_c+=data; self._render(cur_r, cur_c)
                self.sess_in+=self.ctx_in; self.sess_out+=self.ctx_out

                evo_match = re.search(r'<\\{evolve\\((.*?)\\)\\}>', cur_c, re.DOTALL)
                ws_write = re.findall(r'<\\{ws_write\\(([^)]+)\\)\\}>(.*?)<\\{/ws_write\\}>', cur_c, re.DOTALL)
                ws_read = re.search(r'<\\{ws_read\\(([^)]+)\\)\\}>', cur_c)
                ws_list = '<{ws_list}>' in cur_c
                ws_del = re.search(r'<\\{ws_delete\\(([^)]+)\\)\\}>', cur_c)
                
                feedback = []
                
                if ("action" in cur_c and "structure" in cur_c) or (cur_c.strip().startswith("{") and cur_c.strip().endswith("}")):
                    feedback.append("[ERROR] Invalid format. DO NOT output JSON. You MUST use <{ws_write(filename)}>content<{/ws_write}> tags for each file.")
                else:
                    if evo_match:
                        prop = evo_match.group(1).strip()
                        pid = len(self.evolution.get("proposals",[]))+1
                        self.evolution.setdefault("proposals",[]).append({"id":pid,"proposal":prop,"status":"pending","ts":self._get_time()})
                        self._save_json(self.evo_path, self.evolution)
                        feedback.append(f"[Evolution] Proposal #{pid} saved. Run /accept {pid} to apply.")
                    if ws_read:
                        fp=self._ws_path(ws_read.group(1))
                        if fp and fp.exists(): feedback.append(f"[WS Read]\\n{fp.read_text(encoding='utf-8',errors='ignore')}")
                        else: feedback.append("[WS Read] File not found.")
                    if ws_write:
                        for fname, content in ws_write:
                            fp=self._ws_path(fname)
                            if fp:
                                fp.parent.mkdir(parents=True, exist_ok=True)
                                fp.write_text(content.strip(), encoding='utf-8')
                                feedback.append(f"[WS Write] Saved {fname}")
                            else: feedback.append(f"[WS Write] Invalid path: {fname}")
                    if ws_list:
                        files=[f.name for f in (self.ws_dir/self.active_ws).iterdir() if f.is_file()]
                        feedback.append(f"[WS List] {', '.join(files) if files else 'Empty'}")
                    if ws_del:
                        fp=self._ws_path(ws_del.group(1))
                        if fp and fp.exists(): fp.unlink(); feedback.append(f"[WS Delete] Removed {fp.name}")
                        else: feedback.append("[WS Delete] Not found.")

                cleaned = re.sub(r'<\\{evolve\\(.*?\\)\\}>', '', cur_c, flags=re.DOTALL)
                cleaned = re.sub(r'<\\{ws_.*?\\}>.*?<\\{/ws_.*?\\}>', '', cleaned, flags=re.DOTALL)
                cleaned = re.sub(r'<\\{ws_.*?\\}>', '', cleaned)
                cleaned = re.sub(r'<\\{mem\\}>.*?<\\{mem\\}>', '', cleaned, flags=re.DOTALL).strip()
                
                new_mems = re.findall(r'<\\{mem\\}>(.*?)<\\{mem\\}>', cur_c, re.DOTALL)
                status=""
                if new_mems and not err:
                    for m in new_mems:
                        mc=f"[{self._get_time()}] {m.strip()}"
                        if mc not in self.memories: self.memories.append(mc)
                    self._save_json(self.mem_path, self.memories); self._update_context(); status="Memory updated"

                if feedback:
                    self.messages.append({"role":"assistant","content":cur_c})
                    self.messages.append({"role":"user","content":"\\n".join(feedback)+"\\nAnalyze and continue or finalize."})
                    self._render(cur_r, cleaned, status="WS/Evo feedback injected")
                    continue

                if not err and cleaned:
                    self.messages.append({"role":"assistant","content":cleaned})
                    self.history_data["recent"].extend([{"role":"user","content":ui,"ts":self._get_time()},{"role":"assistant","content":cleaned,"ts":self._get_time()}])
                    self.chat_counter+=1; self._save_json(self.hist_path, self.history_data)

                self._render(cur_r, cleaned, complete=True, status=status)
                self.last_assistant, self.last_reasoning = cleaned, cur_r
        except KeyboardInterrupt:
            self._save_json(self.hist_path, self.history_data)
            self._clear(); print("\\nInterrupted. Saved.")

if __name__ == "__main__":
    TerminalChat().run()
'''

with open(os.path.join(PKG_DIR, "main.py"), "w", encoding="utf-8") as f:
    f.write(MAIN_CODE)

setup(
    name="synapse-ai-cli",
    version="1.2.3",
    description="Synapse AI Terminal Client with DNA/Evolution/Workspace Architecture",
    packages=["synapse"],
    python_requires=">=3.8",
    entry_points={"console_scripts": ["synapse=synapse.cli:run"]}
)
