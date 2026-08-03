import re
from synapse.core.workspace import Workspace
from synapse.core.memory import MemoryManager
from synapse.core.history import HistoryManager

MODE_CHAT, MODE_NATIVE, MODE_CRACK = "chat", "nativeagent", "crackagent"

class AgentController:
    def __init__(self, engine, ws, mem, hist):
        self.engine = engine
        self.ws = ws
        self.mem = mem
        self.hist = hist
        self.mode = MODE_CHAT

    def set_mode(self, m):
        if m in (MODE_CHAT, MODE_NATIVE, MODE_CRACK):
            self.mode = m
            return True
        return False

    def build_prompt(self, dna, time_str):
        p = [f"TIME: {time_str}", "RULES: Direct answers only. No filler. Use markdown. Be concise."]
        p.append(f"WS: {self.ws.active} | Files: {', '.join(self.ws.list_files()) or 'Empty'}")
        p.append("File ops: <{ws_write(f)}>content<{/ws_write}> ONLY.")
        if self.mode == MODE_NATIVE:
            p.append("MODE: NATIVE AGENT - Multi-step, loop until done.")
        elif self.mode == MODE_CRACK:
            p.append("MODE: CRACK AGENT - Parse tags, loop on actions.")
        else:
            p.append("MODE: CHAT - Single response.")
        ms = self.mem.get_all()
        if ms:
            p.append("MEMORIES:\n" + "\n".join(f"- {m}" for m in ms[-10:]))
        return "\n".join(p)

    def process(self, content):
        acts = []
        for f, c in re.findall(r'<\{ws_write\(([^)]+)\)\}>(.*?)<\{/ws_write\}>', content, re.DOTALL):
            if self.ws.write(f, c):
                acts.append(f"[WS] Saved {f}")
        m = re.search(r'<\{ws_read\(([^)]+)\)\}>', content)
        if m:
            d = self.ws.read(m.group(1))
            acts.append(f"[WS Read]\n{d}" if d else "[WS Read] Not found.")
        if '<{ws_list}>' in content:
            acts.append(f"[WS List] {', '.join(self.ws.list_files()) or 'Empty'}")
        md = re.search(r'<\{ws_delete\(([^)]+)\)\}>', content)
        if md and self.ws.delete_file(md.group(1)):
            acts.append(f"[WS Del] {md.group(1)}")
        for tag in re.findall(r'<\{mem\}>(.*?)<\{mem\}>', content, re.DOTALL):
            if self.mem.add(tag):
                acts.append("[Mem] Saved")
        clean = re.sub(r'<\{ws_write\([^)]+\)\}>.*?<\{/ws_write\}>', '', content, flags=re.DOTALL)
        clean = re.sub(r'<\{ws_(?:read|delete|list)\([^)]*\)\}>', '', clean)
        clean = re.sub(r'<\{ws_list\}>', '', clean)
        clean = re.sub(r'<\{mem\}>.*?<\{mem\}>', '', clean, flags=re.DOTALL).strip()
        return clean, acts

    def should_loop(self):
        return self.mode in (MODE_NATIVE, MODE_CRACK)
