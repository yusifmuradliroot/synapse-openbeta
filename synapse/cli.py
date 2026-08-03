import os
from synapse.synapsis import Synapsis

def run_cli():
    try:
        app = Synapsis()
    except ValueError as e:
        print(f"\033[31m[!] {e}\033[0m")
        return

    os.system('')
    print("\033[1;36m  SYNAPSE v3.0.0 CLI\033[0m")
    print(f"  \033[90m{app.engine.provider_name.upper()} | {app.engine.model} | {app.agent.mode}\033[0m\n")

    try:
        while True:
            try:
                ui = input("\033[1mYou:\033[0m ").strip()
            except EOFError:
                break
            if ui.lower() in ("exit", "quit"):
                print("\033[32mSaved.\033[0m")
                break
            if ui.startswith("/"):
                print(app.handle_command(ui))
                continue
            if not ui:
                continue

            print("\033[90m[Thinking...]\033[0m", end="", flush=True)
            last = ""
            for chunk in app.stream_chat(ui):
                if chunk["type"] == "content":
                    last += chunk["data"]
                    print(f"\r\033[90m[Gen {len(last)}c]\033[0m", end="", flush=True)
                elif chunk["type"] == "error":
                    print(f"\n\033[31m{chunk['data']}\033[0m")
                    break
                elif chunk["type"] == "actions":
                    for a in chunk["data"]:
                        print(f"\n  \033[36m{a}\033[0m")
                elif chunk["type"] == "done":
                    print(f"\n\n\033[1mAssistant:\033[0m\n{chunk['data']}\n")
    except KeyboardInterrupt:
        print("\n\033[33mSaved.\033[0m")
