from datetime import datetime
from synapse.core.config import HISTORY_PATH, load_json, save_json

MAX_CHARS = 1024

class HistoryManager:
    def __init__(self):
        self.data = load_json(HISTORY_PATH, {"compressed_3": "", "ultra_10": "", "recent": [], "total_chars": 0})
        self.compressed_3 = self.data.get("compressed_3", "")
        self.ultra_10 = self.data.get("ultra_10", "")
        self.recent = self.data.get("recent", [])
        self.total_chars = len(self.compressed_3) + len(self.ultra_10) + sum(len(m.get("content", "")) for m in self.recent)

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
        if self.ultra_10:
            ctx.append({"role": "system", "content": f"[Old Context] {self.ultra_10}"})
        if self.compressed_3:
            ctx.append({"role": "system", "content": f"[Recent Context] {self.compressed_3}"})
        ctx.extend(self.recent[-5:])
        return ctx

    def needs_optimization(self):
        return len(self.recent) >= 8 or self.total_chars > 700

    def optimize(self, ai_c3, ai_u10):
        self.compressed_3 = ai_c3[:400]
        self.ultra_10 = ai_u10[:400]
        self.recent = self.recent[-3:]
        self.total_chars = len(self.compressed_3) + len(self.ultra_10) + sum(len(m.get("content", "")) for m in self.recent)
        self._save()

    def _save(self):
        self.data = {"compressed_3": self.compressed_3, "ultra_10": self.ultra_10, "recent": self.recent, "total_chars": self.total_chars}
        save_json(HISTORY_PATH, self.data)

    def clear(self):
        self.compressed_3 = self.ultra_10 = ""
        self.recent = []
        self.total_chars = 0
        self._save()
