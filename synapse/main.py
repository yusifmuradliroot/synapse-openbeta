import sys
import subprocess
from synapse import __version__
from synapse.core.config import load_json, save_json, CONFIG_PATH, init_config

REPO_URL = "git+https://github.com/yusifmuradliroot/synapse-openbeta.git"

def main():
    args = sys.argv[1:]
    init_config()
    cfg = load_json(CONFIG_PATH, {})

    if "--update" in args:
        print(f"\033[33m[*] Updating Synapse (current: v{__version__})...\033[0m")
        res = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "--user", REPO_URL], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"\033[32m[✓] Updated to latest. Restart 'synapse'.\033[0m")
        else:
            print(f"\033[31m[!] Update failed:\n{res.stderr.strip()}\033[0m")
        sys.exit(0)

    if "--ver" in args:
        print(f"Synapse v{__version__}")
        sys.exit(0)

    if "--reset" in args:
        if input("\033[31m[!] Delete all Synapse data? Type RESET: \033[0m").strip() == "RESET":
            import shutil
            from pathlib import Path
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
