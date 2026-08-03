import os
import sys
from synapse.synapsis import Synapsis

def run_cli():
    try:
        app = Synapsis()
    except ValueError as e:
        print("\033[31m[!] " + str(e) + "\033[0m")
        return
    os.system('')
    print("\033[1;36m  SYNAPSE v3.0.0 CLI\033[0m")
    print("  \033[90m" + app.engine.provider_name.upper() + " | " + app.engine.model + " | " + app.agent.mode + "\033[0m\n")
    try:
        while True:
            try:
                ui = input("\033[1mYou:\033[0m ").strip()
            except EOFError:
                break
            if ui.lower() in ("exit", "quit"):
                print("\033[32mSaved.\033[0m"); break
            if ui.startswith("/"):
                print(app.handle_command(ui)); continue
            if not ui: continue
            in_thinking = False
            in_content = False
            for chunk in app.stream_chat(ui):
                ctype = chunk["type"]; cdata = chunk["data"]
                if ctype == "reasoning":
                    if not in_thinking: sys.stdout.write("\033[90m[Thinking] "); sys.stdout.flush(); in_thinking = True
                    sys.stdout.write(cdata); sys.stdout.flush()
                elif ctype == "content":
                    if in_thinking: sys.stdout.write("\033[0m\n"); in_thinking = False
                    if not in_content: sys.stdout.write("\033[1mAssistant:\033[0m "); sys.stdout.flush(); in_content = True
                    sys.stdout.write(cdata); sys.stdout.flush()
                elif ctype == "loop_status":
                    if in_thinking: sys.stdout.write("\033[0m\n"); in_thinking = False
                    if in_content: sys.stdout.write("\n"); in_content = False
                    print("\033[33m[Loop] " + cdata + "\033[0m")
                elif ctype == "action":
                    if in_content: sys.stdout.write("\n"); in_content = False
                    print("  \033[36m" + cdata + "\033[0m")
                elif ctype == "actions":
                    if in_content: sys.stdout.write("\n"); in_content = False
                    for a in cdata: print("  \033[36m" + a + "\033[0m")
                elif ctype == "error":
                    if in_thinking: sys.stdout.write("\033[0m\n")
                    print("\033[31m" + cdata + "\033[0m"); break
                elif ctype == "done":
                    if in_thinking: sys.stdout.write("\033[0m\n")
                    if in_content: sys.stdout.write("\n")
                    print("\033[90m[Tokens] In:" + str(app.engine.ctx_in) + " Out:" + str(app.engine.ctx_out) + "\033[0m\n")
    except KeyboardInterrupt:
        print("\n\033[33mSaved.\033[0m")
