import {validateOntology,viewSystems,ontologyGraph,stats} from "./core.mjs";
const $=id=>document.getElementById(id),NS="http://www.w3.org/2000/svg";
let registry=null,activeId=null;
const node=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e;};
const sv=(tag,attrs={})=>{const e=document.createElementNS(NS,tag);for(const [key,value] of Object.entries(attrs))e.setAttribute(key,String(value));return e;};
const shorter=(text,max)=>text.length>max?text.slice(0,max-1)+"…":text;
const elText=(g,x,y,text,cls)=>{const n=sv("text",{x,y,class:cls});n.textContent=text;g.append(n);return n;};
function filters(){return {query:$("query").value,branch:$("branch").value,domain:$("domain").value,status:$("status").value};}
function setSelection(id){
 activeId=id;render();
 if(window.innerWidth<900)$("inspector").scrollIntoView({behavior:"instant",block:"nearest"});
}
function inspector(selected){
 const root=$("inspector");root.replaceChildren();
 if(!selected){root.append(node("p","placeholder","No system matches the current filters. Adjust the ontology view."));return;}
 root.append(node("div","obj-class","OBJECT / CAPABILITY SYSTEM"),node("h2","inspector-title",selected.name),node("span","inspector-status",selected.status));
 root.append(node("p","inspector-copy",selected.assessment));
 const facts=node("div","facts");
 for(const [key,value] of [["MILITARY SERVICE",selected.branch],["CAPABILITY DOMAIN",selected.domain],["HIGH-LEVEL MISSION",selected.role],["EVIDENCE DATE",selected.evidence_date],["PROVENANCE",selected.source.publisher],["WEAPON ACTIVATION",selected.activation],["LIVE TELEMETRY",selected.telemetry]]){
  const fact=node("div","fact");fact.append(node("span",null,key),node("span",null,value));facts.append(fact);
 }
 root.append(facts);
 const link=node("a","proof","OPEN OFFICIAL EVIDENCE ↗");link.href=selected.source.url;link.target="_blank";link.rel="noopener noreferrer";root.append(link);
 root.append(node("p","no-link","Evidence records support public milestones only. No technical specifications, targeting data, or current activation can be inferred."));
}
function paintGraph(selected){
 const graph=$("ontology-graph");graph.replaceChildren();
 const systems=selected,info=ontologyGraph(registry,filters());
 const h=Math.max(850,120+systems.length*63),sy=(i)=>95+i*63;
 graph.setAttribute("viewBox","0 0 1320 "+h);
 const bg=sv("g");
 for(let y=36;y<=h;y+=43)bg.append(sv("line",{x1:0,y1:y,x2:1320,y2:y,stroke:"#3d6065","stroke-width":".5",opacity:".27"}));
 for(let x=0;x<=1320;x+=48)bg.append(sv("line",{x1:x,y1:0,x2:x,y2:h,stroke:"#3d6065","stroke-width":".5",opacity:".19"}));
 graph.append(bg);
 elText(graph,25,36,"SERVICE BRANCH","graph-headings");elText(graph,400,36,"PUBLIC SYSTEM RECORD","graph-headings");elText(graph,1040,36,"DOMAIN","graph-headings");
 if(!systems.length){elText(graph,420,220,"NO MATCHING PUBLIC OBJECTS","graph-headings");return;}
 const serviceGroups=new Map(),domainGroups=new Map();
 systems.forEach((p,i)=>{for(const [set,key] of [[serviceGroups,p.branch],[domainGroups,p.domain]]){if(!set.has(key))set.set(key,[]);set.get(key).push(sy(i));}});
 const positions=new Map();
 for(const [name,ys] of serviceGroups)positions.set("service:"+name,ys.reduce((a,b)=>a+b,0)/ys.length);
 for(const [name,ys] of domainGroups)positions.set("domain:"+name,ys.reduce((a,b)=>a+b,0)/ys.length);
 const connectors=sv("g"),hubs=sv("g"),programs=sv("g");graph.append(connectors,hubs,programs);
 for(const [kind,groups,x,w,cls] of [["service",serviceGroups,20,245,"graph-service"],["domain",domainGroups,1030,280,"graph-domain"]]){
  for(const name of groups.keys()){
   const y=positions.get(kind+":"+name),g=sv("g");
   g.append(sv("rect",{x,y:y-22,width:w,height:44,rx:5,class:cls}));
   elText(g,x+12,y+5,shorter(name,31),"graph-label");hubs.append(g);
  }
 }
 systems.forEach((p,i)=>{
  const y=sy(i),isActive=p.id===activeId;
  const branchY=positions.get("service:"+p.branch),domainY=positions.get("domain:"+p.domain);
  const c1=sv("path",{d:"M265 "+branchY+" C315 "+branchY+" 325 "+y+" 385 "+y,class:"graph-edge"+(isActive?" highlight":"")});
  const c2=sv("path",{d:"M890 "+y+" C940 "+y+" 966 "+domainY+" 1030 "+domainY,class:"graph-edge domain"+(isActive?" highlight":"")});
  connectors.append(c1,c2);
  const g=sv("g",{tabindex:"0",role:"button","aria-label":"Inspect "+p.name+", "+p.status,class:"graph-program"});
  const rect=sv("rect",{x:385,y:y-27,width:505,height:54,rx:5,class:"graph-system"+(isActive?" selected":"")});
  g.append(rect);
  const title=sv("title");title.textContent=p.name+" / "+p.status;g.append(title);
  elText(g,397,y-5,shorter(p.name,53),"graph-label");
  elText(g,397,y+14,shorter(p.status.toUpperCase()+" · EVIDENCE "+p.evidence_date,69),"graph-small");
  g.addEventListener("click",()=>setSelection(p.id));
  g.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();setSelection(p.id);}});
  programs.append(g);
 });
 $("graph-status").textContent=info.nodes.length+" OBJECTS / "+info.edges.length+" LINKS";
}
function paintCatalog(items){
 const grid=$("system-grid"),frag=document.createDocumentFragment();
 for(const p of items){
  const b=node("button","system-card"+(p.id===activeId?" selected":""));
  b.type="button";b.append(node("small",null,p.branch.toUpperCase()+" / "+p.domain.toUpperCase()),node("strong",null,p.name),node("p",null,p.role),node("span",null,p.status+" · "+p.evidence_date));
  b.addEventListener("click",()=>setSelection(p.id));frag.append(b);
 }
 grid.replaceChildren(frag);$("catalog-count").textContent=items.length+" PUBLIC OBJECTS";
}
function render(){
 if(!registry)return;
 const items=viewSystems(registry,filters());
 if(!items.some(x=>x.id===activeId))activeId=items[0]?.id||null;
 const s=stats(registry,filters());
 $("metric-systems").textContent=s.systems;$("metric-branches").textContent=s.branches;$("metric-domains").textContent=s.domains;
 inspector(items.find(x=>x.id===activeId));paintGraph(items);paintCatalog(items);
 $("load-state").textContent=items.length?items.length+" evidence-linked public system records selected; actual activation remains NOT PUBLICLY VERIFIED.":"No matches; no substitute records.";
 $("export").disabled=items.length===0;
}
function exportView(){
 if(!registry)return;
 const items=viewSystems(registry,filters()),graph=ontologyGraph(registry,filters());
 const payload={schema:registry.schema,as_of:registry.as_of,palantir_connection:"NOT_CONNECTED",live_activation_feeds:0,
  authorized_systems_connected:0,status:"PUBLIC_EVIDENCE_ONLY_NOT_ACTIVE_ARSENAL",
  export_time:new Date().toISOString(),filters:filters(),programs:items,
  object_types:registry.object_types,link_types:registry.link_types,graph};
 const blob=new Blob([JSON.stringify(payload,null,2)],{type:"application/json"});
 const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="xunia-glass-onion-nonkinetic-ontology.json";
 document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function populate(select,values){
 for(const name of values){const opt=node("option",null,name);opt.value=name;select.append(opt);}
}
async function init(){
 $("export").disabled=true;
 try{
  const response=await fetch("./ontology.json",{cache:"no-store"});
  if(!response.ok)throw Error("Cannot load source registry");
  registry=validateOntology(await response.json());
  populate($("branch"),registry.services);populate($("domain"),registry.domains);populate($("status"),registry.statuses);
  render();
 }catch{
  $("load-state").textContent="PUBLIC ONTOLOGY UNAVAILABLE — no alternative or simulated records loaded.";
  $("graph-status").textContent="NO VERIFIED DATA";
  $("inspector").replaceChildren(node("p","placeholder","Unable to validate the public evidence registry."));
 }
}
for(const id of ["branch","domain","status"])$(id).addEventListener("change",render);
$("query").addEventListener("input",render);
$("export").addEventListener("click",exportView);
init();
