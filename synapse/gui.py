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
body{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;height:100vh;height:100dvh;display:flex;flex-direction:column;overflow:hidden}
header{padding:10px 16px;border-bottom:1px solid #30363d;background:#010409;display:flex;justify-content:space-between;align-items:center;flex-shrink:0;gap:8px}
h1{font-size:15px;color:#58a6ff;font-weight:700;white-space:nowrap}
.hdr-btns{display:flex;gap:6px;align-items:center}
.hdr-btn{background:#21262d;border:1px solid #30363d;color:#c9d1d9;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:12px}
.hdr-btn:hover{background:#30363d}
#status{font-size:11px;color:#8b949e;margin-left:8px}
#main{flex:1;display:flex;overflow:hidden;position:relative}
#sidebar{width:220px;background:#010409;border-right:1px solid #30363d;display:flex;flex-direction:column;transition:margin-left .2s;flex-shrink:0}
#sidebar.hidden{margin-left:-220px}
.sb-hdr{padding:10px;border-bottom:1px solid #30363d;display:flex;justify-content:space-between;align-items:center}
.sb-hdr span{font-size:13px;font-weight:600;color:#58a6ff}
#new-session{background:#238636;color:#fff;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px}
#session-list{flex:1;overflow-y:auto;padding:6px}
.sess-item{padding:8px 10px;border-radius:6px;cursor:pointer;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center;font-size:13px;background:#161b22;border:1px solid #30363d}
.sess-item.active{border-color:#58a6ff;background:#1f2937}
.sess-title{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sess-del{background:none;border:none;color:#f85149;cursor:pointer;font-size:14px;padding:0 4px;opacity:0.6}
.sess-del:hover{opacity:1}
#chat-area{flex:1;display:flex;flex-direction:column;overflow:hidden}
#chat{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;-webkit-overflow-scrolling:touch}
.msg{max-width:88%;padding:10px 14px;border-radius:12px;font-size:14px;white-space:pre-wrap;word-break:break-word;line-height:1.6;position:relative}
.user{align-self:flex-end;background:#161b22;border:1px solid #30363d}
.ai{align-self:flex-start;background:#1f2937;border:1px solid #30363d}
.thinking{align-self:flex-start;background:#1a1a2e;border:1px solid #4a4a6a;color:#8b8bab;font-size:12px;font-style:italic}
.err{align-self:flex-start;background:#2d1117;border:1px solid #f85149;color:#f85149}
.msg-actions{position:absolute;top:4px;right:4px;display:none;gap:4px}
.user:hover .msg-actions{display:flex}
.edit-btn{background:#21262d;border:1px solid #30363d;color:#c9d1d9;border-radius:4px;padding:2px 6px;cursor:pointer;font-size:11px}
.edit-btn:hover{background:#30363d}
#input-area{padding:10px 12px;border-top:1px solid #30363d;display:flex;gap:8px;background:#010409;flex-shrink:0;align-items:center}
#inp{flex:1;background:#161b22;border:1px solid #30363d;color:#c9d1d9;padding:10px 12px;border-radius:10px;outline:none;font-size:15px}
#inp:focus{border-color:#58a6ff}
#send{background:#238636;color:#fff;border:none;padding:10px 18px;border-radius:10px;cursor:pointer;font-weight:600;font-size:14px}
#send:active{background:#2ea043}
#send:disabled{opacity:0.4;cursor:default}
#stop{background:#da3633;color:#fff;border:none;padding:10px 18px;border-radius:10px;cursor:pointer;font-weight:600;font-size:14px;display:none}
#stop:active{background:#f85149}
#edit-indicator{display:none;padding:6px 12px;background:#1f2937;border-top:1px solid #30363d;font-size:12px;color:#d29922;align-items:center;justify-content:space-between}
#cancel-edit{background:none;border:none;color:#f85149;cursor:pointer;font-size:12px}
@media(max-width:600px){#sidebar{position:absolute;z-index:10;height:100%;box-shadow:2px 0 8px rgba(0,0,0,0.5)}}
</style>
</head>
<body>
<header>
  <h1>SYNAPSE v3.0.0</h1>
  <div class="hdr-btns">
    <button class="hdr-btn" id="toggle-sb">☰ Sessions</button>
    <span id="status">Ready</span>
  </div>
</header>
<div id="main">
  <div id="sidebar" class="hidden">
    <div class="sb-hdr">
      <span>Sessions</span>
      <button id="new-session">+ New</button>
    </div>
    <div id="session-list"></div>
  </div>
  <div id="chat-area">
    <div id="chat"></div>
    <div id="edit-indicator">
      <span>Editing message...</span>
      <button id="cancel-edit">Cancel</button>
    </div>
    <div id="input-area">
      <input id="inp" type="text" placeholder="Message..." autocomplete="off">
      <button id="send" type="button">Send</button>
      <button id="stop" type="button">Stop</button>
    </div>
  </div>
</div>
<script>
var chat=document.getElementById('chat'),inp=document.getElementById('inp'),btn=document.getElementById('send'),stopBtn=document.getElementById('stop'),st=document.getElementById('status');
var sidebar=document.getElementById('sidebar'),sessList=document.getElementById('session-list'),newSessBtn=document.getElementById('new-session'),toggleSb=document.getElementById('toggle-sb');
var editInd=document.getElementById('edit-indicator'),cancelEdit=document.getElementById('cancel-edit');
var busy=false,controller=null,editIndex=-1,msgElements=[];

function addMsg(role,text,idx){
 var d=document.createElement('div');d.className='msg '+role;d.textContent=text||'';
 if(role==='user'&&idx>=0){
  var acts=document.createElement('div');acts.className='msg-actions';
  var eb=document.createElement('button');eb.className='edit-btn';eb.textContent='✎';
  eb.onclick=function(){startEdit(idx,text)};
  acts.appendChild(eb);d.appendChild(acts);
 }
 chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d;
}

function setBusy(v){busy=v;btn.disabled=v;btn.style.display=v?'none':'block';stopBtn.style.display=v?'block':'none';st.textContent=v?'Generating...':'Ready';}

function startEdit(idx,text){editIndex=idx;inp.value=text;editInd.style.display='flex';inp.focus();}
cancelEdit.onclick=function(){editIndex=-1;inp.value='';editInd.style.display='none';};

function sendMsg(){
 var t=inp.value.trim();if(!t||busy)return;
 inp.value='';setBusy(true);
 var userBox=addMsg('user',t,editIndex>=0?-1:msgElements.length);
 if(editIndex<0)msgElements.push(userBox);
 var thinkBox=null,aiBox=null;
 controller=new AbortController();
 var body=JSON.stringify({message:t,edit_index:editIndex});
 editIndex=-1;editInd.style.display='none';

 fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:body,signal:controller.signal})
 .then(function(res){
  if(!res.ok)throw new Error('HTTP '+res.status);
  var reader=res.body.getReader(),dec=new TextDecoder(),buf='';
  function pump(){
   return reader.read().then(function(r){
    if(r.done){setBusy(false);return;}
    buf+=dec.decode(r.value,{stream:true});
    var lines=buf.split('\\n');buf=lines.pop();
    for(var i=0;i<lines.length;i++){
     var line=lines[i];if(line.indexOf('data: ')!==0)continue;
     var payload=line.substring(6);if(payload==='[DONE]')continue;
     try{
      var obj=JSON.parse(payload);
      if(obj.type==='reasoning'){if(!thinkBox)thinkBox=addMsg('thinking','');thinkBox.textContent+=obj.content;chat.scrollTop=chat.scrollHeight;}
      else if(obj.type==='content'){if(!aiBox)aiBox=addMsg('ai','');aiBox.textContent+=obj.content;chat.scrollTop=chat.scrollHeight;}
      else if(obj.type==='error'){if(!aiBox)aiBox=addMsg('err','');aiBox.textContent+=obj.content;chat.scrollTop=chat.scrollHeight;}
      else if(obj.type==='action'){if(!aiBox)aiBox=addMsg('ai','');aiBox.textContent+=obj.content+'\\n';chat.scrollTop=chat.scrollHeight;}
     }catch(e){}
    }
    return pump();
   });
  }
  return pump();
 })
 .catch(function(e){
  setBusy(false);
  if(e.name==='AbortError'){if(!aiBox)aiBox=addMsg('ai','[Stopped]');}
  else{addMsg('err','[Error] '+e.message);}
 });
}

stopBtn.onclick=function(){if(controller)controller.abort();};
btn.onclick=sendMsg;
inp.onkeydown=function(e){if(e.key==='Enter'){e.preventDefault();sendMsg();}};
toggleSb.onclick=function(){sidebar.classList.toggle('hidden');};

function loadSessions(){
 fetch('/api/sessions').then(function(r){return r.json();}).then(function(data){
  sessList.innerHTML='';
  (data.sessions||[]).forEach(function(s){
   var d=document.createElement('div');d.className='sess-item'+(s.active?' active':'');
   var t=document.createElement('span');t.className='sess-title';t.textContent=s.title||s.id;
   var del=document.createElement('button');del.className='sess-del';del.textContent='✕';
   del.onclick=function(ev){ev.stopPropagation();deleteSession(s.id);};
   d.appendChild(t);d.appendChild(del);
   d.onclick=function(){switchSession(s.id);};
   sessList.appendChild(d);
  });
 }).catch(function(){});
}

function switchSession(sid){
 fetch('/api/session/load',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:sid})})
 .then(function(){chat.innerHTML='';msgElements=[];loadSessions();loadHistory();});
}

function deleteSession(sid){
 fetch('/api/session/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:sid})})
 .then(function(){loadSessions();});
}

newSessBtn.onclick=function(){
 fetch('/api/session/new',{method:'POST'}).then(function(){chat.innerHTML='';msgElements=[];loadSessions();});
};

function loadHistory(){
 fetch('/api/history').then(function(r){return r.json();}).then(function(data){
  (data.messages||[]).forEach(function(m,i){
   var box=addMsg(m.role==='user'?'user':'ai',m.content,m.role==='user'?i:-1);
   if(m.role==='user')msgElements.push(box);
  });
 }).catch(function(){});
}

loadSessions();
loadHistory();
</script>
</body>
</html>"""

app = None

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, format, *args):
        pass

    def _send_json(self, data, code=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode('utf-8'))
        except Exception:
            return {}

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            data = HTML.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path == '/api/sessions':
            sessions = app.list_sessions()
            active = app.sessions.active_id
            result = [{"id": s["id"], "title": s["title"], "active": s["id"] == active} for s in sessions]
            self._send_json({"sessions": result})
        elif self.path == '/api/history':
            msgs = [{"role": m["role"], "content": m["content"]} for m in app.current_session_msgs]
            self._send_json({"messages": msgs})
        else:
            self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/session/new':
            sid = app.new_session()
            self._send_json({"id": sid})
        elif self.path == '/api/session/load':
            body = self._read_body()
            sid = body.get("id", "")
            ok = app.load_session(sid)
            self._send_json({"ok": ok})
        elif self.path == '/api/session/delete':
            body = self._read_body()
            sid = body.get("id", "")
            app.delete_session(sid)
            self._send_json({"ok": True})
        elif self.path == '/api/chat':
            self._handle_chat()
        else:
            self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()

    def _handle_chat(self):
        body = self._read_body()
        msg = body.get('message', '').strip()
        edit_idx = body.get('edit_index', -1)

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
                stream = app.edit_and_resend(edit_idx, msg)
            else:
                stream = app.stream_chat(msg)

            for chunk in stream:
                ctype = chunk.get("type", "")
                cdata = chunk.get("data", "")
                if ctype == "reasoning":
                    payload = json.dumps({"type": "reasoning", "content": cdata})
                elif ctype == "content":
                    payload = json.dumps({"type": "content", "content": cdata})
                elif ctype == "error":
                    payload = json.dumps({"type": "error", "content": str(cdata)})
                elif ctype == "actions":
                    acts = cdata if isinstance(cdata, list) else []
                    for a in acts:
                        p = json.dumps({"type": "action", "content": a})
                        self.wfile.write(("data: " + p + "\n\n").encode('utf-8'))
                        self.wfile.flush()
                    continue
                elif ctype == "done":
                    continue
                else:
                    continue
                self.wfile.write(("data: " + payload + "\n\n").encode('utf-8'))
                self.wfile.flush()

            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

        except BrokenPipeError:
            pass
        except Exception as e:
            try:
                payload = json.dumps({"type": "error", "content": str(e)})
                self.wfile.write(("data: " + payload + "\n\n").encode('utf-8'))
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
