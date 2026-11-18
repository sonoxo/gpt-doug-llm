/* XUNIA CL1 XENOLOGY / creative non-kinetic browser atlas
 * Important: aliens, Shaggoths and shape diagrams are illustrative, not detections.
 * AARO cases reference official public pages; no live feeds, paid APIs or device access.
 */
(()=>{"use strict";
const $=id=>document.getElementById(id),TAU=Math.PI*2;
const groups=["aliens","uap","records","shaggoth"],groupNames={aliens:"CREATIVE ARCHETYPE",uap:"ILLUSTRATED UAP FORM",records:"OFFICIAL PUBLIC RECORD",shaggoth:"ORIGINAL CL1 FICTION"};
const groupColor={aliens:"#58dfcb",uap:"#75c7ff",records:"#efbf76",shaggoth:"#b58bff"};
const gridIds={aliens:"alienGrid",uap:"uapGrid",records:"reportGrid",shaggoth:"shoggothGrid"};
const sectionIds={aliens:"alienSection",uap:"uapSection",records:"reportSection",shaggoth:"shoggothSection"};
const countIds={aliens:"alienCount",uap:"uapCount",records:"reportCount",shaggoth:"shoggothCount"};
const evidenceNames={fictional:"FICTIONAL / CREATIVE",speculative:"SPECULATIVE / FOLKLORE",illustrative:"ILLUSTRATION / NO REPORT",documented:"DOCUMENTED PUBLIC REPORT",resolved:"RESOLVED PUBLIC REPORT"};
const state={data:[],byId:new Map(),selected:"s-shaggoth-prime",query:"",groups:new Set(groups),evidence:new Set(Object.keys(evidenceNames)),tab:"overview",
  angle:0,zoom:1,intensity:60,paused:false,animate:true,links:true,mode:"graph",points:[],drag:null,frame:0,motionTime:0,lastDraw:0,ready:false,quiet:false};
const motionReduced=!!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
let rootEdges=[];
function visible(){return state.data.filter(r=>state.groups.has(r.group)&&state.evidence.has(r.evidence)&&
  (!state.query||(r.name+" "+r.description+" "+r.domain+" "+r.id).toLowerCase().includes(state.query)));}
function selected(){return state.byId.get(state.selected)}
function hash(str){let h=2166136261;for(let i=0;i<str.length;i++){h^=str.charCodeAt(i);h=Math.imul(h,16777619)}return h>>>0}
function notify(t){$("cmdStatus").textContent=String(t)}
function scaleCanvas(canvas,ctx){const box=canvas.getBoundingClientRect(),w=Math.max(80,box.width),h=Math.max(80,box.height),dpr=Math.min(window.devicePixelRatio||1,2),cw=Math.round(w*dpr),ch=Math.round(h*dpr);if(canvas.width!==cw||canvas.height!==ch){canvas.width=cw;canvas.height=ch}ctx.setTransform(dpr,0,0,dpr,0,0);return [w,h]}
function gradient(ctx,x,y,r,a,b){const g=ctx.createRadialGradient(x-r*.25,y-r*.24,2,x,y,r);g.addColorStop(0,a);g.addColorStop(1,b);return g}
function line(ctx,coords,color,width=1){ctx.beginPath();ctx.moveTo(coords[0][0],coords[0][1]);for(let i=1;i<coords.length;i++)ctx.lineTo(coords[i][0],coords[i][1]);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke()}
function art(ctx,w,h,record,t=0,rotation=0,energy=.6){
  const color=groupColor[record.group]||"#7edfeb";
  ctx.save();ctx.clearRect(0,0,w,h);ctx.translate(w/2,h/2);ctx.scale(w/240,h/200);ctx.translate(-120,-100);
  const bg=ctx.createRadialGradient(122,84,6,122,104,150);bg.addColorStop(0,record.group==="shaggoth"?"#241047":"#17364c");bg.addColorStop(.58,"#071425");bg.addColorStop(1,"#020610");ctx.fillStyle=bg;ctx.fillRect(0,0,240,200);
  const seed=hash(record.id);ctx.fillStyle="#a9cbd9";
  for(let i=0;i<55;i++){const x=(seed+i*497+37)%238,y=(seed*3+i*331+11)%195,rad=(i%13===0?1.4:.55);ctx.globalAlpha=.12+(i%5)*.09;ctx.fillRect(x,y,rad,rad)}ctx.globalAlpha=1;
  const glow=Math.max(.07,Math.min(.92,energy));
  ctx.save();ctx.translate(120,101);ctx.rotate(rotation*.11);ctx.translate(-120,-101);
  if(record.group==="shaggoth"||record.visual==="cephalopod"||record.visual==="energy"||record.visual==="shadow"){
    ctx.shadowColor=record.group==="shaggoth"?"#aa70fa":color;ctx.shadowBlur=15+glow*28;
    const tentacleCount=record.group==="shaggoth"?13:7;
    for(let i=0;i<tentacleCount;i++){
      const a=i*TAU/tentacleCount+Math.sin(t*.65+i)*.09,r=record.group==="shaggoth"?98:61;
      const x=120+Math.cos(a)*r,y=107+Math.sin(a)*r*.78;
      const bend=28*Math.sin(a*2+t*.7+i);
      ctx.beginPath();ctx.moveTo(120,104);
      ctx.bezierCurveTo(120+Math.cos(a)*40,102+Math.sin(a)*35,
        x+Math.sin(a)*bend,y-Math.cos(a)*bend,x,y);
      ctx.strokeStyle=i%3===0?"#7041a5":"#1b233e";ctx.lineWidth=record.group==="shaggoth"?13:7;ctx.lineCap="round";ctx.stroke();
      ctx.strokeStyle=i%2===0?"rgba(172,104,255,.50)":"rgba(76,198,244,.27)";ctx.lineWidth=2;ctx.stroke();
    }
    ctx.shadowBlur=0;
    ctx.fillStyle=gradient(ctx,120,90,62,record.group==="shaggoth"?"#342056":"#225d75","#050915");
    ctx.beginPath();ctx.ellipse(120,94,record.group==="shaggoth"?58:43,record.group==="shaggoth"?52:48,0,0,TAU);ctx.fill();
    ctx.strokeStyle="#8d80bb";ctx.lineWidth=1.5;ctx.stroke();
    const eyes=record.group==="shaggoth"?5:2;
    for(let i=0;i<eyes;i++){
      const a=eyes===5?(i-2)*.38:(i*2-1)*.55;
      const ex=120+Math.sin(a)*40,ey=89+Math.cos(a)*9;
      ctx.shadowColor="#ffad77";ctx.shadowBlur=14;ctx.fillStyle=i%2===0?"#ff9d6c":"#a7f1ff";
      ctx.beginPath();ctx.ellipse(ex,ey,eyes===5?5:9,eyes===5?6:4,0,0,TAU);ctx.fill();
    }ctx.shadowBlur=0;
    if(record.group==="shaggoth"){
      ctx.strokeStyle="rgba(174,108,245,.64)";ctx.lineWidth=2;
      for(let i=0;i<3;i++){ctx.beginPath();ctx.arc(120,100,67+i*12,t*.2+i*.4,Math.PI+t*.2+i*.4);ctx.stroke();}
    }
  }else if(record.group==="uap"||record.group==="records"){
    ctx.shadowColor="#72d2ef";ctx.shadowBlur=20;
    ctx.fillStyle=gradient(ctx,120,94,92,"#d3e3ee","#273a52");
    const typ=record.visual;
    if(typ==="triangle"){
      ctx.beginPath();ctx.moveTo(120,32);ctx.lineTo(201,140);ctx.lineTo(36,140);ctx.closePath();ctx.fill();
      ctx.strokeStyle="#d2edf2";ctx.lineWidth=2;ctx.stroke();
      for(const [x,y] of [[120,51],[57,133],[181,133]]){ctx.beginPath();ctx.arc(x,y,6,0,TAU);ctx.fillStyle="#ffb68c";ctx.fill()}
    }else if(typ==="cigar"||typ==="tic-tac"){
      ctx.save();ctx.translate(120,92);ctx.rotate(-.3);ctx.beginPath();ctx.ellipse(0,0,93,typ==="cigar"?19:26,0,0,TAU);ctx.fill();ctx.strokeStyle="#f1ffff";ctx.lineWidth=2;ctx.stroke();ctx.restore();
    }else if(typ==="cube"){
      ctx.beginPath();ctx.moveTo(77,48);ctx.lineTo(149,37);ctx.lineTo(190,67);ctx.lineTo(180,136);ctx.lineTo(111,157);ctx.lineTo(75,121);ctx.closePath();ctx.fill();line(ctx,[[149,37],[146,113],[111,157]],"#83d8ee",2);line(ctx,[[75,121],[146,113],[190,67]],"#83d8ee",2);
    }else if(typ==="orb"||typ==="light"||typ==="pr017"){
      const g=ctx.createRadialGradient(107,73,3,120,104,70);g.addColorStop(0,"#f7ffff");g.addColorStop(.37,"#95e3f7");g.addColorStop(.72,"#326f94");g.addColorStop(1,"#0b1a31");
      ctx.fillStyle=g;ctx.beginPath();ctx.arc(120,100,57,0,TAU);ctx.fill();
    }else if(typ==="torus"){
      ctx.beginPath();ctx.ellipse(120,100,83,61,.16,0,TAU);ctx.lineWidth=23;ctx.strokeStyle="#8abeda";ctx.stroke();
      ctx.beginPath();ctx.ellipse(120,100,83,61,.16,0,TAU);ctx.lineWidth=4;ctx.strokeStyle="#f5f5ff";ctx.stroke();
    }else if(typ==="transmedium"){
      ctx.beginPath();ctx.ellipse(120,94,93,27,0,0,TAU);ctx.fill();ctx.fillStyle="#0e2936";ctx.fillRect(20,115,195,8);
    }else if(typ==="balloons"){
      for(let i=0;i<5;i++){ctx.beginPath();ctx.ellipse(82+i*17,74+(i%2)*12,20,24,.1,0,TAU);ctx.fillStyle=i%2?"#9fc3d3":"#c2d4e5";ctx.fill();line(ctx,[[82+i*17,99+(i%2)*11],[113,155]],"#4c9db5",1);}
    }else{
      ctx.beginPath();ctx.ellipse(120,110,104,27,0,0,TAU);ctx.fill();ctx.strokeStyle="#e7f2f7";ctx.lineWidth=2;ctx.stroke();
      ctx.fillStyle="#566e83";ctx.beginPath();ctx.ellipse(120,99,52,29,0,Math.PI,0);ctx.fill();
      for(let i=0;i<8;i++){ctx.shadowBlur=12;ctx.fillStyle=i%2?"#53cbed":"#eac89e";ctx.beginPath();ctx.arc(34+i*24,113,3,0,TAU);ctx.fill();}
    }
    ctx.shadowBlur=0;
  }else{
    ctx.fillStyle=gradient(ctx,120,99,92,"#406b79","#091421");ctx.beginPath();ctx.ellipse(120,192,85,53,0,0,TAU);ctx.fill();
    const kind=record.visual;const green=["reptilian","mantis","insectoid","plant"].includes(kind);
    const metal=["synthetic","crystal","shape"].includes(kind);
    const main=metal?"#82b2cd":green?"#568a55":kind==="aquatic"?"#237eaf":kind==="feline"?"#ba955f":kind==="avian"?"#a6afbd":"#98afbd";
    const dark=metal?"#142c4d":green?"#18392f":"#24333d";
    if(["mantis","insectoid","avian","feline","reptilian","plant"].includes(kind)){
      ctx.strokeStyle=main;ctx.lineWidth=11;ctx.lineCap="round";
      for(const dir of [-1,1]){
        ctx.beginPath();ctx.moveTo(120+dir*35,74);
        ctx.quadraticCurveTo(120+dir*75,25,120+dir*62,4);ctx.stroke();
      }
    }
    ctx.shadowColor=main;ctx.shadowBlur=9;ctx.fillStyle=gradient(ctx,120,80,92,main,dark);
    ctx.beginPath();
    ctx.moveTo(120,20);ctx.bezierCurveTo(191,10,196,78,171,117);ctx.quadraticCurveTo(120,178,70,119);ctx.bezierCurveTo(42,73,55,12,120,20);ctx.fill();
    ctx.shadowBlur=0;ctx.lineWidth=1.5;ctx.strokeStyle="#c8e6e570";ctx.stroke();
    for(const dir of [-1,1]){
      ctx.save();ctx.translate(120+dir*30,82);ctx.rotate(dir*.20);
      ctx.fillStyle=kind==="synthetic"?"#5de9ff":kind==="grey"?"#07111f":"#08191e";
      ctx.beginPath();ctx.ellipse(0,0,22,12,dir*.13,0,TAU);ctx.fill();ctx.strokeStyle=green?"#cbeb7d":"#9adced";ctx.lineWidth=1.3;ctx.stroke();
      if(kind!=="grey"){ctx.shadowColor="#a1f5ff";ctx.shadowBlur=10;ctx.fillStyle="#73eefa";ctx.beginPath();ctx.arc(0,0,4,0,TAU);ctx.fill();}ctx.restore();
    }
    line(ctx,[[110,128],[130,128]],"#26303e",2);
    if(kind==="crystal"){
      ctx.strokeStyle="#d4ecff";ctx.lineWidth=2;for(let i=0;i<5;i++){const x=76+i*22;line(ctx,[[x,34],[x+16,88],[120,145]],"rgba(200,236,255,.52)",1)}
    }
    if(kind==="synthetic"){
      ctx.strokeStyle="#6edaf1";ctx.lineWidth=2;ctx.strokeRect(94,101,52,30);
    }
  }
  ctx.restore();ctx.restore();
}
function renderCards(){
  const items=visible();const sets=Object.fromEntries(groups.map(g=>[g,items.filter(r=>r.group===g)]));
  for(const group of groups){
    const grid=$(gridIds[group]);grid.replaceChildren();const data=sets[group];
    $(sectionIds[group]).hidden=data.length===0;$(countIds[group]).textContent=data.length+" / "+state.data.filter(x=>x.group===group).length;
    for(const r of data){
      const btn=document.createElement("button");btn.type="button";btn.className="entity-card"+(group==="records"?" record-card":"");
      btn.dataset.entityId=r.id;btn.setAttribute("aria-pressed",String(r.id===state.selected));btn.setAttribute("aria-label",r.name+", "+evidenceNames[r.evidence]);
      const canvas=document.createElement("canvas");canvas.width=180;canvas.height=148;canvas.setAttribute("aria-hidden","true");
      art(canvas.getContext("2d"),180,148,r,0,0,.60);
      const info=document.createElement("span"),title=document.createElement("strong"),tag=document.createElement("small");
      title.textContent=r.name;tag.textContent=group==="records"?r.evidence.toUpperCase():r.group==="shaggoth"?"CL1 / FICTION":r.evidence.toUpperCase();
      info.append(title,tag);btn.append(canvas,info);
      btn.addEventListener("click",()=>choose(r.id));grid.appendChild(btn);
    }
  }
  $("filteredTotal").textContent=String(items.length);
}
function buildRelations(){
  const edges=[];const byGroup=Object.fromEntries(groups.map(g=>[g,state.data.filter(r=>r.group===g)]));
  for(const group of groups){
    const records=byGroup[group];
    records.forEach((r,i)=>{if(i>0)edges.push({source:records[i-1].id,target:r.id,relation:"shares fictional taxonomy / visualization group"});});
  }
  const pairs=[["s-shaggoth-prime","s-void-shaggoth"],["a-cephalopod-archetype","s-shaggoth-prime"],["u-disc-saucer","r-gofast-official-footage"],["u-orb-sphere","r-pr-017-europe-2024"],["u-unidentified-light","r-al-taqaddum-resolved"],["a-luminous-being","s-stellar-shaggoth"],["a-synthetic-intelligence","u-cube"],["s-planetary-shaggoth","u-mothership"]];
  for(const [a,b] of pairs)if(state.byId.has(a)&&state.byId.has(b))edges.push({source:a,target:b,relation:"visual theme cross-reference only / not evidence of causal link"});
  return edges;
}
function neighbors(id){return rootEdges.filter(e=>e.source===id||e.target===id).map(e=>({record:state.byId.get(e.source===id?e.target:e.source),relation:e.relation})).filter(x=>x.record)}
function choose(id){if(!state.byId.has(id))return;state.selected=id;updateInspector();renderCards();$("creatureCanvas").dataset.entityId=id;state.quiet=false;}
function safeOfficial(url){try{const u=new URL(url);return u.protocol==="https:"&&["science.nasa.gov","www.aaro.mil"].includes(u.hostname)}catch(_){return false}}
function updateInspector(){
  const r=selected();if(!r)return;
  $("selectedName").textContent=r.name;$("selectedDescription").textContent=r.description;
  $("selectedGroup").textContent=groupNames[r.group];$("selectedEvidence").textContent=evidenceNames[r.evidence];
  $("selectedDomain").textContent=r.domain;$("selectedOrigin").textContent=r.origin;
  const link=$("sourceLink");if(r.source_url&&safeOfficial(r.source_url)){link.href=r.source_url;link.textContent="VIEW "+r.source_label.toUpperCase()+" ↗";link.hidden=false}else{link.removeAttribute("href");link.hidden=true}
  const box=$("tabBody");box.replaceChildren();
  const para=(t)=>{const p=document.createElement("p");p.textContent=t;box.appendChild(p)};
  if(state.tab==="overview"){para("Classification is explicit: "+groupNames[r.group]+".");
    para(r.group==="records"?"Official publication is not proof of an extraterrestrial origin. Open the linked report for current assessment.":"This is a visual concept, not a biologically verified alien or documented extraterrestrial craft.");
  }else if(state.tab==="data"){
    para("ID: "+r.id);para("Evidence status: "+evidenceNames[r.evidence]);
    para("Context: "+r.domain);para("Provenance: "+(r.source_label||"Original concept"));
  }else if(state.tab==="relations"){
    const links=neighbors(r.id);
    if(!links.length)para("No conceptual links recorded for this entry.");
    for(const item of links.slice(0,12)){const b=document.createElement("button");b.type="button";b.textContent=item.record.name+" ↗";b.title=item.relation;b.addEventListener("click",()=>choose(item.record.id));box.appendChild(b);}
    para("All edges are editorial design cross-references, never alleged extraterrestrial contact.");
  }else{
    para("Visual simulation only: rotate, zoom, change intensity or pause. No RF emission, equipment actuation, sensors, biological inference or physical telemetry.");
    const b=document.createElement("button");b.type="button";b.textContent=state.paused?"RESUME LOCAL VISUAL":"PAUSE LOCAL VISUAL";b.addEventListener("click",()=>togglePause());box.appendChild(b);
  }
}
function updateTabs(){document.querySelectorAll("[data-tab]").forEach(b=>b.setAttribute("aria-selected",String(b.dataset.tab===state.tab)));updateInspector()}
function updateStats(){
  const counts=Object.fromEntries(groups.map(g=>[g,state.data.filter(r=>r.group===g).length]));
  for(const g of groups){document.querySelectorAll('[data-count="'+g+'"]').forEach(el=>el.textContent=String(counts[g]));}
  for(const [k,id] of [["aliens","statAliens"],["uap","statUap"],["records","statReports"],["shaggoth","statShaggoth"]])$(id).textContent=String(counts[k]);
  $("statTotal").textContent=String(state.data.length);$("recordTotal").textContent=String(state.data.length);$("statEdges").textContent=String(rootEdges.length);
}
function setFilter(){
  state.query=$("query").value.trim().toLowerCase();
  state.groups=new Set(Array.from(document.querySelectorAll('#groupFilters input:checked')).map(x=>x.value));
  state.evidence=new Set(Array.from(document.querySelectorAll('#evidenceFilters input:checked')).map(x=>x.value));
  if(!visible().some(r=>r.id===state.selected)&&visible().length){state.selected=visible()[0].id;updateInspector();}
  renderCards();
}
function resetFilters(){document.querySelectorAll("#groupFilters input,#evidenceFilters input").forEach(x=>x.checked=true);$("query").value="";setFilter();notify("FILTERS RESET / full curated catalog");}
function togglePause(set){
  state.paused=typeof set==="boolean"?set:!state.paused;
  $("pauseScene").textContent=state.paused?"RESUME SCENE":"PAUSE SCENE";
  $("pauseScene").setAttribute("aria-pressed",String(state.paused));updateInspector();
}
const viewer=$("creatureCanvas"),vctx=viewer.getContext("2d"),graph=$("graphCanvas"),gctx=graph.getContext("2d");
function drawViewer(time){
  const r=selected();if(!r||!vctx)return;
  const [w,h]=scaleCanvas(viewer,vctx),t=state.motionTime;
  vctx.save();vctx.translate(w/2,h/2);vctx.scale(state.zoom,state.zoom);vctx.translate(-w/2,-h/2);
  art(vctx,w,h,r,t,state.angle,state.intensity/100);vctx.restore();
  viewer.dataset.entityId=r.id;viewer.dataset.rendered="true";viewer.dataset.frame=String(state.frame);
}
function layoutGraph(w,h){
  const items=visible(),arr=[];
  if(state.mode==="graph"){
    const centers={aliens:[w*.22,h*.46],uap:[w*.55,h*.30],records:[w*.80,h*.36],shaggoth:[w*.58,h*.75]};
    for(const g of groups){
      const inGroup=items.filter(r=>r.group===g),[cx,cy]=centers[g];
      inGroup.forEach((r,i)=>{const a=i*2.39996+hash(r.id)%12*.03,rad=Math.sqrt(i+1)*Math.min(w,h)*.043;
        arr.push({id:r.id,x:cx+Math.cos(a)*rad,y:cy+Math.sin(a)*rad})});
    }
  }else{
    items.forEach((r,i)=>{const a=i*2.39996,rad=13+Math.sqrt(i+1)*Math.min(w,h)*.055;
      arr.push({id:r.id,x:w/2+Math.cos(a)*rad*1.65,y:h/2+Math.sin(a)*rad*.83})});
  }
  return arr;
}
function drawGraph(time){
  if(!gctx)return;const [w,h]=scaleCanvas(graph,gctx),ctx=gctx;
  ctx.clearRect(0,0,w,h);
  const grad=ctx.createRadialGradient(w/2,h/2,4,w/2,h/2,Math.max(w,h)*.7);grad.addColorStop(0,"#26305b");grad.addColorStop(.4,"#141d3e");grad.addColorStop(1,"#040b16");ctx.fillStyle=grad;ctx.fillRect(0,0,w,h);
  for(let i=0;i<100;i++){const x=((i*1733+139)%991)/991*w,y=((i*731+77)%997)/997*h;ctx.fillStyle="rgba(195,191,255,"+(.13+(i%4)*.08)+")";ctx.fillRect(x,y,1.4,1.4)}
  state.points=layoutGraph(w,h);const lookup=new Map(state.points.map(p=>[p.id,p]));
  if(state.mode==="field"){
    ctx.strokeStyle="rgba(138,92,248,.21)";for(let i=1;i<6;i++){ctx.beginPath();ctx.ellipse(w/2,h/2,i*w*.085,i*h*.075,-.2,0,TAU);ctx.stroke();}
  }
  if(state.links)for(const e of rootEdges){const a=lookup.get(e.source),b=lookup.get(e.target);if(!a||!b)continue;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.strokeStyle="rgba(126,146,250,.29)";ctx.lineWidth=.7;ctx.stroke();}
  for(const p of state.points){
    const r=state.byId.get(p.id),chosen=r.id===state.selected;
    ctx.shadowColor=groupColor[r.group];ctx.shadowBlur=chosen?19:8;ctx.fillStyle=groupColor[r.group];ctx.beginPath();ctx.arc(p.x,p.y,chosen?5.7:3.1,0,TAU);ctx.fill();ctx.shadowBlur=0;
    if(chosen||r.visual==="prime"){ctx.fillStyle="#eafaff";ctx.font=chosen?"bold 11px Menlo,monospace":"9px Menlo,monospace";ctx.fillText(r.name,p.x+9,p.y-9);}
  }
  graph.dataset.renderedNodes=String(state.points.length);graph.dataset.renderedEdges=String(rootEdges.filter(e=>lookup.has(e.source)&&lookup.has(e.target)).length);
  graph.dataset.mapMode=state.mode;
}
function updateMapMode(mode){
  if(!["graph","field"].includes(mode))return;
  state.mode=mode;$("graphMode").setAttribute("aria-pressed",String(mode==="graph"));$("fieldMode").setAttribute("aria-pressed",String(mode==="field"));drawGraph(0);
}
function exportData(){
  const data={schema:"xunia.cl1.xenology-export.v1",export_scope:"filtered-curated-only",generated_at:new Date().toISOString(),disclaimer:"Creative archetypes and illustrative UAP forms are not verified alien evidence.",records:visible(),relations:rootEdges.filter(e=>visible().some(r=>r.id===e.source)&&visible().some(r=>r.id===e.target))};
  const blob=new Blob([JSON.stringify(data,null,2)+"\n"],{type:"application/json"});
  const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="cl1-xenology-curated.json";document.body.appendChild(a);a.click();a.remove();window.setTimeout(()=>URL.revokeObjectURL(url),1500);
  notify("EXPORTED "+data.records.length+" CURATED ENTRIES / YOUR BROWSER ONLY");
}
function randomPick(){const items=visible();if(!items.length){notify("NO RESULTS / RESET FILTERS");return;}choose(items[Math.floor(Math.random()*items.length)].id);notify("SELECTED / "+selected().name)}
function command(raw){
  const line=String(raw||"").trim().replace(/^\//,"");const match=line.match(/^(\S+)(?:\s+(.*))?$/);
  if(!match){notify("EMPTY COMMAND / TRY /help");return;}
  const op=match[1].toLowerCase(),arg=(match[2]||"").trim();
  if(op==="help"){notify("/find NAME · /select NAME · /group aliens|uap|records|shaggoth|all · /tab overview|data|relations|simulation · /mode graph|field · /intensity 0-100 · /zoom 0.6-2.5 · /pause · /play · /random · /export · /reset");return;}
  if(op==="find"){$("query").value=arg;setFilter();notify("FILTERED TO / "+visible().length+" RECORDS");return;}
  if(op==="select"){const q=arg.toLowerCase();const hit=state.data.find(r=>r.id===q||r.name.toLowerCase()===q)||state.data.find(r=>r.name.toLowerCase().includes(q)&&q);
    if(hit){if(!state.groups.has(hit.group)||!state.evidence.has(hit.evidence)||state.query){resetFilters();}choose(hit.id);notify("INSPECTING / "+hit.name);}else notify("NOT FOUND / SEARCH CURATED NAMES");return;}
  if(op==="group"){if(arg==="all"){resetFilters();return;}if(!groups.includes(arg)){notify("UNKNOWN GROUP / ALIENS UAP RECORDS SHAGGOTH ALL");return;}document.querySelectorAll("#groupFilters input").forEach(x=>x.checked=x.value===arg);setFilter();notify("GROUP / "+arg.toUpperCase());return;}
  if(op==="tab"){if(!["overview","data","relations","simulation"].includes(arg)){notify("UNKNOWN TAB");return;}state.tab=arg;updateTabs();notify("INSPECTOR / "+arg.toUpperCase());return;}
  if(op==="mode"){if(!["graph","field"].includes(arg)){notify("MODE GRAPH OR FIELD");return;}updateMapMode(arg);notify("KNOWLEDGE VIEW / "+arg.toUpperCase());return;}
  if(op==="intensity"){const n=Number(arg);if(!arg||!Number.isFinite(n)||n<0||n>100){notify("INTENSITY RANGE 0–100");return;}state.intensity=n;$("intensity").value=n;$("intensityValue").textContent=n+"%";notify("VIRTUAL SIMULATION INTENSITY / "+n+"%");return;}
  if(op==="zoom"){const n=Number(arg);if(!arg||!Number.isFinite(n)||n<.6||n>2.5){notify("ZOOM RANGE 0.6–2.5");return;}state.zoom=n;notify("SIMULATED CAMERA ZOOM / "+n.toFixed(2));return;}
  if(op==="pause"){togglePause(true);notify("SCENE PAUSED");return;}
  if(op==="play"){togglePause(false);notify("SCENE PLAYING / LOCAL ONLY");return;}
  if(op==="random"){randomPick();return;}
  if(op==="export"){exportData();return;}
  if(op==="reset"){state.angle=0;state.zoom=1;state.intensity=60;$("intensity").value=60;$("intensityValue").textContent="60%";state.tab="overview";updateTabs();resetFilters();notify("CL1 VIEW RESET");return;}
  notify("UNKNOWN COMMAND / TRY /help");
}
function wire(){
  $("query").addEventListener("input",setFilter);
  document.querySelectorAll("#groupFilters input,#evidenceFilters input").forEach(x=>x.addEventListener("change",setFilter));
  $("resetFilters").addEventListener("click",resetFilters);
  $("motion").checked=!motionReduced;
  state.animate=!motionReduced;$("motion").addEventListener("change",e=>state.animate=e.target.checked);
  $("linksToggle").addEventListener("change",e=>{state.links=e.target.checked;drawGraph(0)});
  document.querySelectorAll("[data-tab]").forEach(b=>b.addEventListener("click",()=>{state.tab=b.dataset.tab;updateTabs()}));
  $("sceneLeft").addEventListener("click",()=>state.angle-=.32);
  $("sceneRight").addEventListener("click",()=>state.angle+=.32);
  $("sceneZoomIn").addEventListener("click",()=>state.zoom=Math.min(2.5,state.zoom*1.15));
  $("sceneZoomOut").addEventListener("click",()=>state.zoom=Math.max(.6,state.zoom/1.15));
  $("sceneReset").addEventListener("click",()=>{state.angle=0;state.zoom=1});
  $("intensity").addEventListener("input",e=>{state.intensity=Number(e.target.value);$("intensityValue").textContent=state.intensity+"%"});
  $("pauseScene").addEventListener("click",()=>togglePause());
  $("graphMode").addEventListener("click",()=>updateMapMode("graph"));
  $("fieldMode").addEventListener("click",()=>updateMapMode("field"));
  $("exploreSelected").addEventListener("click",()=>{state.zoom=1.35;state.angle=0;viewer.focus();notify("FOCUSED / "+selected().name)});
  $("randomEntity").addEventListener("click",randomPick);
  $("exportData").addEventListener("click",exportData);
  $("runSimulation").addEventListener("click",()=>{togglePause(false);state.angle+=.25;state.tab="simulation";updateTabs();notify("SIMULATION ACTIVE / VISUAL ONLY")});
  $("openConsole").addEventListener("click",()=>{$("consoleInput").focus();notify("CL1 CONSOLE ACTIVE / /help")});
  $("consoleForm").addEventListener("submit",e=>{e.preventDefault();command($("consoleInput").value);$("consoleInput").value=""});
  document.addEventListener("keydown",e=>{
    const tag=document.activeElement?.tagName,editing=["INPUT","TEXTAREA","SELECT"].includes(tag);
    if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();$("consoleInput").focus();}
    else if(e.key==="Escape"&&document.activeElement===$("consoleInput")){e.preventDefault();viewer.focus();}
    else if(!editing&&e.key.toLowerCase()==="r"){randomPick();}
  });
  viewer.addEventListener("pointerdown",e=>{if(e.button!==0)return;state.drag={x:e.clientX,y:e.clientY};viewer.setPointerCapture(e.pointerId);viewer.focus()});
  viewer.addEventListener("pointermove",e=>{if(!state.drag)return;state.angle+=(e.clientX-state.drag.x)*.019;state.drag.x=e.clientX;state.drag.y=e.clientY;});
  for(const event of ["pointerup","pointercancel","lostpointercapture"])viewer.addEventListener(event,()=>state.drag=null);
  viewer.addEventListener("wheel",e=>{e.preventDefault();state.zoom=Math.min(2.5,Math.max(.6,state.zoom*(e.deltaY<0?1.1:.91)))},{passive:false});
  viewer.addEventListener("keydown",e=>{if(e.key==="ArrowLeft")state.angle-=.15;else if(e.key==="ArrowRight")state.angle+=.15;else if(e.key==="+")state.zoom=Math.min(2.5,state.zoom*1.1);else if(e.key==="-")state.zoom=Math.max(.6,state.zoom/1.1);else return;e.preventDefault()});
  graph.addEventListener("click",e=>{const rect=graph.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top;let best=null,dist=17;for(const p of state.points){const d=Math.hypot(p.x-x,p.y-y);if(d<dist){dist=d;best=p}}if(best)choose(best.id)});
  graph.addEventListener("keydown",e=>{if(!["ArrowRight","ArrowLeft"].includes(e.key))return;e.preventDefault();const items=visible();let i=items.findIndex(x=>x.id===state.selected);if(items.length)choose(items[(i+(e.key==="ArrowRight"?1:items.length-1))%items.length].id)});
  window.addEventListener("resize",()=>drawGraph(0));
}
function loop(time){
  if(!state.ready)return;
  if(time-state.lastDraw>45){
    if(!state.paused&&state.animate&&!motionReduced){state.angle+=.001;state.motionTime+=.021;}
    state.frame++;drawViewer(time);
    if(state.frame%3===0||state.frame===1)drawGraph(time);
    state.lastDraw=time;
  }
  window.requestAnimationFrame(loop);
}
async function boot(){
  wire();if(!vctx||!gctx){notify("CANVAS UNSUPPORTED / BROWSER REQUIREMENTS");return;}
  try{
    const response=await fetch("./catalog.json",{credentials:"omit",cache:"no-store"});if(!response.ok)throw Error("CATALOG MISSING");
    const catalog=await response.json();
    if(catalog.schema!=="xunia.cl1.xenology-archive.v1"||!Array.isArray(catalog.records)||catalog.records.length<20)throw Error("BAD SCHEMA");
    const ids=new Set();
    for(const r of catalog.records){
      if(!r||typeof r.id!=="string"||ids.has(r.id)||!groups.includes(r.group)||!(r.evidence in evidenceNames)||typeof r.name!=="string"||r.name.length>100){throw Error("INVALID ENTITY");}
      if(r.source_url&&!safeOfficial(r.source_url))throw Error("UNTRUSTED SOURCE URL");
      ids.add(r.id);state.byId.set(r.id,r);
    }
    state.data=catalog.records;rootEdges=buildRelations();
    if(!state.byId.has(state.selected))state.selected=state.data[0].id;
    updateStats();renderCards();updateInspector();state.ready=true;
    notify("READY / "+state.data.length+" CURATED ENTRIES · "+rootEdges.length+" EDITORIAL RELATIONSHIPS · NO EXTRATERRESTRIAL CLAIMS");
    window.requestAnimationFrame(loop);
  }catch(error){notify("CL1 ARCHIVE ERROR / "+String(error.message).slice(0,110));$("selectedName").textContent="Catalog unavailable";}
}
boot();
})();
