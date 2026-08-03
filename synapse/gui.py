import json
import socket
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from synapse.synapsis import Synapsis
from synapse.core.config import CONFIG_PATH, load_json, save_json

HTML = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Synapse</title>
<style>
:root{
  --bg:#000;--bg2:#0a0a0a;--bg3:#111;--bg4:#1a1a1a;--bg5:#222;
  --fg:#fff;--fg2:#ccc;--fg3:#999;--fg4:#666;
  --border:#222;--border2:#333;
  --accent:#fff;--accent-dim:rgba(255,255,255,0.08);
  --blur:blur(24px);--radius:16px;--radius-sm:10px;
  --shadow:0 8px 32px rgba(0,0,0,0.4);
  --transition:all 0.3s cubic-bezier(0.4,0,0.2,1);
}
[data-theme="light"]{
  --bg:#fff;--bg2:#f7f7f7;--bg3:#f0f0f0;--bg4:#e8e8e8;--bg5:#ddd;
  --fg:#000;--fg2:#333;--fg3:#666;--fg4:#999;
  --border:#e0e0e0;--border2:#ccc;
  --accent:#000;--accent-dim:rgba(0,0,0,0.05);
  --shadow:0 8px 32px rgba(0,0,0,0.08);
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;height:100vh;height:100dvh;display:flex;flex-direction:column;overflow:hidden;transition:background 0.4s,color 0.4s}

header{padding:12px 16px;border-bottom:1px solid var(--border);background:var(--bg2);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);display:flex;justify-content:space-between;align-items:center;flex-shrink:0;z-index:20;position:relative}
h1{font-size:15px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--fg)}
.hdr-right{display:flex;gap:8px;align-items:center}
#status{font-size:11px;color:var(--fg3);transition:var(--transition)}
.hdr-btn{width:34px;height:34px;border-radius:var(--radius-sm);background:var(--accent-dim);border:1px solid var(--border);color:var(--fg2);cursor:pointer;font-size:14px;display:flex;align-items:center;justify-content:center;transition:var(--transition)}
.hdr-btn:hover{background:var(--bg5);transform:translateY(-1px)}
.hdr-btn:active{transform:scale(0.95)}

#main{flex:1;display:flex;overflow:hidden;position:relative}

#sidebar{width:260px;background:var(--bg2);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);border-right:1px solid var(--border);display:flex;flex-direction:column;transition:transform 0.35s cubic-bezier(0.4,0,0.2,1);flex-shrink:0;z-index:15}
#sidebar.hidden{transform:translateX(-100%);position:absolute;height:100%}
.sb-hdr{padding:14px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.sb-hdr span{font-size:12px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--fg3)}
.sb-btn{background:var(--accent);color:var(--bg);border:none;padding:5px 12px;border-radius:var(--radius-sm);cursor:pointer;font-size:11px;font-weight:600;transition:var(--transition)}
.sb-btn:hover{opacity:0.8;transform:translateY(-1px)}
.sb-btn:active{transform:scale(0.95)}
#session-list{flex:1;overflow-y:auto;padding:8px}
#session-list::-webkit-scrollbar{width:4px}
#session-list::-webkit-scrollbar-thumb{background:var(--border2);border-radius:4px}
.sess-item{padding:10px 12px;border-radius:var(--radius-sm);cursor:pointer;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center;font-size:13px;background:var(--bg3);border:1px solid transparent;transition:var(--transition);gap:6px}
.sess-item:hover{background:var(--bg4);border-color:var(--border)}
.sess-item.active{border-color:var(--fg4);background:var(--bg4)}
.sess-title{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--fg2)}
.sess-actions{display:flex;gap:2px;opacity:0;transition:opacity 0.2s}
.sess-item:hover .sess-actions{opacity:1}
.sess-btn{background:none;border:none;color:var(--fg4);cursor:pointer;font-size:12px;padding:2px 4px;border-radius:4px;transition:var(--transition)}
.sess-btn:hover{color:var(--fg);background:var(--bg5)}
.sess-btn.del:hover{color:#f44}

#chat-area{flex:1;display:flex;flex-direction:column;overflow:hidden}
#chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;-webkit-overflow-scrolling:touch}
#chat::-webkit-scrollbar{width:4px}
#chat::-webkit-scrollbar-thumb{background:var(--border2);border-radius:4px}

.msg{max-width:85%;padding:12px 16px;border-radius:var(--radius);font-size:14px;line-height:1.7;position:relative;animation:msgIn 0.35s cubic-bezier(0.4,0,0.2,1)}
@keyframes msgIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.msg.user{align-self:flex-end;background:var(--bg4);border:1px solid var(--border);white-space:pre-wrap;word-break:break-word}
.msg.ai{align-self:flex-start;background:var(--bg3);border:1px solid var(--border)}
.msg.thinking{align-self:flex-start;background:var(--bg2);border:1px solid var(--border);color:var(--fg4);font-size:12px;font-style:italic;white-space:pre-wrap}
.msg.err{align-self:flex-start;background:var(--bg3);border:1px solid #f44;color:#f44}
.msg-actions{position:absolute;top:6px;right:6px;display:none;gap:4px}
.msg.user:hover .msg-actions{display:flex}
.edit-btn{background:var(--bg5);border:1px solid var(--border2);color:var(--fg2);border-radius:6px;padding:3px 8px;cursor:pointer;font-size:11px;transition:var(--transition)}
.edit-btn:hover{background:var(--border2)}

.code-block{margin:8px 0;border-radius:var(--radius-sm);overflow:hidden;border:1px solid var(--border);background:var(--bg);animation:msgIn 0.3s ease}
.code-header{background:var(--bg4);padding:8px 12px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border)}
.code-lang{font-size:10px;color:var(--fg3);font-weight:600;text-transform:uppercase;letter-spacing:1px}
.copy-btn{background:var(--bg5);border:1px solid var(--border2);color:var(--fg2);padding:3px 10px;border-radius:6px;cursor:pointer;font-size:11px;transition:var(--transition)}
.copy-btn:hover{background:var(--border2)}
.copy-btn:active{transform:scale(0.95)}
.code-content{background:var(--bg);padding:12px;overflow-x:auto;font-family:'SF Mono','Fira Code',monospace;font-size:13px;line-height:1.6;white-space:pre;color:var(--fg2)}
.code-content::-webkit-scrollbar{height:4px}
.code-content::-webkit-scrollbar-thumb{background:var(--border2);border-radius:4px}
.text-content{white-space:pre-wrap;word-break:break-word}

#input-area{padding:12px 16px;border-top:1px solid var(--border);display:flex;gap:10px;background:var(--bg2);backdrop-filter:var(--blur);-webkit-backdrop-filter:var(--blur);flex-shrink:0;align-items:center}
#inp{flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--fg);padding:12px 16px;border-radius:var(--radius);outline:none;font-size:14px;transition:var(--transition)}
#inp:focus{border-color:var(--fg4);box-shadow:0 0 0 3px var(--accent-dim)}
#inp::placeholder{color:var(--fg4)}
#send{background:var(--accent);color:var(--bg);border:none;padding:12px 20px;border-radius:var(--radius);cursor:pointer;font-weight:600;font-size:13px;transition:var(--transition);letter-spacing:0.5px}
#send:hover{opacity:0.85;transform:translateY(-1px)}
#send:active{transform:scale(0.97)}
#send:disabled{opacity:0.3;cursor:default;transform:none}
#stop{background:var(--bg4);color:var(--fg);border:1px solid var(--border2);padding:12px 20px;border-radius:var(--radius);cursor:pointer;font-weight:600;font-size:13px;display:none;transition:var(--transition)}
#stop:hover{background:var(--bg5)}
#edit-indicator{display:none;padding:8px 16px;background:var(--bg3);border-top:1px solid var(--border);font-size:12px;color:var(--fg3);align-items:center;justify-content:space-between}
#cancel-edit{background:none;border:none;color:var(--fg);cursor:pointer;font-size:12px;text-decoration:underline}

.modal-overlay{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);z-index:100;align-items:center;justify-content:center;animation:fadeIn 0.25s ease}
.modal-overlay.show{display:flex}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.modal{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:24px;width:92%;max-width:520px;max-height:85vh;overflow-y:auto;box-shadow:var(--shadow);animation:modalIn 0.3s cubic-bezier(0.4,0,0.2,1)}
@keyframes modalIn{from{opacity:0;transform:scale(0.95) translateY(10px)}to{opacity:1;transform:scale(1) translateY(0)}}
.modal::-webkit-scrollbar{width:4px}
.modal::-webkit-scrollbar-thumb{background:var(--border2);border-radius:4px}
.modal h3{font-size:16px;font-weight:700;margin-bottom:20px;letter-spacing:1px;color:var(--fg)}
.modal-section{margin-bottom:20px}
.modal-section label{font-size:11px;color:var(--fg3);display:block;margin-bottom:6px;text-transform:uppercase;letter-spacing:1px;font-weight:600}
.modal textarea{width:100%;background:var(--bg);border:1px solid var(--border);color:var(--fg);padding:10px 12px;border-radius:var(--radius-sm);font-size:13px;min-height:80px;resize:vertical;font-family:inherit;transition:var(--transition)}
.modal textarea:focus{border-color:var(--fg4);outline:none}
.modal input[type="text"],.modal input[type="password"],.modal select{width:100%;background:var(--bg);border:1px solid var(--border);color:var(--fg);padding:10px 12px;border-radius:var(--radius-sm);font-size:13px;transition:var(--transition)}
.modal input:focus,.modal select:focus{border-color:var(--fg4);outline:none}
.modal select{cursor:pointer;appearance:none;-webkit-appearance:none}
.modal-btns{display:flex;gap:8px;margin-top:20px;justify-content:flex-end}
.modal-btn{padding:8px 18px;border-radius:var(--radius-sm);cursor:pointer;font-size:12px;font-weight:600;border:none;transition:var(--transition)}
.modal-btn:active{transform:scale(0.97)}
.modal-btn.primary{background:var(--accent);color:var(--bg)}
.modal-btn.primary:hover{opacity:0.85}
.modal-btn.secondary{background:var(--bg4);color:var(--fg2);border:1px solid var(--border)}
.modal-btn.secondary:hover{background:var(--bg5)}

.theme-grid{display:flex;gap:8px;margin-bottom:12px}
.theme-opt{flex:1;padding:14px;border-radius:var(--radius-sm);border:2px solid var(--border);cursor:pointer;text-align:center;font-size:12px;font-weight:600;transition:var(--transition)}
.theme-opt:hover{border-color:var(--fg4)}
.theme-opt.active{border-color:var(--fg)}
.theme-opt.dark-opt{background:#000;color:#fff}
.theme-opt.light-opt{background:#fff;color:#000;border-color:#ccc}

.pinned-list{margin:8px 0}
.pinned-item{display:flex;justify-content:space-between;align-items:center;padding:6px 10px;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius-sm);margin-bottom:4px;font-size:12px;color:var(--fg2)}
.pinned-item button{background:none;border:none;color:var(--fg4);cursor:pointer;font-size:14px;transition:var(--transition)}
.pinned-item button:hover{color:#f44}

.provider-row{display:flex;gap:8px;margin-bottom:8px;align-items:center}
.provider-row select{flex:1}
.provider-row input{flex:2}
.code-ctx-item{padding:6px 0;border-bottom:1px solid var(--border);font-size:12px;color:var(--fg3)}

@media(max-width:768px){
  #sidebar{position:absolute;z-index:15;height:100%;box-shadow:var(--shadow);width:280px}
  .msg{max-width:92%}
  header{padding:10px 12px}
  #chat{padding:12px}
  #input-area{padding:10px 12px}
  .modal{width:95%;padding:16px}
}
</style>
</head>
<body>
<header>
  <h1>SYNAPSE</h1>
  <div class="hdr-right">
    <span id="status">Ready</span>
    <button class="hdr-btn" id="btn-settings" title="Settings">⚙</button>
    <button class="hdr-btn" id="toggle-sb" title="Sessions">☰</button>
  </div>
</header>
<div id="main">
  <div id="sidebar" class="hidden">
    <div class="sb-hdr">
      <span>Sessions</span>
      <button class="sb-btn" id="new-session">+ New</button>
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

<div class="modal-overlay" id="settings-modal">
  <div class="modal">
    <h3>Settings</h3>

    <div class="modal-section">
      <label>Theme</label>
      <div class="theme-grid">
        <div class="theme-opt dark-opt" id="theme-dark" onclick="setTheme('dark')">Dark</div>
        <div class="theme-opt light-opt" id="theme-light" onclick="setTheme('light')">Light</div>
      </div>
    </div>

    <div class="modal-section">
      <label>System Prompt</label>
      <textarea id="sys-prompt" placeholder="Custom system prompt..."></textarea>
    </div>

    <div class="modal-section">
      <label>Pinned Files</label>
      <div class="pinned-list" id="pinned-list"></div>
      <div style="display:flex;gap:6px;margin-top:6px">
        <input type="text" id="pin-input" placeholder="filename.py" style="flex:1">
        <button class="modal-btn primary" id="pin-add" style="padding:8px 14px">Pin</button>
      </div>
    </div>

    <div class="modal-section">
      <label>Code Context</label>
      <div id="code-ctx-list"></div>
    </div>

    <div class="modal-section">
      <label>Provider & Model</label>
      <div class="provider-row">
        <select id="prov-select"></select>
      </div>
      <div class="provider-row">
        <input type="text" id="model-input" placeholder="Model name">
      </div>
      <div class="provider-row">
        <input type="password" id="apikey-input" placeholder="API Key">
      </div>
      <button class="modal-btn secondary" id="save-provider" style="width:100%;margin-top:4px">Save Provider Settings</button>
    </div>

    <div class="modal-btns">
      <button class="modal-btn secondary" id="settings-close">Close</button>
      <button class="modal-btn primary" id="settings-save">Save All</button>
    </div>
  </div>
</div>

<script>
var MAX_DOM_MSGS=60;
var chat=document.getElementById('chat'),inp=document.getElementById('inp'),btn=document.getElementById('send'),stopBtn=document.getElementById('stop'),st=document.getElementById('status');
var sidebar=document.getElementById('sidebar'),sessList=document.getElementById('session-list');
var editInd=document.getElementById('edit-indicator'),cancelEditBtn=document.getElementById('cancel-edit');
var settingsModal=document.getElementById('settings-modal');
var busy=false,controller=null,editIndex=-1,msgCount=0,renderQueue=0;

function setTheme(t){
  document.documentElement.setAttribute('data-theme',t);
  localStorage.setItem('synapse-theme',t);
  document.getElementById('theme-dark').classList.toggle('active',t==='dark');
  document.getElementById('theme-light').classList.toggle('active',t==='light');
}
(function(){var t=localStorage.getItem('synapse-theme')||'dark';setTheme(t);})();

function trimDOM(){
  while(chat.children.length>MAX_DOM_MSGS){chat.removeChild(chat.firstChild);}
}

function renderCodeBlocks(text){
  var parts=[];var re=/```(\\w*)\\n([\\s\\S]*?)```/g;var last=0;var m;
  while((m=re.exec(text))!==null){
    if(m.index>last)parts.push({type:'text',content:text.substring(last,m.index)});
    parts.push({type:'code',lang:m[1]||'code',content:m[2]});
    last=m.index+m[0].length;
  }
  if(last<text.length)parts.push({type:'text',content:text.substring(last)});
  return parts;
}

function buildCodeBlock(p){
  var block=document.createElement('div');block.className='code-block';
  var hdr=document.createElement('div');hdr.className='code-header';
  var lang=document.createElement('span');lang.className='code-lang';lang.textContent=p.lang;
  var cpBtn=document.createElement('button');cpBtn.className='copy-btn';cpBtn.textContent='Copy';
  cpBtn.onclick=(function(code,b){return function(){
    if(navigator.clipboard){navigator.clipboard.writeText(code).then(function(){b.textContent='Copied';setTimeout(function(){b.textContent='Copy'},1500);});}
    else{var ta=document.createElement('textarea');ta.value=code;document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);b.textContent='Copied';setTimeout(function(){b.textContent='Copy'},1500);}
  }})(p.content,cpBtn);
  hdr.appendChild(lang);hdr.appendChild(cpBtn);
  var pre=document.createElement('div');pre.className='code-content';pre.textContent=p.content;
  block.appendChild(hdr);block.appendChild(pre);
  return block;
}

function addMsg(role,text,idx){
  var d=document.createElement('div');d.className='msg '+role;
  if(role==='user'){
    d.textContent=text||'';
    if(idx>=0){
      var acts=document.createElement('div');acts.className='msg-actions';
      var eb=document.createElement('button');eb.className='edit-btn';eb.textContent='Edit';
      eb.onclick=function(){startEdit(idx,text)};
      acts.appendChild(eb);d.appendChild(acts);
    }
  }else if(role==='ai'){
    d._rawText=text||'';
    var parts=renderCodeBlocks(d._rawText);
    for(var i=0;i<parts.length;i++){
      if(parts[i].type==='code')d.appendChild(buildCodeBlock(parts[i]));
      else{var s=document.createElement('span');s.className='text-content';s.textContent=parts[i].content;d.appendChild(s);}
    }
  }else{d.textContent=text||'';}
  chat.appendChild(d);trimDOM();chat.scrollTop=chat.scrollHeight;msgCount++;return d;
}

function appendToMsg(el,text,role){
  if(role==='ai'){
    el._rawText=(el._rawText||'')+text;
    if(++renderQueue%3!==0)return;
    requestAnimationFrame(function(){
      el.innerHTML='';
      var parts=renderCodeBlocks(el._rawText);
      for(var i=0;i<parts.length;i++){
        if(parts[i].type==='code')el.appendChild(buildCodeBlock(parts[i]));
        else{var s=document.createElement('span');s.className='text-content';s.textContent=parts[i].content;el.appendChild(s);}
      }
      chat.scrollTop=chat.scrollHeight;
    });
  }else{el.textContent+=text;chat.scrollTop=chat.scrollHeight;}
}

function setBusy(v){busy=v;btn.disabled=v;btn.style.display=v?'none':'block';stopBtn.style.display=v?'block':'none';st.textContent=v?'Generating...':'Ready';}
function startEdit(idx,text){editIndex=idx;inp.value=text;editInd.style.display='flex';inp.focus();}
cancelEditBtn.onclick=function(){editIndex=-1;inp.value='';editInd.style.display='none';};

function sendMsg(){
  var t=inp.value.trim();if(!t||busy)return;
  inp.value='';setBusy(true);
  var msgIdx=editIndex>=0?-1:msgCount;
  addMsg('user',t,editIndex>=0?-1:msgIdx);
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
        if(r.done){setBusy(false);renderQueue=0;if(aiBox){el=aiBox;el.innerHTML='';var parts=renderCodeBlocks(el._rawText);for(var i=0;i<parts.length;i++){if(parts[i].type==='code')el.appendChild(buildCodeBlock(parts[i]));else{var s=document.createElement('span');s.className='text-content';s.textContent=parts[i].content;el.appendChild(s);}}chat.scrollTop=chat.scrollHeight;}return;}
        buf+=dec.decode(r.value,{stream:true});
        var lines=buf.split('\\n');buf=lines.pop();
        for(var i=0;i<lines.length;i++){
          var line=lines[i];if(line.indexOf('data: ')!==0)continue;
          var payload=line.substring(6);if(payload==='[DONE]')continue;
          try{
            var obj=JSON.parse(payload);
            if(obj.type==='reasoning'){if(!thinkBox)thinkBox=addMsg('thinking','');thinkBox.textContent+=obj.content;chat.scrollTop=chat.scrollHeight;}
            else if(obj.type==='content'){if(!aiBox)aiBox=addMsg('ai','');appendToMsg(aiBox,obj.content,'ai');}
            else if(obj.type==='error'){if(!aiBox)aiBox=addMsg('err','');aiBox.textContent+=obj.content;}
            else if(obj.type==='action'){if(!aiBox)aiBox=addMsg('ai','');appendToMsg(aiBox,obj.content+'\\n','ai');}
          }catch(e){}
        }
        return pump();
      });
    }
    return pump();
  })
  .catch(function(e){
    setBusy(false);
    if(e.name==='AbortError'){if(!aiBox)addMsg('ai','[Stopped]');}
    else{addMsg('err','[Error] '+e.message);}
  });
}

stopBtn.onclick=function(){if(controller)controller.abort();};
btn.onclick=sendMsg;
inp.onkeydown=function(e){if(e.key==='Enter'){e.preventDefault();sendMsg();}};
document.getElementById('toggle-sb').onclick=function(){sidebar.classList.toggle('hidden');};

document.getElementById('btn-settings').onclick=function(){
  fetch('/api/settings').then(function(r){return r.json();}).then(function(data){
    document.getElementById('sys-prompt').value=data.system_prompt||'';
    renderPinned(data.pinned_files||[]);
    renderCodeCtx(data.code_context||{});
    loadProviders(data.providers||{});
    settingsModal.classList.add('show');
  });
};
document.getElementById('settings-close').onclick=function(){settingsModal.classList.remove('show');};
document.getElementById('settings-save').onclick=function(){
  fetch('/api/settings/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({system_prompt:document.getElementById('sys-prompt').value})})
  .then(function(){settingsModal.classList.remove('show');});
};

function renderPinned(files){
  var el=document.getElementById('pinned-list');el.innerHTML='';
  files.forEach(function(f){
    var d=document.createElement('div');d.className='pinned-item';
    var s=document.createElement('span');s.textContent=f;
    var b=document.createElement('button');b.textContent='✕';
    b.onclick=function(){fetch('/api/pinned/remove',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({file:f})}).then(function(){loadSettingsRefresh();});};
    d.appendChild(s);d.appendChild(b);el.appendChild(d);
  });
}
function renderCodeCtx(ctx){
  var el=document.getElementById('code-ctx-list');el.innerHTML='';
  var keys=Object.keys(ctx);
  if(!keys.length){el.innerHTML='<div class="code-ctx-item">No code files in context.</div>';return;}
  keys.forEach(function(k){
    var d=document.createElement('div');d.className='code-ctx-item';
    d.textContent=k+' ('+ctx[k].length+' chars)';el.appendChild(d);
  });
}
function loadSettingsRefresh(){
  fetch('/api/settings').then(function(r){return r.json();}).then(function(data){
    renderPinned(data.pinned_files||[]);renderCodeCtx(data.code_context||{});
  });
}
document.getElementById('pin-add').onclick=function(){
  var f=document.getElementById('pin-input').value.trim();if(!f)return;
  fetch('/api/pinned/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({file:f})})
  .then(function(){document.getElementById('pin-input').value='';loadSettingsRefresh();});
};

function loadProviders(provData){
  var sel=document.getElementById('prov-select');sel.innerHTML='';
  var names=Object.keys(provData);
  names.forEach(function(n){
    var o=document.createElement('option');o.value=n;o.textContent=n.toUpperCase();sel.appendChild(o);
  });
  if(names.length){
    sel.value=names[0];
    var p=provData[names[0]];
    document.getElementById('model-input').value=p.model||'';
    document.getElementById('apikey-input').value=p.api_key||'';
  }
  sel.onchange=function(){
    var p=provData[sel.value]||{};
    document.getElementById('model-input').value=p.model||'';
    document.getElementById('apikey-input').value=p.api_key||'';
  };
}
document.getElementById('save-provider').onclick=function(){
  var prov=document.getElementById('prov-select').value;
  var model=document.getElementById('model-input').value.trim();
  var key=document.getElementById('apikey-input').value.trim();
  fetch('/api/providers/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:prov,model:model,api_key:key})})
  .then(function(r){return r.json();}).then(function(d){
    if(d.ok)alert('Provider settings saved. Restart may be needed.');
    else alert('Error: '+(d.error||'unknown'));
  });
};

function loadSessions(){
  fetch('/api/sessions').then(function(r){return r.json();}).then(function(data){
    sessList.innerHTML='';
    (data.sessions||[]).forEach(function(s){
      var d=document.createElement('div');d.className='sess-item'+(s.active?' active':'');
      var t=document.createElement('span');t.className='sess-title';t.textContent=s.title||s.id;
      var acts=document.createElement('div');acts.className='sess-actions';
      var ren=document.createElement('button');ren.className='sess-btn';ren.textContent='✎';
      ren.onclick=function(ev){ev.stopPropagation();renameSession(s.id,s.title);};
      var del=document.createElement('button');del.className='sess-btn del';del.textContent='✕';
      del.onclick=function(ev){ev.stopPropagation();deleteSession(s.id);};
      acts.appendChild(ren);acts.appendChild(del);
      d.appendChild(t);d.appendChild(acts);
      d.onclick=function(){switchSession(s.id);};
      sessList.appendChild(d);
    });
  }).catch(function(){});
}
function renameSession(sid,old){
  var t=prompt('Rename session:',old);
  if(t&&t.trim()){fetch('/api/session/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:sid,title:t.trim()})}).then(function(){loadSessions();});}
}
function switchSession(sid){
  fetch('/api/session/load',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:sid})})
  .then(function(){chat.innerHTML='';msgCount=0;loadSessions();loadHistory();sidebar.classList.add('hidden');});
}
function deleteSession(sid){
  fetch('/api/session/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:sid})})
  .then(function(){chat.innerHTML='';msgCount=0;loadSessions();});
}
document.getElementById('new-session').onclick=function(){
  fetch('/api/session/new',{method:'POST'}).then(function(){chat.innerHTML='';msgCount=0;loadSessions();sidebar.classList.add('hidden');});
};
function loadHistory(){
  fetch('/api/history').then(function(r){return r.json();}).then(function(data){
    (data.messages||[]).forEach(function(m,i){addMsg(m.role==='user'?'user':'ai',m.content,m.role==='user'?i:-1);});
  }).catch(function(){});
}
loadSessions();loadHistory();
</script>
</body>
</html>"""

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
            result = [{"id": s["id"], "title": s["title"], "active": s["id"] == active} for s in sessions]
            self._json({"sessions": result})
        elif self.path == '/api/history':
            msgs = [{"role": m["role"], "content": m["content"]} for m in app.current_session_msgs]
            self._json({"messages": msgs})
        elif self.path == '/api/settings':
            cfg = load_json(CONFIG_PATH, {})
            self._json({
                "system_prompt": app.custom_system_prompt,
                "pinned_files": app.pinned_files,
                "code_context": app.code_context,
                "providers": cfg.get("providers", {}),
                "default_provider": cfg.get("default_provider", "")
            })
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
        elif self.path == '/api/pinned/add':
            f = body.get("file", "")
            if f:
                app.add_pinned_file(f)
            self._json({"ok": True})
        elif self.path == '/api/pinned/remove':
            f = body.get("file", "")
            if f:
                app.remove_pinned_file(f)
            self._json({"ok": True})
        elif self.path == '/api/providers/save':
            try:
                cfg = load_json(CONFIG_PATH, {})
                prov = body.get("provider", "")
                if prov and prov in cfg.get("providers", {}):
                    if body.get("model"):
                        cfg["providers"][prov]["model"] = body["model"]
                    if body.get("api_key"):
                        cfg["providers"][prov]["api_key"] = body["api_key"]
                    cfg["default_provider"] = prov
                    save_json(CONFIG_PATH, cfg)
                    app.cfg = cfg
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
            stream = app.edit_and_resend(edit_idx, msg) if edit_idx >= 0 else app.stream_chat(msg)
            for chunk in stream:
                ct = chunk.get("type", "")
                cd = chunk.get("data", "")
                if ct in ("reasoning", "content", "error"):
                    payload = json.dumps({"type": ct, "content": cd})
                    self.wfile.write(("data: " + payload + "\n\n").encode('utf-8'))
                    self.wfile.flush()
                elif ct == "actions":
                    for a in (cd if isinstance(cd, list) else []):
                        p = json.dumps({"type": "action", "content": a})
                        self.wfile.write(("data: " + p + "\n\n").encode('utf-8'))
                        self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except BrokenPipeError:
            pass
        except Exception as e:
            try:
                p = json.dumps({"type": "error", "content": str(e)})
                self.wfile.write(("data: " + p + "\n\n").encode('utf-8'))
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
