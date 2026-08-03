import re
from synapse.core.workspace import Workspace

MODE_CHAT = "chat"
MODE_CODE = "code"
MODE_AGENT = "agent"

AGENT_WORKFLOW = """WORKFLOW (MANDATORY):
1. ANALYZE: Read relevant files first. Use <{ws_read(f)}> or <{cmd(cat f)}>.
2. PLAN: Output a numbered plan. Keep it under 5 steps.
3. EXECUTE: Do ONE step per response. One file per <{ws_write}>.
4. VERIFY: After writing code, test it: <{cmd(python file.py)}> or <{cmd(node file.js)}>.
5. FIX: If errors, analyze and fix. Re-verify.
6. CONTINUE: End with <{uncompleted}> to proceed.
7. DONE: When ALL steps complete and verified, finish WITHOUT <{uncompleted}>.
RULES: Max 80 lines per response. Never skip verification. Never output untested code as final."""

class AgentController:
    def __init__(self, engine, ws, mem, hist):
        self.engine = engine
        self.ws = ws
        self.mem = mem
        self.hist = hist
        self.mode = MODE_CHAT
        self.mode_params = {}

    def set_mode(self, m, params=None):
        if m in (MODE_CHAT, MODE_CODE, MODE_AGENT):
            self.mode = m
            self.mode_params = params or {}
            self.engine.set_params(self.mode_params)
            return True
        return False

    def build_prompt(self, dna, time_str, mode_hint=""):
        p = [f"TIME: {time_str}"]
        p.append(f"WS: {self.ws.active} | Files: {', '.join(self.ws.list_files()) or 'Empty'}")
        p.append("File ops: <{ws_write(f)}>content<{/ws_write}> to create/overwrite.")
        p.append("File edit: <{ws_edit(f)}>new_full_content<{/ws_edit}> to update existing.")
        p.append("File read: <{ws_read(f)}> to read.")
        p.append("Terminal: <{cmd(command)}> to run shell commands.")

        if mode_hint:
            p.append("MODE RULES: " + mode_hint)

        if self.mode == MODE_AGENT:
            p.append(AGENT_WORKFLOW)
        elif self.mode == MODE_CODE:
            p.append("CODE MODE: Output only code. Use <{ws_write}> to save. No explanations.")
        else:
            p.append("CHAT MODE: Short, direct answers. No code unless asked.")

        ms = self.mem.get_all()
        if ms:
            p.append("MEMORIES:\n" + "\n".join(f"- {m}" for m in ms[-10:]))
        return "\n".join(p)

    def process(self, content):
        acts = []
        for f, c in re.findall(r'<\{ws_write\(([^)]+)\)\}>(.*?)<\{/ws_write\}>', content, re.DOTALL):
            if self.ws.write(f, c):
                acts.append(f"[WS] Created {f}")
        for f, c in re.findall(r'<\{ws_edit\(([^)]+)\)\}>(.*?)<\{/ws_edit\}>', content, re.DOTALL):
            if self.ws.write(f, c):
                acts.append(f"[WS] Updated {f}")
        m = re.search(r'<\{ws_read\(([^)]+)\)\}>', content)
        if m:
            d = self.ws.read(m.group(1))
            acts.append(f"[WS Read]\n{d}" if d else "[WS Read] Not found: " + m.group(1))
        if '<{ws_list}>' in content:
            acts.append(f"[WS List] {', '.join(self.ws.list_files()) or 'Empty'}")
        md = re.search(r'<\{ws_delete\(([^)]+)\)\}>', content)
        if md and self.ws.delete_file(md.group(1)):
            acts.append(f"[WS Del] {md.group(1)}")
        for tag in re.findall(r'<\{mem\}>(.*?)<\{mem\}>', content, re.DOTALL):
            if self.mem.add(tag):
                acts.append("[Mem] Saved")
        clean = re.sub(r'<\{ws_write\([^)]+\)\}>.*?<\{/ws_write\}>', '', content, flags=re.DOTALL)
        clean = re.sub(r'<\{ws_edit\([^)]+\)\}>.*?<\{/ws_edit\}>', '', clean, flags=re.DOTALL)
        clean = re.sub(r'<\{ws_(?:read|delete|list)\([^)]*\)\}>', '', clean)
        clean = re.sub(r'<\{ws_list\}>', '', clean)
        clean = re.sub(r'<\{mem\}>.*?<\{mem\}>', '', clean, flags=re.DOTALL)
        clean = re.sub(r'<\{cmd\([^)]*\)\}>', '', clean)
        clean = clean.replace("<{uncompleted}>", "").replace("<{resume}>", "").strip()
        return clean, acts

    def extract_commands(self, content):
        return re.findall(r'<\{cmd\(([^)]+)\)\}>', content)

    def has_actions(self, content):
        return bool(re.search(r'<\{ws_(?:write|edit|read|delete)\(', content) or re.search(r'<\{cmd\(', content) or '<{ws_list}>' in content)

    def has_errors_in_output(self, cmd_results):
        error_keywords = ["error", "traceback", "exception", "failed", "not found", "permission denied"]
        for r in cmd_results:
            lower = r.lower()
            if any(k in lower for k in error_keywords):
                return True
        return False
