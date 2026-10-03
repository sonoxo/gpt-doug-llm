
(() => {
  "use strict";
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.documentElement.classList.add("motion-ready");

  function enhanceSitebar(){
    const bar=document.querySelector(".xunia-sitebar");
    const nav=bar?.querySelector("nav");
    if(!bar||!nav||bar.querySelector(".xunia-nav-toggle")) return;
    const btn=document.createElement("button");
    btn.type="button";
    btn.className="xunia-nav-toggle";
    btn.setAttribute("aria-expanded","false");
    btn.textContent="MENU";
    bar.insertBefore(btn,nav);
    btn.addEventListener("click",()=>{
      const open=bar.classList.toggle("nav-open");
      btn.setAttribute("aria-expanded",String(open));
      btn.textContent=open?"CLOSE":"MENU";
    });
  }

  function reveal(){
    if(reduce||!("IntersectionObserver" in window)) return;
    const nodes=document.querySelectorAll(".zyra-card,.motion-panel,.overall,.panel,.tile,figure");
    const io=new IntersectionObserver(entries=>{
      entries.forEach(entry=>{
        if(!entry.isIntersecting) return;
        entry.target.animate(
          [{opacity:.08,transform:"translateY(18px) scale(.985)"},{opacity:1,transform:"translateY(0) scale(1)"}],
          {duration:560,easing:"cubic-bezier(.2,.78,.2,1)",fill:"both"}
        );
        io.unobserve(entry.target);
      });
    },{threshold:.08});
    nodes.forEach(n=>io.observe(n));
  }

  function tactile(){
    if(reduce) return;
    document.addEventListener("pointerdown",event=>{
      const hit=event.target.closest("a,button");
      if(!hit) return;
      const pulse=document.createElement("i");
      pulse.className="xunia-motion-pulse";
      pulse.style.left=event.clientX+"px";
      pulse.style.top=event.clientY+"px";
      document.body.appendChild(pulse);
      setTimeout(()=>pulse.remove(),520);
    },{passive:true});
  }

  enhanceSitebar();
  reveal();
  tactile();
})();
