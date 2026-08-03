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
                meta = data.get("meta", {})
                self.sessions[f.stem] = meta
            except Exception:
                pass

    def create(self, title="New Chat"):
        sid = datetime.now().strftime("%Y%m%d_%H%M%S")
        data = {
            "meta": {"id": sid, "title": title, "created": datetime.now().isoformat()},
            "messages": []
        }
        (SESSIONS_DIR / (sid + ".json")).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.sessions[sid] = data["meta"]
        self.active_id = sid
        return sid

    def load(self, sid):
        path = SESSIONS_DIR / (sid + ".json")
        if path.exists():
            self.active_id = sid
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return {"meta": {"id": sid}, "messages": []}
        return None

    def save_messages(self, sid, messages):
        path = SESSIONS_DIR / (sid + ".json")
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {"meta": {"id": sid}, "messages": []}
            data["messages"] = messages
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

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

    def rename(self, sid, title):
        path = SESSIONS_DIR / (sid + ".json")
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                data["meta"]["title"] = title
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                if sid in self.sessions:
                    self.sessions[sid]["title"] = title
            except Exception:
                pass
