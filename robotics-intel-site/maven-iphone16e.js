(() => {
  "use strict";
  const root=document.documentElement;
  let raf=0;

  function applyViewport(){
    cancelAnimationFrame(raf);
    raf=requestAnimationFrame(()=>{
      const vv=window.visualViewport;
      const h=vv?vv.height:window.innerHeight;
      root.style.setProperty("--maven-app-h",Math.round(h)+"px");
      root.classList.toggle("iphone-compact",matchMedia("(max-width:430px) and (pointer:coarse)").matches);
      root.classList.toggle("iphone-landscape",matchMedia("(max-height:500px) and (orientation:landscape) and (pointer:coarse)").matches);
    });
  }

  applyViewport();
  addEventListener("resize",applyViewport,{passive:true});
  addEventListener("orientationchange",()=>setTimeout(applyViewport,120),{passive:true});
  visualViewport?.addEventListener("resize",applyViewport,{passive:true});
  visualViewport?.addEventListener("scroll",applyViewport,{passive:true});

  const active=document.querySelector("[data-mobile-pane].active");
  if(!active&&matchMedia("(max-width:900px)").matches){
    document.querySelector('[data-mobile-pane="map"]')?.click();
  }
})();
