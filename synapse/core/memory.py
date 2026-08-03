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

    def get_all(self):
        return self.memories

    def needs_optimization(self):
        return self.total_chars > OPTIMIZE_AT

    def optimize(self, ai_list):
        self.memories = [m.strip() for m in ai_list if m.strip()]
        self.total_chars = sum(len(m) for m in self.memories)
        if self.total_chars > MAX_CHARS:
            self.memories = self.memories[-15:]
            self.total_chars = sum(len(m) for m in self.memories)
        self._save()

    def _save(self):
        self.data = {"memories": self.memories, "total_chars": self.total_chars}
        save_json(MEMORY_PATH, self.data)

    def clear(self):
        self.memories, self.total_chars = [], 0
        self._save()
