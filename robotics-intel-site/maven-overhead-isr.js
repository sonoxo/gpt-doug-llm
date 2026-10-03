(() => {
  "use strict";
  const canvas=document.getElementById("overheadCanvas");
  const logEl=document.getElementById("overheadLog");
  if(!canvas||!logEl) return;
  const ctx=canvas.getContext("2d");
  let w=1,h=1,dpr=1,last=performance.now(),mode="eo",zoom=1.0,panX=0,panY=0;
  let sweeping=true;

  const syntheticActors=Array.from({length:16},(_,i)=>({
    x:.08+((i*.173)%0.84),y:.12+((i*.227)%0.76),vx:((i%2)?1:-1)*(.010+(i%4)*.003),vy:((i%3)-1)*.004,phase:i*.63
  }));

  function resize(){
    const r=canvas.getBoundingClientRect();
    dpr=Math.min(devicePixelRatio||1,1.6);
    w=Math.max(1,r.width);h=Math.max(1,r.height);
    canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  new ResizeObserver(resize).observe(canvas);

  function log(msg){
    const row=document.createElement("div");
    row.textContent="["+new Date().toLocaleTimeString()+"] "+msg;
    logEl.prepend(row);
    while(logEl.children.length>24) logEl.removeChild(logEl.lastChild);
  }

  function setMode(next){
    mode=next;
    const label=next==="eo"?"EO DAY":next==="ir"?"IR SYNTH":"PUBLIC SAT";
    document.getElementById("sensorMode").textContent=label;
    const hud=document.getElementById("sensorModeHud"); if(hud) hud.textContent=label;
    document.querySelectorAll("[data-overhead-mode]").forEach(b=>b.classList.toggle("active",b.dataset.overheadMode===next));
    log("Overhead mode set to "+next.toUpperCase()+" (simulation/public context only)");
  }

  function update(dt){
    for(const a of syntheticActors){
      a.x+=a.vx*dt/1000;a.y+=a.vy*dt/1000;
      if(a.x<.04||a.x>.96)a.vx*=-1;
      if(a.y<.08||a.y>.92)a.vy*=-1;
    }
  }

  function drawTerrain(){
    ctx.save();
    ctx.translate(w/2+panX,h/2+panY);
    ctx.scale(zoom,zoom);
    ctx.translate(-w/2,-h/2);

    ctx.fillStyle=mode==="ir"?"#020302":"#061007";
    ctx.fillRect(0,0,w,h);

    for(let i=0;i<22;i++){
      const x=((i*97)%Math.max(1,w));
      const y=((i*61)%Math.max(1,h));
      const rw=40+((i*17)%120),rh=22+((i*11)%70);
      ctx.fillStyle=mode==="ir"?"rgba(220,255,220,.05)":"rgba(41,83,49,.32)";
      ctx.fillRect(x,y,rw,rh);
    }

    ctx.strokeStyle=mode==="ir"?"rgba(220,255,220,.12)":"rgba(130,232,255,.08)";
    for(let i=0;i<10;i++){
      ctx.beginPath();
      ctx.moveTo(0,h*(i/10));
      ctx.bezierCurveTo(w*.25,h*((i+1)%10)/10,w*.65,h*((i+2)%10)/10,w,h*((i+3)%10)/10);
      ctx.stroke();
    }

    for(let i=0;i<syntheticActors.length;i++){
      const a=syntheticActors[i],x=a.x*w,y=a.y*h;
      if(mode==="ir"){
        ctx.fillStyle="rgba(220,255,220,.80)";
        ctx.beginPath();ctx.arc(x,y,3.5,0,Math.PI*2);ctx.fill();
      }else{
        ctx.strokeStyle="rgba(156,255,170,.65)";
        ctx.strokeRect(x-4,y-4,8,8);
      }
      ctx.fillStyle=mode==="ir"?"rgba(220,255,220,.9)":"#9cffaa";
      ctx.font="7px monospace";
      ctx.fillText("SIM-"+String(i+1).padStart(2,"0"),x+7,y-6);
    }

    ctx.restore();
  }

  function draw(ts){
    ctx.clearRect(0,0,w,h);
    drawTerrain();

    if(sweeping){
      ctx.strokeStyle="rgba(130,232,255,.28)";
      const x=(ts*.08)%w;
      ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();
    }

    document.getElementById("zoomValue").textContent=zoom.toFixed(1)+"x";
    document.getElementById("actorCount").textContent=String(syntheticActors.length);
  }

  function frame(ts){
    const dt=Math.min(40,ts-last);last=ts;
    update(dt);draw(ts);requestAnimationFrame(frame);
  }

  document.querySelectorAll("[data-overhead-mode]").forEach(b=>b.addEventListener("click",()=>setMode(b.dataset.overheadMode)));
  document.getElementById("zoomIn")?.addEventListener("click",()=>{zoom=Math.min(2.8,zoom+.2);log("Synthetic camera zoom increased")});
  document.getElementById("zoomOut")?.addEventListener("click",()=>{zoom=Math.max(.7,zoom-.2);log("Synthetic camera zoom decreased")});
  document.getElementById("recenter")?.addEventListener("click",()=>{zoom=1;panX=0;panY=0;log("Overhead viewport recentered")});
  document.getElementById("toggleSweep")?.addEventListener("click",e=>{sweeping=!sweeping;e.currentTarget.classList.toggle("active",sweeping);log("Synthetic scan "+(sweeping?"enabled":"disabled"))});

  resize();setMode("eo");requestAnimationFrame(frame);
})();
