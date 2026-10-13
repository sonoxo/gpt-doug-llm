"""Zero-dependency local dashboard. Status is supplied only by localhost."""
HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GPT-Doug Sensor Swarm</title>
<style>
:root{color-scheme:dark;font:15px system-ui,sans-serif;background:#07101b;color:#edf6ff}
*{box-sizing:border-box}body{margin:0 auto;max-width:1190px;padding:32px 20px}
header{display:flex;justify-content:space-between;align-items:center;gap:16px;border-bottom:1px solid #244058;padding-bottom:20px}
h1{margin:0;font-size:1.6rem}h2{font-size:1rem;margin:0 0 14px;color:#9bd9ed}
small,.muted{color:#a5b7c9}.tag{background:#15354b;border:1px solid #2b6883;border-radius:30px;padding:6px 12px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:24px 0}
.stat,.panel{border:1px solid #244058;border-radius:14px;background:#0c1c2b;padding:20px}
.num{font-weight:750;font-size:2rem;margin:7px 0}.layout{display:grid;grid-template-columns:1fr 1.6fr;gap:16px}
table{border-collapse:collapse;width:100%;font-size:.82rem}td,th{padding:11px 8px;text-align:left;border-bottom:1px solid #244058}
th{color:#a5b7c9}td{overflow-wrap:anywhere}.healthy{color:#7ee4b1}.rejected{color:#ffb9a8}
.code{font-family:ui-monospace,monospace}.scroll{max-height:430px;overflow:auto}
footer{margin-top:24px;color:#a5b7c9;font-size:.85rem}
@media(max-width:760px){.layout{grid-template-columns:1fr}header{align-items:flex-start;flex-direction:column}}
</style></head><body>
<header><div><h1>GPT-Doug / Sensor Swarm</h1><small>Provenance-first · read-only · localhost</small></div>
<span class="tag" id="connection">Connecting</span></header>
<div class="stats"><section class="stat"><div class="muted">Evidence events</div><div class="num" id="event-count">—</div></section>
<section class="stat"><div class="muted">Active adapters</div><div class="num" id="sensor-count">—</div></section>
<section class="stat"><div class="muted">Policy failures</div><div class="num" id="failed-count">—</div></section></div>
<main class="layout"><section class="panel"><h2>Sensor fleet health</h2><div class="scroll">
<table><thead><tr><th>Sensor</th><th>Adapter</th><th>Status</th></tr></thead><tbody id="sensors"></tbody></table></div></section>
<section class="panel"><h2>Evidence stream</h2><div class="scroll">
<table><thead><tr><th>Observed (UTC)</th><th>Source</th><th>Metric</th><th>Value</th></tr></thead><tbody id="events"></tbody></table></div></section></main>
<footer>No camera capture, remote scanning, personal identification, process actuation, or automatic external actions.
Events are bounded scalar observations. Official patent verification remains pending. Refreshes every five seconds.</footer>
<script>
const el=id=>document.getElementById(id);
function cell(row,text,className=''){
  const c=document.createElement('td');c.textContent=String(text);c.className=className;row.appendChild(c);
}
function table(target,rows,make){
  const t=el(target);t.replaceChildren();
  rows.forEach(item=>{const tr=document.createElement('tr');make(tr,item);t.appendChild(tr)});
}
async function update(){
  try{
    const r=await fetch('/api/status',{cache:'no-store'});
    if(!r.ok)throw Error('status unavailable');
    const d=await r.json();
    el('connection').textContent='Local link online';
    el('event-count').textContent=d.stored_count;
    el('sensor-count').textContent=d.sensors.length;
    el('failed-count').textContent=d.sensors.filter(s=>s.status!=='healthy').length;
    table('sensors',d.sensors,(tr,s)=>{cell(tr,s.id,'code');cell(tr,s.adapter);cell(tr,s.status,s.status)});
    table('events',d.events,(tr,e)=>{cell(tr,e.observed_at);cell(tr,e.source_id,'code');cell(tr,e.metric);cell(tr,e.value)});
  }catch(e){el('connection').textContent='Local link unavailable'}
}
update();setInterval(update,5000);
</script></body></html>"""
