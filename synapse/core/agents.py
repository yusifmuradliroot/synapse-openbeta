import re
from synapse.core.workspace import Workspace

MODE_CHAT = "chat"
MODE_CODE = "code"
MODE_AGENT = "agent"

class AgentController:
    def __init__(self, engine, ws, mem, hist):
        self.engine = engine
        self.ws = ws
        self.mem = mem
        self.hist = hist
        self.mode = MODE_CHAT

    def set_mode(self, m):
        if m in (MODE_CHAT, MODE_CODE, MODE_AGENT):
            self.mode = m
            self.engine.set_mode_params(m)
            return True
        return False

    def build_prompt(self, dna, time_str):
        p = [f"TIME: {time_str}"]
        p.append(f"WS: {self.ws.active} | Files: {', '.join(self.ws.list_files()) or 'Empty'}")
        p.append("File ops: <{ws_write(f)}>content<{/ws_write}> ONLY.")
        p.append("Terminal ops: <{cmd(command)}> to run shell commands.")

        if self.mode == MODE_CHAT:
            p.append("MODE: CHAT")
            p.append("RULES: Short, direct answers. Max 5 sentences unless asked for more.")
            p.append("Do NOT generate code unless explicitly asked.")
            p.append("Be conversational but concise. No filler, no greetings.")

        elif self.mode == MODE_CODE:
            p.append("MODE: CODE")
            p.append("RULES: Output ONLY code in markdown code blocks.")
            p.append("No explanations before or after code unless critical.")
            p.append("Use <{ws_write(f)}>content<{/ws_write}> to save files.")
            p.append("Temperature is low. Be precise, deterministic, production-ready.")
            p.append("Include error handling. Follow best practices.")

        elif self.mode == MODE_AGENT:
            p.append("MODE: AGENT - Full autonomous execution.")
            p.append("WORKFLOW:")
            p.append("1. ANALYZE: Understand the task. Read existing files if needed via <{ws_read(f)}>.")
            p.append("2. PLAN: Break into steps. State your plan briefly.")
            p.append("3. EXECUTE: Do ONE step per response. Use <{ws_write}> for files, <{cmd}> for commands.")
            p.append("4. VERIFY: After writing code, run it with <{cmd}> to check for errors.")
            p.append("5. FIX: If errors, fix and re-verify.")
            p.append("6. CONTINUE: End with <{uncompleted}> to proceed to next step.")
            p.append("7. FINISH: When ALL steps done, finish WITHOUT <{uncompleted}>.")
            p.append("RULES: Max 80 lines of code per response. One file per step. Always verify.")

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
        clean = re.sub(r'<\{mem\}>.*?<\{mem\}>', '', clean, flags=re.DOTALL)
        clean = re.sub(r'<\{cmd\([^)]*\)\}>', '', clean)
        clean = clean.replace("<{uncompleted}>", "").replace("<{resume}>", "").strip()
        return clean, acts

    def extract_commands(self, content):
        return re.findall(r'<\{cmd\(([^)]+)\)\}>', content)

    def has_actions(self, content):
        return bool(
            re.search(r'<\{ws_write\(', content) or
            re.search(r'<\{cmd\(', content) or
            re.search(r'<\{ws_read\(', content) or
            re.search(r'<\{ws_delete\(', content) or
            '<{ws_list}>' in content
        )
