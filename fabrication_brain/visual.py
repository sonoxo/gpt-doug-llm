"""Offline preview rendering; bounding-box geometry is NOT production-ready CAD."""
from __future__ import annotations
import html
import json

def scad_preview(report):
    rows = ["// GPT-Doug engineering draft: bounding-box proxy ONLY", "$fn=32;"]
    colors = ("[0.18,0.68,0.89]", "[0.96,0.65,0.19]", "[0.28,0.80,0.54]", "[0.75,0.42,0.84]")
    for i, part in enumerate(report["design"]["parts"]):
        center = ", ".join(map(str, part["center_mm"]))
        size = ", ".join(map(str, part["size_mm"]))
        rows.append("color(" + colors[i % len(colors)] + ",0.65) translate([" + center + "]) cube([" + size + "],center=true);")
    return "\n".join(rows) + "\n"

def mermaid_chart(report):
    tasks = report["assembly_plan"]
    ids = {t["id"]: "T" + str(i) for i, t in enumerate(tasks)}
    rows = ["flowchart TD", "  HUMAN[Engineer review only] --> GATE[Human safety release gate]"]
    for task in tasks:
        node = ids[task["id"]]
        rows.append('  ' + node + '["' + html.escape(task["id"], quote=True) + '"]')
        for dep in task["depends_on"]:
            rows.append('  ' + ids[dep] + ' --> ' + node)
        if not task["depends_on"]:
            rows.append('  GATE --> ' + node)
    return "\n".join(rows) + "\n"

def html_view(report):
    payload = json.dumps({"parts": report["design"]["parts"], "name": report["design"]["name"], "summary": report["summary"], "issues": report["blockers"] + report["warnings"]}, ensure_ascii=True).replace("<","\\u003c")
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GPT-Doug Fabrication Brain</title>
<style>body{background:#091323;color:#eef6ff;font:15px system-ui;margin:0}header{padding:20px;background:#101f35}h1{margin:8px 0}.badge{color:#e8f99c}main{display:grid;grid-template-columns:2fr 1fr;gap:15px;padding:16px}.pane{background:#13243b;padding:18px;border:1px solid #304861;border-radius:12px}canvas{width:100%;height:500px;background:#081323;touch-action:none}small{color:#b2c8e0}#issues{max-height:250px;overflow:auto}#parts{max-height:220px;overflow:auto}button{padding:7px}input{accent-color:cyan}@media(max-width:720px){main{grid-template-columns:1fr}}</style></head>
<body><header><small class="badge">ENGINEERING DRAFT ONLY - NO ACTUATION</small><h1 id="title"></h1><small>Welding / vehicles / 3D printing / robotics / assembly</small></header>
<main><section class="pane"><h3>Interactive 3D geometry proxy</h3><canvas id="view"></canvas><label>Yaw <input id="yaw" type="range" min="0" max="360" value="35"></label><label>Pitch <input id="pitch" type="range" min="5" max="85" value="38"></label><button id="reset">Reset</button><p><small>Axis-aligned part envelopes only. No clearances, loads, toolpaths, weld geometry or collision simulation.</small></p></section>
<section class="pane"><h3>Design / bill of materials</h3><div id="summary"></div><div id="parts"></div><h3>Engineering review flags</h3><div id="issues"></div></section></main>
<script>
const data = __REPORT__;
const byId = id => document.getElementById(id);byId('title').textContent=data.name;
byId('summary').textContent=data.summary.part_count+' parts / '+data.summary.joint_count+' joints / '+data.summary.manufacturing_readiness;
const colors=['#42b6df','#eab15a','#70cfa7','#c49bea','#eb7898','#779cec'];
data.parts.forEach((p,i)=>{let d=document.createElement('p');d.textContent=p.name+' - '+p.material+' / '+p.process+' / '+p.size_mm.join('x')+' mm';d.style.color=colors[i%colors.length];byId('parts').appendChild(d)});
data.issues.forEach(p=>{let d=document.createElement('p');d.textContent=p.code+': '+p.subject+' - '+p.detail;byId('issues').appendChild(d)});
const can=byId('view'),ctx=can.getContext('2d');let yaw=35*Math.PI/180,pitch=38*Math.PI/180,down=false,lastX=0;
function rotate(v){let [x,y,z]=v,c=Math.cos(yaw),s=Math.sin(yaw),a=x*c-y*s,b=x*s+y*c;return [a,b*Math.sin(pitch)-z*Math.cos(pitch),b*Math.cos(pitch)+z*Math.sin(pitch)]}
function draw(){let rect=can.getBoundingClientRect(),dpr=window.devicePixelRatio||1;can.width=rect.width*dpr;can.height=rect.height*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,rect.width,rect.height);
const boxes=data.parts.map(p=>{let [x,y,z]=p.center_mm,[w,h,d]=p.size_mm,v=[];for(let sx of [-1,1])for(let sy of [-1,1])for(let sz of [-1,1])v.push(rotate([x+sx*w/2,y+sy*h/2,z+sz*d/2]));return v});
let xs=boxes.flat().map(v=>v[0]),ys=boxes.flat().map(v=>v[1]),minx=Math.min(...xs),maxx=Math.max(...xs),miny=Math.min(...ys),maxy=Math.max(...ys),scale=Math.min((rect.width-50)/Math.max(1,maxx-minx),(rect.height-50)/Math.max(1,maxy-miny));
function point(v){return [(v[0]-(minx+maxx)/2)*scale+rect.width/2,((miny+maxy)/2-v[1])*scale+rect.height/2,v[2]]}
const groups=[[0,2,6,4],[1,5,7,3],[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6]],faces=[];
boxes.forEach((vs,i)=>groups.forEach(g=>{let f=g.map(j=>point(vs[j]));faces.push({f,i,depth:f.reduce((s,x)=>s+x[2],0)/4})}));
faces.sort((a,b)=>b.depth-a.depth);faces.forEach(o=>{ctx.beginPath();o.f.forEach((p,j)=>j?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.fillStyle=colors[o.i%colors.length]+'a0';ctx.strokeStyle='#d2efff';ctx.fill();ctx.stroke()})}
function update(){requestAnimationFrame(draw)}byId('yaw').oninput=e=>{yaw=+e.target.value*Math.PI/180;update()};byId('pitch').oninput=e=>{pitch=+e.target.value*Math.PI/180;update()};byId('reset').onclick=()=>{yaw=35*Math.PI/180;pitch=38*Math.PI/180;update()};
can.onpointerdown=e=>{down=true;lastX=e.clientX;can.setPointerCapture(e.pointerId)};can.onpointermove=e=>{if(down){yaw+=(e.clientX-lastX)*.01;lastX=e.clientX;update()}};can.onpointerup=()=>down=false;window.onresize=update;update();
</script></body></html>""".replace("__REPORT__", payload)
