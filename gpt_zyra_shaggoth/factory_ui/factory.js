'use strict';
const csrf = document.querySelector('meta[name="factory-csrf"]').content;
const $ = id => document.getElementById(id);
let latest = null;
let connected = false;
function el(tag, className, text) {
  const node = document.createElement(tag);
  if(className) node.className = className;
  if(text !== undefined) node.textContent = String(text);
  return node;
}
function conciseTime(value) {
  if(!value) return '--';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '--' : date.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit'});
}
function setConnected(value) {
  connected = value;
  $('connection-text').textContent = value ? 'LIVE LOCAL STREAM' : 'Reconnecting...';
  $('connection-dot').className = 'status-light ' + (value ? 'running' : 'waiting');
}
function message(text) { $('action-feedback').textContent = text; }
async function action(path, data) {
  try {
    const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json', 'X-Factory-CSRF':csrf}, body:JSON.stringify(data)});
    const output = await response.json();
    if(!response.ok) throw new Error(output.error || 'Request rejected');
    message('Accepted locally. View production and events below.');
    await refresh();
    return output;
  } catch(e) {
    message('Factory: ' + String(e.message || e).slice(0,180));
    return null;
  }
}
function shortStage(stage) { return String(stage).replaceAll('_', ' '); }
function renderJob(job) {
  const row = el('article', 'job');
  const top = el('div', 'job-top');
  top.appendChild(el('h3','',job.goal));
  const cls = ['BLOCKED','REJECTED'].includes(job.stage)?'bad': ['AWAITING_REVIEW'].includes(job.stage)?'wait':job.stage==='APPROVED_LOCAL'?'ok':'';
  top.appendChild(el('span','job-tag '+cls, shortStage(job.stage)));
  const sub = el('div','job-sub');
  sub.appendChild(el('span','',job.kind));sub.appendChild(el('span','',job.backend));sub.appendChild(el('span','',conciseTime(job.updated)));
  const progress = el('div','job-progress');const bar=el('span');bar.style.width = (Number(job.progress)||0)+'%';progress.appendChild(bar);
  row.append(top,sub,progress);
  if(job.stage === 'AWAITING_REVIEW' || job.stage === 'APPROVED_LOCAL') {
    const actions = el('div','job-actions');
    if(job.artifact_sha256) {const download=el('a','','Download verified ZIP');download.href='/api/jobs/'+job.id+'/download';actions.appendChild(download);}
    if(job.stage === 'AWAITING_REVIEW') {
      const accept=el('button','','Approve local draft');
      const reject=el('button','','Reject');
      accept.onclick=()=>action('/api/jobs/'+job.id+'/review',{action:'approve'});
      reject.onclick=()=>action('/api/jobs/'+job.id+'/review',{action:'reject'});
      actions.append(accept,reject);
    }
    row.appendChild(actions);
  }
  return row;
}
function renderEvents(rows) {
  const host=$('events');host.replaceChildren();
  if(!rows.length){host.appendChild(el('div','empty-state','Waiting for factory events'));return;}
  for(const ev of [...rows].reverse().slice(0,40)){
    const row=el('div','event');row.appendChild(el('div','event-code','EV-'+String(ev.seq).padStart(3,'0')));
    const body=el('div','event-info');body.appendChild(el('strong','',shortStage(ev.stage)));
    body.appendChild(el('p','',ev.detail));row.appendChild(body);
    row.appendChild(el('div','event-time',conciseTime(ev.created)));host.appendChild(row);
  }
}
function render(s) {
  if(!s || typeof s !== 'object') return;
  latest=s;
  const counts=s.counts || {};
  $('total-jobs').textContent=s.jobs_total || 0;
  $('active-jobs').textContent=['QUEUED','PLANNING','BUILDING','VERIFYING','CRITIQUING'].reduce((total,k)=>total+(counts[k]||0),0);
  $('review-jobs').textContent=counts.AWAITING_REVIEW || 0;
  $('approved-jobs').textContent=counts.APPROVED_LOCAL || 0;
  $('uptime').textContent='UPTIME '+String(s.uptime_seconds||0)+'s';
  $('last-update').textContent='SNAPSHOT / '+(s.last_updated||'--');
  const policy=s.policy || {};
  $('policy-state').textContent=policy.state || 'UNKNOWN';
  $('policy-state').style.color=(policy.local_drafts_allowed?'#77e8b6':'#f4a16b');
  $('policy-note').textContent=policy.reason || 'unknown';
  $('policy-count').textContent=(policy.rules_matching||0)+' / '+(policy.rules_total||18)+' EXPECTED CONTROLS';
  $('policy-fill').style.width=(100*(policy.rules_matching||0)/(policy.rules_total||18))+'%';
  $('create-job').disabled=!policy.local_drafts_allowed;
  $('job-backend').querySelector('option[value="ollama"]').disabled=s.backend!=='offline+opt-in-local-ollama' || !policy.ollama_allowed;
  if($('job-backend').selectedOptions[0]?.disabled) $('job-backend').value='offline';
  $('seed-demo').disabled=!policy.local_drafts_allowed;
  $('pause-worker').textContent=s.worker_paused?'Resume worker':'Pause worker';
  $('factory-mode').textContent=s.worker_paused?'PAUSED':'AUTOMATIC';
  const processing=(s.jobs||[]).filter(x=>['PLANNING','BUILDING','VERIFYING','CRITIQUING'].includes(x.stage))[0];
  const phase=processing?processing.stage:null;
  const ready=(!phase && (counts.AWAITING_REVIEW||0)>0);
  document.querySelectorAll('.station').forEach(node=>{
    node.classList.toggle('active',node.dataset.phase===phase);
    node.classList.toggle('ready',node.dataset.phase==='AWAITING_REVIEW'&&ready);
  });
  $('live-stage-label').textContent=processing ? 'PROCESSING '+processing.id.slice(0,8)+' / '+shortStage(phase) : (ready?'OUTPUTS AWAITING REVIEW':'AWAITING PRODUCTION');
  $('telemetry-phase').textContent=processing?shortStage(phase):(s.worker_paused?'PAUSED':'IDLE');
  $('active-order').textContent=processing?processing.goal:'No active order — factory standing by';
  $('active-progress').style.width=processing?String(processing.progress||0)+'%':'0%';
  $('pending-count').textContent=counts.QUEUED||0;
  $('review-count').textContent=counts.AWAITING_REVIEW||0;
  const jobs=$('jobs');jobs.replaceChildren();
  if(!(s.jobs||[]).length){const e=el('div','empty-state');e.append(el('strong','','No jobs yet'),el('span','','Submit a directive or run sample jobs to activate production.'));jobs.appendChild(e);}
  else for(const job of s.jobs) jobs.appendChild(renderJob(job));
  renderEvents(s.events||[]);
}
async function refresh(){try{const response=await fetch('/api/status',{cache:'no-store'});if(!response.ok)throw Error('offline');render(await response.json());setConnected(true);}catch{setConnected(false);}}
$('job-goal').addEventListener('input',()=>{$('chars').textContent=String($('job-goal').value.length)+' / 480';});
$('job-form').addEventListener('submit',async evt=>{
  evt.preventDefault();
  const goal=$('job-goal').value;
  if(goal.trim().length<4){message('Describe a task with at least four characters.');return;}
  const value=await action('/api/jobs',{kind:$('job-kind').value,goal,backend:$('job-backend').value});
  if(value)$('job-goal').value='';
  $('chars').textContent=$('job-goal').value.length+' / 480';
});
$('seed-demo').addEventListener('click',()=>action('/api/demo',{}));
$('pause-worker').addEventListener('click',()=>action('/api/pause',{paused:!latest?.worker_paused}));
try{
  const stream=new EventSource('/events');
  stream.onmessage=event=>{try{render(JSON.parse(event.data));setConnected(true);}catch{setConnected(false);}};
  stream.onerror=()=>setConnected(false);
} catch {}
refresh();
setInterval(()=>{if(!connected)refresh();},4000);
