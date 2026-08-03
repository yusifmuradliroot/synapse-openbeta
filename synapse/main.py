import sys
import shutil
from pathlib import Path
from synapse import __version__
from synapse.core.config import load_json, save_json, CONFIG_PATH, init_config

def main():
    args = sys.argv[1:]
    init_config()
    cfg = load_json(CONFIG_PATH, {})

    if "--update" in args:
        from synapse.updateengine import compare_and_update
        compare_and_update()
        sys.exit(0)

    if "--reinstall" in args:
        from synapse.updateengine import full_reinstall
        full_reinstall()
        sys.exit(0)

    if "--ver" in args:
        print("Synapse v" + __version__)
        sys.exit(0)

    if "--updatenotes" in args:
        print("""
SYNAPSE v3.0.0
- UpdateEngine: File-level sync, bypasses pip
- GUI: Fixed SSE streaming, no f-string errors
- CLI & GUI separated
- Memory: max 2048 chars, optimize at 256
- History: max 1024 chars, compressed tiers
- Agent modes: /chat, /nativeagent, /crackagent
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
                print("[✓] Default interface: " + mode.upper())
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
