import subprocess
import os

MAX_TIMEOUT = 30
MAX_OUTPUT = 8000

class TerminalExecutor:
    def __init__(self):
        self.cwd = os.path.expanduser("~")

    def execute(self, command, timeout=None):
        try:
            command = command.strip()
            if not command:
                return {"ok": False, "output": "[Error] Empty command"}
            if command.startswith("cd "):
                target = command[3:].strip()
                new_path = os.path.expanduser(target)
                if os.path.isdir(new_path):
                    self.cwd = new_path
                    return {"ok": True, "output": "[OK] " + new_path}
                return {"ok": False, "output": "[Error] Not found: " + target}
            t = timeout or MAX_TIMEOUT
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=t, cwd=self.cwd)
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += ("\n[STDERR]\n" + result.stderr) if output else result.stderr
            if not output.strip():
                output = "[OK] (no output)"
            if len(output) > MAX_OUTPUT:
                output = output[:MAX_OUTPUT] + "\n...[truncated]"
            return {"ok": result.returncode == 0, "output": output}
        except subprocess.TimeoutExpired:
            return {"ok": False, "output": f"[Error] Timeout ({timeout or MAX_TIMEOUT}s)"}
        except Exception as e:
            return {"ok": False, "output": "[Error] " + str(e)}

    def get_tree(self, max_depth=2):
        try:
            result = subprocess.run(f"find . -maxdepth {max_depth} -type f | head -50", shell=True, capture_output=True, text=True, timeout=5, cwd=self.cwd)
            return result.stdout.strip() or "[Empty]"
        except Exception:
            return "[Error]"
