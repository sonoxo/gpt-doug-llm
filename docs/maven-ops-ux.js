(() => {
  "use strict";
  document.body.classList.add("ops-motion-on");
  const rail=document.getElementById("commandRail");
  const railToggle=document.getElementById("opsRailToggle");
  const stateKey="xunia.maven.fold.v2";
  let saved={};
  try{saved=JSON.parse(localStorage.getItem(stateKey)||"{}")}catch{}

  function slug(text,i){return String(text||"panel-"+i).toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,64)||"panel-"+i}

  document.querySelectorAll("#commandRail .card").forEach((card,i)=>{
    const heading=card.querySelector(":scope > h2");
    if(!heading) return;
    const id=slug(heading.textContent,i);
    const defaultOpen=/map control|live xunia ops/i.test(heading.textContent);
    const open=saved[id]===undefined?defaultOpen:saved[id]!==false;

    const inner=document.createElement("div");inner.className="fold-inner";
    const body=document.createElement("div");body.className="fold-body";
    while(heading.nextSibling) inner.appendChild(heading.nextSibling);
    body.appendChild(inner);

    const button=document.createElement("button");
    button.type="button";button.className="fold-head";button.setAttribute("aria-expanded",String(open));
    button.innerHTML='<span class="fold-title"></span><span class="fold-chevron" aria-hidden="true">⌄</span>';
    button.querySelector(".fold-title").textContent=heading.textContent;
    heading.replaceWith(button);card.appendChild(body);
    card.dataset.foldId=id;
    if(!open) card.classList.add("collapsed");

    button.addEventListener("click",()=>{
      const collapsed=card.classList.toggle("collapsed");
      button.setAttribute("aria-expanded",String(!collapsed));
      saved[id]=!collapsed;
      try{localStorage.setItem(stateKey,JSON.stringify(saved))}catch{}
    });
  });

  function setRail(open){
    rail.classList.toggle("open",open);
    railToggle.setAttribute("aria-expanded",String(open));
    railToggle.textContent=open?"✕ CLOSE":"☰ COMMAND";
    try{localStorage.setItem("xunia.maven.commandRail",open?"1":"0")}catch{}
    if(open&&!matchMedia("(prefers-reduced-motion: reduce)").matches){
      rail.animate([{opacity:.35,transform:matchMedia("(max-width:900px)").matches?"translateY(16px)":"translateX(16px)"},{opacity:1,transform:"translate(0,0)"}],{duration:260,easing:"cubic-bezier(.2,.78,.2,1)"});
    }
  }
  let initial=false;
  try{initial=localStorage.getItem("xunia.maven.commandRail")==="1"}catch{}
  setRail(initial);
  railToggle.addEventListener("click",()=>setRail(!rail.classList.contains("open")));
  document.addEventListener("keydown",e=>{
    if(e.key==="Escape"&&rail.classList.contains("open")) setRail(false);
    if((e.key==="c"||e.key==="C")&&!/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName||"")) setRail(!rail.classList.contains("open"));
  });
})();