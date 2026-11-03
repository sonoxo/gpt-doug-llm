"use strict";
(() => {
  const byId = id => document.getElementById(id);
  const palette = ["#45ead3","#72bafa","#c3a1fc","#f0c47b","#87dba8","#ef9ab6","#d4d8ea","#71a6b8"];
  const state = {snapshot:null,repos:[],selected:null,live:false,checkedAt:null,workflows:new Map(),search:"",category:""};
  const graph = {nodes:[],categoryNodes:[],owner:null,scale:1,panX:0,panY:0,moving:false,pointer:null};
  const canvas = byId("graph"), ctx = canvas.getContext("2d"), tooltip=byId("tooltip");
  let viewWidth=0,viewHeight=0;
  const safeGithubUrl = id => /^sonoxo\/[A-Za-z0-9_.-]+$/.test(id) ? "https://github.com/"+id : null;
  const setStatus = (text,error=false) => {byId("status").textContent=text;byId("status").classList.toggle("error",error);};
  function escapeNone() { /* Text is assigned with textContent, never raw HTML. */ }
  function matching(r) {
    return (!state.category||r.category===state.category) &&
      (!state.search||[r.id,r.category,r.defaultBranch,r.language||""].join(" ").toLowerCase().includes(state.search));
  }
  function stateCounts() {
    const repos=state.repos;
    byId("total").textContent=repos.length.toLocaleString();
    byId("curated").textContent=repos.filter(r=>r.classificationBasis==="museum catalog").length;
    byId("inferred").textContent=repos.filter(r=>r.classificationBasis!=="museum catalog").length;
    byId("archived").textContent=repos.filter(r=>r.archived).length;
    const dated=repos.filter(r=>r.pushedAt&&Number.isFinite(Date.parse(r.pushedAt)));
    const recent=dated.filter(r=>Date.now()-Date.parse(r.pushedAt)<=30*86400000).length;
    byId("active").textContent=dated.length===repos.length?recent.toLocaleString():"—";
    byId("activeHint").textContent=dated.length===repos.length?"Based on GitHub push timestamps":"Available after live scan";
    byId("timestamp").textContent=state.live?"Live metadata checked "+new Date(state.checkedAt).toLocaleString():"Snapshot dated "+state.snapshot.snapshotDate;
  }
  function colorOf(category) {
    const cats=[...new Set(state.repos.map(r=>r.category))].sort();
    return palette[Math.max(0,cats.indexOf(category))%palette.length];
  }
  function renderBars() {
    const container=byId("bars");container.replaceChildren();
    const cats=[...new Set(state.repos.map(r=>r.category))].sort();
    const total=state.repos.length||1;
    cats.forEach(cat=>{
      const count=state.repos.filter(r=>r.category===cat).length;
      const row=document.createElement("div");row.className="line";
      const label=document.createElement("label");label.textContent=cat;
      const percent=document.createElement("span");percent.className="pct";percent.textContent=count+" / "+Math.round(count/total*100)+"%";
      const track=document.createElement("div");track.className="bar-track";
      const fill=document.createElement("i");fill.style.width=(count/total*100)+"%";fill.style.background=colorOf(cat);
      track.append(fill);row.append(label,percent,track);container.append(row);
    });
  }
  function renderCategories() {
    const options=byId("category"), prior=state.category;options.replaceChildren();
    const start=document.createElement("option");start.value="";start.textContent="All groups";options.append(start);
    [...new Set(state.repos.map(r=>r.category))].sort().forEach(cat=>{
      const opt=document.createElement("option");opt.value=cat;opt.textContent=cat;options.append(opt);
    });
    if([...options.options].some(o=>o.value===prior))options.value=prior;else state.category="";
  }
  function el(tag,text,cls) {const item=document.createElement(tag);if(text!=null)item.textContent=text;if(cls)item.className=cls;return item;}
  function dateString(value) {const d=new Date(value);return Number.isFinite(d.getTime())?d.toLocaleDateString():"Not checked";}
  function renderTable() {
    const body=byId("table");body.replaceChildren();
    const rows=state.repos.filter(matching).sort((a,b)=>a.name.localeCompare(b.name));
    byId("tableCount").textContent=rows.length+" of "+state.repos.length+" public repositories displayed. Click a row to inspect.";
    byId("matching").textContent=rows.length+" repositories in view";
    const frag=document.createDocumentFragment();
    rows.forEach(r=>{
      const tr=el("tr");tr.addEventListener("click",e=>{if(e.target.closest("a"))return;selectRepo(r.id);});
      const name=el("td"),a=el("a",r.name);a.href=safeGithubUrl(r.id)||"#";a.target="_blank";a.rel="noopener noreferrer";name.append(a);
      const cat=el("td",r.category);const basis=el("small"," ("+r.classificationBasis+")");basis.style.color="#829fac";cat.append(basis);
      const lang=el("td",r.language||"Not checked");
      const push=el("td",r.pushedAt?dateString(r.pushedAt):"Not checked");
      const status=el("td",r.archived?"Archived":r.fork===true?"Fork":"Public");
      tr.append(name,cat,lang,push,status);frag.append(tr);
    });
    body.append(frag);
  }
  function renderInspector() {
    const box=byId("inspector");box.replaceChildren();
    const r=state.repos.find(x=>x.id===state.selected);
    if(!r){box.append(el("p","Select a repository node or list item. Categories indicate visual grouping only."));return;}
    box.append(el("h3",r.name));
    const dl=el("dl");
    [["Owner", "sonoxo"],["Classification",r.category],["Evidence",r.classificationBasis],["Default branch",r.defaultBranch||"Unavailable"],
     ["Visibility","Public"],["Archived",r.archived?"Yes":"No"],["Fork",r.fork===undefined?"Not checked":r.fork?"Yes":"No"],
     ["Language",r.language||"Not checked"],["Last push",r.pushedAt?dateString(r.pushedAt):"Not checked"],
     ["Stars",r.stars==null?"Not checked":String(r.stars)],["Open issues",r.openIssues==null?"Not checked":String(r.openIssues)]
    ].forEach(([k,v])=>{dl.append(el("dt",k),el("dd",v));});box.append(dl);
    const link=el("a","Open GitHub repository ↗");link.href=safeGithubUrl(r.id);link.target="_blank";link.rel="noopener noreferrer";box.append(link);
    box.append(el("p","Workflow status is a recent CI observation, not a security assessment.","fine"));
    const btn=el("button","Check latest GitHub workflow");btn.type="button";btn.addEventListener("click",()=>checkWorkflow(r.id,btn));box.append(btn);
    const status=state.workflows.get(r.id);if(status)box.append(el("p",workflowLabel(status),"fine"));
  }
  function workflowLabel(w) {return w.available?(w.workflow+": "+(w.conclusion||w.status||"unknown")+" ("+dateString(w.createdAt)+")"):"Workflow unavailable: "+(w.reason||"no public run returned");}
  function renderWorkflow() {
    const box=byId("workflows");box.replaceChildren();
    if(!state.workflows.size){box.append(el("p","Not checked yet. Scan GitHub or inspect an individual repository.","fine"));return;}
    [...state.workflows.entries()].sort().forEach(([id,w])=>{
      const item=el("div",null,"workflow-item");item.append(el("strong",id.split("/")[1]));
      const detail=el("span",workflowLabel(w));if(w.available&&w.conclusion==="success")detail.className="success";else if(w.available&&w.conclusion==="failure")detail.className="failure";
      item.append(detail);if(w.url&&/^https:\/\/github\.com\/sonoxo\//.test(w.url)){const a=el("a"," · Run details ↗");a.href=w.url;a.target="_blank";a.rel="noopener noreferrer";item.append(a);}
      box.append(item);
    });
  }
  function positionNodes() {
    const groups=[...new Set(state.repos.map(r=>r.category))].sort();
    const weights=groups.map(c=>.6+Math.sqrt(state.repos.filter(r=>r.category===c).length));
    const total=weights.reduce((a,b)=>a+b,0);
    graph.owner={type:"owner",id:"sonoxo",x:0,y:0,r:23};
    graph.nodes=[];graph.categoryNodes=[];
    let cursor=-Math.PI/2;
    groups.forEach((category,i)=>{
      const members=state.repos.filter(r=>r.category===category).sort((a,b)=>a.name.localeCompare(b.name));
      const span=Math.PI*2*weights[i]/total,mid=cursor+span/2;
      const hub={type:"category",id:category,x:Math.cos(mid)*175,y:Math.sin(mid)*175,r:12,color:palette[i%palette.length]};
      graph.categoryNodes.push(hub);
      const rings=Math.max(2,Math.ceil(Math.sqrt(members.length/2.8)));
      const angularSlots=Math.ceil(members.length/rings);
      members.forEach((r,j)=>{
        const band=j%rings,slot=Math.floor(j/rings);
        const angle=cursor+span*((slot+.5)/angularSlots);
        const radius=300+band*47;
        graph.nodes.push({type:"repo",id:r.id,category,x:Math.cos(angle)*radius,y:Math.sin(angle)*radius,r:r.classificationBasis==="museum catalog"?5.3:3.8,color:palette[i%palette.length],basis:r.classificationBasis});
      });cursor+=span;
    });
  }
  function fitGraph() {
    graph.scale=Math.min(viewWidth/1470,viewHeight/1470);graph.panX=0;graph.panY=0;drawGraph();
  }
  function screenXY(p) {return {x:viewWidth/2+graph.panX+p.x*graph.scale,y:viewHeight/2+graph.panY+p.y*graph.scale};}
  function resize() {
    const rect=canvas.getBoundingClientRect();if(rect.width<20||rect.height<20)return;
    viewWidth=rect.width;viewHeight=rect.height;
    const dpr=Math.min(window.devicePixelRatio||1,2);
    canvas.width=Math.round(viewWidth*dpr);canvas.height=Math.round(viewHeight*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
    if(!graph.scale||graph.scale===1)fitGraph();else drawGraph();
  }
  function drawGraph() {
    if(!viewWidth||!graph.owner)return;
    ctx.clearRect(0,0,viewWidth,viewHeight);
    const gridStep=90*graph.scale;
    if(gridStep>15){ctx.strokeStyle="#18384b55";ctx.lineWidth=.5;for(let x=(viewWidth/2+graph.panX)%gridStep;x<viewWidth;x+=gridStep){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,viewHeight);ctx.stroke();}for(let y=(viewHeight/2+graph.panY)%gridStep;y<viewHeight;y+=gridStep){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(viewWidth,y);ctx.stroke();}}
    const owner=screenXY(graph.owner);
    graph.categoryNodes.forEach(h=>{const p=screenXY(h);ctx.strokeStyle="#65b4c755";ctx.setLineDash([]);ctx.lineWidth=1.25;ctx.beginPath();ctx.moveTo(owner.x,owner.y);ctx.lineTo(p.x,p.y);ctx.stroke();});
    const lookup=new Map(graph.categoryNodes.map(h=>[h.id,h]));
    graph.nodes.forEach(n=>{
      const parent=screenXY(lookup.get(n.category)),p=screenXY(n);
      const selected=state.selected===n.id, match=matching(state.repos.find(r=>r.id===n.id));
      ctx.strokeStyle=selected?"#f8e59b":match?"#39798666":"#24475823";
      ctx.lineWidth=selected?2:.65;ctx.setLineDash(n.basis==="museum catalog"?[]:[3,5]);ctx.beginPath();ctx.moveTo(parent.x,parent.y);ctx.lineTo(p.x,p.y);ctx.stroke();
    });ctx.setLineDash([]);
    graph.nodes.forEach(n=>{
      const r=state.repos.find(x=>x.id===n.id),match=matching(r),p=screenXY(n),selected=state.selected===n.id;
      ctx.beginPath();ctx.arc(p.x,p.y,Math.max(2.7,n.r*Math.max(graph.scale,.75))+(selected?3:0),0,Math.PI*2);
      ctx.fillStyle=match?n.color:"#41535b";ctx.globalAlpha=match?1:.18;ctx.fill();ctx.globalAlpha=1;
      if(selected){ctx.strokeStyle="#ffffff";ctx.lineWidth=2;ctx.stroke();}
    });
    graph.categoryNodes.forEach(h=>{
      const p=screenXY(h);ctx.beginPath();ctx.arc(p.x,p.y,10,0,Math.PI*2);ctx.fillStyle=h.color;ctx.fill();
      ctx.font="bold 11px system-ui";ctx.textAlign="center";ctx.textBaseline="bottom";ctx.fillStyle="#d7eaf3";
      const label=h.id.replace(" & "," / ").replace(" repositories","");
      const short=label.length>23?label.slice(0,21)+"…":label;ctx.fillText(short,p.x,p.y-15);
    });
    ctx.beginPath();ctx.arc(owner.x,owner.y,21,0,Math.PI*2);ctx.fillStyle="#ffe7a0";ctx.fill();ctx.fillStyle="#05202b";ctx.font="bold 15px system-ui";ctx.textBaseline="middle";ctx.textAlign="center";ctx.fillText("S",owner.x,owner.y);
    byId("graphScale").textContent=Math.round(graph.scale*100)+"%";
  }
  function hit(x,y) {
    for(let i=graph.nodes.length-1;i>=0;i--){const n=graph.nodes[i],p=screenXY(n),dx=p.x-x,dy=p.y-y;if(dx*dx+dy*dy<Math.pow(Math.max(9,8*graph.scale),2))return n;}
    for(const n of graph.categoryNodes){const p=screenXY(n);if(Math.hypot(p.x-x,p.y-y)<14)return n;}return null;
  }
  function pointerPos(e) {const b=canvas.getBoundingClientRect();return{x:e.clientX-b.left,y:e.clientY-b.top};}
  canvas.addEventListener("pointerdown",e=>{canvas.setPointerCapture(e.pointerId);const p=pointerPos(e);graph.pointer={x:p.x,y:p.y,originX:p.x,originY:p.y,moved:false};graph.moving=true;});
  canvas.addEventListener("pointermove",e=>{
    const p=pointerPos(e);
    if(graph.moving&&graph.pointer){const v=graph.pointer;graph.panX+=p.x-v.x;graph.panY+=p.y-v.y;if(Math.hypot(p.x-v.originX,p.y-v.originY)>6)v.moved=true;v.x=p.x;v.y=p.y;drawGraph();tooltip.hidden=true;return;}
    const n=hit(p.x,p.y);canvas.style.cursor=n?"pointer":"grab";
    if(n){tooltip.hidden=false;tooltip.textContent=n.type==="repo"?n.id:n.id;tooltip.style.left=Math.min(p.x+15,viewWidth-250)+"px";tooltip.style.top=Math.min(p.y+10,viewHeight-45)+"px";}else tooltip.hidden=true;
  });
  canvas.addEventListener("pointerup",e=>{const p=pointerPos(e),v=graph.pointer;graph.moving=false;graph.pointer=null;if(!v?.moved){const n=hit(p.x,p.y);if(n?.type==="repo")selectRepo(n.id);else if(n?.type==="category"){state.category=n.id;byId("category").value=n.id;renderTable();drawGraph();}}});
  canvas.addEventListener("pointercancel",()=>{graph.moving=false;graph.pointer=null;});
  canvas.addEventListener("wheel",e=>{e.preventDefault();const p=pointerPos(e),beforeX=(p.x-viewWidth/2-graph.panX)/graph.scale,beforeY=(p.y-viewHeight/2-graph.panY)/graph.scale;
    graph.scale=Math.min(2.8,Math.max(.12,graph.scale*(e.deltaY<0?1.12:.89)));
    graph.panX=p.x-viewWidth/2-beforeX*graph.scale;graph.panY=p.y-viewHeight/2-beforeY*graph.scale;drawGraph();
  },{passive:false});
  function selectRepo(id) {state.selected=id;renderInspector();drawGraph();}
  async function fetchJson(url) {
    const r=await fetch(url,{headers:{"Accept":"application/vnd.github+json"},cache:"no-store"});
    if(!r.ok)throw new Error("GitHub HTTP "+r.status+(r.status===403?" (public API rate limit or access restriction)":""));
    return r.json();
  }
  async function checkWorkflow(id,button) {
    if(!safeGithubUrl(id))return;
    if(button)button.disabled=true;
    try {
      const d=await fetchJson("https://api.github.com/repos/"+id+"/actions/runs?per_page=1");
      const run=Array.isArray(d.workflow_runs)?d.workflow_runs[0]:null;
      const record=run?{available:true,workflow:run.name||"Workflow",status:run.status,conclusion:run.conclusion,createdAt:run.created_at,url:run.html_url}:{available:false,reason:"No public workflow runs returned"};
      state.workflows.set(id,record);
    }catch(e){state.workflows.set(id,{available:false,reason:String(e.message)});}
    if(button)button.disabled=false;renderWorkflow();renderInspector();
  }
  async function scanGithub() {
    const button=byId("refreshBtn");button.disabled=true;setStatus("Reading public GitHub repository pages — no login or paid API needed…");
    try {
      const found=new Map();let complete=false;
      for(let page=1;page<=8;page++){
        const data=await fetchJson("https://api.github.com/users/sonoxo/repos?per_page=100&type=owner&sort=updated&page="+page);
        if(!Array.isArray(data))throw Error("Unexpected GitHub response");
        data.forEach(x=>{
          if(x.owner?.login!=="sonoxo"||x.private===true||x.visibility==="private")return;
          if(!safeGithubUrl(x.full_name))return;
          const prev=state.repos.find(y=>y.id===x.full_name);
          found.set(x.full_name,{id:x.full_name,name:x.name,url:safeGithubUrl(x.full_name),category:prev?.category||"Other public repositories",classificationBasis:prev?.classificationBasis||"unclassified",defaultBranch:x.default_branch||null,archived:x.archived===true,sizeKB:x.size??null,pushedAt:x.pushed_at||null,language:x.language||null,stars:x.stargazers_count??null,openIssues:x.open_issues_count??null,fork:x.fork===true});
        });
        setStatus("Scanning GitHub page "+page+" — "+found.size+" public repositories observed…");
        if(data.length<100){complete=true;break;}
      }
      if(!complete)throw Error("Eight-page safety limit reached; data may be incomplete");
      if(!found.size)throw Error("No public repositories returned");
      state.repos=[...found.values()].sort((a,b)=>a.id.localeCompare(b.id));state.live=true;state.checkedAt=new Date().toISOString();
      if(state.selected&&!state.repos.some(r=>r.id===state.selected))state.selected=null;
      fullRender();setStatus("Live GitHub scan completed: "+state.repos.length+" public repositories. Private repositories excluded; this does not audit code vulnerabilities.");
      const key=["sonoxo/gpt-doug-llm","sonoxo/xuniadao","sonoxo/zyra","sonoxo/thegreenhouse","sonoxo/gods-eye-viewXUNIA"];
      await Promise.allSettled(key.filter(id=>found.has(id)).map(id=>checkWorkflow(id)));
    }catch(e){setStatus("Live scan unavailable: "+e.message+". Existing verified public snapshot remains visible.",true);}
    finally{button.disabled=false;}
  }
  function exportJSON() {
    const output={schema:"xunia.ecosystem-visual-export.v1",source:state.live?"live public GitHub API":"repository snapshot",checkedAt:state.checkedAt||state.snapshot?.snapshotDate,coverage:state.snapshot?.coverage,repositoryCount:state.repos.length,securityAuditPerformed:false,codeExecutionPerformed:false,relationshipBasis:"ownership + visual classifications; not dependencies",repositories:state.repos,observedWorkflowRuns:Object.fromEntries(state.workflows)};
    const blob=new Blob([JSON.stringify(output,null,2)],{type:"application/json"});
    const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="xunia-public-ecosystem-"+new Date().toISOString().slice(0,10)+".json";document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function fullRender() {stateCounts();renderCategories();renderBars();renderTable();renderInspector();renderWorkflow();positionNodes();fitGraph();}
  byId("refreshBtn").addEventListener("click",scanGithub);
  byId("exportBtn").addEventListener("click",exportJSON);
  byId("fitBtn").addEventListener("click",fitGraph);
  byId("search").addEventListener("input",e=>{state.search=e.target.value.toLowerCase().trim();renderTable();drawGraph();});
  byId("category").addEventListener("change",e=>{state.category=e.target.value;renderTable();drawGraph();});
  window.addEventListener("resize",resize);
  (async()=>{
    try{
      const r=await fetch("./snapshot.json",{cache:"no-store"});if(!r.ok)throw Error("Snapshot HTTP "+r.status);
      const snapshot=await r.json();
      if(snapshot.schema!=="xunia.public-repo-scan.v1"||!Array.isArray(snapshot.repositories))throw Error("Unrecognized snapshot schema");
      if(snapshot.repositories.some(x=>!safeGithubUrl(x.id)))throw Error("Non-public or invalid source present");
      state.snapshot=snapshot;state.repos=snapshot.repositories;
      fullRender();setStatus("Public snapshot loaded: "+state.repos.length+" verified Sonoxo repositories. Select 'Scan GitHub now' for live language, push, stars and workflow observations.");
    }catch(e){setStatus("Could not load public repository snapshot: "+e.message+". Open from xunia.org rather than the local file URL.",true);}
  })();
  if(window.ResizeObserver)new ResizeObserver(resize).observe(byId("graphWrap"));
})();
