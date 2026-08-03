import os
from setuptools import setup, find_packages

PKG = "synapse"
CORE = os.path.join(PKG, "core")
os.makedirs(CORE, exist_ok=True)

VERSION = "2.2.0"

with open(os.path.join(PKG, "__init__.py"), "w", encoding="utf-8") as f:
    f.write(f'__version__ = "{VERSION}"\n')
with open(os.path.join(CORE, "__init__.py"), "w", encoding="utf-8") as f:
    f.write("")

CONFIG_CODE = '''import json
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
    "core_directives": ["DIRECT MODE: No greetings, filler, or meta-commentary.", "Provide only exact answers or code.", "Use markdown code blocks.", "Be strictly relevant and concise."],
    "response_rules": ["Save facts with <{mem}>fact<{mem}>.", "Output <{time}> for time.", "Use <{evolve(proposal)}> for improvements.", "CRITICAL: Workspace files ONLY via <{ws_write(f)}>content<{/ws_write}>."],
    "immutable": True
}

def ensure_dirs():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    WS_DIR.mkdir(parents=True, exist_ok=True)
    (WS_DIR / "default").mkdir(exist_ok=True)

def load_json(path, default=None):
    if not Path(path).exists(): return default
    try:
        c = Path(path).read_text(encoding="utf-8").strip()
        return json.loads(c) if c else default
    except Exception: return default

def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def init_config():
    ensure_dirs()
    if not CONFIG_PATH.exists(): save_json(CONFIG_PATH, {"default_provider": "nvidia", "providers": PROVIDERS, "default_interface": "cli"})
    if not DNA_PATH.exists(): save_json(DNA_PATH, DEFAULT_DNA)
    if not MEMORY_PATH.exists(): save_json(MEMORY_PATH, {"memories": [], "total_chars": 0})
    if not HISTORY_PATH.exists(): save_json(HISTORY_PATH, {"compressed_3": "", "ultra_10": "", "recent": [], "total_chars": 0})

def setup_wizard():
    cfg = load_json(CONFIG_PATH, {"default_provider": "nvidia", "providers": PROVIDERS, "default_interface": "cli"})
    if cfg is None: cfg = {"default_provider": "nvidia", "providers": PROVIDERS, "default_interface": "cli"}
    providers = cfg.get("providers", {})
    needs = any("YOUR_" in providers.get(p, {}).get("api_key", "") for p in PROVIDERS)
    if not needs: return cfg

    print("\\033[1;36m\\n  SYNAPSE v2.2.0 - Setup\\033[0m")
    print("  Configure providers. Enter to skip.\\n")
    for name in ["nvidia", "openrouter", "cohere"]:
        cur = providers.get(name, {})
        if "YOUR_" in cur.get("api_key", ""):
            k = input(f"  \\033[1m{name.upper()}\\033[0m Key (skip: Enter): ").strip()
            if k:
                cur["api_key"] = k
                m = input(f"  \\033[1m{name.upper()}\\033[0m Model (default: {cur.get('model','')}): ").strip()
                if m: cur["model"] = m
                providers[name] = cur
                print(f"  \\033[32m[✓] {name} set\\033[0m\\n")
            else: print(f"  \\033[33m[~] {name} skipped\\033[0m\\n")
    ok = [p for p in PROVIDERS if "YOUR_" not in providers.get(p, {}).get("api_key", "")]
    cfg["default_provider"] = ok[0] if ok else "nvidia"
    cfg["providers"] = providers
    
    iface = input("  Default Interface [cli/gui]: ").strip().lower()
    cfg["default_interface"] = iface if iface in ("cli", "gui") else "cli"
    
    save_json(CONFIG_PATH, cfg)
    print("\\033[32m  [✓] Saved to ~/synapse/config.json\\033[0m\\n")
    return cfg
'''
with open(os.path.join(CORE, "config.py"), "w", encoding="utf-8") as f: f.write(CONFIG_CODE)

ENGINE_CODE = '''import json, urllib.request, urllib.error

class Engine:
    def __init__(self):
        self.api_key = self.model = self.api_url = self.provider_name = ""
        self.provider_type = "openai"
        self.headers = {}
        self.ctx_in = self.ctx_out = self.sess_in = self.sess_out = 0
        self.tokens_exact = False

    def apply(self, name, providers):
        if name not in providers: return False
        p = providers[name]
        if not p.get("api_key") or "YOUR_" in p.get("api_key", ""): return False
        self.provider_name, self.api_key, self.model, self.api_url = name, p["api_key"], p["model"], p["api_url"]
        self.provider_type = "cohere" if "cohere" in self.api_url.lower() else "openai"
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "User-Agent": "Synapse/2.2"}
        return True

    def est_tok(self, t): return max(0, len(t.encode("utf-8")) // 4)

    def stream(self, messages):
        self.ctx_in = self.est_tok(json.dumps(messages))
        self.ctx_out = 0
        self.tokens_exact = False
        payload = {"model": self.model, "messages": messages, "stream": True, "temperature": 0.3}
        if "nvidia" in self.api_url.lower():
            payload.update({"top_p": 0.9, "max_tokens": 4096, "chat_template_kwargs": {"enable_thinking": False}})
        req = urllib.request.Request(self.api_url, data=json.dumps(payload).encode("utf-8"), headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as res:
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
                    except Exception: continue
        except urllib.error.HTTPError as e: yield "error", f"[HTTP {e.code}]"
        except Exception as e: yield "error", f"[Error] {str(e)}"
'''
with open(os.path.join(CORE, "engine.py"), "w", encoding="utf-8") as f: f.write(ENGINE_CODE)

MEMORY_CODE = '''import json
from pathlib import Path
from datetime import datetime
from synapse.core.config import MEMORY_PATH, load_json, save_json

MAX_CHARS = 2048
OPTIMIZE_AT = 256

class MemoryManager:
    def __init__(self):
        self.data = load_json(MEMORY_PATH, {"memories": [], "total_chars": 0})
        self.memories = self.data.get("memories", [])
        self.total_chars = sum(len(m) for m in self.memories)

    def add(self, fact):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"[{ts}] {fact.strip()}"
        if entry not in self.memories:
            self.memories.append(entry)
            self.total_chars += len(entry)
            self._save()
            return True
        return False

    def get_all(self): return self.memories
    def needs_optimization(self): return self.total_chars > OPTIMIZE_AT
    def optimize(self, ai_list):
        self.memories = [m.strip() for m in ai_list if m.strip()]
        self.total_chars = sum(len(m) for m in self.memories)
        if self.total_chars > MAX_CHARS:
            self.memories = self.memories[-15:]
            self.total_chars = sum(len(m) for m in self.memories)
        self._save()
    def build_prompt(self):
        txt = "\\n".join(f"- {m}" for m in self.memories)
        return f"Condense these memories. Remove duplicates. Keep all facts. Output ONLY a JSON array of strings. Max 2048 chars total.\\n\\n{txt}"
    def _save(self):
        self.data = {"memories": self.memories, "total_chars": self.total_chars}
        save_json(MEMORY_PATH, self.data)
    def clear(self):
        self.memories, self.total_chars = [], 0
        self._save()
'''
with open(os.path.join(CORE, "memory.py"), "w", encoding="utf-8") as f: f.write(MEMORY_CODE)

HISTORY_CODE = '''import json
from pathlib import Path
from datetime import datetime
from synapse.core.config import HISTORY_PATH, load_json, save_json

MAX_CHARS = 1024

class HistoryManager:
    def __init__(self):
        self.data = load_json(HISTORY_PATH, {"compressed_3": "", "ultra_10": "", "recent": [], "total_chars": 0})
        self.compressed_3 = self.data.get("compressed_3", "")
        self.ultra_10 = self.data.get("ultra_10", "")
        self.recent = self.data.get("recent", [])
        self.total_chars = len(self.compressed_3) + len(self.ultra_10) + sum(len(m.get("content","")) for m in self.recent)

    def add(self, role, content):
        self.recent.append({"role": role, "content": content, "ts": datetime.now().strftime("%H:%M:%S")})
        self.total_chars += len(content)
        self._enforce()
        self._save()

    def _enforce(self):
        while self.total_chars > MAX_CHARS and len(self.recent) > 2:
            rem = self.recent.pop(0)
            self.total_chars -= len(rem.get("content", ""))

    def get_context(self):
        ctx = []
        if self.ultra_10: ctx.append({"role": "system", "content": f"[Old Context] {self.ultra_10}"})
        if self.compressed_3: ctx.append({"role": "system", "content": f"[Recent Context] {self.compressed_3}"})
        ctx.extend(self.recent[-5:])
        return ctx

    def needs_optimization(self): return len(self.recent) >= 8 or self.total_chars > 700
    def optimize(self, ai_c3, ai_u10):
        self.compressed_3 = ai_c3[:400]
        self.ultra_10 = ai_u10[:400]
        self.recent = self.recent[-3:]
        self.total_chars = len(self.compressed_3) + len(self.ultra_10) + sum(len(m.get("content","")) for m in self.recent)
        self._save()
    def build_prompt(self):
        txt = "\\n".join(f"{m['role']}: {m['content'][:100]}" for m in self.recent[-10:])
        return f"Compress this chat history.\\n1. Last 3 messages -> detailed summary (max 400 chars).\\n2. Older messages -> ultra-brief 1-line summaries (max 400 chars).\\nOutput ONLY two JSON strings: [\\"compressed_3\\", \\"ultra_10\\"]\\n\\n{txt}"
    def _save(self):
        self.data = {"compressed_3": self.compressed_3, "ultra_10": self.ultra_10, "recent": self.recent, "total_chars": self.total_chars}
        save_json(HISTORY_PATH, self.data)
    def clear(self):
        self.compressed_3 = self.ultra_10 = ""
        self.recent = []
        self.total_chars = 0
        self._save()
'''
with open(os.path.join(CORE, "history.py"), "w", encoding="utf-8") as f: f.write(HISTORY_CODE)

WORKSPACE_CODE = '''from pathlib import Path
from synapse.core.config import WS_DIR
import shutil

class Workspace:
    def __init__(self):
        self.active = "default"
        self.base = WS_DIR
    @property
    def path(self): return self.base / self.active
    def create(self, n): (self.base / n).mkdir(parents=True, exist_ok=True)
    def switch(self, n):
        p = self.base / n
        if p.exists(): self.active = n; return True
        return False
    def delete(self, n):
        p = self.base / n
        if p.exists() and n != "default": shutil.rmtree(p); return True
        return False
    def list_all(self): return [d.name for d in self.base.iterdir() if d.is_dir()]
    def list_files(self): return [f.name for f in self.path.iterdir() if f.is_file()] if self.path.exists() else []
    def resolve(self, f):
        p = (self.path / f).resolve()
        return p if str(p).startswith(str(self.base.resolve())) else None
    def read(self, f):
        p = self.resolve(f)
        return p.read_text(encoding="utf-8", errors="ignore") if p and p.exists() else None
    def write(self, f, c):
        p = self.resolve(f)
        if p: p.parent.mkdir(parents=True, exist_ok=True); p.write_text(c.strip(), encoding="utf-8"); return True
        return False
    def delete_file(self, f):
        p = self.resolve(f)
        if p and p.exists(): p.unlink(); return True
        return False
'''
with open(os.path.join(CORE, "workspace.py"), "w", encoding="utf-8") as f: f.write(WORKSPACE_CODE)

AGENTS_CODE = '''import re
from synapse.core.workspace import Workspace
from synapse.core.memory import MemoryManager
from synapse.core.history import HistoryManager

MODE_CHAT, MODE_NATIVE, MODE_CRACK = "chat", "nativeagent", "crackagent"

class AgentController:
    def __init__(self, engine, ws, mem, hist):
        self.engine, self.ws, self.mem, self.hist = engine, ws, mem, hist
        self.mode = MODE_CHAT
    def set_mode(self, m):
        if m in (MODE_CHAT, MODE_NATIVE, MODE_CRACK): self.mode = m; return True
        return False
    def build_prompt(self, dna, time_str):
        p = [f"TIME: {time_str}", "RULES: Direct answers only. No filler. Use markdown. Be concise."]
        p.append(f"WS: {self.ws.active} | Files: {', '.join(self.ws.list_files()) or 'Empty'}")
        p.append("File ops: <{ws_write(f)}>content<{/ws_write}> ONLY.")
        if self.mode == MODE_NATIVE: p.append("MODE: NATIVE AGENT - Multi-step, loop until done.")
        elif self.mode == MODE_CRACK: p.append("MODE: CRACK AGENT - Parse tags, loop on actions.")
        else: p.append("MODE: CHAT - Single response.")
        ms = self.mem.get_all()
        if ms: p.append("MEMORIES:\\n" + "\\n".join(f"- {m}" for m in ms[-10:]))
        return "\\n".join(p)
    def process(self, content):
        acts = []
        for f, c in re.findall(r'<\\{ws_write\\(([^)]+)\\)\\}>(.*?)<\\{/ws_write\\}>', content, re.DOTALL):
            if self.ws.write(f, c): acts.append(f"[WS] Saved {f}")
        m = re.search(r'<\\{ws_read\\(([^)]+)\\)\\}>', content)
        if m:
            d = self.ws.read(m.group(1))
            acts.append(f"[WS Read]\\n{d}" if d else "[WS Read] Not found.")
        if '<{ws_list}>' in content: acts.append(f"[WS List] {', '.join(self.ws.list_files()) or 'Empty'}")
        md = re.search(r'<\\{ws_delete\\(([^)]+)\\)\\}>', content)
        if md and self.ws.delete_file(md.group(1)): acts.append(f"[WS Del] {md.group(1)}")
        for tag in re.findall(r'<\\{mem\\}>(.*?)<\\{mem\\}>', content, re.DOTALL):
            if self.mem.add(tag): acts.append(f"[Mem] Saved")
        clean = re.sub(r'<\\{ws_write\\([^)]+\\)\\}>.*?<\\{/ws_write\\}>', '', content, flags=re.DOTALL)
        clean = re.sub(r'<\\{ws_(?:read|delete|list)\\([^)]*\\)\\}>', '', clean)
        clean = re.sub(r'<\\{ws_list\\}>', '', clean)
        clean = re.sub(r'<\\{mem\\}>.*?<\\{mem\\}>', '', clean, flags=re.DOTALL).strip()
        return clean, acts
    def should_loop(self): return self.mode in (MODE_NATIVE, MODE_CRACK)
'''
with open(os.path.join(CORE, "agents.py"), "w", encoding="utf-8") as f: f.write(AGENTS_CODE)

CLI_CODE = '''import os, sys
from datetime import datetime
from synapse.core.config import init_config, setup_wizard, load_json, save_json, CONFIG_PATH, DNA_PATH
from synapse.core.engine import Engine
from synapse.core.memory import MemoryManager
from synapse.core.history import HistoryManager
from synapse.core.workspace import Workspace
from synapse.core.agents import AgentController, MODE_CHAT, MODE_NATIVE, MODE_CRACK

def run_cli():
    init_config()
    cfg = setup_wizard()
    save_json(CONFIG_PATH, cfg)
    eng = Engine()
    prov = cfg.get("default_provider", "nvidia")
    if not eng.apply(prov, cfg.get("providers", {})):
        print(f"\\033[31m[!] Provider '{prov}' invalid. Edit ~/synapse/config.json\\033[0m"); sys.exit(1)
    mem, hist, ws = MemoryManager(), HistoryManager(), Workspace()
    agent = AgentController(eng, ws, mem, hist)
    dna = load_json(DNA_PATH, {"core_directives": [], "response_rules": []})
    
    os.system('')
    print("\\033[1;36m  SYNAPSE v2.2.0 CLI\\033[0m")
    print(f"  \\033[90m{eng.provider_name.upper()} | {eng.model} | {agent.mode}\\033[0m\\n")
    last_resp = ""
    try:
        while True:
            try: ui = input("\\033[1mYou:\\033[0m ").strip()
            except EOFError: break
            if ui.lower() in ("exit", "quit"): hist._save(); print("\\033[32mSaved.\\033[0m"); break
            if ui == "/chat": agent.set_mode(MODE_CHAT); print("\\033[32m[✓] Chat\\033[0m"); continue
            if ui == "/nativeagent": agent.set_mode(MODE_NATIVE); print("\\033[32m[✓] Native\\033[0m"); continue
            if ui == "/crackagent": agent.set_mode(MODE_CRACK); print("\\033[32m[✓] Crack\\033[0m"); continue
            if ui == "/memory":
                print("\\n\\033[1m[Memories]\\033[0m")
                for i, m in enumerate(mem.get_all(), 1): print(f"  {i}. {m}")
                if not mem.get_all(): print("  None")
                print(); continue
            if ui == "/clear": mem.clear(); hist.clear(); print("\\033[32m[✓] Cleared\\033[0m"); continue
            if ui.startswith("/ws "):
                pts = ui.split(); cmd = pts[1].lower() if len(pts)>1 else ""
                if cmd=="create" and len(pts)>2: ws.create(pts[2]); print(f"\\033[32m[✓] {pts[2]}\\033[0m")
                elif cmd=="switch" and len(pts)>2: print(f"\\033[32m[✓] {ws.switch(pts[2])}\\033[0m")
                elif cmd=="list": print(f"\\033[36m{', '.join(ws.list_all())}\\033[0m")
                elif cmd=="delete" and len(pts)>2: print(f"\\033[32m[✓] {ws.delete(pts[2])}\\033[0m")
                continue
            if ui.startswith("/"):
                p = ui[1:].lower()
                if p in cfg.get("providers", {}):
                    if eng.apply(p, cfg["providers"]): print(f"\\033[32m[✓] {p.upper()}\\033[0m")
                    else: print("\\033[31m[!] Invalid key\\033[0m")
                else: print("\\033[31m[!] Unknown\\033[0m")
                continue
            if not ui: continue
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msgs = [{"role": "system", "content": agent.build_prompt(dna, ts)}]
            msgs.extend(hist.get_context())
            msgs.append({"role": "user", "content": ui})
            cur_c = ""
            err = False
            print("\\033[90m[Thinking...]\\033[0m", end="", flush=True)
            for ev, data in eng.stream(msgs):
                if ev == "error": cur_c = data; err = True; break
                elif ev == "content": cur_c += data; print(f"\\r\\033[90m[Gen {len(cur_c)}c]\\033[0m", end="", flush=True)
            print()
            eng.sess_in += eng.ctx_in; eng.sess_out += eng.ctx_out
            clean, acts = agent.process(cur_c)
            hist.add("user", ui); hist.add("assistant", clean)
            last_resp = clean
            if acts:
                for a in acts: print(f"  \\033[36m{a}\\033[0m")
                if agent.should_loop():
                    msgs.append({"role": "assistant", "content": cur_c})
                    msgs.append({"role": "user", "content": "\\n".join(acts)+"\\nContinue."})
                    print("\\033[33m[Loop...]\\033[0m"); continue
            hist._save()
            if last_resp: print(f"\\n\\033[1mAssistant:\\033[0m\\n{last_resp}\\n")
    except KeyboardInterrupt: hist._save(); print("\\n\\033[33mSaved.\\033[0m")
'''
with open(os.path.join(PKG, "cli.py"), "w", encoding="utf-8") as f: f.write(CLI_CODE)

GUI_CODE = '''import os, sys, json, threading, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from synapse.core.config import init_config, setup_wizard, load_json, save_json, CONFIG_PATH, DNA_PATH
from synapse.core.engine import Engine
from synapse.core.memory import MemoryManager
from synapse.core.history import HistoryManager
from synapse.core.workspace import Workspace
from synapse.core.agents import AgentController

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Synapse v2.2.0</title>
<style>
:root{--bg:#0d1117;--fg:#c9d1d9;--acc:#58a6ff;--msg-u:#161b22;--msg-a:#1f2937;--bdr:#30363d}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,sans-serif;height:100vh;display:flex;flex-direction:column}
header{padding:12px 16px;border-bottom:1px solid var(--bdr);display:flex;justify-content:space-between;align-items:center;background:#010409}
h1{font-size:16px;color:var(--acc)}
#status{font-size:12px;color:#8b949e}
#chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}
.msg{max-width:85%;padding:10px 14px;border-radius:12px;line-height:1.5;font-size:14px;white-space:pre-wrap;word-break:break-word}
.user{align-self:flex-end;background:var(--msg-u);border:1px solid var(--bdr)}
.ai{align-self:flex-start;background:var(--msg-a);border:1px solid var(--bdr)}
#input-area{padding:12px;border-top:1px solid var(--bdr);display:flex;gap:8px;background:#010409}
#inp{flex:1;background:var(--msg-u);border:1px solid var(--bdr);color:var(--fg);padding:10px;border-radius:8px;outline:none;font-size:14px}
#send{background:var(--acc);color:#fff;border:none;padding:0 16px;border-radius:8px;cursor:pointer;font-weight:600}
#send:disabled{opacity:0.5;cursor:default}
code{background:#000;padding:2px 4px;border-radius:4px;font-family:monospace}
</style>
</head>
<body>
<header><h1>SYNAPSE v2.2.0</h1><span id="status">Ready</span></header>
<div id="chat"></div>
<div id="input-area"><input id="inp" placeholder="Type a message..." autocomplete="off"><button id="send">Send</button></div>
<script>
const chat=document.getElementById('chat'),inp=document.getElementById('inp'),btn=document.getElementById('send'),st=document.getElementById('status');
let curMsg=null;
function addMsg(role,text){const d=document.createElement('div');d.className=`msg ${role}`;d.textContent=text;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d;}
async function send(){
  const txt=inp.value.trim(); if(!txt)return;
  inp.value=''; btn.disabled=true; st.textContent='Thinking...';
  addMsg('user',txt);
  curMsg=addMsg('ai','');
  try{
    const res=await fetch('/api/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:txt})});
    const reader=res.body.getReader(),dec=new TextDecoder();
    let buf='';
    while(true){
      const{done,value}=await reader.read(); if(done)break;
      buf+=dec.decode(value,{stream:true});
      const lines=buf.split('\\n'); buf=lines.pop();
      for(const line of lines){
        if(line.startsWith('data: ')){
          const d=line.slice(6);
          if(d==='[DONE]'){st.textContent='Ready';btn.disabled=false;return;}
          try{const p=JSON.parse(d); if(p.content){curMsg.textContent+=p.content;chat.scrollTop=chat.scrollHeight;}}catch(e){}
        }
      }
    }
  }catch(e){curMsg.textContent='[Error] '+e.message;st.textContent='Error';btn.disabled=false;}
}
btn.onclick=send; inp.onkeydown=e=>{if(e.key==='Enter')send()};
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    engine = None
    agent = None
    hist = None
    mem = None
    ws = None
    dna = None
    cfg = None

    def log_message(self, format, *args): pass

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/stream':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))
            user_msg = body.get('message', '')
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            msgs = [{"role": "system", "content": self.agent.build_prompt(self.dna, ts)}]
            msgs.extend(self.hist.get_context())
            msgs.append({"role": "user", "content": user_msg})
            
            full_resp = ""
            try:
                for ev, data in self.engine.stream(msgs):
                    if ev == "content":
                        full_resp += data
                        chunk = json.dumps({"content": data})
                        self.wfile.write(f"data: {chunk}\\n\\n".encode())
                        self.wfile.flush()
                    elif ev == "error":
                        err_chunk = json.dumps({"content": f"[Error] {data}"})
                        self.wfile.write(f"data: {err_chunk}\\n\\n".encode())
                        self.wfile.flush()
                        break
                self.wfile.write(b"data: [DONE]\\n\\n")
                self.wfile.flush()
                
                clean, acts = self.agent.process(full_resp)
                self.hist.add("user", user_msg)
                self.hist.add("assistant", clean)
                self.hist._save()
            except Exception as e:
                self.wfile.write(f"data: {json.dumps({'content': f'[Server Error] {str(e)}'})}\\n\\n".encode())
                self.wfile.flush()
        else:
            self.send_response(404)
            self.end_headers()

def run_gui():
    init_config()
    cfg = setup_wizard()
    save_json(CONFIG_PATH, cfg)
    
    eng = Engine()
    prov = cfg.get("default_provider", "nvidia")
    if not eng.apply(prov, cfg.get("providers", {})):
        print(f"[!] Provider '{prov}' invalid. Edit ~/synapse/config.json"); sys.exit(1)
        
    Handler.engine = eng
    Handler.mem = MemoryManager()
    Handler.hist = HistoryManager()
    Handler.ws = Workspace()
    Handler.agent = AgentController(eng, Handler.ws, Handler.mem, Handler.hist)
    Handler.dna = load_json(DNA_PATH, {"core_directives": [], "response_rules": []})
    Handler.cfg = cfg
    
    port = 8080
    server = HTTPServer(('127.0.0.1', port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"\\033[1;36m  SYNAPSE v2.2.0 GUI\\033[0m")
    print(f"  \\033[32mServer running at {url}\\033[0m")
    print("  Opening browser... (Press Ctrl+C to stop)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("\\n[✓] Server stopped.")
'''
with open(os.path.join(PKG, "gui.py"), "w", encoding="utf-8") as f: f.write(GUI_CODE)

MAIN_CODE = '''import sys
from synapse.core.config import load_json, CONFIG_PATH, init_config, save_json

def main():
    args = sys.argv[1:]
    init_config()
    cfg = load_json(CONFIG_PATH, {})
    
    if "--defaultinterface" in args:
        idx = args.index("--defaultinterface")
        if idx + 1 < len(args):
            mode = args[idx+1].lower().lstrip("-")
            if mode in ("cli", "gui"):
                cfg["default_interface"] = mode
                save_json(CONFIG_PATH, cfg)
                print(f"[✓] Default interface set to {mode.upper()}")
            else:
                print("[!] Use --cli or --gui")
        else:
            print("[!] Specify --cli or --gui after --defaultinterface")
        sys.exit(0)
        
    if "--cli" in args:
        from synapse.cli import run_cli
        run_cli()
    elif "--gui" in args:
        from synapse.gui import run_gui
        run_gui()
    else:
        default = cfg.get("default_interface", "cli")
        if default == "gui":
            from synapse.gui import run_gui
            run_gui()
        else:
            from synapse.cli import run_cli
            run_cli()

if __name__ == "__main__":
    main()
'''
with open(os.path.join(PKG, "main.py"), "w", encoding="utf-8") as f: f.write(MAIN_CODE)

setup(
    name="synapse-ai-cli",
    version=VERSION,
    description="Synapse AI v2.2.0 - CLI & Web GUI (Termux Compatible)",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={"console_scripts": ["synapse=synapse.main:main"]}
)
