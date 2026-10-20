/* XUNIA Watchtower: synthetic museum + authenticated same-origin loopback operator UI.
   No browser secrets persist; no provider APIs or external scanning are called. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const demoModels = [
    {model_id:'gpt-doug-llm',provider:'XUNIA / synthetic',agent_id:'orchestrator',grants:['inference:chat','model_update:self_modify'],scopes:['public']},
    {model_id:'gpt-6',provider:'OpenAI / illustrative',agent_id:'reviewer',grants:['inference:chat'],scopes:['public']},
    {model_id:'claude',provider:'Anthropic / illustrative',agent_id:'analyst',grants:['inference:chat'],scopes:['public']},
    {model_id:'gemini',provider:'Google / illustrative',agent_id:'summarizer',grants:['inference:chat'],scopes:['public']},
    {model_id:'llama3:8b',provider:'Ollama / illustrative',agent_id:'local-worker',grants:['inference:chat'],scopes:['public']},
    {model_id:'qwen3:4b',provider:'Open weights / illustrative',agent_id:'critic',grants:['telemetry:heartbeat'],scopes:['public']}
  ];
  const makeEvent = (model,kind,action,verdict,reason,risk,id) => ({id,model_id:model,kind,action,verdict,reason,risk,at:Date.now()/1000});
  const demoEvents = [
    makeEvent('gpt-doug-llm','inference','chat','allow','within_registered_policy','low','SIM-301'),
    makeEvent('llama3:8b','telemetry','heartbeat','allow','within_registered_policy','low','SIM-302'),
    makeEvent('gpt-doug-llm','model_update','self_modify','review','human_approval_required','high','SIM-303'),
    makeEvent('gemini','tool_call','execute','deny','capability_not_granted','high','SIM-304'),
    makeEvent('claude','inference','chat','allow','within_registered_policy','low','SIM-305'),
    makeEvent('qwen3:4b','retrieval','read_internal','deny','data_scope_not_granted','high','SIM-306'),
    makeEvent('gpt-6','inference','chat','allow','within_registered_policy','low','SIM-307'),
    makeEvent('gpt-doug-llm','policy_change','activate','review','human_approval_required','high','SIM-308')
  ];
  let mode = 'demo', stopped = false, events = [...demoEvents], models = [...demoModels], pendingReviews = [],
      operatorToken = '', lastOverview = null, auditState = {valid:null,records:8}, scenarioNumber = 400;
  const ephemeralText = 'Synthetic demonstration; not an actual AI provider connection.';
  function el(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=String(text);return node;}
  function notice(message){const t=$('toast');t.textContent=message;t.classList.add('show');clearTimeout(notice.timer);notice.timer=setTimeout(()=>t.classList.remove('show'),3600);}
  function updateClock(){ $('utcClock').textContent = new Date().toISOString().slice(11,19)+' UTC'; }
  updateClock();setInterval(updateClock,1000);
  function nfmt(n){return Number(n||0).toLocaleString('en-US');}
  function fmtTime(ts){let t=new Date((ts||Date.now()/1000)*1000);return Number.isFinite(t.getTime())?t.toISOString().slice(11,19):'--:--:--';}
  function publicEvent(a){return {id:a.id||a.decision_id,model_id:a.model_id,provider:a.provider||'synthetic',kind:a.kind,action:a.action,verdict:a.verdict,risk:a.risk,reason:a.reason,at:a.at,event_digest:a.event_digest||undefined};}
  function metrics(){
    const counts = lastOverview?.stats && mode==='live' ? lastOverview.stats : {models:models.length,decisions:events.length,allowed:events.filter(x=>x.verdict==='allow').length,denied:events.filter(x=>x.verdict==='deny').length,reviewed:events.filter(x=>x.verdict==='review').length};
    $('metricModels').textContent=nfmt(counts.models);$('metricEvents').textContent=nfmt(counts.decisions);$('metricDenied').textContent=nfmt(counts.denied);$('metricReview').textContent=nfmt(counts.reviewed);
    $('metricModelsNote').textContent=mode==='demo'?'Synthetic roster':'Registered at localhost';
    $('feedCount').textContent=events.length+' EVENTS';$('fleetCount').textContent=models.length+(mode==='demo'?' SYNTHETIC':' REGISTERED');
    $('auditRecords').textContent=nfmt(auditState.records);$('auditValidity').textContent=mode==='demo'?'SIMULATED':auditState.valid?'VERIFIED':'INTEGRITY ALERT';
    $('auditCoverage').textContent=mode==='demo'?'DEMO ONLY':'CONNECTED ONLY';$('auditState').textContent=mode==='demo'?'DEMO / SYNTHETIC':auditState.valid?'HMAC VERIFIED':'AUDIT FAILURE';
  }
  function controls(){
    $('stopVisual').classList.toggle('stopped',stopped);
    $('controlLabel').textContent=stopped?'STOP LATCHED':'GUARD ACTIVE';
    $('stopMessage').textContent=stopped?'Execution denied until operator rearm':'Operator-governed AI stop path available';
    $('modePill').textContent=mode==='demo'?'● SYNTHETIC DEMO':'● LOOPBACK GATEWAY';
    $('modeDescription').textContent=mode==='demo'?ephemeralText:'Authenticated, instrumented runtimes only. All decisions stored locally.';
    $('useDemo').classList.toggle('selected',mode==='demo');$('connectLocal').classList.toggle('selected',mode==='live');
  }
  function feed(){
    const container=$('eventFeed');container.replaceChildren();
    const recent=[...events].reverse().slice(0,11);
    if(!recent.length)container.append(el('p','helper','No decisions recorded. Instrument a model to begin.'));
    recent.forEach(e=>{
      const row=el('div','feed-item');row.append(el('span','feed-time',fmtTime(e.at)));
      const message=el('div','feed-message');message.append(el('strong','',e.model_id+' · '+e.action),el('small','',String(e.reason).replaceAll('_',' ')));
      row.append(message,el('span','verdict '+e.verdict,e.verdict.toUpperCase()));container.append(row);
    });
  }
  function renderModels(){
    const grid=$('modelGrid');grid.replaceChildren();
    if(!models.length)grid.append(el('p','helper','No models registered. Use the local operator API to enroll one.'));
    models.forEach((m,i)=>{
      const card=el('article','model-card '+(mode==='demo'?'synthetic':''));
      card.append(el('div','model-logo',['◈','✳','◉','⌬','⬡','◆'][i%6]));
      card.append(el('h3','',m.model_id),el('p','',m.provider+' / '+m.agent_id));
      const status=el('div','model-status');status.append(el('span','',m.grants?.length+' GRANTS · '+(m.scopes?.join(', ')||'public')),el('span','',mode==='demo'?'NOT CONNECTED':'ENROLLED'));
      card.append(status);grid.append(card);
    });
  }
  function renderApprovals(){
    const box=$('approvalQueue');box.replaceChildren();let reviews=(mode==='live'?pendingReviews:[...events].reverse().filter(x=>x.verdict==='review')).slice(0,10);
    if(!reviews.length)box.append(el('p','helper','No events awaiting human review.'));
    reviews.forEach(e=>{
      const row=el('div','approval-item');const info=el('div');info.append(el('b','',e.model_id+' / '+e.kind+':'+e.action),el('small','',e.id+' · '+e.reason));
      const use=el('button','',mode==='demo'?'Simulated':'Select');
      use.type='button';use.addEventListener('click',()=>{$('approvalDecision').value=mode==='demo'?'':e.id;notice(mode==='demo'?'Public demo approvals are informational.':'Decision ID selected for operator review.');});
      row.append(info,use);box.append(row);
    });
  }
  function renderAudit(){
    const box=$('auditTable');box.replaceChildren();
    [...events].reverse().slice(0,22).forEach(e=>{
      const row=el('div','log-row');row.append(el('span','',fmtTime(e.at)),el('b','',e.model_id+' / '+e.kind+':'+e.action),el('span','',e.verdict.toUpperCase()));box.append(row);
    });
  }
  function render(){metrics();controls();feed();renderModels();renderApprovals();renderAudit();}
  function addDemoEvent(e){events.push(e);auditState.records=events.length;render();}
  function scenario(){
    if(mode==='live'){notice('Training drill runs only in synthetic mode.');return;}
    const c=scenarioNumber++;
    [makeEvent('llama3:8b','inference','generate',stopped?'deny':'allow',stopped?'operator_emergency_stop':'within_registered_policy','low','SIM-'+c),
     makeEvent('gpt-doug-llm','model_update','self_modify',stopped?'deny':'review',stopped?'operator_emergency_stop':'human_approval_required','high','SIM-'+(scenarioNumber++)),
     makeEvent('gemini','tool_call','administer','deny',stopped?'operator_emergency_stop':'capability_not_granted','high','SIM-'+(scenarioNumber++))].forEach(addDemoEvent);
    notice('Three synthetic policy decisions evaluated.');
  }
  $('runScenario').addEventListener('click',scenario);
  $('injectRSI').addEventListener('click',()=>{
    if(mode!=='demo'){notice('Submit governed model updates through the authenticated model API.');return;}
    addDemoEvent(makeEvent('gpt-doug-llm','model_update','self_modify',stopped?'deny':'review',stopped?'operator_emergency_stop':'human_approval_required','high','SIM-'+scenarioNumber++));
    notice('Synthetic RSI proposal held for independent review.');
  });
  const download=(name,data)=>{const b=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(b);const a=el('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  $('exportReport').addEventListener('click',()=>{download('xunia-watchtower-evidence.json',{schema:'xunia.watchtower.evidence.v1',mode:mode==='demo'?'synthetic_demo':'local_operator_gateway',generated_at:new Date().toISOString(),models:models.map(m=>({model_id:m.model_id,provider:m.provider,agent_id:m.agent_id,grants:m.grants,scopes:m.scopes})),events:events.map(publicEvent),audit:auditState,privacy:'No prompt plaintext or API credentials included.'});notice('Evidence JSON exported.');});
  document.querySelectorAll('.nav-item').forEach(btn=>btn.addEventListener('click',()=>{
    document.querySelectorAll('.nav-item').forEach(x=>x.classList.toggle('active',x===btn));
    document.querySelectorAll('.panel-content').forEach(x=>x.classList.toggle('active',x.dataset.section===btn.dataset.panel));
  }));
  $('useDemo').addEventListener('click',()=>{mode='demo';operatorToken='';lastOverview=null;stopped=false;models=[...demoModels];events=[...demoEvents];auditState={valid:null,records:events.length};render();notice('Switched to public synthetic simulation.');});
  async function req(path,{method='GET',body=null}={}){
    const opt={method,headers:{Authorization:'Bearer '+operatorToken}};
    if(body!==null){opt.headers['Content-Type']='application/json';opt.body=JSON.stringify(body);}
    const resp=await fetch(path,opt);let data=await resp.json().catch(()=>({error:'non_json_response'}));
    if(!resp.ok)throw Error(data.error||data.reason||'HTTP '+resp.status);
    return data;
  }
  async function refresh(){
    if(mode!=='live')return;
    try{
      const [summary,feedData,pendingData]=await Promise.all([req('/api/v1/overview'),req('/api/v1/events'),req('/api/v1/pending')]);
      if(mode!=='live')return;
      lastOverview=summary;models=summary.models||[];events=(feedData.events||[]).reverse().map(e=>({id:e.id,...e}));pendingReviews=(pendingData.decisions||[]).map(e=>({id:e.id,...e}));
      stopped=!!summary.stop?.stopped;auditState=summary.audit||{valid:false,records:0};render();
      if(auditState.valid===false)notice('Audit integrity failure: take the system out of operation.');
    }catch(err){notice('Live connection unavailable: '+err.message);}
  }
  function isLocal(){return ['127.0.0.1','localhost'].includes(window.location.hostname);}
  $('connectLocal').addEventListener('click',()=>{
    if(!isLocal()){notice('Start the local Watchtower service and open http://127.0.0.1:8877/ to use live controls.');return;}
    $('authDialog').showModal();
  });
  $('cancelConnect').addEventListener('click',()=>{$('authDialog').close();});
  $('connectForm').addEventListener('submit',async event=>{
    event.preventDefault();let proposed=$('operatorToken').value;const old=operatorToken;operatorToken=proposed;
    try{const result=await req('/api/v1/overview');mode='live';lastOverview=result;$('authDialog').close();$('operatorToken').value='';await refresh();notice('Authenticated loopback gateway connected.');}
    catch(err){operatorToken=old;notice('Gateway authentication failed: '+err.message);}
  });
  setInterval(()=>{if(mode==='live')refresh();},3500);
  async function toggleStop(rearm){
    if(mode==='demo'){stopped=!rearm;render();notice(stopped?'Synthetic emergency stop engaged.':'Synthetic stop rearmed.');return;}
    let body;
    if(rearm){const answer=prompt('Type REARM WATCHTOWER to resume AI actions:');if(answer!=='REARM WATCHTOWER')return;body={confirmation:answer};}
    else{if(!confirm('Engage WATCHTOWER operator stop for all integrated models?'))return;body={reason:'dashboard_operator_stop'};}
    try{await req(rearm?'/api/v1/rearm':'/api/v1/stop',{method:'POST',body});await refresh();notice(rearm?'Operator confirmed rearm.':'All instrumented actions now blocked.');}
    catch(e){notice('Stop control error: '+e.message);}
  }
  $('stopBtn').addEventListener('click',()=>toggleStop(false));$('rearmBtn').addEventListener('click',()=>toggleStop(true));
  $('verifyAudit').addEventListener('click',async()=>{
    if(mode==='demo'){notice('Public demo has synthetic records, not a cryptographic audit ledger.');return;}
    try{auditState=await req('/api/v1/audit/verify');render();notice(auditState.valid?'Cryptographic audit chain verified.':'Chain verification failed.');}catch(err){auditState={valid:false,records:0};render();notice('Audit verification failed: '+err.message);}
  });
  $('registerForm').addEventListener('submit',async event=>{
    event.preventDefault();if(mode!=='live'){notice('Registration requires local operator connection.');return;}
    let p=$('registerProfile').value;let grants=p==='observe'?['telemetry:heartbeat','telemetry:observe']:p==='inference'?['telemetry:heartbeat','inference:chat','inference:generate','inference:embed','retrieval:read_public']:['telemetry:heartbeat','inference:chat','inference:generate','retrieval:read_public','tool_call:read','tool_call:write','tool_call:execute','model_update:self_modify','training:start','deployment:promote'];
    const o={model_id:$('registerModel').value.trim(),provider:$('registerProvider').value.trim(),agent_id:$('registerAgent').value.trim(),grants,scopes:['public']};
    try{const result=await req('/api/v1/models',{method:'POST',body:o});$('registerResult').textContent='Registered: '+result.model_id+'\nONE-TIME INGEST TOKEN (copy now; do not paste into public sites):\n'+result.ingest_token;await refresh();}
    catch(err){$('registerResult').textContent='Enrollment rejected: '+err.message;}
  });
  $('approveBtn').addEventListener('click',async()=>{
    if(mode!=='live'){notice('Synthetic demonstration cannot approve real execution.');return;}
    try{let r=await req('/api/v1/approve',{method:'POST',body:{decision_id:$('approvalDecision').value.trim(),review_evidence_sha256:$('approvalEvidence').value.trim(),ttl_seconds:300}});$('approvalResult').textContent='ONE-TIME APPROVAL ID (transfer to authorized adapter): '+r.approval_id+'\nExpires: '+new Date(r.expires_at*1000).toISOString();notice('Exact event digest approved; one execution only.');await refresh();}
    catch(e){$('approvalResult').textContent='Approval not granted: '+e.message;}
  });
  render();
})();
