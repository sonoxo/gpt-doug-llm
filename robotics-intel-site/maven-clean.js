(() => {
  "use strict";
  const ready=fn=>document.readyState==="loading"?document.addEventListener("DOMContentLoaded",fn,{once:true}):fn();
  ready(()=>{
    document.body.classList.add("clean-child");
    const top=document.querySelector(".top");
    if(!top) return;

    const keepIds=new Set(["opsChip","liveBusChip","palBroadcastChip"]);
    const movable=[...top.querySelectorAll(":scope > span.chip")].filter(x=>!keepIds.has(x.id));
    if(!movable.length) return;

    const wrap=document.createElement("div");
    wrap.className="clean-child-status-wrap";
    const trigger=document.createElement("button");
    trigger.type="button";
    trigger.className="clean-child-status-trigger";
    trigger.textContent="STATUS";
    trigger.setAttribute("aria-expanded","false");
    const menu=document.createElement("div");
    menu.className="clean-child-status";
    movable.forEach(x=>menu.appendChild(x));
    wrap.append(trigger,menu);

    const media=document.getElementById("mediaToggle");
    if(media) top.insertBefore(wrap,media);
    else top.appendChild(wrap);

    const setOpen=open=>{
      menu.classList.toggle("open",open);
      trigger.setAttribute("aria-expanded",String(open));
      trigger.textContent=open?"CLOSE":"STATUS";
    };
    trigger.addEventListener("click",e=>{e.stopPropagation();setOpen(!menu.classList.contains("open"))});
    menu.addEventListener("click",e=>e.stopPropagation());
    document.addEventListener("click",()=>setOpen(false));
    document.addEventListener("keydown",e=>{if(e.key==="Escape")setOpen(false)});
  });
})();
