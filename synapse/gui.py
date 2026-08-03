import json
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from synapse.synapsis import Synapsis

HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Synapse v3.0.0</title>
<style>:root{--bg:#0d1117;--fg:#c9d1d9;--acc:#58a6ff;--bdr:#30363d}*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:system-ui;height:100vh;display:flex;flex-direction:column}
header{padding:12px 16px;border-bottom:1px solid var(--bdr);background:#010409;display:flex;justify-content:space-between}
h1{font-size:16px;color:var(--acc)}#status{font-size:12px;color:#8b949e}
#chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}
.msg{max-width:85%;padding:10px 14px;border-radius:12px;font-size:14px;white-space:pre-wrap;word-break:break-word;line-height:1.5}
.user{align-self:flex-end;background:#161b22;border:1px solid var(--bdr)}
.ai{align-self:flex-start;background:#1f2937;border:1px solid var(--bdr)}
#input-area{padding:12px;border-top:1px solid var(--bdr);display:flex;gap:8px;background:#010409}
#inp{flex:1;background:#161b22;border:1px solid var(--bdr);color:var(--fg);padding:10px;border-radius:8px;outline:none}
#send{background:var(--acc);color:#fff;border:none;padding:0 16px;border-radius:8px;cursor:pointer;font-weight:600}
</style></head><body>
<header><h1>SYNAPSE v3.0.0</h1><span id="status">Ready</span></header>
<div id="chat"></div>
<div id="input-area"><input id="inp" placeholder="Type..." autocomplete="off"><button id="send">Send</button></div>
<script>
const chat=document.getElementById('chat'),inp=document.getElementById('inp'),btn=document.getElementById('send'),st=document.getElementById('status');
let cur=null;
function add(r,t){const d=document.createElement('div');d.className='msg '+r;d.textContent=t;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d;}
async function send(){
 const t=inp.value.trim();if(!t)return;inp.value='';btn.disabled=true;st.textContent='Thinking...';
 add('user',t);cur=add('ai','');
 try{
  const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:t})});
  const rd=r.body.getReader(),dec=new TextDecoder();let buf='';
  while(true){const{done,value}=await rd.read();if(done)break;buf+=dec.decode(value,{stream:true});
   const ls=buf.split('\\n');buf=ls.pop();
   for(const l of ls){if(l.startsWith('data: ')){const d=l.slice(6);if(d==='[DONE]'){st.textContent='Ready';btn.disabled=false;return;}
    try{const p=JSON.parse(d);if(p.content){cur.textContent+=p.content;chat.scrollTop=chat.scrollHeight;}}catch(e){}}}}
 }catch(e){cur.textContent='[Error] '+e.message;st.textContent='Error';btn.disabled=false;}
}
btn.onclick=send;inp.onkeydown=e=>{if(e.key==='Enter')send()};
</script></body></html>"""

app = None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != '/api/chat':
            self.send_response(404)
            self.end_headers()
            return
        
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length))
        msg = body.get('message', '')
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        
        try:
            for chunk in app.stream_chat(msg):
                ctype = chunk["type"]
                cdata = chunk["data"]
                
                if ctype == "content":
                    payload = json.dumps({"content": cdata})
                    line = "data: " + payload + "\n\n"
                    self.wfile.write(line.encode())
                    self.wfile.flush()
                elif ctype == "error":
                    err_msg = "[Error] " + str(cdata)
                    payload = json.dumps({"content": err_msg})
                    line = "data: " + payload + "\n\n"
                    self.wfile.write(line.encode())
                    self.wfile.flush()
            
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
            
        except Exception as e:
            err_msg = "[Server Error] " + str(e)
            payload = json.dumps({"content": err_msg})
            line = "data: " + payload + "\n\n"
            self.wfile.write(line.encode())
            self.wfile.flush()

def run_gui():
    global app
    try:
        app = Synapsis()
    except ValueError as e:
        print("[!] " + str(e))
        return
    
    port = 8080
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    url = "http://127.0.0.1:" + str(port)
    
    print("\033[1;36m  SYNAPSE v3.0.0 GUI\033[0m")
    print("  \033[32mRunning at " + url + "\033[0m")
    print("  Press Ctrl+C to stop.")
    
    try:
        webbrowser.open(url)
    except Exception:
        pass
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("\n[✓] Stopped.")
