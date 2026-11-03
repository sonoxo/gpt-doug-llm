"use strict";
(() => {
  const get = id => document.getElementById(id);
  const canvas = get("graph");
  const ctx = canvas.getContext("2d");
  const graph = {nodes:[], edges:[], zoom:1, ox:0, oy:0, width:0, height:0, pointer:null};
  const state = {data:null, query:"", selected:null, imported:false};
  const colors = ["#63f4e1","#83bafb","#f2cc83","#d1a9ff","#8bdab2","#f0a9af"];
  const status = (message, error=false) => {get("notice").textContent=message;get("notice").classList.toggle("error",error);};
  const textNode = (tag,text,cls) => {
    const node=document.createElement(tag);
    if(text!==undefined)node.textContent=String(text);
    if(cls)node.className=cls;
    return node;
  };
  const isUrl = url => {
    try {
      const u=new URL(url);
      return u.protocol==="https:" && !u.username && !u.password && !u.search && !u.hash && u.hostname!=="" && u.port==="";
    } catch {return false;}
  };
  function validate(snapshot) {
    if(!snapshot || snapshot.schema!=="xunia.open-web-mirror.v1" ||
       !Array.isArray(snapshot.pages) || !Array.isArray(snapshot.edges))throw Error("Not a XUNIA Open Web Mirror JSON archive.");
    if(snapshot.pages.length>500 || snapshot.edges.length>10000)throw Error("Archive exceeds browser safety limits.");
    if(typeof snapshot.allowedHost!=="string" || !/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(snapshot.allowedHost))throw Error("Invalid allowed host.");
    const set=new Set();
    for(const p of snapshot.pages) {
      if(!isUrl(p.url) || new URL(p.url).hostname!==snapshot.allowedHost)throw Error("Page outside allowed host.");
      if(set.has(p.url))throw Error("Duplicate archived page URL.");
      set.add(p.url);
      if(typeof p.title!=="string" || typeof p.text!=="string" || p.text.length>40000)throw Error("Invalid page text.");
    }
    for(const e of snapshot.edges) {
      if(!set.has(e.source)||!set.has(e.target))throw Error("Edge references unknown page.");
    }
    if(!Array.isArray(snapshot.outboundDomains))throw Error("Invalid outbound domains.");
    return snapshot;
  }
  const matches = p => !state.query || [p.url,p.title,p.text].join(" ").toLowerCase().includes(state.query);
  const isCaptured = p => !!p.text.trim() && p.archived!==false && state.data.mode!=="documented-route-preview";
  function metrics() {
    const d=state.data, pages=d.pages;
    get("pageCount").textContent=pages.length;
    get("archivedCount").textContent=pages.filter(isCaptured).length;
    get("linkCount").textContent=d.edges.length;
    get("domainCount").textContent=d.outboundDomains.length;
    get("mode").textContent=state.imported?"Imported archive":"Documented route preview";
    get("date").textContent="Source: "+(d.createdAt||"unknown");
    get("export").disabled=!state.imported;
  }
  function layout() {
    const data=state.data;
    graph.nodes=[];
    const count=data.pages.length;
    data.pages.forEach((page,i)=>{
      const angle=2*Math.PI*i/Math.max(count,1)-Math.PI/2;
      const ring=Math.floor(i/22);
      const radius=count===1?0:220+ring*85;
      graph.nodes.push({url:page.url,x:Math.cos(angle)*radius,y:Math.sin(angle)*radius,color:colors[ring%colors.length],page});
    });
    graph.edges=data.edges;
  }
  function screenXY(node) {return{x:graph.width/2+graph.ox+node.x*graph.zoom,y:graph.height/2+graph.oy+node.y*graph.zoom};}
  function fit() {
    if(!graph.width||!graph.height)return;
    const far=Math.max(310,...graph.nodes.map(n=>Math.hypot(n.x,n.y)+80));
    graph.zoom=Math.min(graph.width/(far*2),graph.height/(far*2))*.87;
    graph.ox=0;graph.oy=0;draw();
  }
  function resize() {
    const rect=canvas.getBoundingClientRect();
    if(rect.width<50||rect.height<50)return;
    graph.width=rect.width;graph.height=rect.height;
    const dpr=Math.min(window.devicePixelRatio||1,2);
    canvas.width=Math.floor(rect.width*dpr);
    canvas.height=Math.floor(rect.height*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
    if(!graph.zoom||graph.zoom===1)fit();else draw();
  }
  function draw() {
    if(!graph.width||!state.data)return;
    ctx.clearRect(0,0,graph.width,graph.height);
    const lookup=new Map(graph.nodes.map(n=>[n.url,n]));
    for(const edge of graph.edges) {
      const a=lookup.get(edge.source),b=lookup.get(edge.target);
      if(!a||!b)continue;
      const pa=screenXY(a),pb=screenXY(b);
      ctx.strokeStyle="#6aa4b24a";ctx.lineWidth=1.2;
      ctx.beginPath();ctx.moveTo(pa.x,pa.y);ctx.lineTo(pb.x,pb.y);ctx.stroke();
    }
    const labelAll=graph.nodes.length<=22;
    for(const n of graph.nodes) {
      const p=screenXY(n),match=matches(n.page),selected=state.selected===n.url;
      const size=(selected?9:6)*Math.max(.8,graph.zoom);
      ctx.globalAlpha=match?1:.16;ctx.fillStyle=isCaptured(n.page)?n.color:"#97adb9";
      ctx.beginPath();ctx.arc(p.x,p.y,size,0,2*Math.PI);ctx.fill();
      if(selected){ctx.lineWidth=2;ctx.strokeStyle="#fff3ab";ctx.stroke();}
      ctx.globalAlpha=1;
      if((labelAll||selected)&&match){
        ctx.fillStyle="#d9ecf3";ctx.font="11px system-ui";ctx.textAlign="center";ctx.textBaseline="top";
        const label=n.page.title.length>23?n.page.title.slice(0,22)+"…":n.page.title;
        ctx.fillText(label,p.x,p.y+11);
      }
    }
  }
  function hit(x,y) {
    for(let i=graph.nodes.length-1;i>=0;i--) {
      const n=graph.nodes[i],p=screenXY(n);
      if(Math.hypot(p.x-x,p.y-y)<Math.max(12,11*graph.zoom))return n;
    }
    return null;
  }
  function point(e){const rect=canvas.getBoundingClientRect();return{x:e.clientX-rect.left,y:e.clientY-rect.top};}
  canvas.addEventListener("pointerdown",e=>{
    const p=point(e);graph.pointer={id:e.pointerId,x:p.x,y:p.y,moved:false};
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener("pointermove",e=>{
    if(!graph.pointer)return;
    const p=point(e),a=graph.pointer;
    graph.ox+=p.x-a.x;graph.oy+=p.y-a.y;
    if(Math.abs(p.x-a.x)+Math.abs(p.y-a.y)>1)a.moved=true;
    a.x=p.x;a.y=p.y;draw();
  });
  canvas.addEventListener("pointerup",e=>{
    const p=point(e),a=graph.pointer;
    graph.pointer=null;
    if(a&&!a.moved){const node=hit(p.x,p.y);if(node)select(node.url);}
  });
  canvas.addEventListener("pointercancel",()=>{graph.pointer=null;});
  canvas.addEventListener("wheel",e=>{
    e.preventDefault();const p=point(e),old=graph.zoom;
    graph.zoom=Math.max(.18,Math.min(3,old*(e.deltaY<0?1.13:.89)));
    graph.ox=(p.x-graph.width/2)-(p.x-graph.width/2-graph.ox)*graph.zoom/old;
    graph.oy=(p.y-graph.height/2)-(p.y-graph.height/2-graph.oy)*graph.zoom/old;
    draw();
  },{passive:false});
  function select(url) {
    state.selected=url;draw();
    const detail=get("detail");detail.replaceChildren();
    const p=state.data.pages.find(x=>x.url===url);
    if(!p){detail.append(textNode("p","Select a page."));return;}
    detail.append(textNode("h3",p.title));
    const dl=textNode("dl");
    for(const [name,value] of [
      ["URL",p.url],["Mode",isCaptured(p)?"Captured text":"Reference only"],
      ["Depth",p.depth??"—"],["Bytes",p.bytes??"Not captured"],["SHA-256",p.sha256??"Not captured"],
      ["Observed",p.observedAt??"Not captured"]
    ]){dl.append(textNode("dt",name),textNode("dd",value));}
    detail.append(dl);
    const a=textNode("a","Open original page ↗");a.href=p.url;a.rel="noopener noreferrer";a.target="_blank";detail.append(a);
    const pre=textNode("pre",isCaptured(p)?p.text:"This route is documented in XUNIA's source, but no page content has been captured yet. Import a crawler-generated JSON snapshot to read its archived text.");
    detail.append(pre);
  }
  function table() {
    const body=get("table");body.replaceChildren();
    const list=state.data.pages.filter(matches);
    get("matching").textContent=list.length+" of "+state.data.pages.length+" pages match";
    const frag=document.createDocumentFragment();
    for(const p of list){
      const tr=textNode("tr");
      tr.tabIndex=0;tr.setAttribute("role","button");
      tr.addEventListener("click",()=>select(p.url));
      tr.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();select(p.url);}});
      tr.append(textNode("td",p.title),textNode("td",p.url),textNode("td",p.text.length+" chars"),textNode("td",p.depth??"—"),textNode("td",isCaptured(p)?"Archived":"Reference"));
      frag.append(tr);
    }
    body.append(frag);
  }
  function domains(){
    const el=get("domains");el.replaceChildren();
    const list=state.data.outboundDomains.slice(0,45);
    if(!list.length){el.append(textNode("p","No outbound domains recorded.","fine"));return;}
    for(const e of list){
      const row=textNode("div",undefined,"domainItem");
      row.append(textNode("span",e.host),textNode("span",e.references??"—"));el.append(row);
    }
  }
  function load(data,imported){
    validate(data);
    state.data=data;state.imported=imported;state.selected=null;state.query="";get("search").value="";
    metrics();layout();table();domains();select(data.pages[0]?.url??null);
    fit();
    status(imported?
      "Local archive loaded: "+data.coverage.pagesStored+" captured text pages. All content stays in your browser; it is not uploaded.":
      "Documented route preview loaded. 0 pages crawled. Use the local crawler and import its output to build a real offline archive.");
  }
  get("search").addEventListener("input",e=>{state.query=e.target.value.toLowerCase().trim();table();draw();});
  get("fit").addEventListener("click",fit);
  get("loadFile").addEventListener("click",()=>get("file").click());
  get("file").addEventListener("change",async e=>{
    const file=e.target.files?.[0];if(!file)return;
    if(file.size>8_000_000){status("Archive too large: import a JSON file under 8 MB.",true);return;}
    try{load(JSON.parse(await file.text()),true);}
    catch(err){status("Could not open archive: "+err.message,true);}
    finally{e.target.value="";}
  });
  get("export").addEventListener("click",()=>{
    if(!state.imported)return;
    const blob=new Blob([JSON.stringify(state.data,null,2)],{type:"application/json"});
    const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="xunia-open-web-archive.json";document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  get("copy").addEventListener("click",async()=>{
    const str=get("command").textContent;
    try{await navigator.clipboard.writeText(str);status("Command copied. Run it in the repository root on a permitted domain, then import the JSON here.");}
    catch{status("Clipboard access unavailable. Select and copy the displayed command manually.",true);}
  });
  window.addEventListener("resize",resize);
  (async()=>{
    try {
      const response=await fetch("./seed-map.json",{cache:"no-store"});
      if(!response.ok)throw Error("Seed map HTTP "+response.status);
      load(await response.json(),false);
    }catch(err){status("Could not load route preview: "+err.message,true);}
  })();
  if("ResizeObserver" in window)new ResizeObserver(resize).observe(get("map"));
})();
