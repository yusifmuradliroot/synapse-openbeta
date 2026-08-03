import json
import socket
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from synapse.synapsis import Synapsis
from synapse.core.config import load_context, save_context
from synapse.core.gui_html import get_html

HTML = get_html()
app = None

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt, *args):
        pass

    def _json(self, data, code=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception:
            return {}

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            data = HTML.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path == '/api/sessions':
            sessions = app.list_sessions()
            active = app.sessions.active_id
            self._json({"sessions": [{"id": s["id"], "title": s["title"], "active": s["id"] == active} for s in sessions]})
        elif self.path == '/api/history':
            self._json({"messages": [{"role": m["role"], "content": m["content"]} for m in app.current_session_msgs]})
        elif self.path == '/api/settings':
            ctx = app.get_context()
            mode = app.get_mode()
            self._json({
                "system_prompt": app.custom_system_prompt,
                "providers": ctx.get("providers", {}),
                "default_provider": ctx.get("active_provider", ""),
                "mode": mode,
                "mode_params": ctx.get("modes", {}).get(mode, {}),
                "agent_settings": ctx.get("agent", {})
            })
        elif self.path == '/api/code_context':
            self._json({"code_context": app.code_context})
        else:
            self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()

    def do_POST(self):
        body = self._body()
        if self.path == '/api/session/new':
            self._json({"id": app.new_session()})
        elif self.path == '/api/session/load':
            self._json({"ok": app.load_session(body.get("id", ""))})
        elif self.path == '/api/session/delete':
            app.delete_session(body.get("id", ""))
            self._json({"ok": True})
        elif self.path == '/api/session/rename':
            app.rename_session(body.get("id", ""), body.get("title", ""))
            self._json({"ok": True})
        elif self.path == '/api/settings/save':
            app.set_system_prompt(body.get("system_prompt", ""))
            self._json({"ok": True})
        elif self.path == '/api/mode':
            self._json({"ok": app.set_mode(body.get("mode", "chat")), "mode": app.get_mode()})
        elif self.path == '/api/params/save':
            mode = body.get("mode", "chat")
            ctx = app.get_context()
            if mode not in ctx.get("modes", {}):
                ctx["modes"][mode] = {}
            ctx["modes"][mode]["temperature"] = body.get("temperature", 0.5)
            ctx["modes"][mode]["top_p"] = body.get("top_p", 0.9)
            ctx["modes"][mode]["max_tokens"] = body.get("max_tokens", 2048)
            ctx["modes"][mode]["reasoning_budget"] = body.get("reasoning_budget", 1024)
            save_context(ctx)
            if mode == app.get_mode():
                app.set_mode(mode)
            self._json({"ok": True})
        elif self.path == '/api/agent/save':
            ctx = app.get_context()
            ctx["agent"]["max_loops"] = body.get("max_loops", 25)
            ctx["agent"]["max_cmd_timeout"] = body.get("max_cmd_timeout", 30)
            ctx["agent"]["auto_verify"] = body.get("auto_verify", True)
            save_context(ctx)
            self._json({"ok": True})
        elif self.path == '/api/providers/save':
            try:
                ctx = app.get_context()
                prov = body.get("provider", "")
                if prov and prov in ctx.get("providers", {}):
                    if body.get("model"):
                        ctx["providers"][prov]["model"] = body["model"]
                    if body.get("api_key"):
                        ctx["providers"][prov]["api_key"] = body["api_key"]
                    save_context(ctx)
                    app.switch_provider(prov)
                    self._json({"ok": True})
                else:
                    self._json({"ok": False, "error": "Provider not found"})
            except Exception as e:
                self._json({"ok": False, "error": str(e)})
        elif self.path == '/api/chat':
            self._chat(body)
        else:
            self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()

    def _chat(self, body):
        msg = body.get('message', '').strip()
        edit_idx = body.get('edit_index', -1)
        sid = body.get('session_id', None)
        if not msg:
            self.send_response(400)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        try:
            if edit_idx >= 0:
                stream = app.edit_and_resend(edit_idx, msg, sid)
            else:
                stream = app.stream_chat(msg, sid)
            for chunk in stream:
                ct = chunk.get("type", "")
                cd = chunk.get("data", "")
                if ct in ("reasoning", "content", "error", "loop_status", "action"):
                    payload = json.dumps({"type": ct, "content": cd})
                    out = "data: " + payload + "\n\n"
                    self.wfile.write(out.encode('utf-8'))
                    self.wfile.flush()
                elif ct == "actions":
                    for a in (cd if isinstance(cd, list) else []):
                        payload = json.dumps({"type": "action", "content": a})
                        out = "data: " + payload + "\n\n"
                        self.wfile.write(out.encode('utf-8'))
                        self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except BrokenPipeError:
            pass
        except Exception as e:
            try:
                payload = json.dumps({"type": "error", "content": str(e)})
                out = "data: " + payload + "\n\n"
                self.wfile.write(out.encode('utf-8'))
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except Exception:
                pass

def find_free_port(start=8080, tries=20):
    for p in range(start, start + tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', p))
                return p
        except OSError:
            continue
    return None

def run_gui():
    global app
    try:
        app = Synapsis()
    except ValueError as e:
        print("[!] " + str(e))
        return
    port = find_free_port()
    if not port:
        print("\033[31m[!] No free port.\033[0m")
        return
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    url = "http://127.0.0.1:" + str(port)
    print("\033[1;36m  SYNAPSE v4.0.0\033[0m")
    print("  \033[32mRunning at " + url + "\033[0m")
    print("  Press Ctrl+C to stop.\n")
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("\n[✓] Stopped.")
