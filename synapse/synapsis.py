import re
from datetime import datetime
from synapse.core.config import init_config, load_json, save_json, CONFIG_PATH, DNA_PATH
from synapse.core.engine import Engine
from synapse.core.memory import MemoryManager
from synapse.core.history import HistoryManager
from synapse.core.workspace import Workspace
from synapse.core.agents import AgentController
from synapse.core.sessions import SessionManager

class Synapsis:
    def __init__(self):
        init_config()
        self.cfg = load_json(CONFIG_PATH, {})
        self.dna = load_json(DNA_PATH, {"core_directives": [], "response_rules": []})
        self.engine = Engine()
        self.mem = MemoryManager()
        self.hist = HistoryManager()
        self.ws = Workspace()
        self.sessions = SessionManager()
        self.agent = AgentController(self.engine, self.ws, self.mem, self.hist)
        self.current_session_msgs = []
        prov = self.cfg.get("default_provider", "nvidia")
        if not self.engine.apply(prov, self.cfg.get("providers", {})):
            raise ValueError("Provider '" + prov + "' not configured.")
        if not self.sessions.list_all():
            self.sessions.create("Default Session")

    def switch_provider(self, name):
        return self.engine.apply(name, self.cfg.get("providers", {}))

    def new_session(self, title="New Chat"):
        sid = self.sessions.create(title)
        self.current_session_msgs = []
        self.hist.clear()
        return sid

    def load_session(self, sid):
        data = self.sessions.load(sid)
        if data:
            self.current_session_msgs = data.get("messages", [])
            return True
        return False

    def delete_session(self, sid):
        self.sessions.delete(sid)
        if self.sessions.active_id == sid:
            self.current_session_msgs = []
            self.hist.clear()

    def list_sessions(self):
        return self.sessions.list_all()

    def build_messages(self, user_input):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msgs = [{"role": "system", "content": self.agent.build_prompt(self.dna, ts)}]
        for m in self.current_session_msgs[-10:]:
            msgs.append({"role": m["role"], "content": m["content"]})
        msgs.append({"role": "user", "content": user_input})
        return msgs

    def stream_chat(self, user_input):
        msgs = self.build_messages(user_input)
        full = ""
        for ev, data in self.engine.stream(msgs):
            if ev == "content":
                full += data
                yield {"type": "content", "data": data}
            elif ev == "reasoning":
                yield {"type": "reasoning", "data": data}
            elif ev == "error":
                yield {"type": "error", "data": data}
                return

        clean, acts = self.agent.process(full)
        self.current_session_msgs.append({"role": "user", "content": user_input})
        self.current_session_msgs.append({"role": "assistant", "content": clean})
        if self.sessions.active_id:
            self.sessions.save_messages(self.sessions.active_id, self.current_session_msgs)

        if acts:
            yield {"type": "actions", "data": acts}
        yield {"type": "done", "data": clean}

    def edit_and_resend(self, index, new_text):
        if 0 <= index < len(self.current_session_msgs):
            self.current_session_msgs = self.current_session_msgs[:index]
            if self.sessions.active_id:
                self.sessions.save_messages(self.sessions.active_id, self.current_session_msgs)
            return self.stream_chat(new_text)
        return iter([{"type": "error", "data": "Invalid message index"}])

    def handle_command(self, cmd):
        cmd = cmd.strip()
        if cmd == "/chat":
            self.agent.set_mode("chat")
            return "[OK] Chat mode"
        if cmd == "/nativeagent":
            self.agent.set_mode("nativeagent")
            return "[OK] Native Agent mode"
        if cmd == "/crackagent":
            self.agent.set_mode("crackagent")
            return "[OK] Crack Agent mode"
        if cmd == "/memory":
            ms = self.mem.get_all()
            return "\n".join(str(i) + ". " + m for i, m in enumerate(ms, 1)) if ms else "No memories."
        if cmd == "/clear":
            self.mem.clear()
            self.hist.clear()
            self.current_session_msgs = []
            if self.sessions.active_id:
                self.sessions.save_messages(self.sessions.active_id, [])
            return "[OK] Cleared"
        if cmd.startswith("/ws "):
            parts = cmd.split()
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub == "create" and len(parts) > 2:
                self.ws.create(parts[2])
                return "[OK] Created " + parts[2]
            if sub == "switch" and len(parts) > 2:
                return "[OK] Switched" if self.ws.switch(parts[2]) else "[!] Not found"
            if sub == "list":
                return ", ".join(self.ws.list_all()) or "Empty"
            if sub == "delete" and len(parts) > 2:
                return "[OK] Deleted" if self.ws.delete(parts[2]) else "[!] Invalid"
        if cmd.startswith("/"):
            p = cmd[1:].lower()
            if p in self.cfg.get("providers", {}):
                return "[OK] " + p.upper() if self.switch_provider(p) else "[!] Invalid key"
        return "[!] Unknown command"
