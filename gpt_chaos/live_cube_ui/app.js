'use strict';
// Visual interaction never issues authentication, credential, or execution calls.
const $ = (id) => document.getElementById(id);
const ruleList = $('rule-list');
const moduleList = $('module-list');
const cube = $('cube');
const scene = $('cube-scene');
const axisCoordinates = {
  identity: [-23, -34], scope: [-23, -124], consent: [-23, -214],
  policy: [-23, 56], resources: [-110, -34], audit: [68, -34]
};
const faceColors = {
  ENFORCED: {color:'#2fcfa7',glow:'#91ffdf',shadow:'#38e4bb55'},
  REVIEW: {color:'#eaa94b',glow:'#ffe4a4',shadow:'#e8b25955'},
  LIMITED: {color:'#eaa94b',glow:'#ffe4a4',shadow:'#e8b25955'},
  UNVERIFIED: {color:'#dc5d74',glow:'#ffb0ba',shadow:'#e1627755'}
};
const state = {rules:[],selected:'identity',x:-23,y:-34,history:[],connection:'waiting'};
const abbreviations = {identity:'ID',scope:'SC',consent:'CN',policy:'PL',resources:'RS',audit:'AU'};
const symbols=['D','P','S','C','R','B','+'];

function cell(tag,className,text){
  const e=document.createElement(tag);
  if(className)e.className=className;
  if(text!==undefined)e.textContent=String(text);
  return e;
}
function paintCube(){
  for(const face of document.querySelectorAll('.face')){
    const id=face.dataset.axis;
    const axis=state.rules.find(r=>r.id===id);
    const status=axis ? axis.state:'UNVERIFIED';
    const tone=faceColors[status] || faceColors.UNVERIFIED;
    face.replaceChildren();
    face.style.setProperty('--tile-color',tone.color);
    face.style.setProperty('--tile-glow',tone.glow);
    face.style.setProperty('--tile-shadow',tone.shadow);
    for(let i=0;i<9;i++){
      const sq=cell('div','tile');
      sq.style.opacity=String(i===4?1:0.82+(i%3)*0.06);
      if(i===4)sq.appendChild(cell('span','tile-label',abbreviations[id]||''));
      face.appendChild(sq);
    }
  }
}
function faceView(axis, animate=true){
  const r=state.rules.find(row=>row.id===axis);
  state.selected=axis;
  const coords=axisCoordinates[axis];
  if(coords){state.x=coords[0];state.y=coords[1];}
  if(!animate)cube.style.transition='none';
  cube.style.transform=`rotateX(${state.x}deg) rotateY(${state.y}deg)`;
  if(!animate)requestAnimationFrame(()=>{cube.style.transition='';});
  $('selected-title').textContent=r?.name || axis.toUpperCase();
  $('selected-explain').textContent=r?.detail || 'Select a policy facet to inspect its status';
  for(const item of ruleList.querySelectorAll('button'))item.classList.toggle('active',item.dataset.axis===axis);
}
function updateRules(data){
  state.rules=Array.isArray(data)?data:[];
  const frag=document.createDocumentFragment();
  for(const axis of state.rules){
    const btn=cell('button','rule');
    btn.type='button';btn.dataset.axis=axis.id;
    btn.title='Rotate visual cube to '+axis.name;
    btn.append(cell('i',`rule-color ${axis.state}`),cell('span','rule-name',axis.name),cell('span','rule-state',axis.state));
    btn.addEventListener('click',()=>faceView(axis.id));
    frag.appendChild(btn);
  }
  ruleList.replaceChildren(frag);
  paintCube();
  // Selecting a face doesn't change the policy data.
  const selected=state.rules.some(r=>r.id===state.selected)?state.selected:'identity';
  const r=state.rules.find(x=>x.id===selected);
  $('selected-title').textContent=r?.name || selected;
  $('selected-explain').textContent=r?.detail || 'Waiting for policy data';
  for(const item of ruleList.querySelectorAll('button'))item.classList.toggle('active',item.dataset.axis===selected);
}
function updateModules(data){
  const frag=document.createDocumentFragment();
  const arr=Array.isArray(data)?data:[];
  for(let i=0;i<arr.length;i++){
    const item=arr[i];
    const card=cell('div','module');
    card.appendChild(cell('span','module-symbol',symbols[i]||'+'));
    const descriptor=cell('div','');
    descriptor.append(cell('span','module-name',item.name),cell('span','module-role',item.role));
    card.appendChild(descriptor);
    const badge=cell('span',item.source_state==='PRESENT'?'source-state':'source-state off',item.source_state==='PRESENT'?'SOURCE':'MISSING');
    badge.title=item.note+' • runtime '+item.runtime_state;
    card.appendChild(badge);frag.appendChild(card);
  }
  moduleList.replaceChildren(frag);
}
function fmtUp(n){
  const sec=Math.max(0,Math.floor(Number(n)||0));
  return [Math.floor(sec/3600),Math.floor(sec/60)%60,sec%60].map(v=>String(v).padStart(2,'0')).join(':');
}
function updateSnapshot(data){
  if(data?.name!=='GPT-DOUG-CHAOS'||!Array.isArray(data.access_cube))return;
  $('utc-time').textContent=(data.timestamp_utc?.slice(11,19)||'--:--:--')+' UTC';
  $('uptime').textContent=fmtUp(data.uptime_seconds);
  $('modules-count').textContent=`${data.counts.source_present} / ${data.counts.source_total}`;
  $('viewers').textContent=String(data.connected_viewers);
  $('requests').textContent=String(data.http_requests);
  $('sequence').textContent='#'+String(data.sequence).padStart(4,'0');
  $('agents-active').textContent=String(data.counts.running_agents_verified);
  const matched=data.policy?.state==='MATCHED';
  $('hero-policy').textContent=matched?'POLICY SAMPLE MATCHED':(data.policy?.state||'UNVERIFIED');
  $('hero-policy').classList.toggle('good',matched);
  $('hero-hash').textContent=matched?`${data.policy.controls_checked}/${data.policy.controls_total} checks • fingerprint ${data.policy.fingerprint}`:
    (data.policy?.reason||'No policy source available');
  $('audit-status').textContent=matched?'PROJECT POLICY SAMPLE VERIFIED • ACTION AUTHORITY NOT GRANTED':
    'POLICY NOT VERIFIED • EXTERNAL ACTIONS DISABLED';
  $('cube-update').textContent=`SAMPLE ${data.sequence} / ${data.timestamp_utc?.slice(11,19)||''}`;
  updateRules(data.access_cube);
  updateModules(data.modules);
  state.history.push(Number(data.http_requests)||0);
  if(state.history.length>45)state.history.shift();
  drawPulse();
}
function connection(next){
  state.connection=next;
  const e=$('connection');e.className='connection '+next;
  const lbl={connected:'LIVE LOCAL STREAM',waiting:'CONNECTING',disconnected:'RECONNECTING'}[next]||'OFFLINE';
  $('connection-label').textContent=lbl;
  $('feed-label').textContent=next==='connected'?'ACTIVE':next.toUpperCase();
}
function drawPulse(){
  const canvas=$('pulse');const ctx=canvas.getContext('2d');if(!ctx)return;
  const bounds=canvas.getBoundingClientRect(), scale=window.devicePixelRatio||1;
  const w=Math.max(120,Math.round(bounds.width*scale)),h=Math.round(101*scale);
  if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
  ctx.clearRect(0,0,w,h);
  const pad=12*scale;
  ctx.strokeStyle='#2d4760';ctx.lineWidth=scale;
  for(let i=0;i<4;i++){
    const y=pad+(h-2*pad)*i/3;
    ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();
  }
  if(state.history.length<2)return;
  const vals=state.history;
  const min=Math.min(...vals),max=Math.max(...vals);
  const spread=Math.max(3,max-min);
  const coords=vals.map((v,i)=>({x:pad+(w-2*pad)*i/(vals.length-1),
    y:h-pad-(v-min+0.5)/spread*(h-2*pad)}));
  const grad=ctx.createLinearGradient(0,0,0,h);
  grad.addColorStop(0,'#4de4c044');grad.addColorStop(1,'#4de4c000');
  ctx.fillStyle=grad;ctx.beginPath();ctx.moveTo(coords[0].x,h-pad);
  for(const pt of coords)ctx.lineTo(pt.x,pt.y);
  ctx.lineTo(coords[coords.length-1].x,h-pad);ctx.closePath();ctx.fill();
  ctx.strokeStyle='#53dfbc';ctx.lineWidth=2.2*scale;
  ctx.beginPath();ctx.moveTo(coords[0].x,coords[0].y);
  for(let i=1;i<coords.length;i++)ctx.lineTo(coords[i].x,coords[i].y);
  ctx.stroke();
  const last=coords[coords.length-1];ctx.fillStyle='#86ffe1';ctx.beginPath();ctx.arc(last.x,last.y,3.8*scale,0,Math.PI*2);ctx.fill();
}
$('rotate-left').addEventListener('click',()=>{state.y-=90;cube.style.transform=`rotateX(${state.x}deg) rotateY(${state.y}deg)`;});
$('rotate-right').addEventListener('click',()=>{state.y+=90;cube.style.transform=`rotateX(${state.x}deg) rotateY(${state.y}deg)`;});
$('rotate-up').addEventListener('click',()=>{state.x-=90;cube.style.transform=`rotateX(${state.x}deg) rotateY(${state.y}deg)`;});
$('reset-view').addEventListener('click',()=>faceView('identity'));
let dragging=false,px=0,py=0;
scene.addEventListener('pointerdown',e=>{dragging=true;px=e.clientX;py=e.clientY;scene.setPointerCapture(e.pointerId);cube.style.transition='none';});
scene.addEventListener('pointermove',e=>{if(!dragging)return;state.y+=(e.clientX-px)*.55;state.x-=(e.clientY-py)*.55;px=e.clientX;py=e.clientY;cube.style.transform=`rotateX(${state.x}deg) rotateY(${state.y}deg)`;});
function endDrag(){if(!dragging)return;dragging=false;cube.style.transition='';}
scene.addEventListener('pointerup',endDrag);scene.addEventListener('pointercancel',endDrag);
window.addEventListener('resize',drawPulse);
async function initial(){
  try{const res=await fetch('/api/status',{cache:'no-store'});if(res.ok)updateSnapshot(await res.json());}
  catch(_){ /* EventSource can still reconnect */ }
  const events=new EventSource('/events');
  events.addEventListener('snapshot',e=>{try{updateSnapshot(JSON.parse(e.data));connection('connected');}catch(_){connection('disconnected');}});
  events.addEventListener('open',()=>connection('connected'));
  events.addEventListener('error',()=>connection('disconnected'));
}
paintCube();drawPulse();initial();
