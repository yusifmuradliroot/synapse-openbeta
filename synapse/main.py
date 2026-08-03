import sys
import shutil
from pathlib import Path
from synapse import __version__
from synapse.core.config import load_context, save_context, CONTEXT_PATH, init_config, BASE_DIR

REPO_ZIP_URL = "https://github.com/yusifmuradliroot/synapse-openbeta/archive/refs/heads/main.zip"

def main():
    args = sys.argv[1:]
    init_config()
    ctx = load_context()

    if "--update" in args:
        try:
            from synapse.updateengine import compare_and_update
            compare_and_update()
        except ImportError:
            print("[!] updateengine.py not found. Run: pip install --user --force-reinstall .")
        sys.exit(0)

    if "--ver" in args:
        print("Synapse v" + __version__)
        sys.exit(0)

    if "--updatenotes" in args:
        print("""
SYNAPSE v4.0.0
- context.json unified config system
- Three modes: Chat, Code, Agent with per-mode parameters
- Plan-Execute-Verify-Fix agent workflow
- Auto error detection and fix loop
- File edit support (<{ws_edit}>)
- GUI settings: General, Provider, Parameters, Agent tabs
- Temperature, top_p, max_tokens, reasoning_budget per mode
- Agent settings: max_loops, timeout, auto_verify, plan_first
- Terminal access in Agent mode
- Code panel with HTML preview
- Session persistence and background processing
""")
        sys.exit(0)

    if "--reset" in args:
        if input("\033[31m[!] Delete all Synapse data? Type RESET: \033[0m").strip() == "RESET":
            if BASE_DIR.exists():
                shutil.rmtree(BASE_DIR)
            print("\033[32m[✓] Reset complete.\033[0m")
        sys.exit(0)

    if "--defaultinterface" in args:
        idx = args.index("--defaultinterface")
        if idx + 1 < len(args):
            mode = args[idx + 1].lower().lstrip("-")
            if mode in ("cli", "gui"):
                ctx["interface"] = mode
                save_context(ctx)
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
        default = ctx.get("interface", "cli")
        if default == "gui":
            from synapse.gui import run_gui
            run_gui()
        else:
            from synapse.cli import run_cli
            run_cli()

if __name__ == "__main__":
    main()
