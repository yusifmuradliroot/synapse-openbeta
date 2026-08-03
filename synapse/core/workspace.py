import shutil
from pathlib import Path
from synapse.core.config import WS_DIR

class Workspace:
    def __init__(self):
        self.active = "default"
        self.base = WS_DIR

    @property
    def path(self):
        return self.base / self.active

    def create(self, n):
        (self.base / n).mkdir(parents=True, exist_ok=True)

    def switch(self, n):
        p = self.base / n
        if p.exists():
            self.active = n
            return True
        return False

    def delete(self, n):
        p = self.base / n
        if p.exists() and n != "default":
            shutil.rmtree(p)
            return True
        return False

    def list_all(self):
        return [d.name for d in self.base.iterdir() if d.is_dir()]

    def list_files(self):
        return [f.name for f in self.path.iterdir() if f.is_file()] if self.path.exists() else []

    def resolve(self, f):
        p = (self.path / f).resolve()
        return p if str(p).startswith(str(self.base.resolve())) else None

    def read(self, f):
        p = self.resolve(f)
        return p.read_text(encoding="utf-8", errors="ignore") if p and p.exists() else None

    def write(self, f, c):
        p = self.resolve(f)
        if p:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(c.strip(), encoding="utf-8")
            return True
        return False

    def delete_file(self, f):
        p = self.resolve(f)
        if p and p.exists():
            p.unlink()
            return True
        return False
