'use strict';
const $ = (id) => document.getElementById(id);
const transcript = $('transcript');
const modelSelect = $('model');
const pending = [];
const say = (text, kind) => {
  const node = document.createElement('div');
  node.className = 'message ' + kind;
  node.textContent = text;
  transcript.appendChild(node);
  transcript.scrollTop = transcript.scrollHeight;
};
async function api(path, options) {
  const resp = await fetch(path, {cache:'no-store', ...options});
  const payload = await resp.json();
  if(!resp.ok) throw new Error(payload.error || ('HTTP ' + resp.status));
  return payload;
}
async function refresh(){
  try{
    const [status, models, graph] = await Promise.all([
      api('/api/status'),api('/api/models'),api('/api/ontology')
    ]);
    $('service-status').textContent = 'GATE ACTIVE / LOCAL';
    $('stop-state').textContent = status.blocked ? 'ENGAGED' : 'ARMED';
    $('governance-stop').textContent = status.blocked ? 'ACTIVE - BLOCKED' : 'ENFORCED';
    $('model-state').textContent = models.connected ? (models.models.length ? 'ONLINE' : 'NO MODELS') : 'OFFLINE';
    const old = modelSelect.value;
    modelSelect.replaceChildren();
    if(models.connected && models.models.length){
      for(const m of models.models){const option=document.createElement('option');option.value=m;option.textContent=m;modelSelect.appendChild(option)}
      modelSelect.value = models.models.includes(old) ? old : models.models.includes(models.default) ? models.default : models.models[0];
    }else{const option=document.createElement('option');option.value='';option.textContent='Ollama offline or model missing';modelSelect.appendChild(option)}
    $('nodes').replaceChildren();
    for(const item of graph.nodes){
      const n = document.createElement('div');n.className='node '+(/not-connected|conceptual/.test(item.status)?'planned':'');
      const label = document.createElement('span');label.textContent=item.label;
      const info = document.createElement('small');info.textContent=item.status.toUpperCase();
      n.append(label,info);$('nodes').appendChild(n);
    }
    return !status.blocked;
  }catch(e){$('service-status').textContent='CONNECTION ERROR';say(e.message,'error');return false}
}
$('chat-form').addEventListener('submit',async (event)=>{
  event.preventDefault();const input=$('prompt').value.trim();const model=modelSelect.value;
  if(!input||!model)return;
  const btn=$('send');btn.disabled=true;
  say(input,'user');pending.push({role:'user',content:input});
  $('prompt').value='';
  try{
    const response=await api('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({model,messages:pending.slice(-12)})});
    say(response.reply,'assistant');pending.push({role:'assistant',content:response.reply});
  }catch(e){say(e.message,'error');pending.pop()}
  finally{btn.disabled=false;$('prompt').focus()}
});
$('route').addEventListener('click',async()=>{
  const task=$('prompt').value.trim();if(!task)return;
  $('route').disabled=true;
  try{const r=await api('/api/route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task})});say('ADVISORY ROUTE: '+r.roles.join(' / ')+'\nNo agents executed.','system')}
  catch(e){say(e.message,'error')}
  finally{$('route').disabled=false}
});
refresh();
