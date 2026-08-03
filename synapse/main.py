import sys
import os
import json
import tempfile
import zipfile
import hashlib
import urllib.request
import subprocess
import shutil
from pathlib import Path
from synapse import __version__
from synapse.core.config import load_json, save_json, CONFIG_PATH, init_config

REPO_ZIP_URL = "https://github.com/yusifmuradliroot/synapse-openbeta/archive/refs/heads/main.zip"

def get_installed_files():
    try:
        import synapse
        pkg_dir = Path(synapse.__file__).parent
        files = {}
        for p in pkg_dir.rglob("*.py"):
            rel = str(p.relative_to(pkg_dir))
            try:
                files[rel] = hashlib.md5(p.read_bytes()).hexdigest()
            except Exception:
                files[rel] = None
        return files
    except Exception:
        return {}

def get_new_files(tmpdir):
    files = {}
    pkg_dir = None
    for d in Path(tmpdir).iterdir():
        if d.is_dir() and (d / "synapse").exists():
            pkg_dir = d / "synapse"
            break
    if not pkg_dir:
        return None, files
    for p in pkg_dir.rglob("*.py"):
        rel = str(p.relative_to(pkg_dir))
        try:
            files[rel] = hashlib.md5(p.read_bytes()).hexdigest()
        except Exception:
            files[rel] = None
    return pkg_dir, files

def do_update():
    print(f"\033[33m[*] Checking updates (current: v{__version__})...\033[0m")
    
    old_files = get_installed_files()
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "repo.zip")
            print("\033[33m[*] Downloading latest version...\033[0m")
            urllib.request.urlretrieve(REPO_ZIP_URL, zip_path)
            
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(tmpdir)
            
            new_pkg_dir, new_files = get_new_files(tmpdir)
            if not new_pkg_dir:
                print("\033[31m[!] Could not find synapse package in download.\033[0m")
                return False
            
            changed = []
            added = []
            removed = []
            
            for f, h in new_files.items():
                if f not in old_files:
                    added.append(f)
                elif old_files[f] != h:
                    changed.append(f)
            
            for f in old_files:
                if f not in new_files:
                    removed.append(f)
            
            if not changed and not added and not removed:
                print("\033[32m[✓] Already up to date. No changes detected.\033[0m")
                return True
            
            print(f"\033[1;36m\n  Update: v{__version__} → latest\033[0m")
            print(f"  \033[1mChanged files:\033[0m")
            
            if changed:
                for f in sorted(changed):
                    print(f"    \033[33m[~] {f}\033[0m")
            if added:
                for f in sorted(added):
                    print(f"    \033[32m[+] {f}\033[0m")
            if removed:
                for f in sorted(removed):
                    print(f"    \033[31m[-] {f}\033[0m")
            
            if not changed and not added:
                print("    \033[90m(no functional changes)\033[0m")
            
            print(f"\n\033[33m[*] Installing update...\033[0m")
            repo_root = new_pkg_dir.parent
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--user", "--force-reinstall", "-q", str(repo_root)],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                print(f"\033[32m[✓] Update successful. Run 'synapse' to use new version.\033[0m")
                return True
            else:
                print(f"\033[31m[!] Install failed:\n{result.stderr.strip()}\033[0m")
                return False
                
    except Exception as e:
        print(f"\033[31m[!] Update error: {e}\033[0m")
        return False

def main():
    args = sys.argv[1:]
    init_config()
    cfg = load_json(CONFIG_PATH, {})

    if "--update" in args:
        do_update()
        sys.exit(0)

    if "--ver" in args:
        print(f"Synapse v{__version__}")
        sys.exit(0)

    if "--updatenotes" in args:
        print("""
SYNAPSE v3.0.0
- Modular architecture (core/, synapsis.py middleware)
- CLI & GUI separated
- File-level update detection
- Memory: max 2048 chars, optimize at 256
- History: max 1024 chars, compressed tiers
- Agent modes: /chat, /nativeagent, /crackagent
- Web GUI (Termux compatible)
""")
        sys.exit(0)

    if "--reset" in args:
        if input("\033[31m[!] Delete all Synapse data? Type RESET: \033[0m").strip() == "RESET":
            p = Path.home() / "synapse"
            if p.exists():
                shutil.rmtree(p)
            print("\033[32m[✓] Reset complete.\033[0m")
        sys.exit(0)

    if "--defaultinterface" in args:
        idx = args.index("--defaultinterface")
        if idx + 1 < len(args):
            mode = args[idx + 1].lower().lstrip("-")
            if mode in ("cli", "gui"):
                cfg["default_interface"] = mode
                save_json(CONFIG_PATH, cfg)
                print(f"[✓] Default interface: {mode.upper()}")
            else:
                print("[!] Use --cli or --gui")
        sys.exit(0)

    if "--cli" in args:
        from synapse.cli import run_cli
        run_cli()
    elif "--gui" in args:
        from synapse.gui import run_gui
        run_gui()
    else:
        default = cfg.get("default_interface", "cli")
        if default == "gui":
            from synapse.gui import run_gui
            run_gui()
        else:
            from synapse.cli import run_cli
            run_cli()

if __name__ == "__main__":
    main()
