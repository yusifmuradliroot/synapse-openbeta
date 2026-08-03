import re
from datetime import datetime
from synapse.core.config import init_config, load_json, save_json, CONFIG_PATH, DNA_PATH
from synapse.core.engine import Engine
from synapse.core.memory import MemoryManager
from synapse.core.history import HistoryManager
from synapse.core.workspace import Workspace
from synapse.core.agents import AgentController

class Synapsis:
    def __init__(self):
        init_config()
        self.cfg = load_json(CONFIG_PATH, {})
        self.dna = load_json(DNA_PATH, {"core_directives": [], "response_rules": []})
        self.engine = Engine()
        self.mem = MemoryManager()
        self.hist = HistoryManager()
        self.ws = Workspace()
        self.agent = AgentController(self.engine, self.ws, self.mem, self.hist)
        prov = self.cfg.get("default_provider", "nvidia")
        if not self.engine.apply(prov, self.cfg.get("providers", {})):
            raise ValueError(f"Provider '{prov}' not configured.")

    def switch_provider(self, name):
        if self.engine.apply(name, self.cfg.get("providers", {})):
            return True
        return False

    def build_messages(self, user_input):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msgs = [{"role": "system", "content": self.agent.build_prompt(self.dna, ts)}]
        msgs.extend(self.hist.get_context())
        msgs.append({"role": "user", "content": user_input})
        return msgs

    def stream_chat(self, user_input):
        msgs = self.build_messages(user_input)
        full = ""
        for ev, data in self.engine.stream(msgs):
            if ev == "content":
                full += data
                yield {"type": "content", "data": data}
            elif ev == "error":
                yield {"type": "error", "data": data}
                return
        clean, acts = self.agent.process(full)
        self.hist.add("user", user_input)
        self.hist.add("assistant", clean)
        self.hist._save()
        yield {"type": "actions", "data": acts}
        yield {"type": "done", "data": clean}

    def handle_command(self, cmd):
        cmd = cmd.strip()
        if cmd == "/chat":
            self.agent.set_mode("chat")
            return "[✓] Chat mode"
        if cmd == "/nativeagent":
            self.agent.set_mode("nativeagent")
            return "[✓] Native Agent mode"
        if cmd == "/crackagent":
            self.agent.set_mode("crackagent")
            return "[✓] Crack Agent mode"
        if cmd == "/memory":
            ms = self.mem.get_all()
            return "\n".join(f"{i}. {m}" for i, m in enumerate(ms, 1)) if ms else "No memories."
        if cmd == "/clear":
            self.mem.clear()
            self.hist.clear()
            return "[✓] Cleared"
        if cmd.startswith("/ws "):
            parts = cmd.split()
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub == "create" and len(parts) > 2:
                self.ws.create(parts[2])
                return f"[✓] Created {parts[2]}"
            if sub == "switch" and len(parts) > 2:
                return f"[✓] Switched" if self.ws.switch(parts[2]) else "[!] Not found"
            if sub == "list":
                return ", ".join(self.ws.list_all()) or "Empty"
            if sub == "delete" and len(parts) > 2:
                return f"[✓] Deleted" if self.ws.delete(parts[2]) else "[!] Invalid"
        if cmd.startswith("/"):
            p = cmd[1:].lower()
            if p in self.cfg.get("providers", {}):
                return f"[✓] {p.upper()}" if self.switch_provider(p) else "[!] Invalid key"
        return "[!] Unknown command"
