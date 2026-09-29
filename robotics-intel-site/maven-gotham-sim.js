(() => {
  "use strict";
  const bay=document.getElementById("gothamBay");
  const canvas=document.getElementById("gothamCanvas");
  const close=document.getElementById("gothamClose");
  const channelLabel=document.getElementById("gothamChannel");
  const actorCount=document.getElementById("gothamActors");
  const sectorLabel=document.getElementById("gothamSector");
  const tempoLabel=document.getElementById("gothamTempo");
  const signalLabel=document.getElementById("gothamSignal");
  if(!bay||!canvas) return;

  const ctx=canvas.getContext("2d");
  let w=1,h=1,dpr=1,last=performance.now();
  let channel=0;
  let paused=false;
  let cinematic=true;
  const channels=[
    {name:"GOTHAM ALPHA",sector:"NARROWS",tempo:1.00},
    {name:"GOTHAM BRAVO",sector:"MIDTOWN",tempo:.78},
    {name:"GOTHAM ROOFTOP",sector:"CROWN",tempo:.55},
    {name:"GOTHAM STREETCAM",sector:"DOCKS",tempo:.92}
  ];
  const actors=Array.from({length:14},(_,i)=>({
    id:"G-"+String(i+1).padStart(2,"0"),
    x:.12+(i%5)*.17,
    y:.28+Math.floor(i/5)*.2,
    vx:(i%2?1:-1)*(.018+(i%3)*.004),
    vy:((i%3)-1)*.006,
    phase:i*.71,
    team:i%2===0?"A":"B"
  }));

  function resize(){
    const r=canvas.getBoundingClientRect();
    dpr=Math.min(devicePixelRatio||1,1.6);
    w=Math.max(1,r.width);h=Math.max(1,r.height);
    canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  new ResizeObserver(resize).observe(canvas);

  function setChannel(i){
    channel=(i+channels.length)%channels.length;
    const c=channels[channel];
    channelLabel.textContent=c.name;
    sectorLabel.textContent=c.sector;
    tempoLabel.textContent=(c.tempo*100).toFixed(0)+"%";
    document.querySelectorAll("[data-gotham-channel]").forEach((b,n)=>b.classList.toggle("active",n===channel));
  }

  function open(){
    bay.classList.add("active");
    resize();
  }
  function hide(){bay.classList.remove("active")}

  function update(dt){
    if(paused) return;
    const c=channels[channel];
    for(const a of actors){
      a.x+=a.vx*c.tempo*dt/1000;
      a.y+=a.vy*c.tempo*dt/1000;
      if(a.x<.06||a.x>.94) a.vx*=-1;
      if(a.y<.18||a.y>.88) a.vy*=-1;
    }
  }

  function draw(ts){
    ctx.clearRect(0,0,w,h);
    const c=channels[channel];

    ctx.fillStyle="#020604";ctx.fillRect(0,0,w,h);
    ctx.strokeStyle="rgba(124,231,255,.07)";ctx.lineWidth=1;
    for(let x=0;x<w;x+=38){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke()}
    for(let y=0;y<h;y+=38){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}

    ctx.strokeStyle="rgba(156,255,170,.08)";
    for(let i=0;i<7;i++){
      ctx.beginPath();
      ctx.moveTo(0,h*(.15+i*.12));
      ctx.lineTo(w,h*(.09+i*.13));
      ctx.stroke();
    }

    if(cinematic){
      ctx.fillStyle="rgba(130,232,255,.025)";
      const sweep=((ts*.04)%(w+120))-120;
      ctx.fillRect(sweep,0,120,h);
    }

    for(const a of actors){
      const x=a.x*w,y=a.y*h;
      const bob=Math.sin(ts*.004+a.phase)*2;
      ctx.save();
      ctx.translate(x,y+bob);
      ctx.strokeStyle=a.team==="A"?"#9cffaa":"#82e8ff";
      ctx.fillStyle=a.team==="A"?"rgba(156,255,170,.13)":"rgba(130,232,255,.13)";
      ctx.lineWidth=1.2;
      ctx.beginPath();ctx.arc(0,-7,3.2,0,Math.PI*2);ctx.fill();ctx.stroke();
      ctx.beginPath();ctx.moveTo(0,-3);ctx.lineTo(0,8);ctx.moveTo(0,1);ctx.lineTo(-5,5);ctx.moveTo(0,1);ctx.lineTo(5,5);ctx.moveTo(0,8);ctx.lineTo(-4,14);ctx.moveTo(0,8);ctx.lineTo(4,14);ctx.stroke();
      ctx.strokeStyle="rgba(255,209,102,.38)";
      ctx.strokeRect(-9,-15,18,31);
      ctx.fillStyle="#96aa9b";ctx.font="7px monospace";ctx.fillText(a.id,11,-8);
      ctx.restore();
    }

    ctx.strokeStyle="rgba(255,177,29,.35)";
    ctx.beginPath();ctx.moveTo(w*.5-22,h*.5);ctx.lineTo(w*.5+22,h*.5);ctx.moveTo(w*.5,h*.5-22);ctx.lineTo(w*.5,h*.5+22);ctx.stroke();

    actorCount.textContent=String(actors.length);
    signalLabel.textContent=paused?"HOLD":"SIM LIVE";
  }

  function frame(ts){
    const dt=Math.min(40,ts-last);last=ts;
    update(dt);draw(ts);
    requestAnimationFrame(frame);
  }

  document.querySelectorAll("[data-gotham-channel]").forEach((b,i)=>b.addEventListener("click",()=>setChannel(i)));
  document.getElementById("gothamPrev")?.addEventListener("click",()=>setChannel(channel-1));
  document.getElementById("gothamNext")?.addEventListener("click",()=>setChannel(channel+1));
  document.getElementById("gothamPause")?.addEventListener("click",e=>{paused=!paused;e.currentTarget.textContent=paused?"RESUME":"HOLD";e.currentTarget.classList.toggle("active",paused)});
  document.getElementById("gothamCine")?.addEventListener("click",e=>{cinematic=!cinematic;e.currentTarget.classList.toggle("active",cinematic)});
  close?.addEventListener("click",hide);

  document.addEventListener("maven:gotham-open",open);
  window.addEventListener("message",evt=>{
    if(!["https://xunia.org","https://www.xunia.org"].includes(evt.origin)) return;
    if(evt.data?.type==="maven-ui"&&evt.data.action==="open-gotham") open();
  });

  setChannel(0);resize();requestAnimationFrame(frame);
})();