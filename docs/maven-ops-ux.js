(() => {
  "use strict";
  document.body.classList.add("ops-motion-on");
  const rail=document.getElementById("commandRail");
  const railToggle=document.getElementById("opsRailToggle");
  const stateKey="xunia.maven.fold.v3";\n  const railClose=document.getElementById("commandRailClose");\n  const railScrim=document.getElementById("railScrim");\n  const railCollapseAll=document.getElementById("railCollapseAll");

  if(rail && !document.getElementById("palantirBridgeCard")){
    const card=document.createElement("div");
    card.className="card";
    card.id="palantirBridgeCard";
    card.innerHTML=`
      <h2>PALANTIR FOUNDRY BRIDGE</h2>
      <div class="metric"><span>MODE</span><b id="palMode">CHECKING</b></div>
      <div class="metric"><span>CONNECTED</span><b id="palConnected">—</b></div>
      <div class="metric"><span>ONTOLOGY</span><b id="palOntology">—</b></div>
      <div class="metric"><span>OBJECT TYPES</span><b id="palObjects">—</b></div>
      <div class="metric"><span>ACTION TYPES</span><b id="palActions">—</b></div>
      <div class="feed" id="palNote">Server-side Foundry bridge. Credentials remain outside the browser.</div>
    `;
    const firstCard=rail.querySelector(".card");
    if(firstCard) firstCard.insertAdjacentElement("afterend",card);
    else rail.appendChild(card);

    const refreshPalantir=async()=>{
      try{
        const res=await fetch("https://xunia-palantir-bridge.onrender.com/api/status",{cache:"no-store"});
        if(!res.ok) throw new Error("HTTP "+res.status);
        const d=await res.json();
        card.querySelector("#palMode").textContent=d.mode||"UNKNOWN";
        card.querySelector("#palConnected").textContent=d.connected?"YES":"NO";
        card.querySelector("#palOntology").textContent=d.ontology_bound?"BOUND":d.configured?"NOT FOUND":"WAITING FOR TENANT";
        card.querySelector("#palObjects").textContent=d.object_type_count??"—";
        card.querySelector("#palActions").textContent=d.action_type_count??"—";
        card.querySelector("#palNote").textContent=d.connected
          ?"Foundry OAuth connected. Only aggregate schema health is shown here."
          :"Bridge is online; bind your Foundry hostname, client ID, client secret, and ontology in the Render service environment.";
      }catch(err){
        card.querySelector("#palMode").textContent="BRIDGE WARMING";
        card.querySelector("#palConnected").textContent="NO";
        card.querySelector("#palNote").textContent="Bridge unavailable or warming: "+err.message;
      }
    };
    refreshPalantir();
    setInterval(refreshPalantir,60000);
  }
  let saved={};
  try{saved=JSON.parse(localStorage.getItem(stateKey)||"{}")}catch{}

  function slug(text,i){return String(text||"panel-"+i).toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,64)||"panel-"+i}

  document.querySelectorAll("#commandRail .card").forEach((card,i)=>{
    const heading=card.querySelector(":scope > h2");
    if(!heading) return;
    const id=slug(heading.textContent,i);
    const defaultOpen=/map control/i.test(heading.textContent);
    const open=saved[id]===undefined?defaultOpen:saved[id]!==false;

    const inner=document.createElement("div");inner.className="fold-inner";
    const body=document.createElement("div");body.className="fold-body";
    while(heading.nextSibling) inner.appendChild(heading.nextSibling);
    body.appendChild(inner);

    const button=document.createElement("button");
    button.type="button";button.className="fold-head";button.setAttribute("aria-expanded",String(open));
    button.innerHTML='<span class="fold-title"></span><span class="fold-side"><span class="fold-action"></span><span class="fold-chevron" aria-hidden="true">⌄</span></span>';
    button.querySelector(".fold-title").textContent=heading.textContent;
    button.querySelector(".fold-action").textContent=open?"CLOSE":"OPEN";
    heading.replaceWith(button);card.appendChild(body);
    card.dataset.foldId=id;
    if(!open) card.classList.add("collapsed");

    button.addEventListener("click",()=>{
      const collapsed=card.classList.toggle("collapsed");
      button.setAttribute("aria-expanded",String(!collapsed));
      button.querySelector(".fold-action").textContent=collapsed?"OPEN":"CLOSE";
      saved[id]=!collapsed;
      try{localStorage.setItem(stateKey,JSON.stringify(saved))}catch{}
    });
  });

  function setRail(open){
    if(!rail||!railToggle) return;
    rail.classList.toggle("open",open);
    document.body.classList.toggle("rail-open",open);
    rail.setAttribute("aria-hidden",String(!open));
    railToggle.setAttribute("aria-expanded",String(open));
    railToggle.textContent=open?"✕ PANEL":"☰ PANEL";
    railScrim?.classList.toggle("open",open);
    if(open){
      requestAnimationFrame(()=>railClose?.focus({preventScroll:true}));
    }else if(document.activeElement===railClose){
      railToggle.focus({preventScroll:true});
    }
  }

  const initial=new URLSearchParams(location.search).get("panel")==="open";
  setRail(initial);
  railToggle?.addEventListener("click",()=>setRail(!rail.classList.contains("open")));
  railClose?.addEventListener("click",()=>setRail(false));
  railScrim?.addEventListener("click",()=>setRail(false));
  railCollapseAll?.addEventListener("click",()=>{
    document.querySelectorAll("#commandRail .card").forEach(card=>{
      card.classList.add("collapsed");
      const button=card.querySelector(".fold-head");
      button?.setAttribute("aria-expanded","false");
      const action=button?.querySelector(".fold-action");
      if(action) action.textContent="OPEN";
      const id=card.dataset.foldId;
      if(id) saved[id]=false;
    });
    try{localStorage.setItem(stateKey,JSON.stringify(saved))}catch{}
  });

  document.addEventListener("keydown",e=>{
    if(e.key==="Escape"&&rail.classList.contains("open")) setRail(false);
    if((e.key==="c"||e.key==="C")&&!/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName||"")) setRail(!rail.classList.contains("open"));
  });
})();
