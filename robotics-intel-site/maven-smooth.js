(() => {
  "use strict";
  const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;

  if(!reduce){
    document.querySelectorAll(".panel").forEach((panel,index)=>{
      panel.animate(
        [
          {opacity:.01,transform:"translate3d(0,10px,0) scale(.995)"},
          {opacity:1,transform:"translate3d(0,0,0) scale(1)"}
        ],
        {duration:360+index*55,easing:"cubic-bezier(.16,1,.3,1)",fill:"both"}
      );
    });
    document.querySelector(".tactical-strip")?.animate(
      [{opacity:0,transform:"translateY(-6px)"},{opacity:1,transform:"translateY(0)"}],
      {duration:420,easing:"cubic-bezier(.16,1,.3,1)",fill:"both"}
    );
  }

  document.querySelectorAll(".panel-focus").forEach(button=>{
    if(button.dataset.smoothBound==="1") return;
    button.dataset.smoothBound="1";
    button.addEventListener("pointerdown",()=>{
      if(reduce) return;
      button.animate(
        [{transform:"scale(1)"},{transform:"scale(.97)"},{transform:"scale(1)"}],
        {duration:180,easing:"ease-out"}
      );
    });
  });
})();
