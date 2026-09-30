(() => {
  "use strict";
  function ready(fn){
    if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",fn,{once:true});
    else fn();
  }

  ready(()=>{
    document.body.classList.add("clean-ui");
    const header=document.querySelector("header");
    const modebar=document.querySelector(".modebar");
    if(!header||!modebar) return;

    const primaryIds=new Set(["worldGridBtn","tacOpsBtn","roverOpsBtn"]);
    const primaryModes=new Set(["broadcast","palantir"]);
    const panelBtn=document.getElementById("opsRailToggle");

    const secondary=[];
    [...modebar.querySelectorAll(".modebtn")].forEach(btn=>{
      if(btn===panelBtn) return;
      const keep=primaryIds.has(btn.id)||primaryModes.has(btn.dataset.mode||"");
      if(!keep) secondary.push(btn);
    });

    const wrap=document.createElement("div");
    wrap.className="clean-menu-wrap clean-more-wrap";
    const trigger=document.createElement("button");
    trigger.type="button";
    trigger.className="clean-menu-trigger";
    trigger.textContent="MORE";
    trigger.setAttribute("aria-expanded","false");
    const menu=document.createElement("div");
    menu.className="clean-menu";
    menu.setAttribute("role","menu");

    const modeLabel=document.createElement("div");
    modeLabel.className="clean-section-label";
    modeLabel.textContent="More modes";
    menu.appendChild(modeLabel);
    secondary.forEach(btn=>menu.appendChild(btn));

    const statusLabel=document.createElement("div");
    statusLabel.className="clean-section-label";
    statusLabel.textContent="System status";
    menu.appendChild(statusLabel);
    const status=document.createElement("div");
    status.className="clean-status-list";
    [...header.querySelectorAll(":scope > .pill")].forEach(p=>status.appendChild(p));
    menu.appendChild(status);

    wrap.append(trigger,menu);
    if(panelBtn) modebar.insertBefore(wrap,panelBtn);
    else modebar.appendChild(wrap);

    function setOpen(open){
      menu.classList.toggle("open",open);
      trigger.setAttribute("aria-expanded",String(open));
      trigger.textContent=open?"CLOSE":"MORE";
    }
    trigger.addEventListener("click",e=>{e.stopPropagation();setOpen(!menu.classList.contains("open"))});
    menu.addEventListener("click",e=>{
      if(e.target.closest(".modebtn")) setOpen(false);
      e.stopPropagation();
    });
    document.addEventListener("click",()=>setOpen(false));
    document.addEventListener("keydown",e=>{if(e.key==="Escape")setOpen(false)});
  });
})();