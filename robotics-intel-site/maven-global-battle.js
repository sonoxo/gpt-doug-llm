(() => {
  "use strict";
  const canvas=document.getElementById("globalBattleCanvas");
  const logEl=document.getElementById("globalBattleLog");
  if(!canvas||!logEl) return;

  const ctx=canvas.getContext("2d");
  let w=1,h=1,dpr=1,last=performance.now();
  let stance="defense";
  const layers={land:true,air:true,sea:true};
  const effects=[];

  const units=[];
  for(let i=0;i<18;i++){
    const domain=i%3===0?"air":i%3===1?"sea":"land";
    units.push({
      id:(domain==="land"?"L":domain==="air"?"A":"S")+"-"+String(i+1).padStart(2,"0"),
      domain,
      x:.08+((i*0.137)%0.84),
      y:.16+((i*0.217)%0.68),
      vx:((i%2)?1:-1)*(.010+(i%5)*.002),
      vy:((i%3)-1)*.003,
      team:i%2===0?"BLUE":"AMBER",
      phase:i*.77
    });
  }

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
    while(logEl.children.length>26) logEl.removeChild(logEl.lastChild);
  }

  function setStance(next){
    stance=next;
    document.getElementById("battleStance").textContent=next.toUpperCase()+" SIM";
    document.querySelectorAll("[data-stance]").forEach(b=>b.classList.toggle("active",b.dataset.stance===next));
    log("Global "+next+" simulation posture enabled");
  }

  function setLayer(domain){
    layers[domain]=!layers[domain];
    document.querySelector('[data-domain="'+domain+'"]')?.classList.toggle("active",layers[domain]);
    log(domain.toUpperCase()+" domain "+(layers[domain]?"enabled":"hidden"));
  }

  function addEffect(type){
    effects.push({type,start:performance.now(),duration:type==="fortify"?6500:type==="advance"?5000:4200});
    log(type.replaceAll("-"," ").toUpperCase()+" effect deployed in synthetic space");
  }

  function worldToXY(lon,lat){
    return [(lon+180)/360*w,(90-lat)/180*h];
  }

  function drawWorld(){
    ctx.fillStyle="#020604";ctx.fillRect(0,0,w,h);
    ctx.strokeStyle="rgba(130,232,255,.045)";
    ctx.lineWidth=1;
    for(let lon=-180;lon<=180;lon+=30){
      const [x]=worldToXY(lon,0);
      ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();
    }
    for(let lat=-60;lat<=60;lat+=30){
      const [,y]=worldToXY(0,lat);
      ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();
    }

    ctx.fillStyle="rgba(26,57,35,.78)";
    const blobs=[
      [[-168,72],[-52,72],[-48,16],[-97,8],[-130,20]],
      [[-82,13],[-34,13],[-36,-56],[-74,-55],[-82,-5]],
      [[-18,72],[160,72],[174,8],[124,-10],[70,7],[18,34]],
      [[-20,35],[52,35],[48,-35],[15,-35],[-12,-5]],
      [[110,-10],[155,-10],[155,-45],[112,-45]]
    ];
    for(const poly of blobs){
      ctx.beginPath();
      poly.forEach(([lon,lat],i)=>{const [x,y]=worldToXY(lon,lat);i?ctx.lineTo(x,y):ctx.moveTo(x,y)});
      ctx.closePath();ctx.fill();
    }
  }

  function drawUnit(u,ts){
    if(!layers[u.domain]) return;
    const x=u.x*w,y=u.y*h;
    const color=u.domain==="land"?"#9cffaa":u.domain==="air"?"#82e8ff":"#c8a4ff";
    ctx.save();ctx.translate(x,y);
    ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=1.25;
    if(u.domain==="land"){
      ctx.strokeRect(-5,-4,10,8);ctx.beginPath();ctx.moveTo(-7,5);ctx.lineTo(7,5);ctx.stroke();
    }else if(u.domain==="air"){
      ctx.beginPath();ctx.moveTo(-8,0);ctx.lineTo(8,0);ctx.moveTo(0,-6);ctx.lineTo(3,5);ctx.stroke();
    }else{
      ctx.beginPath();ctx.moveTo(-8,3);ctx.lineTo(7,3);ctx.lineTo(3,7);ctx.lineTo(-5,7);ctx.closePath();ctx.stroke();
    }
    ctx.font="7px monospace";ctx.fillText(u.id,9,-6);
    ctx.restore();
  }

  function update(dt){
    const pace=stance==="offense"?1.25:.72;
    for(const u of units){
      u.x+=u.vx*pace*dt/1000;
      u.y+=u.vy*pace*dt/1000;
      if(u.x<.03||u.x>.97)u.vx*=-1;
      if(u.y<.08||u.y>.92)u.vy*=-1;
    }
    const now=performance.now();
    for(let i=effects.length-1;i>=0;i--) if(now-effects[i].start>effects[i].duration) effects.splice(i,1);
  }

  function drawEffects(ts){
    for(const e of effects){
      const p=Math.min(1,(ts-e.start)/e.duration);
      if(e.type==="fortify"){
        ctx.strokeStyle="rgba(156,255,170,"+(1-p)+")";ctx.lineWidth=2;
        for(let i=0;i<4;i++){ctx.beginPath();ctx.arc(w*(.2+i*.2),h*.5,28+Math.sin(ts*.004+i)*5,0,Math.PI*2);ctx.stroke()}
      }else if(e.type==="intercept"){
        ctx.strokeStyle="rgba(130,232,255,"+(1-p)+")";
        for(let i=0;i<8;i++){ctx.beginPath();ctx.moveTo(w*.5,h*.5);ctx.lineTo((i/7)*w,(i%2?0:h));ctx.stroke()}
      }else if(e.type==="decoy"){
        ctx.fillStyle="rgba(130,232,255,"+(1-p)+")";
        for(let i=0;i<18;i++){const a=i*.7+ts*.001;ctx.beginPath();ctx.arc(w*.5+Math.cos(a)*w*.28,h*.5+Math.sin(a)*h*.24,2,0,Math.PI*2);ctx.fill()}
      }else if(e.type==="repair"){
        ctx.fillStyle="rgba(156,255,170,"+(1-p)*.1+")";ctx.fillRect(0,0,w,h);
      }else if(e.type==="advance"){
        ctx.strokeStyle="rgba(255,177,29,"+(1-p)+")";ctx.lineWidth=2;
        for(let i=0;i<6;i++){const y=h*(.18+i*.12);ctx.beginPath();ctx.moveTo(w*.1,y);ctx.lineTo(w*(.1+.75*p),y);ctx.stroke()}
      }else if(e.type==="flank"){
        ctx.strokeStyle="rgba(255,177,29,"+(1-p)+")";
        ctx.beginPath();ctx.arc(w*.5,h*.5,p*Math.min(w,h)*.62,Math.PI*.15,Math.PI*1.4);ctx.stroke();
      }else if(e.type==="pressure"){
        ctx.strokeStyle="rgba(255,140,90,"+(1-p)+")";
        ctx.beginPath();ctx.arc(w*.5,h*.5,p*Math.min(w,h)*.68,0,Math.PI*2);ctx.stroke();
      }else if(e.type==="breakthrough"){
        ctx.strokeStyle="rgba(255,209,102,"+(1-p)+")";ctx.lineWidth=3;
        ctx.beginPath();ctx.moveTo(w*.15,h*.78);ctx.lineTo(w*(.15+.7*p),h*.22);ctx.stroke();
      }
    }
  }

  function frame(ts){
    const dt=Math.min(40,ts-last);last=ts;
    drawWorld();update(dt);drawEffects(ts);
    units.forEach(u=>drawUnit(u,ts));
    requestAnimationFrame(frame);
  }

  document.querySelectorAll("[data-stance]").forEach(b=>b.addEventListener("click",()=>setStance(b.dataset.stance)));
  document.querySelectorAll("[data-domain]").forEach(b=>b.addEventListener("click",()=>setLayer(b.dataset.domain)));
  document.querySelectorAll("[data-action]").forEach(b=>b.addEventListener("click",()=>addEffect(b.dataset.action)));

  document.getElementById("landCount").textContent=String(units.filter(u=>u.domain==="land").length);
  document.getElementById("airCount").textContent=String(units.filter(u=>u.domain==="air").length);
  document.getElementById("seaCount").textContent=String(units.filter(u=>u.domain==="sea").length);
  resize();setStance("defense");requestAnimationFrame(frame);
})();