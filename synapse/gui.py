import json
import socket
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from synapse.synapsis import Synapsis

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Synapse v3.0.0</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;height:100vh;height:100dvh;display:flex;flex-direction:column}
header{padding:10px 16px;border-bottom:1px solid #30363d;background:#010409;display:flex;justify-content:space-between;align-items:center;flex-shrink:0}
h1{font-size:15px;color:#58a6ff;font-weight:700}
#status{font-size:11px;color:#8b949e}
#chat{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;-webkit-overflow-scrolling:touch}
.msg{max-width:88%;padding:10px 14px;border-radius:12px;font-size:14px;white-space:pre-wrap;word-break:break-word;line-height:1.6}
.user{align-self:flex-end;background:#161b22;border:1px solid #30363d}
.ai{align-self:flex-start;background:#1f2937;border:1px solid #30363d}
.err{align-self:flex-start;background:#2d1117;border:1px solid #f85149;color:#f85149}
#input-area{padding:10px 12px;border-top:1px solid #30363d;display:flex;gap:8px;background:#010409;flex-shrink:0}
#inp{flex:1;background:#161b22;border:1px solid #30363d;color:#c9d1d9;padding:10px 12px;border-radius:10px;outline:none;font-size:15px}
#inp:focus{border-color:#58a6ff}
#send{background:#238636;color:#fff;border:none;padding:10px 18px;border-radius:10px;cursor:pointer;font-weight:600;font-size:14px}
#send:active{background:#2ea043}
#send:disabled{opacity:0.4;cursor:default}
</style>
</head>
<body>
<header>
  <h1>SYNAPSE v3.0.0</h1>
  <span id="status">Ready</span>
</header>
<div id="chat"></div>
<div id="input-area">
  <input id="inp" type="text" placeholder="Message..." autocomplete="off">
  <button id="send" type="button">Send</button>
</div>
<script>
var chat = document.getElementById('chat');
var inp = document.getElementById('inp');
var btn = document.getElementById('send');
var st = document.getElementById('status');
var busy = false;

function addMsg(role, text) {
  var d = document.createElement('div');
  d.className = 'msg ' + role;
  d.textContent = text;
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
  return d;
}

function setBusy(v) {
  busy = v;
  btn.disabled = v;
  st.textContent = v ? 'Thinking...' : 'Ready';
}

function sendMsg() {
  var t = inp.value.trim();
  if (!t || busy) return;
  inp.value = '';
  setBusy(true);
  addMsg('user', t);
  var aiBox = addMsg('ai', '');

  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/chat', true);
  xhr.setRequestHeader('Content-Type', 'application/json');

  xhr.onprogress = function() {
    var lines = xhr.responseText.split('\\n');
    var txt = '';
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      if (line.indexOf('data: ') === 0) {
        var payload = line.substring(6);
        if (payload === '[DONE]') continue;
        try {
          var obj = JSON.parse(payload);
          if (obj.content) txt += obj.content;
        } catch(e) {}
      }
    }
    aiBox.textContent = txt;
    chat.scrollTop = chat.scrollHeight;
  };

  xhr.onload = function() {
    setBusy(false);
    if (xhr.status !== 200) {
      aiBox.className = 'msg err';
      aiBox.textContent = '[HTTP Error] ' + xhr.status;
    }
  };

  xhr.onerror = function() {
    setBusy(false);
    aiBox.className = 'msg err';
    aiBox.textContent = '[Network Error] Connection failed.';
  };

  xhr.send(JSON.stringify({message: t}));
}

btn.addEventListener('click', sendMsg);
inp.addEventListener('keydown', function(e) {
  if (e.key === 'Enter') {
    e.preventDefault();
    sendMsg();
  }
});
</script>
</body>
</html>"""

app = None

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            data = HTML.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()

    def do_POST(self):
        if self.path != '/api/chat':
            self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return

        try:
            length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(length)
            body = json.loads(raw.decode('utf-8'))
            msg = body.get('message', '').strip()
        except Exception:
            msg = ''

        if not msg:
            self.send_response(400)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return

        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Accel-Buffering', 'no')
        self.end_headers()

        try:
            for chunk in app.stream_chat(msg):
                ctype = chunk.get("type", "")
                cdata = chunk.get("data", "")

                if ctype == "content":
                    payload = json.dumps({"content": cdata})
                    out = "data: " + payload + "\n\n"
                    self.wfile.write(out.encode('utf-8'))
                    self.wfile.flush()
                elif ctype == "error":
                    payload = json.dumps({"content": "[Error] " + str(cdata)})
                    out = "data: " + payload + "\n\n"
                    self.wfile.write(out.encode('utf-8'))
                    self.wfile.flush()
                elif ctype == "actions":
                    acts = cdata if isinstance(cdata, list) else []
                    for a in acts:
                        payload = json.dumps({"content": a + "\n"})
                        out = "data: " + payload + "\n\n"
                        self.wfile.write(out.encode('utf-8'))
                        self.wfile.flush()

            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

        except BrokenPipeError:
            pass
        except Exception as e:
            try:
                payload = json.dumps({"content": "[Server Error] " + str(e)})
                out = "data: " + payload + "\n\n"
                self.wfile.write(out.encode('utf-8'))
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except Exception:
                pass

def find_free_port(start=8080, max_tries=20):
    for port in range(start, start + max_tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                return port
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
    if port is None:
        print("\033[31m[!] No free port found (8080-8099).\033[0m")
        return

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    url = "http://127.0.0.1:" + str(port)

    print("\033[1;36m  SYNAPSE v3.0.0 GUI\033[0m")
    print("  \033[32mRunning at " + url + "\033[0m")
    print("  Open this URL in your browser.")
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
