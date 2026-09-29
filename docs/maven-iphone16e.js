(() => {
  "use strict";
  const root=document.documentElement;
  const header=document.querySelector("header");
  let raf=0;

  function applyViewport(){
    cancelAnimationFrame(raf);
    raf=requestAnimationFrame(()=>{
      const vv=window.visualViewport;
      const h=vv?vv.height:window.innerHeight;
      root.style.setProperty("--maven-app-h",Math.round(h)+"px");
      if(header) root.style.setProperty("--maven-header-h",Math.ceil(header.getBoundingClientRect().height)+"px");
      root.classList.toggle("iphone-compact",matchMedia("(max-width:430px) and (pointer:coarse)").matches);
      root.classList.toggle("iphone-landscape",matchMedia("(max-height:500px) and (orientation:landscape) and (pointer:coarse)").matches);
    });
  }

  applyViewport();
  addEventListener("resize",applyViewport,{passive:true});
  addEventListener("orientationchange",()=>setTimeout(applyViewport,120),{passive:true});
  visualViewport?.addEventListener("resize",applyViewport,{passive:true});
  visualViewport?.addEventListener("scroll",applyViewport,{passive:true});

  document.querySelectorAll("button,a").forEach(el=>{
    el.addEventListener("touchstart",()=>{}, {passive:true});
  });
})();