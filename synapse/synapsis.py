import re
from datetime import datetime
from synapse.core.config import init_config, load_json, save_json, CONFIG_PATH, DNA_PATH
from synapse.core.engine import Engine
from synapse.core.memory import MemoryManager
from synapse.core.history import HistoryManager
from synapse.core.workspace import Workspace
from synapse.core.agents import AgentController, MODE_CHAT, MODE_CODE, MODE_AGENT
from synapse.core.sessions import SessionManager
from synapse.core.terminal import TerminalExecutor

MAX_LOOPS = 25

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
        self.terminal = TerminalExecutor()
        self.agent = AgentController(self.engine, self.ws, self.mem, self.hist)
        self.current_session_msgs = []
        self.code_context = {}
        self.pinned_files = []
        self.custom_system_prompt = ""
        self.active_session_id = None
        prov = self.cfg.get("default_provider", "nvidia")
        if not self.engine.apply(prov, self.cfg.get("providers", {})):
            raise ValueError("Provider '" + prov + "' not configured.")
        if not self.sessions.list_all():
            self.sessions.create("Default Session")
        self._load_active_session()

    def _load_active_session(self):
        if self.sessions.active_id:
            self.active_session_id = self.sessions.active_id
            data = self.sessions.load(self.sessions.active_id)
            if data:
                self.current_session_msgs = data.get("messages", [])
                self.code_context = data.get("code_context", {})
                self.pinned_files = data.get("pinned_files", [])
                self.custom_system_prompt = data.get("system_prompt", "")

    def _load_session_snapshot(self, sid):
        data = self.sessions.load(sid) if sid else None
        if not data:
            return [], {}, [], ""
        return (
            list(data.get("messages", [])),
            dict(data.get("code_context", {})),
            list(data.get("pinned_files", [])),
            data.get("system_prompt", "")
        )

    def switch_provider(self, name):
        return self.engine.apply(name, self.cfg.get("providers", {}))

    def set_mode(self, mode):
        return self.agent.set_mode(mode)

    def get_mode(self):
        return self.agent.mode

    def new_session(self, title="New Chat"):
        sid = self.sessions.create(title)
        self.current_session_msgs = []
        self.code_context = {}
        self.pinned_files = []
        self.custom_system_prompt = ""
        self.active_session_id = sid
        return sid

    def load_session(self, sid):
        data = self.sessions.load(sid)
        if data:
            self.active_session_id = sid
            self.current_session_msgs = data.get("messages", [])
            self.code_context = data.get("code_context", {})
            self.pinned_files = data.get("pinned_files", [])
            self.custom_system_prompt = data.get("system_prompt", "")
            return True
        return False

    def delete_session(self, sid):
        self.sessions.delete(sid)
        if self.active_session_id == sid:
            self.current_session_msgs = []
            self.code_context = {}
            self.pinned_files = []
            self.custom_system_prompt = ""
            self.active_session_id = None

    def rename_session(self, sid, title):
        self.sessions.rename(sid, title)

    def list_sessions(self):
        return self.sessions.list_all()

    def set_system_prompt(self, prompt):
        self.custom_system_prompt = prompt
        if self.active_session_id:
            self.sessions.save_system_prompt(self.active_session_id, prompt)

    def add_pinned_file(self, fname):
        if fname not in self.pinned_files:
            self.pinned_files.append(fname)
            if self.active_session_id:
                self.sessions.save_pinned_files(self.active_session_id, self.pinned_files)

    def remove_pinned_file(self, fname):
        if fname in self.pinned_files:
            self.pinned_files.remove(fname)
            if self.active_session_id:
                self.sessions.save_pinned_files(self.active_session_id, self.pinned_files)

    def _build_system_block(self, code_ctx, pinned, sys_prompt):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        parts = []
        if sys_prompt:
            parts.append(sys_prompt)
        parts.append(self.agent.build_prompt(self.dna, ts))
        if pinned:
            pc = "PINNED FILES:\n"
            for fname in pinned:
                content = self.ws.read(fname)
                if content:
                    pc += "\n--- " + fname + " ---\n" + content + "\n"
            parts.append(pc)
        if code_ctx:
            cc = "AI-GENERATED CODE FILES:\n"
            for fname, content in code_ctx.items():
                cc += "\n--- " + fname + " ---\n" + content + "\n"
            parts.append(cc)
        return "\n\n".join(parts)

    def _build_loop_messages(self, loop_context, current_prompt, session_msgs, code_ctx, pinned, sys_prompt):
        system_content = self._build_system_block(code_ctx, pinned, sys_prompt)
        msgs = [{"role": "system", "content": system_content}]
        for m in session_msgs[-10:]:
            msgs.append({"role": m["role"], "content": m["content"]})
        msgs.extend(loop_context)
        msgs.append({"role": "user", "content": current_prompt})
        return msgs

    def _extract_code_context(self, full_response, code_ctx):
        writes = re.findall(r'<\{ws_write\(([^)]+)\)\}>(.*?)<\{/ws_write\}>', full_response, re.DOTALL)
        for fname, content in writes:
            code_ctx[fname] = content.strip()

    def _execute_commands(self, content):
        cmds = self.agent.extract_commands(content)
        results = []
        for cmd in cmds:
            res = self.terminal.execute(cmd)
            results.append(f"[CMD] {cmd}\n{res['output']}")
        return results

    def stream_chat(self, user_input, session_id=None):
        sid = session_id or self.active_session_id
        session_msgs, code_ctx, pinned, sys_prompt = self._load_session_snapshot(sid)
        original_input = user_input
        current_prompt = user_input
        loop_context = []
        loop_count = 0
        partial_content = ""
        saved = False
        mode = self.agent.mode

        try:
            while loop_count <= MAX_LOOPS:
                msgs = self._build_loop_messages(loop_context, current_prompt, session_msgs, code_ctx, pinned, sys_prompt)
                full = ""

                for ev, data in self.engine.stream(msgs):
                    if ev == "content":
                        full += data
                        partial_content += data
                        yield {"type": "content", "data": data}
                    elif ev == "reasoning":
                        yield {"type": "reasoning", "data": data}
                    elif ev == "error":
                        yield {"type": "error", "data": data}
                        return

                cmd_results = self._execute_commands(full)
                if cmd_results:
                    for cr in cmd_results:
                        yield {"type": "action", "data": cr}

                has_uncompleted = "<{uncompleted}>" in full
                has_actions = self.agent.has_actions(full) or len(cmd_results) > 0
                should_loop = has_uncompleted or (has_actions and mode == MODE_AGENT)

                if should_loop:
                    loop_count += 1
                    if loop_count > MAX_LOOPS:
                        yield {"type": "error", "data": "Max loop limit reached."}
                        break

                    clean_resp = full.replace("<{uncompleted}>", "").strip()
                    self._extract_code_context(full, code_ctx)
                    if sid:
                        self.sessions.save_code_context(sid, code_ctx)

                    loop_context.append({"role": "assistant", "content": clean_resp})
                    if cmd_results:
                        loop_context.append({"role": "user", "content": "<{resume}> Command results:\n" + "\n".join(cmd_results) + "\nAnalyze results and continue."})
                    else:
                        loop_context.append({"role": "user", "content": "<{resume}> Continue with the next step."})
                    current_prompt = loop_context[-1]["content"]
                    yield {"type": "loop_status", "data": "Step " + str(loop_count) + "/" + str(MAX_LOOPS) + " - Continuing..."}
                    continue
                else:
                    clean, acts = self.agent.process(full)
                    self._extract_code_context(full, code_ctx)
                    session_msgs.append({"role": "user", "content": original_input})
                    session_msgs.append({"role": "assistant", "content": clean})
                    if sid:
                        self.sessions.save_messages(sid, session_msgs)
                        self.sessions.save_code_context(sid, code_ctx)
                    if sid == self.active_session_id:
                        self.current_session_msgs = session_msgs
                        self.code_context = code_ctx
                    saved = True
                    if acts:
                        yield {"type": "actions", "data": acts}
                    yield {"type": "done", "data": clean}
                    break

        except GeneratorExit:
            pass
        finally:
            if not saved and partial_content.strip():
                clean, _ = self.agent.process(partial_content)
                session_msgs.append({"role": "user", "content": original_input})
                session_msgs.append({"role": "assistant", "content": clean + "\n\n[Response interrupted]"})
                self._extract_code_context(partial_content, code_ctx)
                if sid:
                    self.sessions.save_messages(sid, session_msgs)
                    self.sessions.save_code_context(sid, code_ctx)

    def edit_and_resend(self, index, new_text, session_id=None):
        sid = session_id or self.active_session_id
        session_msgs, _, _, _ = self._load_session_snapshot(sid)
        if 0 <= index < len(session_msgs):
            session_msgs = session_msgs[:index]
            if sid:
                self.sessions.save_messages(sid, session_msgs)
            return self.stream_chat(new_text, sid)
        return iter([{"type": "error", "data": "Invalid message index"}])

    def handle_command(self, cmd):
        cmd = cmd.strip()
        if cmd == "/chat":
            self.set_mode(MODE_CHAT)
            return "[OK] Chat mode"
        if cmd == "/code":
            self.set_mode(MODE_CODE)
            return "[OK] Code mode"
        if cmd == "/agent":
            self.set_mode(MODE_AGENT)
            return "[OK] Agent mode"
        if cmd == "/memory":
            ms = self.mem.get_all()
            return "\n".join(str(i) + ". " + m for i, m in enumerate(ms, 1)) if ms else "No memories."
        if cmd == "/clear":
            self.mem.clear()
            self.current_session_msgs = []
            self.code_context = {}
            if self.active_session_id:
                self.sessions.save_messages(self.active_session_id, [])
                self.sessions.save_code_context(self.active_session_id, {})
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
