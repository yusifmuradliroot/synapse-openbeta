import json
from pathlib import Path
from datetime import datetime
from synapse.core.config import BASE_DIR

SESSIONS_DIR = BASE_DIR / "sessions"

class SessionManager:
    def __init__(self):
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self.active_id = None
        self.sessions = {}
        self._load_index()

    def _load_index(self):
        self.sessions = {}
        for f in SESSIONS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                self.sessions[f.stem] = data.get("meta", {})
            except Exception:
                pass

    def create(self, title="New Chat"):
        sid = datetime.now().strftime("%Y%m%d_%H%M%S")
        data = {
            "meta": {"id": sid, "title": title, "created": datetime.now().isoformat()},
            "messages": [],
            "code_context": {},
            "pinned_files": [],
            "system_prompt": ""
        }
        (SESSIONS_DIR / (sid + ".json")).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.sessions[sid] = data["meta"]
        self.active_id = sid
        return sid

    def _read(self, sid):
        path = SESSIONS_DIR / (sid + ".json")
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    def _write(self, sid, data):
        path = SESSIONS_DIR / (sid + ".json")
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load(self, sid):
        data = self._read(sid)
        if data:
            self.active_id = sid
            return data
        return None

    def save_messages(self, sid, messages):
        data = self._read(sid)
        if data:
            data["messages"] = messages
            self._write(sid, data)

    def save_code_context(self, sid, code_ctx):
        data = self._read(sid)
        if data:
            data["code_context"] = code_ctx
            self._write(sid, data)

    def save_pinned_files(self, sid, pinned):
        data = self._read(sid)
        if data:
            data["pinned_files"] = pinned
            self._write(sid, data)

    def save_system_prompt(self, sid, prompt):
        data = self._read(sid)
        if data:
            data["system_prompt"] = prompt
            self._write(sid, data)

    def rename(self, sid, title):
        data = self._read(sid)
        if data:
            data["meta"]["title"] = title
            self._write(sid, data)
            if sid in self.sessions:
                self.sessions[sid]["title"] = title

    def delete(self, sid):
        path = SESSIONS_DIR / (sid + ".json")
        if path.exists():
            path.unlink()
        if sid in self.sessions:
            del self.sessions[sid]
        if self.active_id == sid:
            self.active_id = None

    def list_all(self):
        return [{"id": k, "title": v.get("title", "Untitled"), "created": v.get("created", "")} for k, v in self.sessions.items()]
