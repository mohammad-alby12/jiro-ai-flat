const API = location.protocol === "file:" ? "http://127.0.0.1:8000" : "";
const $ = s => document.querySelector(s);
let currentId = null, aborter = null, uploadedText = "";
const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, opts={}) {
  const r = await fetch(API + path, opts);
  if (!r.ok) { let msg = await r.text(); throw new Error(msg || r.statusText); }
  return r.status === 204 ? null : r.json();
}
function renderMarkdown(text) {
  const html = marked.parse(text || "");
  return DOMPurify.sanitize(html);
}
function addMessage(role, content, id=null) {
  $("#welcome").hidden = true;
  const wrap = document.createElement("div");
  wrap.className = `message ${role}`;
  wrap.dataset.id = id || "";
  wrap.innerHTML = `<div class="avatar">${role==="assistant"?"J":"U"}</div><div class="message-body">${role==="assistant"?renderMarkdown(content):`<p>${esc(content).replace(/\n/g,"<br>")}</p>`}<div class="message-actions">${role==="assistant"?'<button class="copy">Copy</button>':''}</div></div>`;
  $("#messages").append(wrap);
  wrap.querySelector(".copy")?.addEventListener("click",()=>navigator.clipboard.writeText(content));
  wrap._content = content;
  $("#messages").scrollTop = $("#messages").scrollHeight;
  if (window.hljs) wrap.querySelectorAll("pre code").forEach(el=>hljs.highlightElement(el));
  return wrap;
}
async function refreshHistory() {
  try {
    const items = await api("/api/conversations");
    $("#history").innerHTML = "";
    items.forEach(c=>{
      const b=document.createElement("button"); b.className="history-item"; b.textContent=c.title;
      b.onclick=()=>openConversation(c.id); b.oncontextmenu=async e=>{e.preventDefault();const title=prompt("Rename conversation",c.title);if(title){await api(`/api/conversations/${c.id}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({title})});refreshHistory();}};
      $("#history").append(b);
    });
  } catch(e) { console.warn(e); }
}
async function newChat() {
  const c=await api("/api/conversations",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({title:"New chat"})});
  currentId=c.id; $("#messages").innerHTML=$("#welcome").outerHTML; $("#welcome").hidden=false; $("#prompt").focus(); refreshHistory();
}
async function openConversation(id) {
  const c=await api(`/api/conversations/${id}`); currentId=id;
  $("#messages").innerHTML="";
  if(!c.messages.length){$("#messages").innerHTML='<div class="welcome" id="welcome"><div class="welcome-symbol">J</div><h1>Welcome back.</h1></div>';return;}
  c.messages.forEach(m=>addMessage(m.role,m.content,m.id));
}
async function sendMessage() {
  const input=$("#prompt"), message=input.value.trim(); if(!message || aborter) return;
  if(!currentId) await newChat();
  input.value=""; input.style.height="auto";
  addMessage("user",message);
  const assistant=addMessage("assistant","");
  const body=assistant.querySelector(".message-body");
  aborter=new AbortController(); $("#sendBtn").hidden=true; $("#stopBtn").hidden=false;
  try {
    const res=await fetch(API+"/api/chat/stream",{method:"POST",headers:{"Content-Type":"application/json"},signal:aborter.signal,
      body:JSON.stringify({conversation_id:currentId,message:uploadedText?`Document context:\n${uploadedText}\n\nUser question: ${message}`:message,max_new_tokens:Number($("#maxTokens").value)})});
    if(!res.ok) throw new Error(await res.text());
    const reader=res.body.getReader(), decoder=new TextDecoder(); let buffer="",answer="";
    while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});
      const events=buffer.split("\n\n");buffer=events.pop();
      for(const event of events){const line=event.split("\n").find(x=>x.startsWith("data: "));if(!line)continue;const data=JSON.parse(line.slice(6));
        if(event.includes("event: token")){answer+=data.text;body.innerHTML=renderMarkdown(answer);assistant._content=answer;$("#messages").scrollTop=$("#messages").scrollHeight;}
        if(event.includes("event: error")) throw new Error(data.message);
      }
    }
    body.innerHTML=renderMarkdown(answer||"(No text returned)");assistant._content=answer;
    if(window.hljs)body.querySelectorAll("pre code").forEach(el=>hljs.highlightElement(el));
  } catch(e){if(e.name!=="AbortError")body.textContent="Error: "+e.message;}
  finally{aborter=null;$("#sendBtn").hidden=false;$("#stopBtn").hidden=true;uploadedText="";$("#fileState").textContent="Local model · No external AI API";refreshHistory();}
}
async function modelAction(action){try{const r=await api(`/api/models/${action}`,{method:"POST"});alert(action==="load"?"Model loaded.":"Model unloaded.");await refreshStatus();}catch(e){alert("Model error: "+e.message);}}
async function refreshStatus(){
 try{
  const [s,m]=await Promise.all([api("/api/system/status"),api("/api/system/metrics")]);
  $("#engineState").textContent=s.model.loaded?"Engine loaded":"Engine not loaded";$(".engine-dot").classList.toggle("on",s.model.loaded);
  $("#engineName").textContent=s.model.model||s.engine;$("#labEngine").textContent=`${s.engine} · ${s.model.model}`;
  $("#modelName").textContent=s.model.model;$("#modelEngine").textContent=`Runtime: ${s.engine}`;
  $("#modelStatus").textContent=s.model.loaded?"LOADED":"NOT LOADED";$("#modelMetric").textContent=s.model.loaded?"Ready":"Offline";$("#modelDetail").textContent=s.model.error||"Configured model";
  $("#cpuMetric").textContent=m.cpu_percent+"%";$("#ramMetric").textContent=m.ram_percent+"%";$("#ramDetail").textContent=`${m.ram_used_mb} / ${m.ram_total_mb} MB`;
  $("#procMetric").textContent=m.process_rss_mb+" MB";
 }catch(e){$("#engineState").textContent="Backend unavailable";}
}
function showView(name){
 ["chat","lab","models"].forEach(v=>{$(`#${v}View`).hidden=v!==name;});
 $("#pageName").textContent=name==="lab"?"AI Lab":name==="models"?"Model manager":"Chat";
 document.querySelectorAll(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.view===name));
 if(name==="lab"||name==="models")refreshStatus();
}
$("#newChat").onclick=newChat;$("#sendBtn").onclick=sendMessage;$("#stopBtn").onclick=()=>aborter?.abort();
$("#prompt").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMessage();}});
$("#prompt").addEventListener("input",e=>{e.target.style.height="auto";e.target.style.height=Math.min(e.target.scrollHeight,180)+"px";});
document.querySelectorAll(".nav-item").forEach(b=>b.onclick=()=>showView(b.dataset.view));
document.querySelectorAll("[data-prompt]").forEach(b=>b.onclick=()=>{$("#prompt").value=b.dataset.prompt;$("#prompt").focus();});
$("#menuBtn").onclick=()=>$("#sidebar").classList.toggle("open");
$("#loadModel").onclick=$("#loadModel2").onclick=()=>modelAction("load");
$("#unloadModel").onclick=$("#unloadModel2").onclick=()=>modelAction("unload");
$("#attachBtn").onclick=()=>$("#fileInput").click();
$("#fileInput").onchange=async e=>{const f=e.target.files[0];if(!f)return;const fd=new FormData();fd.append("file",f);try{const r=await fetch(API+"/api/documents/upload",{method:"POST",body:fd});if(!r.ok)throw new Error(await r.text());const d=await r.json();uploadedText=d.text;$("#fileState").textContent=`Attached: ${d.filename}`;}catch(err){alert(err.message);}};
$("#settingsBtn").onclick=()=>alert("Configure model, engine, and generation settings in backend/.env, then restart JIRO AI.");
refreshHistory();refreshStatus();setInterval(refreshStatus,8000);
