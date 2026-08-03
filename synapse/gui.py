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
:root{--bg:#000;--bg2:#0a0a0a;--bg3:#111;--bg4:#1a1a1a;--bg5:#222;--fg:#fff;--fg2:#ccc;--fg3:#888;--fg4:#555;--border:#1a1a1a;--border2:#2a2a2a;--accent:#fff;--accent-dim:rgba(255,255,255,0.06);--radius:14px;--radius-sm:10px;--shadow:0 8px 32px rgba(0,0,0,0.5);--tr:all 0.25s cubic-bezier(0.4,0,0.2,1)}
[data-theme="light"]{--bg:#fff;--bg2:#fafafa;--bg3:#f2f2f2;--bg4:#e9e9e9;--bg5:#ddd;--fg:#000;--fg2:#222;--fg3:#666;--fg4:#aaa;--border:#e5e5e5;--border2:#d0d0d0;--accent:#000;--accent-dim:rgba(0,0,0,0.04);--shadow:0 8px 32px rgba(0,0,0,0.06)}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;height:100vh;height:100dvh;display:flex;flex-direction:column;overflow:hidden;transition:background 0.4s,color 0.4s}
header{padding:10px 20px;border-bottom:1px solid var(--border);background:var(--bg2);display:flex;justify-content:space-between;align-items:center;flex-shrink:0;z-index:20}
h1{font-size:14px;font-weight:700;letter-spacing:3px;text-transform:uppercase}
.hdr-right{display:flex;gap:8px;align-items:center}
#status{font-size:11px;color:var(--fg3)}
.hdr-btn{width:32px;height:32px;border-radius:8px;background:var(--accent-dim);border:1px solid var(--border);color:var(--fg2);cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;transition:var(--tr)}
.hdr-btn:hover{background:var(--bg5)}
#main{flex:1;display:flex;overflow:hidden;position:relative}
#sidebar{width:240px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;transition:transform 0.3s;flex-shrink:0;z-index:15}
#sidebar.hidden{transform:translateX(-100%);position:absolute;height:100%}
.sb-hdr{padding:12px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.sb-hdr span{font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--fg3)}
.sb-btn{background:var(--accent);color:var(--bg);border:none;padding:4px 10px;border-radius:8px;cursor:pointer;font-size:11px;font-weight:600}
#session-list{flex:1;overflow-y:auto;padding:6px}
.sess-item{padding:9px 12px;border-radius:var(--radius-sm);cursor:pointer;margin-bottom:3px;display:flex;justify-content:space-between;align-items:center;font-size:13px;background:var(--bg3);border:1px solid transparent;transition:var(--tr);gap:4px}
.sess-item:hover{background:var(--bg4);border-color:var(--border)}
.sess-item.active{border-color:var(--fg4);background:var(--bg4)}
.sess-title{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--fg2)}
.sess-actions{display:flex;gap:2px;opacity:0;transition:opacity 0.15s}
.sess-item:hover .sess-actions{opacity:1}
.sess-btn{background:none;border:none;color:var(--fg4);cursor:pointer;font-size:11px;padding:2px 4px;border-radius:4px}
.sess-btn:hover{color:var(--fg)}
.sess-btn.del:hover{color:#f55}
#chat-area{flex:1;display:flex;flex-direction:column;overflow:hidden;max-width:900px;margin:0 auto;width:100%}
#chat{flex:1;overflow-y:auto;padding:20px 24px;display:flex;flex-direction:column;gap:12px}
#chat::-webkit-scrollbar{width:3px}
#chat::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}
.msg{max-width:80%;padding:12px 16px;border-radius:var(--radius);font-size:14px;line-height:1.7;position:relative;animation:msgIn 0.3s cubic-bezier(0.4,0,0.2,1)}
@keyframes msgIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.msg.user{align-self:flex-end;background:var(--bg4);border:1px solid var(--border);white-space:pre-wrap;word-break:break-word}
.msg.ai{align-self:flex-start;background:var(--bg3);border:1px solid var(--border)}
.msg.thinking{align-self:flex-start;background:transparent;border:none;color:var(--fg4);font-size:12px;font-style:italic;padding:4px 16px}
.msg.err{align-self:flex-start;background:var(--bg3);border:1px solid #f44;color:#f55}
.msg.loop-status{align-self:center;background:var(--bg2);border:1px solid var(--border);color:var(--fg3);font-size:11px;padding:5px 14px;border-radius:20px}
.msg.cmd-result{align-self:flex-start;background:var(--bg);border:1px solid var(--border);font-family:monospace;font-size:12px;color:var(--fg2);white-space:pre-wrap;max-height:200px;overflow-y:auto}
.msg-actions{position:absolute;top:6px;right:6px;display:none;gap:4px}
.msg.user:hover .msg-actions{display:flex}
.edit-btn{background:var(--bg5);border:1px solid var(--border2);color:var(--fg2);border-radius:6px;padding:2px 8px;cursor:pointer;font-size:11px}
.md-content{white-space:pre-wrap;word-break:break-word}
.md-content strong{font-weight:700}
.md-content em{font-style:italic}
.md-content code{background:var(--bg);padding:2px 5px;border-radius:4px;font-family:monospace;font-size:12px;border:1px solid var(--border)}
.md-content h2,.md-content h3,.md-content h4{margin:8px 0 4px;font-weight:700}
.md-content ul{margin:4px 0 4px 18px}
.md-content li{margin:2px 0}
.md-content a{color:var(--fg);text-decoration:underline}
.md-content hr{border:none;border-top:1px solid var(--border);margin:8px 0}
.code-block{margin:8px 0;border-radius:var(--radius-sm);overflow:hidden;border:1px solid var(--border);background:var(--bg)}
.code-header{background:var(--bg4);padding:6px 12px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border)}
.code-lang{font-size:10px;color:var(--fg3);font-weight:600;text-transform:uppercase;letter-spacing:1px}
.code-actions{display:flex;gap:4px}
.copy-btn,.preview-btn{background:var(--bg5);border:1px solid var(--border2);color:var(--fg2);padding:2px 10px;border-radius:6px;cursor:pointer;font-size:11px}
.copy-btn:hover,.preview-btn:hover{background:var(--border2)}
.code-content{background:var(--bg);padding:12px;overflow-x:auto;font-family:'SF Mono','Fira Code',monospace;font-size:13px;line-height:1.6;white-space:pre;color:var(--fg2)}
#mode-bar{padding:6px 24px;border-top:1px solid var(--border);display:flex;gap:6px;align-items:center;background:var(--bg2)}
.mode-btn{padding:5px 16px;border-radius:20px;border:1px solid var(--border);background:transparent;color:var(--fg3);cursor:pointer;font-size:11px;font-weight:600;transition:var(--tr)}
.mode-btn:hover{border-color:var(--fg4);color:var(--fg2)}
.mode-btn.active{background:var(--accent);color:var(--bg);border-color:var(--accent)}
#mode-label{font-size:10px;color:var(--fg4);margin-right:4px;text-transform:uppercase;letter-spacing:1px}
#input-area{padding:12px 24px 16px;border-top:1px solid var(--border);display:flex;gap:10px;background:var(--bg2);flex-shrink:0;align-items:center}
#inp{flex:1;background:var(--bg3);border:1px solid var(--border);color:var(--fg);padding:12px 16px;border-radius:var(--radius);outline:none;font-size:14px}
#inp:focus{border-color:var(--fg4);box-shadow:0 0 0 3px var(--accent-dim)}
#send{background:var(--accent);color:var(--bg);border:none;padding:12px 22px;border-radius:var(--radius);cursor:pointer;font-weight:600;font-size:13px}
#send:disabled{opacity:0.3;cursor:default}
#stop{background:var(--bg4);color:var(--fg);border:1px solid var(--border2);padding:12px 22px;border-radius:var(--radius);cursor:pointer;font-weight:600;font-size:13px;display:none}
#edit-indicator{display:none;padding:6px 24px;background:var(--bg3);border-top:1px solid var(--border);font-size:12px;color:var(--fg3);align-items:center;justify-content:space-between}
#cancel-edit{background:none;border:none;color:var(--fg);cursor:pointer;font-size:12px;text-decoration:underline}
#code-panel{width:0;background:var(--bg2);border-left:1px solid var(--border);overflow:hidden;transition:width 0.3s;flex-shrink:0;display:flex;flex-direction:column}
#code-panel.open{width:350px}
.cp-hdr{padding:10px 14px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.cp-hdr span{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:var(--fg3)}
.cp-close{background:none;border:none;color:var(--fg3);cursor:pointer;font-size:16px}
#code-file-list{padding:6px;border-bottom:1px solid var(--border);max-height:120px;overflow-y:auto}
.code-file-item{padding:6px 10px;border-radius:6px;cursor:pointer;font-size:12px;color:var(--fg2)}
.code-file-item:hover{background:var(--bg4)}
.code-file-item.active{background:var(--bg4);color:var(--fg)}
#code-viewer{flex:1;overflow:auto;padding:12px}
#code-viewer pre{font-family:monospace;font-size:12px;line-height:1.5;white-space:pre-wrap;color:var(--fg2)}
#preview-frame{width:100%;height:100%;border:none;background:#fff;display:none}
.modal-overlay{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);backdrop-filter:blur(8px);z-index:100;align-items:center;justify-content:center}
.modal-overlay.show{display:flex}
.modal{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:24px;width:92%;max-width:520px;max-height:85vh;overflow-y:auto;box-shadow:var(--shadow)}
.modal h3{font-size:15px;font-weight:700;margin-bottom:20px;letter-spacing:1px}
.modal-section{margin-bottom:18px}
.modal-section label{font-size:10px;color:var(--fg3);display:block;margin-bottom:5px;text-transform:uppercase;letter-spacing:1px;font-weight:600}
.modal textarea{width:100%;background:var(--bg);border:1px solid var(--border);color:var(--fg);padding:10px 12px;border-radius:var(--radius-sm);font-size:13px;min-height:70px;resize:vertical;font-family:inherit}
.modal input[type="text"],.modal input[type="password"],.modal select{width:100%;background:var(--bg);border:1px solid var(--border);color:var(--fg);padding:10px 12px;border-radius:var(--radius-sm);font-size:13px}
.modal-btns{display:flex;gap:8px;margin-top:20px;justify-content:flex-end}
.modal-btn{padding:8px 18px;border-radius:var(--radius-sm);cursor:pointer;font-size:12px;font-weight:600;border:none}
.modal-btn.primary{background:var(--accent);color:var(--bg)}
.modal-btn.secondary{background:var(--bg4);color:var(--fg2);border:1px solid var(--border)}
.theme-grid{display:flex;gap:8px;margin-bottom:10px}
.theme-opt{flex:1;padding:12px;border-radius:var(--radius-sm);border:2px solid var(--border);cursor:pointer;text-align:center;font-size:12px;font-weight:600}
.theme-opt.active{border-color:var(--fg)}
.theme-opt.dark-opt{background:#000;color:#fff}
.theme-opt.light-opt{background:#fff;color:#000;border-color:#ccc}
.provider-row{display:flex;gap:8px;margin-bottom:8px}
.provider-row select{flex:1}
.provider-row input{flex:2}
.prov-badge{display:inline-block;padding:3px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.prov-nvidia{background:#76b900;color:#000}
.prov-openrouter{background:#6366f1;color:#fff}
.prov-cohere{background:#ff6b6b;color:#fff}
@media(max-width:768px){
  #sidebar{position:absolute;z-index:15;height:100%;box-shadow:var(--shadow);width:260px}
  .msg{max-width:92%}
  #chat{padding:12px}
  #input-area{padding:10px 12px}
  #code-panel.open{position:absolute;right:0;top:0;height:100%;width:90%;z-index:20}
  #chat-area{max-width:100%}
}
</style>
</head>
<body>
<header>
  <h1>SYNAPSE</h1>
  <div class="hdr-right">
    <span id="status">Ready</span>
    <button class="hdr-btn" id="btn-code" title="Code Panel">{ }</button>
    <button class="hdr-btn" id="btn-settings" title="Settings">⚙</button>
    <button class="hdr-btn" id="toggle-sb" title="Sessions">☰</button>
  </div>
</header>
<div id="main">
  <div id="sidebar" class="hidden">
    <div class="sb-hdr"><span>Sessions</span><button class="sb-btn" id="new-session">+ New</button></div>
    <div id="session-list"></div>
  </div>
  <div id="chat-area">
    <div id="chat"></div>
    <div id="edit-indicator"><span>Editing message...</span><button id="cancel-edit">Cancel</button></div>
    <div id="mode-bar">
      <span id="mode-label">Mode</span>
      <button class="mode-btn active" data-mode="chat">Chat</button>
      <button class="mode-btn" data-mode="code">Code</button>
      <button class="mode-btn" data-mode="agent">Agent</button>
    </div>
    <div id="input-area">
      <input id="inp" type="text" placeholder="Sohbet et..." autocomplete="off">
      <button id="send" type="button">Send</button>
      <button id="stop" type="button">Stop</button>
    </div>
  </div>
  <div id="code-panel">
    <div class="cp-hdr"><span>Code Files</span><button class="cp-close" id="cp-close">✕</button></div>
    <div id="code-file-list"></div>
    <div id="code-viewer"><pre>Click a file to view.</pre></div>
    <iframe id="preview-frame" sandbox="allow-scripts"></iframe>
  </div>
</div>
<div class="modal-overlay" id="settings-modal">
  <div class="modal">
    <h3>Settings</h3>
    <div class="modal-section"><label>Theme</label>
      <div class="theme-grid">
        <div class="theme-opt dark-opt" id="theme-dark" onclick="setTheme('dark')">Dark</div>
        <div class="theme-opt light-opt" id="theme-light" onclick="setTheme('light')">Light</div>
      </div>
    </div>
    <div class="modal-section"><label>Provider</label>
      <div id="prov-badge" class="prov-badge prov-nvidia">NVIDIA</div>
      <div class="provider-row"><select id="prov-select"></select></div>
      <div class="provider-row"><input type="text" id="model-input" placeholder="Model name"></div>
      <div class="provider-row"><input type="password" id="apikey-input" placeholder="API Key"></div>
      <button class="modal-btn secondary" id="save-provider" style="width:100%;margin-top:4px">Save & Switch</button>
    </div>
    <div class="modal-section"><label>System Prompt</label><textarea id="sys-prompt" placeholder="Custom system prompt..."></textarea></div>
    <div class="modal-btns">
      <button class="modal-btn secondary" id="settings-close">Close</button>
      <button class="modal-btn primary" id="settings-save">Save</button>
    </div>
  </div>
</div>
<script>
var chat=document.getElementById('chat'),inp=document.getElementById('inp'),btn=document.getElementById('send'),stopBtn=document.getElementById('stop'),st=document.getElementById('status');
var sidebar=document.getElementById('sidebar'),sessList=document.getElementById('session-list');
var editInd=document.getElementById('edit-indicator'),cancelEditBtn=document.getElementById('cancel-edit');
var settingsModal=document.getElementById('settings-modal');
var codePanel=document.getElementById('code-panel'),codeFileList=document.getElementById('code-file-list'),codeViewer=document.getElementById('code-viewer'),previewFrame=document.getElementById('preview-frame');
var modeBtns=document.querySelectorAll('.mode-btn');
var busy=false,editIndex=-1,msgCount=0,renderQueue=0,currentSessionId=null,bgControllers={};
var PLACEHOLDERS={chat:'Sohbet et...',code:'Kod yaz...',agent:'Görev ver...'};

function setTheme(t){document.documentElement.setAttribute('data-theme',t);localStorage.setItem('synapse-theme',t);document.getElementById('theme-dark').classList.toggle('active',t==='dark');document.getElementById('theme-light').classList.toggle('active',t==='light');}
(function(){var t=localStorage.getItem('synapse-theme')||'dark';setTheme(t);})();

function renderMarkdown(text){
  var s=text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  s=s.replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>');
  s=s.replace(/`([^`]+)`/g,'<code>$1</code>');
  s=s.replace(/^### (.+)$/gm,'<h4>$1</h4>');
  s=s.replace(/^## (.+)$/gm,'<h3>$1</h3>');
  s=s.replace(/^# (.+)$/gm,'<h2>$1</h2>');
  s=s.replace(/^- (.+)$/gm,'<li>$1</li>');
  s=s.replace(/\\[(.+?)\\]\\((.+?)\\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
  s=s.replace(/^---$/gm,'<hr>');
  return s;
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
  var acts=document.createElement('div');acts.className='code-actions';
  var cpBtn=document.createElement('button');cpBtn.className='copy-btn';cpBtn.textContent='Copy';
  cpBtn.onclick=(function(code,b){return function(){if(navigator.clipboard){navigator.clipboard.writeText(code).then(function(){b.textContent='Done';setTimeout(function(){b.textContent='Copy'},1200);});}}})(p.content,cpBtn);
  acts.appendChild(cpBtn);
  if(p.lang==='html'||p.lang==='htm'){
    var pvBtn=document.createElement('button');pvBtn.className='preview-btn';pvBtn.textContent='Preview';
    pvBtn.onclick=(function(code){return function(){showPreview(code);}})(p.content);
    acts.appendChild(pvBtn);
  }
  hdr.appendChild(lang);hdr.appendChild(acts);
  var pre=document.createElement('div');pre.className='code-content';pre.textContent=p.content;
  block.appendChild(hdr);block.appendChild(pre);
  return block;
}
function showPreview(html){
  codePanel.classList.add('open');
  codeViewer.style.display='none';
  previewFrame.style.display='block';
  previewFrame.srcdoc=html;
}
function buildAiContent(el,rawText){
  el.innerHTML='';
  var parts=renderCodeBlocks(rawText);
  for(var i=0;i<parts.length;i++){
    if(parts[i].type==='code')el.appendChild(buildCodeBlock(parts[i]));
    else{var d=document.createElement('div');d.className='md-content';d.innerHTML=renderMarkdown(parts[i].content);el.appendChild(d);}
  }
}
function addMsg(role,text,idx){
  var d=document.createElement('div');d.className='msg '+role;
  if(role==='user'){
    d.textContent=text||'';
    if(idx>=0){var acts=document.createElement('div');acts.className='msg-actions';var eb=document.createElement('button');eb.className='edit-btn';eb.textContent='Edit';eb.onclick=function(){startEdit(idx,text)};acts.appendChild(eb);d.appendChild(acts);}
  }else if(role==='ai'){d._rawText=text||'';buildAiContent(d,d._rawText);}
  else{d.textContent=text||'';}
  chat.appendChild(d);chat.scrollTop=chat.scrollHeight;msgCount++;return d;
}
function appendToMsg(el,text){el._rawText=(el._rawText||'')+text;if(++renderQueue%4!==0)return;requestAnimationFrame(function(){buildAiContent(el,el._rawText);chat.scrollTop=chat.scrollHeight;});}
function setBusy(v){busy=v;btn.disabled=v;btn.style.display=v?'none':'block';stopBtn.style.display=v?'block':'none';st.textContent=v?'Generating...':'Ready';}
function startEdit(idx,text){editIndex=idx;inp.value=text;editInd.style.display='flex';inp.focus();}
cancelEditBtn.onclick=function(){editIndex=-1;inp.value='';editInd.style.display='none';};

modeBtns.forEach(function(b){
  b.onclick=function(){
    modeBtns.forEach(function(x){x.classList.remove('active');});
    b.classList.add('active');
    var mode=b.getAttribute('data-mode');
    inp.placeholder=PLACEHOLDERS[mode]||'Message...';
    fetch('/api/mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:mode})});
  };
});

function sendMsg(){
  var t=inp.value.trim();if(!t||busy)return;
  inp.value='';setBusy(true);
  addMsg('user',t,editIndex>=0?-1:msgCount);
  var thinkBox=null,aiBox=null,reqSession=currentSessionId;
  var ac=new AbortController();bgControllers[reqSession]=ac;
  var body=JSON.stringify({message:t,edit_index:editIndex,session_id:reqSession});
  editIndex=-1;editInd.style.display='none';
  fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:body,signal:ac.signal})
  .then(function(res){
    if(!res.ok)throw new Error('HTTP '+res.status);
    var reader=res.body.getReader(),dec=new TextDecoder(),buf='';
    function pump(){
      return reader.read().then(function(r){
        var isCurrent=(reqSession===currentSessionId);
        if(r.done){delete bgControllers[reqSession];if(isCurrent){setBusy(false);renderQueue=0;if(aiBox&&aiBox._rawText){buildAiContent(aiBox,aiBox._rawText);chat.scrollTop=chat.scrollHeight;}loadCodePanel();}return;}
        buf+=dec.decode(r.value,{stream:true});
        var lines=buf.split('\\n');buf=lines.pop();
        for(var i=0;i<lines.length;i++){
          var line=lines[i];if(line.indexOf('data: ')!==0)continue;
          var payload=line.substring(6);if(payload==='[DONE]')continue;
          try{
            var obj=JSON.parse(payload);
            if(!isCurrent)continue;
            if(obj.type==='reasoning'){if(!thinkBox)thinkBox=addMsg('thinking','');thinkBox.textContent+=obj.content;chat.scrollTop=chat.scrollHeight;}
            else if(obj.type==='content'){if(!aiBox)aiBox=addMsg('ai','');appendToMsg(aiBox,obj.content);}
            else if(obj.type==='error'){if(!aiBox)aiBox=addMsg('err','');aiBox.textContent+=obj.content;}
            else if(obj.type==='loop_status'){addMsg('loop-status',obj.content);}
            else if(obj.type==='action'){addMsg('cmd-result',obj.content);}
          }catch(e){}
        }
        return pump();
      });
    }
    return pump();
  })
  .catch(function(e){delete bgControllers[reqSession];if(reqSession===currentSessionId){setBusy(false);if(e.name!=='AbortError')addMsg('err','[Error] '+e.message);}});
}
stopBtn.onclick=function(){if(currentSessionId&&bgControllers[currentSessionId])bgControllers[currentSessionId].abort();setBusy(false);};
btn.onclick=sendMsg;
inp.onkeydown=function(e){if(e.key==='Enter'){e.preventDefault();sendMsg();}};
document.getElementById('toggle-sb').onclick=function(){sidebar.classList.toggle('hidden');};
document.getElementById('btn-code').onclick=function(){codePanel.classList.toggle('open');if(codePanel.classList.contains('open'))loadCodePanel();};
document.getElementById('cp-close').onclick=function(){codePanel.classList.remove('open');previewFrame.style.display='none';codeViewer.style.display='block';};

function loadCodePanel(){
  fetch('/api/code_context').then(function(r){return r.json();}).then(function(data){
    codeFileList.innerHTML='';
    var ctx=data.code_context||{};
    var keys=Object.keys(ctx);
    if(!keys.length){codeFileList.innerHTML='<div style="padding:8px;font-size:12px;color:var(--fg4)">No files yet.</div>';return;}
    keys.forEach(function(k){
      var d=document.createElement('div');d.className='code-file-item';d.textContent=k;
      d.onclick=function(){
        document.querySelectorAll('.code-file-item').forEach(function(x){x.classList.remove('active');});
        d.classList.add('active');
        previewFrame.style.display='none';codeViewer.style.display='block';
        codeViewer.innerHTML='<pre>'+ctx[k].replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</pre>';
      };
      codeFileList.appendChild(d);
    });
  });
}

document.getElementById('btn-settings').onclick=function(){
  fetch('/api/settings').then(function(r){return r.json();}).then(function(data){
    document.getElementById('sys-prompt').value=data.system_prompt||'';
    loadProviders(data.providers||{},data.default_provider||'');
    updateModeUI(data.mode||'chat');
    settingsModal.classList.add('show');
  });
};
document.getElementById('settings-close').onclick=function(){settingsModal.classList.remove('show');};
document.getElementById('settings-save').onclick=function(){
  fetch('/api/settings/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({system_prompt:document.getElementById('sys-prompt').value})}).then(function(){settingsModal.classList.remove('show');});
};
function updateModeUI(mode){
  modeBtns.forEach(function(b){b.classList.toggle('active',b.getAttribute('data-mode')===mode);});
  inp.placeholder=PLACEHOLDERS[mode]||'Message...';
}
function loadProviders(provData,defaultProv){
  var sel=document.getElementById('prov-select');sel.innerHTML='';
  Object.keys(provData).forEach(function(n){var o=document.createElement('option');o.value=n;o.textContent=n.toUpperCase();sel.appendChild(o);});
  if(defaultProv&&provData[defaultProv])sel.value=defaultProv;
  var cur=provData[sel.value]||{};
  document.getElementById('model-input').value=cur.model||'';
  document.getElementById('apikey-input').value=cur.api_key||'';
  updateProvBadge(sel.value);
  sel.onchange=function(){var p=provData[sel.value]||{};document.getElementById('model-input').value=p.model||'';document.getElementById('apikey-input').value=p.api_key||'';updateProvBadge(sel.value);};
}
function updateProvBadge(name){var b=document.getElementById('prov-badge');b.textContent=name.toUpperCase();b.className='prov-badge prov-'+name.toLowerCase();}
document.getElementById('save-provider').onclick=function(){
  fetch('/api/providers/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:document.getElementById('prov-select').value,model:document.getElementById('model-input').value.trim(),api_key:document.getElementById('apikey-input').value.trim()})})
  .then(function(r){return r.json();}).then(function(d){if(d.ok)alert('Provider saved.');else alert('Error');});
};

function loadSessions(){
  fetch('/api/sessions').then(function(r){return r.json();}).then(function(data){
    sessList.innerHTML='';
    (data.sessions||[]).forEach(function(s){
      if(s.active)currentSessionId=s.id;
      var d=document.createElement('div');d.className='sess-item'+(s.active?' active':'');
      var t=document.createElement('span');t.className='sess-title';t.textContent=s.title||s.id;
      var acts=document.createElement('div');acts.className='sess-actions';
      var ren=document.createElement('button');ren.className='sess-btn';ren.textContent='✎';ren.onclick=function(ev){ev.stopPropagation();renameSession(s.id,s.title);};
      var del=document.createElement('button');del.className='sess-btn del';del.textContent='✕';del.onclick=function(ev){ev.stopPropagation();deleteSession(s.id);};
      acts.appendChild(ren);acts.appendChild(del);
      d.appendChild(t);d.appendChild(acts);
      d.onclick=function(){switchSession(s.id);};
      sessList.appendChild(d);
    });
    localStorage.setItem('synapse-session',currentSessionId||'');
  }).catch(function(){});
}
function renameSession(sid,old){var t=prompt('Rename:',old);if(t&&t.trim())fetch('/api/session/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:sid,title:t.trim()})}).then(function(){loadSessions();});}
function switchSession(sid){
  if(sid===currentSessionId)return;
  currentSessionId=sid;
  localStorage.setItem('synapse-session',sid);
  chat.innerHTML='';msgCount=0;setBusy(false);
  fetch('/api/session/load',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:sid})})
  .then(function(){loadSessions();loadHistory();sidebar.classList.add('hidden');});
}
function deleteSession(sid){
  if(bgControllers[sid]){bgControllers[sid].abort();delete bgControllers[sid];}
  fetch('/api/session/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:sid})})
  .then(function(){if(sid===currentSessionId){chat.innerHTML='';msgCount=0;currentSessionId=null;localStorage.setItem('synapse-session','');}loadSessions();});
}
document.getElementById('new-session').onclick=function(){
  fetch('/api/session/new',{method:'POST'}).then(function(r){return r.json();}).then(function(d){
    currentSessionId=d.id;localStorage.setItem('synapse-session',d.id);
    chat.innerHTML='';msgCount=0;loadSessions();sidebar.classList.add('hidden');
  });
};
function loadHistory(){
  fetch('/api/history').then(function(r){return r.json();}).then(function(data){
    (data.messages||[]).forEach(function(m,i){addMsg(m.role==='user'?'user':'ai',m.content,m.role==='user'?i:-1);});
  }).catch(function(){});
}
(function(){
  var saved=localStorage.getItem('synapse-session');
  if(saved){
    fetch('/api/session/load',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:saved})})
    .then(function(){loadSessions();loadHistory();});
  }else{loadSessions();loadHistory();}
})();
</script>
</body>
</html>"""

app = None

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    def log_message(self, fmt, *args): pass
    def _json(self, data, code=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0: return {}
        try: return json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception: return {}
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
            cfg = load_json(CONFIG_PATH, {})
            self._json({"system_prompt": app.custom_system_prompt, "providers": cfg.get("providers", {}), "default_provider": cfg.get("default_provider", ""), "mode": app.get_mode()})
        elif self.path == '/api/code_context':
            self._json({"code_context": app.code_context})
        else:
            self.send_response(404); self.send_header('Content-Length', '0'); self.end_headers()
    def do_POST(self):
        body = self._body()
        if self.path == '/api/session/new': self._json({"id": app.new_session()})
        elif self.path == '/api/session/load': self._json({"ok": app.load_session(body.get("id", ""))})
        elif self.path == '/api/session/delete': app.delete_session(body.get("id", "")); self._json({"ok": True})
        elif self.path == '/api/session/rename': app.rename_session(body.get("id", ""), body.get("title", "")); self._json({"ok": True})
        elif self.path == '/api/settings/save': app.set_system_prompt(body.get("system_prompt", "")); self._json({"ok": True})
        elif self.path == '/api/mode': self._json({"ok": app.set_mode(body.get("mode", "chat")), "mode": app.get_mode()})
        elif self.path == '/api/providers/save':
            try:
                cfg = load_json(CONFIG_PATH, {})
                prov = body.get("provider", "")
                if prov and prov in cfg.get("providers", {}):
                    if body.get("model"): cfg["providers"][prov]["model"] = body["model"]
                    if body.get("api_key"): cfg["providers"][prov]["api_key"] = body["api_key"]
                    cfg["default_provider"] = prov
                    save_json(CONFIG_PATH, cfg)
                    app.cfg = cfg
                    app.switch_provider(prov)
                    self._json({"ok": True})
                else: self._json({"ok": False, "error": "Provider not found"})
            except Exception as e: self._json({"ok": False, "error": str(e)})
        elif self.path == '/api/chat': self._chat(body)
        else: self.send_response(404); self.send_header('Content-Length', '0'); self.end_headers()
    def _chat(self, body):
        msg = body.get('message', '').strip()
        edit_idx = body.get('edit_index', -1)
        sid = body.get('session_id', None)
        if not msg:
            self.send_response(400); self.send_header('Content-Length', '0'); self.end_headers(); return
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        try:
            stream = app.edit_and_resend(edit_idx, msg, sid) if edit_idx >= 0 else app.stream_chat(msg, sid)
            for chunk in stream:
                ct = chunk.get("type", ""); cd = chunk.get("data", "")
                if ct in ("reasoning", "content", "error", "loop_status", "action"):
                    self.wfile.write(("data: " + json.dumps({"type": ct, "content": cd}) + "\n\n").encode('utf-8'))
                    self.wfile.flush()
                elif ct == "actions":
                    for a in (cd if isinstance(cd, list) else []):
                        self.wfile.write(("data: " + json.dumps({"type": "action", "content": a}) + "\n\n").encode('utf-8'))
                        self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n"); self.wfile.flush()
        except BrokenPipeError: pass
        except Exception as e:
            try:
                self.wfile.write(("data: " + json.dumps({"type": "error", "content": str(e)}) + "\n\n").encode('utf-8'))
                self.wfile.write(b"data: [DONE]\n\n"); self.wfile.flush()
            except Exception: pass

def find_free_port(start=8080, tries=20):
    for p in range(start, start + tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', p))
                return p
        except OSError: continue
    return None

def run_gui():
    global app
    try: app = Synapsis()
    except ValueError as e: print("[!] " + str(e)); return
    port = find_free_port()
    if not port: print("\033[31m[!] No free port.\033[0m"); return
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    url = "http://127.0.0.1:" + str(port)
    print("\033[1;36m  SYNAPSE v3.0.0 GUI\033[0m")
    print("  \033[32mRunning at " + url + "\033[0m")
    print("  Press Ctrl+C to stop.\n")
    try:
        import webbrowser; webbrowser.open(url)
    except Exception: pass
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close(); print("\n[✓] Stopped.")
