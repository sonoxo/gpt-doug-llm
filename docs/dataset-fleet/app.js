"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const state = {source:null,mode:"preview",datasets:[],lineage:[],selected:null,query:""};
  const canvas=$("graph"),ctx=canvas.getContext("2d");
  const universe={nodes:[],center:{x:0,y:0},width:0,height:0,scale:1,ox:0,oy:0,pointer:null};
  const colors=["#59efdd","#78bdfb","#c2a2fb","#ffd49a","#a9dfb3"];
  const status=(message,error=false)=>{$("status").textContent=message;$("status").classList.toggle("error",error);};
  const el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!=null)x.textContent=String(text);if(cls)x.className=cls;return x;};
  const match=d=>!state.query || [d.id,d.name,d.category].join(" ").toLowerCase().includes(state.query);
  function roleCards() {
    const root=$("pipeline");root.replaceChildren();
    const roles=[["DISCOVER","Resolve explicit approved paths","◌"],["VERIFY","Validate schema, public scope & SHA-256","◇"],["INDEX","Process rows into local SQLite","▦"],["RELATE","Record declared reference lineage","⬡"],["AUDIT","Persist receipts, retries & quarantine","◎"]];
    roles.forEach(([name,detail,symbol],i)=>{
      const card=el("div",null,"role");
      const sig=el("div",symbol,"symbol");sig.style.color=colors[i];
      card.append(sig,el("b",name),el("span",detail));root.append(card);
    });
  }
  function validate(data,mode) {
    if(!data||typeof data!=="object")throw Error("JSON object required");
    if(mode==="preview"){
      if(data.schema!=="gpt-doug.dataset-fleet.preview.v1"||data.status!=="reference_only_not_executed")throw Error("Unknown preview schema");
    } else if(data.schema!=="gpt-doug.dataset-fleet.report.v1"||data.networkAccess!==false||data.modelAPICalls!==0) {
      throw Error("Not an approved local GPT-DOUG data fleet report");
    }
    if(!Array.isArray(data.datasets)||data.datasets.length<1||data.datasets.length>100||!Array.isArray(data.lineage))throw Error("Invalid dataset structure");
    const ids=new Set();
    for(const d of data.datasets){
      if(typeof d.id!=="string"||!/^[a-z][a-z0-9-]{2,63}$/.test(d.id)||ids.has(d.id))throw Error("Duplicate or invalid dataset ID");
      ids.add(d.id);
      if(mode!=="preview"&&(!Number.isInteger(d.rows)||d.rows<0||!/^[a-f0-9]{64}$/.test(d.sha256)))throw Error("Invalid dataset count or SHA");
    }
    if(data.lineage.some(e=>!ids.has(e.source_id)||!ids.has(e.target_id)||e.kind!=="curated-reference"))throw Error("Unverified lineage relation");
    return data;
  }
  function load(data,mode) {
    validate(data,mode);
    state.source=data;state.mode=mode;state.datasets=data.datasets.map(d=>({...d,name:d.name||d.id,category:d.category||"public-metadata"}));
    state.lineage=data.lineage;
    if(!state.datasets.some(d=>d.id===state.selected))state.selected=state.datasets[0].id;
    state.query="";$("search").value="";
    const totalRows=state.datasets.reduce((n,d)=>n+(d.rows||0),0);
    $("datasets").textContent=String(state.datasets.length);
    $("rows").textContent=mode==="report"?totalRows.toLocaleString():"—";
    $("edges").textContent=String(state.lineage.length);
    $("mode").textContent=mode==="report"?"LOCAL REPORT IMPORTED":"REFERENCE PREVIEW";
    $("stamp").textContent=mode==="report"?"Local report "+(data.generatedAt||""):"Checked-in source manifest preview";
    $("export").disabled=mode!=="report";
    layout();renderTable();renderDetails();renderDistribution();fit();
    status(mode==="report"?
      "Verified local report imported. Displaying measured records, hashes and declared lineage. The report stays in this browser.":
      "Reference topology loaded: four approved public source definitions. No dataset pipeline has run in this browser. Import a local report to see real results.");
  }
  function layout() {
    const n=state.datasets.length;
    universe.nodes=state.datasets.map((d,i)=>{
      const angle=(Math.PI*2*i/Math.max(n,1))-Math.PI/2;
      const radius=n<6?260:270+Math.floor(i/10)*75;
      return {id:d.id,position:{x:Math.cos(angle)*radius,y:Math.sin(angle)*radius},color:colors[i%colors.length],source:d};
    });
  }
  function screen(p){return{x:universe.width/2+universe.ox+p.x*universe.scale,y:universe.height/2+universe.oy+p.y*universe.scale};}
  function fit() {
    if(!universe.width)return;
    const extent=Math.max(330,...universe.nodes.map(n=>Math.hypot(n.position.x,n.position.y)+110));
    universe.scale=Math.min(universe.width/(2*extent),universe.height/(2*extent))*.90;
    universe.ox=0;universe.oy=0;draw();
  }
  function resize() {
    const rect=canvas.getBoundingClientRect();if(rect.width<40||rect.height<40)return;
    universe.width=rect.width;universe.height=rect.height;
    const dpr=Math.min(window.devicePixelRatio||1,2);
    canvas.width=Math.round(rect.width*dpr);canvas.height=Math.round(rect.height*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
    if(!universe.nodes.length)return;
    if(!universe.scale||universe.scale===1)fit();else draw();
  }
  function draw() {
    if(!universe.width||!state.source)return;
    ctx.clearRect(0,0,universe.width,universe.height);
    const center=screen(universe.center);
    const selected=state.selected;
    for(const node of universe.nodes){
      const p=screen(node.position);
      ctx.strokeStyle="#4b99aa65";ctx.lineWidth=1.7;ctx.beginPath();ctx.moveTo(center.x,center.y);ctx.lineTo(p.x,p.y);ctx.stroke();
    }
    const byId=new Map(universe.nodes.map(x=>[x.id,x]));
    ctx.setLineDash([5,7]);ctx.lineWidth=1.5;ctx.strokeStyle="#b5a1fa";
    for(const line of state.lineage){
      const a=byId.get(line.source_id),b=byId.get(line.target_id);
      if(!a||!b)continue;
      const p=screen(a.position),q=screen(b.position);
      ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);ctx.stroke();
    }
    ctx.setLineDash([]);
    ctx.beginPath();ctx.arc(center.x,center.y,Math.max(18,31*universe.scale),0,Math.PI*2);
    ctx.fillStyle="#f7d79b";ctx.fill();ctx.fillStyle="#11232b";
    ctx.textAlign="center";ctx.textBaseline="middle";ctx.font="bold 13px system-ui";ctx.fillText("DOUG",center.x,center.y);
    universe.nodes.forEach(node=>{
      const p=screen(node.position),active=selected===node.id;
      const radius=Math.max(10,25*universe.scale);
      ctx.globalAlpha=match(node.source)?1:.19;
      ctx.beginPath();ctx.arc(p.x,p.y,radius,0,Math.PI*2);
      ctx.fillStyle=node.color;ctx.fill();
      if(active){ctx.strokeStyle="#ffffff";ctx.lineWidth=3;ctx.stroke();}
      ctx.globalAlpha=1;
      ctx.textAlign="center";ctx.textBaseline="top";ctx.font="bold 12px system-ui";ctx.fillStyle="#e9f7fb";
      const d=node.source;
      ctx.fillText(d.name.length>27?d.name.slice(0,25)+"…":d.name,p.x,p.y+radius+8);
      ctx.font="11px system-ui";ctx.fillStyle="#a8d2dd";
      ctx.fillText(state.mode==="report"?String(d.rows||0)+" rows":"Configured / not run",p.x,p.y+radius+25);
    });
    $("matches").textContent=state.datasets.filter(match).length+" / "+state.datasets.length+" public datasets";
  }
  function hit(p){
    for(let i=universe.nodes.length-1;i>=0;i--){
      const n=universe.nodes[i],q=screen(n.position);
      if(Math.hypot(p.x-q.x,p.y-q.y)<Math.max(21,28*universe.scale))return n;
    }
    return null;
  }
  const point=e=>{const rect=canvas.getBoundingClientRect();return{x:e.clientX-rect.left,y:e.clientY-rect.top};};
  canvas.addEventListener("pointerdown",e=>{
    const p=point(e);canvas.setPointerCapture(e.pointerId);
    universe.pointer={x:p.x,y:p.y,startX:p.x,startY:p.y,moved:false};
  });
  canvas.addEventListener("pointermove",e=>{
    if(!universe.pointer)return;
    const p=point(e),v=universe.pointer;
    universe.ox+=p.x-v.x;universe.oy+=p.y-v.y;
    if(Math.hypot(p.x-v.startX,p.y-v.startY)>5)v.moved=true;
    v.x=p.x;v.y=p.y;draw();
  });
  canvas.addEventListener("pointerup",e=>{
    const p=point(e),prev=universe.pointer;universe.pointer=null;
    if(prev&&!prev.moved){const node=hit(p);if(node){state.selected=node.id;renderDetails();draw();}}
  });
  canvas.addEventListener("pointercancel",()=>{universe.pointer=null;});
  canvas.addEventListener("wheel",e=>{
    e.preventDefault();
    const p=point(e),old=universe.scale;
    universe.scale=Math.max(.20,Math.min(3,universe.scale*(e.deltaY<0?1.13:.89)));
    universe.ox=p.x-universe.width/2-(p.x-universe.width/2-universe.ox)*universe.scale/old;
    universe.oy=p.y-universe.height/2-(p.y-universe.height/2-universe.oy)*universe.scale/old;
    draw();
  },{passive:false});
  function renderDetails() {
    const root=$("detail");root.replaceChildren();
    const d=state.datasets.find(x=>x.id===state.selected);
    if(!d){root.append(el("p","Select a public dataset."));return;}
    root.append(el("h3",d.name));
    const details=[
      ["ID",d.id],["Class",d.category],["State",state.mode==="report"?"Indexed report":"Approved reference"],
      ["Records",state.mode==="report"?d.rows:"Not measured"],["Bytes",d.bytes??"Not measured"],
      ["SHA-256",d.sha256??"Not measured"],["Provenance",d.provenance??d.path??"See manifest"],
      ["Fields",Array.isArray(d.fields)?d.fields.slice(0,18).join(", "):"Only after local run"]
    ];
    const dl=el("dl");details.forEach(([key,value])=>dl.append(el("dt",key),el("dd",value)));root.append(dl);
    const link=(typeof d.provenance==="string" && /^https:\/\/github\.com\/sonoxo\//.test(d.provenance))?d.provenance:null;
    if(link){const a=el("a","Open source evidence ↗");a.href=link;a.rel="noopener noreferrer";a.target="_blank";root.append(a);}
    const target=state.lineage.filter(e=>e.source_id===d.id).map(e=>e.target_id);
    if(target.length)root.append(el("p","Declared reference links: "+target.join(", "),"fine"));
  }
  function renderDistribution() {
    const container=$("distribution");container.replaceChildren();
    if(state.mode==="preview"){container.append(el("p","Awaiting a measured local SQLite index report. Nothing is fabricated.","fine"));return;}
    const max=Math.max(1,...state.datasets.map(d=>d.rows||0));
    state.datasets.forEach((d,i)=>{
      const div=el("div",null,"dist-row"),head=el("div",null,"dist-title");
      head.append(el("span",d.name),el("strong",(d.rows||0).toLocaleString()));
      const track=el("div",null,"track"),bar=el("span");bar.style.width=((d.rows||0)/max*100)+"%";bar.style.background=colors[i%colors.length];track.append(bar);div.append(head,track);container.append(div);
    });
  }
  function renderTable() {
    const body=$("table");body.replaceChildren();
    state.datasets.filter(match).forEach(d=>{
      const tr=el("tr");tr.tabIndex=0;tr.setAttribute("role","button");
      const activate=()=>{state.selected=d.id;renderDetails();draw();};
      tr.addEventListener("click",activate);
      tr.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();activate();}});
      tr.append(el("td",d.name),el("td",d.category),el("td",state.mode==="report"?(d.rows||0).toLocaleString():"—"),
        el("td",state.mode==="report"?"Indexed":"Configured"),
        el("td",state.mode==="report"?"SHA-256 verified":"Source manifest"));
      body.append(tr);
    });
  }
  $("search").addEventListener("input",e=>{state.query=e.target.value.trim().toLowerCase();renderTable();draw();});
  $("fit").addEventListener("click",fit);
  $("load").addEventListener("click",()=>$("file").click());
  $("file").addEventListener("change",async e=>{
    const file=e.target.files?.[0];if(!file)return;
    if(file.size>1_000_000){status("Report exceeds the one-megabyte public visualization limit.",true);return;}
    try{load(JSON.parse(await file.text()),"report");}
    catch(error){status("Import rejected: "+error.message,true);}
    finally{e.target.value="";}
  });
  $("reset").addEventListener("click",async()=>{
    try{const r=await fetch("./preview.json",{cache:"no-store"});if(!r.ok)throw Error("Preview HTTP "+r.status);load(await r.json(),"preview");}
    catch(error){status("Could not restore source preview: "+error.message,true);}
  });
  $("export").addEventListener("click",()=>{
    if(state.mode!=="report")return;
    const blob=new Blob([JSON.stringify(state.source,null,2)],{type:"application/json"});
    const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="gpt-doug-dataset-fleet-evidence.json";document.body.append(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  $("copy").addEventListener("click",async()=>{
    try{await navigator.clipboard.writeText($("command").textContent);status("Local dataset fleet command copied.");}
    catch{status("Clipboard unavailable; select and copy the displayed terminal command.",true);}
  });
  roleCards();window.addEventListener("resize",resize);
  if("ResizeObserver" in window)new ResizeObserver(resize).observe($("area"));
  (async()=>{
    try{const r=await fetch("./preview.json",{cache:"no-store"});if(!r.ok)throw Error("Preview HTTP "+r.status);load(await r.json(),"preview");}
    catch(error){status("Could not load public dataset preview: "+error.message,true);}
  })();
})();
