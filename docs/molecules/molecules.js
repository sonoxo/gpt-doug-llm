/* CL1 Molecular Observatory. Original static browser visualization.
 * Molecules are illustrative atom-bond graphs, NOT measured conformers or spectra.
 * Astronomy-linked catalog references are NOT case-level detection evidence.
 */
(()=>{"use strict";
const $=id=>document.getElementById(id),TAU=Math.PI*2;
const colors={H:"#e7f7fa",C:"#9fc7d2",N:"#649bff",O:"#f18082",S:"#f5d56d",P:"#f7b47a",Cl:"#79dd99",F:"#72ddc0"};
const atomic=Object.fromEntries("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split(" ").map((symbol,index)=>[symbol,index+1]));
const weight={H:1.008,C:12.011,N:14.007,O:15.999,S:32.06,P:30.974,Cl:35.45,F:18.998};
const domains=["fundamental","astro","hydrocarbon","alcohol","organic","biochemical","imported"];
const statuses=["astronomical-reference","chemistry-reference"];
const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));
const modes=["ball","space","wire"];
const state={data:[],byId:new Map(),selected:null,atom:null,query:"",domain:"all",allowed:new Set(statuses),mode:"ball",
   yaw:.45,pitch:.36,zoom:1,phase:0,speed:28,paused:false,reduced:!!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches,
   hit:[],graphHit:[],last:0,lastDraw:0,ready:false,drag:null,frame:0};
if(state.reduced)state.paused=true;
const canvas=$("moleculeCanvas"),ctx=canvas.getContext("2d"),graph=$("bondGraph"),gctx=graph.getContext("2d");
const m=()=>state.byId.get(state.selected);
function message(t){$("actionStatus").textContent=String(t);}
function status(t){$("consoleStatus").textContent=String(t);}
function finite(n){return typeof n==="number"&&Number.isFinite(n);}
function validSource(url){try{const u=new URL(url);return u.protocol==="https:"&&["pubchem.ncbi.nlm.nih.gov","cdms.astro.uni-koeln.de"].includes(u.hostname);}catch(_){return false;}}
function validate(rec){
 if(!rec||typeof rec.id!=="string"||!/^[a-z0-9-]{1,100}$/.test(rec.id)||
    typeof rec.name!=="string"||rec.name.length>150||!rec.name||
    typeof rec.formula!=="string"||!rec.formula||rec.formula.length>80||
    !statuses.includes(rec.status)||!domains.includes(rec.domain)||
    !finite(rec.molar_mass_gmol)||rec.molar_mass_gmol<=0||
    !Array.isArray(rec.atoms)||!rec.atoms.length||rec.atoms.length>350||
    !Array.isArray(rec.bonds)||rec.bonds.length>600||
    !validSource(rec.source_url)||typeof rec.description!=="string")throw Error("MOLECULE SCHEMA INVALID");
 const ids=new Set();
 for(const a of rec.atoms){
   if(!Number.isInteger(a.id)||ids.has(a.id)||!atomic[a.element]||
      ![a.x,a.y,a.z].every(finite)||[a.x,a.y,a.z].some(v=>Math.abs(v)>200))throw Error("ATOM SCHEMA INVALID");
   ids.add(a.id);
 }
 for(const b of rec.bonds){
   if(!ids.has(b.a)||!ids.has(b.b)||b.a===b.b||![1,2,3].includes(b.order))throw Error("BOND SCHEMA INVALID");
 }
 return true;
}
function visible(){return state.data.filter(r=>state.allowed.has(r.status)&&(state.domain==="all"||r.domain===state.domain)&&
  (!state.query||(r.name+" "+r.formula+" "+r.domain+" "+r.id+" "+r.atoms.map(a=>a.element).join(" ")).toLowerCase().includes(state.query)));}
function counts(rec){const c={};for(const a of rec.atoms)c[a.element]=(c[a.element]||0)+1;return c;}
function renderList(){
 const entries=visible(),list=$("moleculeList");list.replaceChildren();
 $("resultCount").textContent=entries.length+" / "+state.data.length;
 for(const r of entries){
  const btn=document.createElement("button");btn.type="button";btn.className="molecule-item";
  btn.setAttribute("aria-pressed",String(r.id===state.selected));btn.dataset.id=r.id;
  const icon=document.createElement("span");icon.className="mini-icon";icon.textContent=r.atoms[0]?.element||"?";
  const label=document.createElement("span"),title=document.createElement("strong"),caption=document.createElement("small"),formula=document.createElement("span");
  title.textContent=r.name;caption.textContent=r.status==="astronomical-reference"?"ASTRONOMY-LINKED":"CHEMISTRY REFERENCE";
  formula.className="chip";formula.textContent=r.formula;
  label.append(title,caption);btn.append(icon,label,formula);
  btn.addEventListener("click",()=>select(r.id));list.appendChild(btn);
 }
 if(!entries.length){const label=document.createElement("p");label.className="empty";label.textContent="No matches. Reset the filters or search another formula.";list.appendChild(label);}
}
function updateAtom(){
 const rec=m(),a=rec?.atoms.find(x=>x.id===state.atom);
 $("selectedAtomTag").textContent=a?a.element+" #"+a.id:"NO SELECTION";
 const box=$("atomDetails");box.replaceChildren();
 if(!a){box.textContent="Click a sphere in the molecule or a node in the bond graph to inspect the atom.";return;}
 const near=rec.bonds.filter(b=>b.a===a.id||b.b===a.id).map(b=>{
  const v=rec.atoms.find(x=>x.id===(b.a===a.id?b.b:b.a));
  return v.element+"#"+v.id+" ("+["","single","double","triple"][b.order]+")";
 });
 const rows=["Element: "+a.element+" (atomic number "+atomic[a.element]+")",
   "Approx. atomic mass: "+(weight[a.element]===undefined?"not bundled":weight[a.element]+" u"),"Neighbors: "+(near.join(", ")||"none")];
 rows.forEach(t=>{const p=document.createElement("div");p.textContent=t;box.appendChild(p);});
}
function inspect(){
 const rec=m();if(!rec)return;
 $("moleculeName").textContent=rec.name;$("moleculeFormula").textContent=rec.formula;
 $("moleculeClass").textContent=rec.domain.toUpperCase()+" / "+(rec.source==="pubchem"?"IMPORTED PUBCHEM":"CURATED EXAMPLE");
 $("description").textContent=rec.description;
 $("mass").textContent=rec.molar_mass_gmol.toLocaleString("en-US",{maximumFractionDigits:3})+" g/mol";
 $("atomCount").textContent=String(rec.atoms.length);$("bondCount").textContent=String(rec.bonds.length);
 $("sourceType").textContent=rec.source==="pubchem"?"PUBCHEM":"CURATED";
 $("referenceTag").textContent=rec.status==="astronomical-reference"?"ASTRO / REFERENCE":"CHEM / REFERENCE";
 $("astronomyNote").textContent=(rec.astro_claim||"No individual astronomical detection claim.")+
   " Illustrated coordinates do not represent experimental geometry.";
 const source=$("sourceLink");source.href=rec.source_url;source.textContent="OPEN "+(rec.source_label||"SOURCE DATABASE").toUpperCase()+" ↗";
 const chips=$("composition");chips.replaceChildren();
 for(const [el,n] of Object.entries(counts(rec)).sort((a,b)=>atomic[a[0]]-atomic[b[0]])){
  const span=document.createElement("span");span.className="element-chip";
  const bold=document.createElement("b");bold.textContent=el;span.append(bold,document.createTextNode("× "+n));chips.appendChild(span);
 }
 updateAtom();
}
function select(id){
 if(!state.byId.has(id))return false;
 const rec=state.byId.get(id);
 if(!visible().some(v=>v.id===id)){
   state.domain="all";state.allowed=new Set(statuses);state.query="";$("query").value="";$("domain").value="all";
   document.querySelectorAll("[data-source]").forEach(c=>c.checked=true);
 }
 state.selected=id;state.atom=null;state.yaw=.45;state.pitch=.36;state.zoom=1;
 inspect();renderList();draw();return true;
}
function chooseAdjacent(delta){
 const list=visible();if(!list.length)return;
 const idx=list.findIndex(x=>x.id===state.selected);
 select(list[(idx+delta+list.length)%list.length].id);
}
function filter(){
 state.query=$("query").value.trim().toLowerCase();
 state.domain=$("domain").value;
 state.allowed=new Set(Array.from(document.querySelectorAll("[data-source]:checked")).map(x=>x.dataset.source));
 const entries=visible();
 if(entries.length&&!entries.some(x=>x.id===state.selected)){
  state.selected=entries[0].id;state.atom=null;inspect();
 }
 renderList();draw();
}
function resize(c,context){
 const r=c.getBoundingClientRect(),w=Math.max(160,Math.round(r.width||700)),h=Math.max(120,Math.round(r.height||400)),dpi=Math.min(window.devicePixelRatio||1,2);
 if(c.width!==Math.round(w*dpi)||c.height!==Math.round(h*dpi)){c.width=Math.round(w*dpi);c.height=Math.round(h*dpi);}
 context.setTransform(dpi,0,0,dpi,0,0);return [w,h];
}
function mapAtoms(rec,w,h){
 const atoms=rec.atoms,centroid=atoms.reduce((s,a)=>[s[0]+a.x,s[1]+a.y,s[2]+a.z],[0,0,0]).map(x=>x/atoms.length);
 const coords=atoms.map(a=>({a,x:a.x-centroid[0],y:a.y-centroid[1],z:a.z-centroid[2]}));
 const rad=Math.max(1,...coords.map(p=>Math.hypot(p.x,p.y,p.z)));
 const fit=Math.min(w,h)*.32/rad*state.zoom;
 const yaw=state.yaw,pitch=state.pitch,cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
 return coords.map(p=>{
  const xr=p.x*cy+p.z*sy,zr=-p.x*sy+p.z*cy;
  const yr=p.y*cp-zr*sp,zz=p.y*sp+zr*cp;
  const perspective=4.8/(4.8-zz/rad);
  return {id:p.a.id,element:p.a.element,x:w/2+xr*fit*perspective,y:h/2-yr*fit*perspective,z:zz,r:(state.mode==="space"?20:state.mode==="wire"?5:p.a.element==="H"?10:15)*clamp(fit/85,.55,1.5)*perspective};
 });
}
function background(context,w,h){
 const grad=context.createRadialGradient(w*.52,h*.47,2,w*.52,h*.47,Math.max(w,h)*.7);
 grad.addColorStop(0,"#193a52");grad.addColorStop(.6,"#0a1b2b");grad.addColorStop(1,"#030911");
 context.fillStyle=grad;context.fillRect(0,0,w,h);
 context.strokeStyle="#a0e8ef0b";context.lineWidth=.7;
 for(let x=0;x<w;x+=36){context.beginPath();context.moveTo(x,0);context.lineTo(x,h);context.stroke();}
 for(let y=0;y<h;y+=36){context.beginPath();context.moveTo(0,y);context.lineTo(w,y);context.stroke();}
 for(let i=0;i<70;i++){const x=((i*1327+19)%991)/991*w,y=((i*1973+87)%997)/997*h;context.fillStyle="rgba(200,244,249,"+(.09+(i%4)*.07)+")";context.fillRect(x,y,i%9?1:2,1);}
}
function drawBonds(rec,map,context,mode){
 const dict=new Map(map.map(x=>[x.id,x]));
 for(const b of rec.bonds){
  const a=dict.get(b.a),z=dict.get(b.b);if(!a||!z)continue;
  const dx=z.x-a.x,dy=z.y-a.y,dist=Math.hypot(dx,dy)||1,nx=-dy/dist,ny=dx/dist;
  const thick=mode==="wire"?1.2:mode==="space"?5:4;
  for(let i=0;i<b.order;i++){
   const offset=(i-(b.order-1)/2)*(mode==="wire"?4:5.5);
   context.beginPath();context.moveTo(a.x+nx*offset,a.y+ny*offset);
   context.lineTo(z.x+nx*offset,z.y+ny*offset);
   context.lineWidth=thick;context.strokeStyle=mode==="wire"?"#b8dbe0":"#6e9daf";context.stroke();
   if(mode==="ball"){
    context.beginPath();context.moveTo(a.x+nx*offset-1,a.y+ny*offset-1);
    context.lineTo(z.x+nx*offset-1,z.y+ny*offset-1);
    context.lineWidth=1.3;context.strokeStyle="#e6faf890";context.stroke();
   }
  }
 }
}
function draw(){
 if(!state.ready||!ctx)return;
 const rec=m(),[w,h]=resize(canvas,ctx);ctx.clearRect(0,0,w,h);background(ctx,w,h);
 if(!rec)return;
 const points=mapAtoms(rec,w,h);state.hit=points;
 drawBonds(rec,points,ctx,state.mode);
 const ordered=[...points].sort((a,b)=>a.z-b.z);
 for(const p of ordered){
  const radius=p.r*(state.mode==="space"?1.18:1),selected=p.id===state.atom;
  if(state.mode==="wire"){
   ctx.beginPath();ctx.arc(p.x,p.y,Math.max(3,radius),0,TAU);ctx.fillStyle=colors[p.element]||"#aaa";ctx.fill();
  }else{
   const g=ctx.createRadialGradient(p.x-radius*.37,p.y-radius*.45,1,p.x,p.y,radius);
   g.addColorStop(0,"#f9ffff");g.addColorStop(.3,colors[p.element]||"#9ec5d3");g.addColorStop(1,"#152635");
   ctx.shadowBlur=selected?23:11;ctx.shadowColor=colors[p.element]||"#9eddec";
   ctx.fillStyle=g;ctx.beginPath();ctx.arc(p.x,p.y,radius,0,TAU);ctx.fill();ctx.shadowBlur=0;
   ctx.strokeStyle=selected?"#ffffee":"#c5f7fa90";ctx.lineWidth=selected?2.2:.8;ctx.stroke();
  }
  if(state.mode!=="space"||selected){
   ctx.font="bold "+Math.max(9,Math.round(radius*.75))+"px ui-monospace,Menlo,monospace";
   ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillStyle=p.element==="C"||p.element==="H"?"#0b1c2a":"#f7ffff";
   ctx.fillText(p.element,p.x,p.y);
  }
 }
 canvas.dataset.molecule=rec.id;canvas.dataset.renderedAtoms=String(points.length);
 canvas.dataset.renderedBonds=String(rec.bonds.length);canvas.dataset.mode=state.mode;
 canvas.dataset.frames=String(++state.frame);
 $("renderState").textContent=rec.atoms.length+" ATOMS / "+rec.bonds.length+" BONDS / "+state.mode.toUpperCase();
 drawBondGraph();state.lastDraw=performance.now();
}
function drawBondGraph(){
 if(!state.ready||!gctx)return;
 const rec=m(),[w,h]=resize(graph,gctx);gctx.clearRect(0,0,w,h);background(gctx,w,h);
 if(!rec)return;
 const atoms=rec.atoms,xs=atoms.map(a=>a.x),ys=atoms.map(a=>a.y),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
 const scale=Math.min(w*.78/Math.max(2,maxX-minX),h*.72/Math.max(2,maxY-minY),60);
 const pts=atoms.map(a=>({id:a.id,element:a.element,x:w/2+(a.x-(minX+maxX)/2)*scale,y:h/2-(a.y-(minY+maxY)/2)*scale}));
 state.graphHit=pts;
 drawBonds(rec,pts,gctx,"wire");
 for(const p of pts){
  gctx.beginPath();gctx.arc(p.x,p.y,p.id===state.atom?10:7,0,TAU);
  gctx.fillStyle=colors[p.element]||"#eaf4f6";gctx.fill();gctx.strokeStyle="#fff8";gctx.stroke();
  gctx.fillStyle="#04121e";gctx.textAlign="center";gctx.textBaseline="middle";
  gctx.font="bold 8px ui-monospace,Menlo,monospace";gctx.fillText(p.element,p.x,p.y);
 }
 graph.dataset.atoms=String(pts.length);graph.dataset.bonds=String(rec.bonds.length);
}
function savePng(){
 draw();try{
  const url=canvas.toDataURL("image/png");if(!url.startsWith("data:image/png;base64,"))throw Error("UNSUPPORTED");
  const a=document.createElement("a");a.href=url;a.download="cl1-molecule-"+m().id+".png";document.body.appendChild(a);a.click();a.remove();
  message("MOL IMAGE EXPORTED / SCHEMATIC MODEL");}
 catch(_){message("PNG UNAVAILABLE / CHECK BROWSER");}
}
function exportJson(){
 const rec=m();if(!rec)return;
 const data={schema:"xunia.cl1.molecule-export.v1",status:rec.status,geometry_disclaimer:"Illustrative structure, not experimental 3D conformer",record:rec};
 const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+"\n"],{type:"application/json"}));
 const a=document.createElement("a");a.href=url;a.download="cl1-molecule-"+rec.id+".json";document.body.appendChild(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1400);message("MOLECULE JSON EXPORTED / LOCAL BROWSER");
}
function selfTest(){
 const seen=new Set(),valid=state.ready&&state.data.length>=30&&state.data.every(rec=>{
  if(seen.has(rec.id))return false;seen.add(rec.id);try{return validate(rec)}catch(_){return false}
 })&&state.byId.has(state.selected)&&canvas.dataset.renderedAtoms===String(m().atoms.length)&&
  graph.dataset.atoms===String(m().atoms.length)&&ctx&&gctx;
 const result=valid?"CL1 SELF-TEST PASS / "+state.data.length+" RECORDS / ATOMS + BONDS RENDERED":
 "CL1 SELF-TEST FAILED / SOURCE OR RENDER ERROR";
 message(result);status(result);return !!valid;
}
function command(value){
 const line=String(value||"").trim().replace(/^\//,""),space=line.indexOf(" "),op=(space<0?line:line.slice(0,space)).toLowerCase(),arg=space<0?"":line.slice(space+1).trim();
 if(op==="help"){status("/find TEXT · /select NAME · /mode ball|space|wire · /speed 0-100 · /next · /previous · /pause · /play · /export · /capture · /health · /reset");return;}
 if(op==="find"){$("query").value=arg;filter();status("FILTERED / "+visible().length+" MOLECULES");return;}
 if(op==="select"){
  const wanted=arg.toLowerCase();const found=state.data.find(r=>r.name.toLowerCase()===wanted||r.id===wanted);
  status(found&&select(found.id)?"MOLECULE / "+found.name:"NOT FOUND / SEARCH CATALOG");return;
 }
 if(op==="mode"){if(!modes.includes(arg)){status("MODE BALL SPACE OR WIRE");return;}setMode(arg);status("MODEL / "+arg.toUpperCase());return;}
 if(op==="speed"){const n=Number(arg);if(!arg||!finite(n)||n<0||n>100){status("SPEED 0–100 ONLY");return;}state.speed=n;$("speed").value=String(n);$("speedValue").textContent=n+"%";status("ROTATION / "+n+"%");return;}
 if(op==="next"||op==="previous"){chooseAdjacent(op==="next"?1:-1);status("MOLECULE / "+m().name);return;}
 if(op==="pause"){setPause(true);return;}
 if(op==="play"){setPause(false);return;}
 if(op==="export"){exportJson();return;}
 if(op==="capture"){savePng();return;}
 if(op==="health"){selfTest();return;}
 if(op==="reset"){reset();return;}
 status("UNKNOWN COMMAND / TYPE /help");
}
function setMode(mode){
 if(!modes.includes(mode))return;
 state.mode=mode;document.querySelectorAll("[data-mode]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.mode===mode)));draw();
}
function setPause(on){state.paused=!!on;$("pause").setAttribute("aria-pressed",String(state.paused));$("pause").textContent=state.paused?"RESUME":"PAUSE";status(state.paused?"MOTION PAUSED":"MOTION PLAYING");draw();}
function reset(){
 state.query="";state.allowed=new Set(statuses);state.domain="all";$("query").value="";$("domain").value="all";
 document.querySelectorAll("[data-source]").forEach(c=>c.checked=true);
 state.yaw=.45;state.pitch=.36;state.zoom=1;setMode("ball");renderList();draw();status("CL1 VIEW RESET");
}
function touchpoint(e,c){const r=c.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top};}
function hit(points,xy,pad){let best=null,d=pad;for(const p of points){const v=Math.hypot(xy.x-p.x,xy.y-p.y);if(v<d){d=v;best=p}}return best;}
function wire(){
 $("query").addEventListener("input",filter);$("domain").addEventListener("change",filter);
 document.querySelectorAll("[data-source]").forEach(c=>c.addEventListener("change",filter));
 $("resetFilter").addEventListener("click",reset);
 $("random").addEventListener("click",()=>{const list=visible();if(list.length)select(list[Math.floor(Math.random()*list.length)].id)});
 document.querySelectorAll("[data-mode]").forEach(b=>b.addEventListener("click",()=>setMode(b.dataset.mode)));
 $("previous").addEventListener("click",()=>chooseAdjacent(-1));$("next").addEventListener("click",()=>chooseAdjacent(1));
 $("zoomIn").addEventListener("click",()=>{state.zoom=Math.min(2.8,state.zoom*1.16);draw()});
 $("zoomOut").addEventListener("click",()=>{state.zoom=Math.max(.5,state.zoom/1.16);draw()});
 $("recenter").addEventListener("click",()=>{state.yaw=.45;state.pitch=.36;state.zoom=1;draw()});
 $("speed").addEventListener("input",e=>{state.speed=Number(e.target.value);$("speedValue").textContent=state.speed+"%"});
 $("pause").addEventListener("click",()=>setPause(!state.paused));
 $("savePng").addEventListener("click",savePng);$("exportJson").addEventListener("click",exportJson);
 $("selfTest").addEventListener("click",selfTest);
 $("consoleForm").addEventListener("submit",e=>{e.preventDefault();command($("consoleInput").value);$("consoleInput").value=""});
 canvas.addEventListener("pointerdown",e=>{if(e.button!==0)return;const p=touchpoint(e,canvas);state.drag={x:p.x,y:p.y,total:0};canvas.setPointerCapture?.(e.pointerId);canvas.focus()});
 canvas.addEventListener("pointermove",e=>{
  if(!state.drag)return;const p=touchpoint(e,canvas),dx=p.x-state.drag.x,dy=p.y-state.drag.y;
  state.drag.total+=Math.hypot(dx,dy);state.drag.x=p.x;state.drag.y=p.y;
  if(state.drag.total>3){state.yaw+=dx*.009;state.pitch=Math.max(-1.35,Math.min(1.35,state.pitch+dy*.008));draw();}
 });
 canvas.addEventListener("pointerup",e=>{
  const old=state.drag;state.drag=null;
  if(!old||old.total>7)return;const p=hit(state.hit,touchpoint(e,canvas),26);
  if(p){state.atom=p.id;updateAtom();draw();}
 });
 for(const event of ["pointercancel","lostpointercapture"])canvas.addEventListener(event,()=>state.drag=null);
 canvas.addEventListener("wheel",e=>{e.preventDefault();state.zoom=Math.max(.5,Math.min(2.8,state.zoom*(e.deltaY<0?1.1:.9)));draw()},{passive:false});
 canvas.addEventListener("keydown",e=>{
  if(e.key==="ArrowLeft"){state.yaw-=.18;}
  else if(e.key==="ArrowRight"){state.yaw+=.18;}
  else if(e.key==="ArrowUp"){state.pitch=Math.min(1.35,state.pitch+.18);}
  else if(e.key==="ArrowDown"){state.pitch=Math.max(-1.35,state.pitch-.18);}
  else{return;}e.preventDefault();draw();
 });
 graph.addEventListener("click",e=>{const p=hit(state.graphHit,touchpoint(e,graph),17);if(p){state.atom=p.id;updateAtom();draw();}});
 document.addEventListener("keydown",e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();$("consoleInput").focus();}});
 window.addEventListener("resize",draw);
}
function loop(now){
 const dt=state.last?Math.min(.08,(now-state.last)/1000):0;state.last=now;
 if(state.ready&&!state.paused&&!state.reduced&&!document.hidden&&state.speed>0&&now-state.lastDraw>45){
  state.yaw+=dt*state.speed*.016;draw();
 }
 window.requestAnimationFrame(loop);
}
async function boot(){
 wire();if(!ctx||!gctx){message("CANVAS UNSUPPORTED");return;}
 try{
  const [r,imp]=await Promise.all([fetch("./catalogs/seed.json",{credentials:"omit"}),
    fetch("./catalogs/pubchem.json",{credentials:"omit"})]);
  if(!r.ok||!imp.ok)throw Error("MOLECULAR SOURCE FILE MISSING");
  const [data,addition]=await Promise.all([r.json(),imp.json()]);
  if(data.schema!=="xunia.cl1.molecules.v1"||addition.schema!=="xunia.cl1.molecules.v1")throw Error("CATALOG VERSION MISMATCH");
  const rows=[...(data.molecules||[]),...(addition.molecules||[])],ids=new Set();
  for(const rec of rows){validate(rec);if(ids.has(rec.id))throw Error("DUPLICATE MOLECULE ID");ids.add(rec.id);}
  state.data=rows;state.byId=new Map(rows.map(x=>[x.id,x]));state.selected=rows.find(x=>x.id==="water")?.id||rows[0]?.id;
  if(!state.selected)throw Error("EMPTY CATALOG");
  $("importState").textContent=addition.status==="not-imported"?
   "PUBCHEM IMPORT NOT RUN / CURATED BASELINE ACTIVE":
   "PUBCHEM IMPORT / "+(addition.molecules||[]).length+" SOURCE RECORDS LOADED";
  $("totalMolecules").textContent=String(rows.length);
  $("totalElements").textContent=String(new Set(rows.flatMap(r=>r.atoms.map(a=>a.element))).size);
  $("astroMolecules").textContent=String(rows.filter(x=>x.status==="astronomical-reference").length);
  state.ready=true;inspect();renderList();draw();
  message("CL1 READY / "+rows.length+" CURATED + IMPORTED RECORDS / NO LIVE API");
  status("MODEL ONLINE / 3D GEOMETRY IS ILLUSTRATIVE");
  window.requestAnimationFrame(loop);
 }catch(e){message("CL1 LOAD FAILED / "+String(e.message).slice(0,90));$("renderState").textContent="CATALOG ERROR";}
}
boot();
})();