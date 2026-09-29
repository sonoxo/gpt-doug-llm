(() => {
  "use strict";
  const bay=document.getElementById("droneBay");
  const canvas=document.getElementById("droneCanvas");
  const toggle=document.getElementById("droneViewToggle");
  if(!bay||!canvas||!toggle) return;

  const simPanel=bay.closest(".sim");
  const ctx=canvas.getContext("2d",{alpha:true});
  const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
  const modeEl=document.getElementById("droneMode");
  const fleetEl=document.getElementById("droneFleet");
  const altEl=document.getElementById("droneAlt");
  const speedEl=document.getElementById("droneSpeed");
  const batteryEl=document.getElementById("droneBattery");
  let mode="GROUND";
  let cockpit=false;
  let t0=performance.now();
  let last=performance.now();
  let dpr=1,w=1,h=1;

  const drones=Array.from({length:4},(_,i)=>({
    id:"SIM-DRONE-"+(i+1),
    x:.34+i*.1,
    y:.64+(i%2)*.06,
    z:0,
    heading:-Math.PI/2,
    speed:0,
    battery:100-i*3,
    phase:i*Math.PI*.5,
    homeX:.34+i*.1,
    homeY:.72
  }));

  function setOpen(open){
    bay.hidden=!open;
    simPanel?.classList.toggle("drone-open",open);
    toggle.classList.toggle("active",open);
    toggle.textContent=open?"DRONE VIEW ON":"DRONE VIEW";
    if(open) resize();
  }

  function resize(){
    const r=canvas.getBoundingClientRect();
    dpr=Math.min(devicePixelRatio||1,1.6);
    w=Math.max(1,r.width);
    h=Math.max(1,r.height);
    canvas.width=Math.round(w*dpr);
    canvas.height=Math.round(h*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  new ResizeObserver(resize).observe(canvas);

  function setMode(next){
    mode=next;
    modeEl.textContent=next;
    document.querySelectorAll("[data-drone-mode]").forEach(btn=>btn.classList.toggle("active",btn.dataset.droneMode===next));
  }

  function average(key){
    return drones.reduce((s,d)=>s+d[key],0)/drones.length;
  }

  function update(dt,ts){
    const sec=ts*.001;
    for(let i=0;i<drones.length;i++){
      const d=drones[i];
      if(mode==="TAKEOFF"){
        d.z=Math.min(1,d.z+dt*.00055);
        d.speed=12+d.z*10;
        if(d.z>.98) setMode("FORMATION");
      }else if(mode==="LAND"){
        d.z=Math.max(0,d.z-dt*.00055);
        d.speed=Math.max(0,d.speed-dt*.02);
        d.x+=(d.homeX-d.x)*Math.min(.035,dt*.0012);
        d.y+=(d.homeY-d.y)*Math.min(.035,dt*.0012);
        if(d.z<.02){d.z=0;d.speed=0}
      }else if(mode==="ORBIT"&&d.z>.05){
        const radius=.18+i*.018;
        const a=sec*.42+i*Math.PI*.5;
        d.x=.5+Math.cos(a)*radius;
        d.y=.52+Math.sin(a)*radius*.52;
        d.heading=a+Math.PI/2;
        d.speed=24+i*1.8;
      }else if(mode==="FORMATION"&&d.z>.05){
        const baseX=.5+Math.sin(sec*.32)*.12;
        const baseY=.52+Math.cos(sec*.21)*.04;
        const offsets=[[-.08,.04],[-.027,-.025],[.027,-.025],[.08,.04]];
        d.x=baseX+offsets[i][0];
        d.y=baseY+offsets[i][1];
        d.heading=-Math.PI/2+Math.sin(sec*.35)*.16;
        d.speed=20+Math.sin(sec*.5+i)*2;
      }else if(mode==="HOME"&&d.z>.05){
        d.x+=(d.homeX-d.x)*Math.min(.028,dt*.0011);
        d.y+=(d.homeY-.12-d.y)*Math.min(.028,dt*.0011);
        d.speed=16;
      }else if(mode==="GROUND"){
        d.z=0;d.speed=0;
      }

      if(d.z>0){
        d.battery=Math.max(12,d.battery-dt*.000045);
        const bob=Math.sin(sec*4+d.phase)*.0015;
        d.y+=reduce?0:bob;
      }
    }

    if(mode==="HOME"&&drones.every(d=>Math.abs(d.x-d.homeX)<.015&&Math.abs(d.y-(d.homeY-.12))<.015)){
      setMode("FORMATION");
    }
  }

  function project(d){
    const altitude=18+d.z*48;
    const scale=.55+d.z*.55;
    return {x:d.x*w,y:d.y*h-altitude*.45,scale,shadowY:d.y*h+10};
  }

  function drawDrone(d,p,ts,selected=false){
    const s=11*p.scale;
    const rotor=4.8*p.scale;
    const spin=ts*.025+d.phase;
    ctx.save();
    ctx.translate(p.x,p.y);
    ctx.rotate(d.heading+Math.PI/2);
    ctx.strokeStyle=selected?"#ffd166":"#82e8ff";
    ctx.fillStyle="rgba(130,232,255,.10)";
    ctx.lineWidth=1.5;
    ctx.beginPath();
    ctx.moveTo(-s,0);ctx.lineTo(s,0);
    ctx.moveTo(0,-s);ctx.lineTo(0,s);
    ctx.stroke();
    const pts=[[-s,-s],[s,-s],[-s,s],[s,s]];
    for(const [rx,ry] of pts){
      ctx.beginPath();
      ctx.arc(rx*.62,ry*.62,rotor*(1+.1*Math.sin(spin+rx)),0,Math.PI*2);
      ctx.stroke();
    }
    ctx.fillStyle=selected?"#ffd166":"#9cffaa";
    ctx.fillRect(-3*p.scale,-3*p.scale,6*p.scale,6*p.scale);
    ctx.restore();

    ctx.fillStyle="rgba(0,0,0,.25)";
    ctx.beginPath();
    ctx.ellipse(p.x,p.shadowY,10*p.scale,4*p.scale,0,0,Math.PI*2);
    ctx.fill();

    ctx.fillStyle=selected?"#ffd166":"#9eb4a4";
    ctx.font="7px monospace";
    ctx.fillText(d.id,p.x+10,p.y-8);
  }

  function drawWorld(ts){
    ctx.clearRect(0,0,w,h);
    const horizon=h*.42;
    ctx.fillStyle="#07130c";ctx.fillRect(0,0,w,horizon);
    ctx.fillStyle="#031009";ctx.fillRect(0,horizon,w,h-horizon);

    const grad=ctx.createLinearGradient(0,0,0,h);
    grad.addColorStop(0,"rgba(124,231,255,.055)");
    grad.addColorStop(.5,"rgba(124,231,255,.018)");
    grad.addColorStop(1,"rgba(156,255,170,.025)");
    ctx.fillStyle=grad;ctx.fillRect(0,0,w,h);

    ctx.strokeStyle="rgba(116,183,132,.08)";
    ctx.lineWidth=1;
    for(let i=0;i<12;i++){
      const yy=horizon+(i*i)*(h-horizon)/144;
      ctx.beginPath();ctx.moveTo(0,yy);ctx.lineTo(w,yy);ctx.stroke();
    }
    for(let i=-10;i<=10;i++){
      ctx.beginPath();
      ctx.moveTo(w*.5+i*18,horizon);
      ctx.lineTo(w*.5+i*70,h);
      ctx.stroke();
    }

    ctx.strokeStyle="rgba(130,232,255,.18)";
    ctx.beginPath();ctx.moveTo(0,horizon);ctx.lineTo(w,horizon);ctx.stroke();

    if(cockpit){
      ctx.strokeStyle="rgba(130,232,255,.22)";
      ctx.beginPath();ctx.moveTo(w*.5-42,h*.58);ctx.lineTo(w*.5+42,h*.58);ctx.stroke();
      ctx.fillStyle="#82e8ff";ctx.font="8px monospace";
      ctx.fillText("SIM FPV // HORIZON "+Math.round((Math.sin(ts*.001)*4))+"°",10,h-12);
    }

    const ordered=[...drones].sort((a,b)=>a.y-b.y);
    ordered.forEach((d,i)=>drawDrone(d,project(d),ts,cockpit&&i===ordered.length-1));
  }

  function updateHud(){
    fleetEl.textContent=String(drones.length);
    altEl.textContent=Math.round(average("z")*80)+" m";
    speedEl.textContent=Math.round(average("speed"))+" km/h";
    batteryEl.textContent=Math.round(average("battery"))+"%";
  }

  function frame(ts){
    const dt=Math.min(40,ts-last);
    last=ts;
    update(dt,ts);
    drawWorld(ts);
    updateHud();
    requestAnimationFrame(frame);
  }

  document.querySelectorAll("[data-drone-mode]").forEach(btn=>btn.addEventListener("click",()=>{
    const next=btn.dataset.droneMode;
    if(next==="COCKPIT"){
      cockpit=!cockpit;
      btn.classList.toggle("active",cockpit);
      btn.textContent=cockpit?"FPV ON":"FPV";
      return;
    }
    if(next==="TAKEOFF"&&drones.every(d=>d.z<.02)) setMode("TAKEOFF");
    else if(next==="LAND") setMode("LAND");
    else if(next==="ORBIT") setMode("ORBIT");
    else if(next==="FORMATION") setMode("FORMATION");
    else if(next==="HOME") setMode("HOME");
  }));

  toggle.addEventListener("click",()=>setOpen(bay.hidden));

  window.addEventListener("message",evt=>{
    if(!["https://xunia.org","https://www.xunia.org"].includes(evt.origin)) return;
    if(evt.data?.type!=="maven-ui") return;
    if(evt.data.action==="open-drone"){
      setOpen(true);
      setMode(drones.every(d=>d.z<.02)?"GROUND":"FORMATION");
    }
  });

  setOpen(false);
  resize();
  requestAnimationFrame(frame);
})();