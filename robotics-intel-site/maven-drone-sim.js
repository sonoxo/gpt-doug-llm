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
  const selectedEl=document.getElementById("droneSelected");
  const trajectoryStateEl=document.getElementById("droneTrajectoryState");

  const head=bay.querySelector(".drone-head");
  const closeBtn=document.createElement("button");
  closeBtn.id="droneBayClose";
  closeBtn.type="button";
  closeBtn.textContent="CLOSE";
  closeBtn.className="drone-bay-close";
  head?.appendChild(closeBtn);

  let mode="GROUND";
  let cockpit=false;
  let last=performance.now();
  let dpr=1,w=1,h=1;
  let selectedIndex=0;

  let recording=false;
  let lastRecordAt=0;
  let trajectoryPath=[];
  let waypoints=[];
  let replay=null;

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

  function selected(){
    return drones[selectedIndex]||drones[0];
  }

  function clamp(v,min,max){
    return Math.max(min,Math.min(max,v));
  }

  function setOpen(open){
    if(open) document.dispatchEvent(new CustomEvent("maven:drone-open"));
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

  if("ResizeObserver" in window) new ResizeObserver(resize).observe(canvas);
  else addEventListener("resize",resize,{passive:true});

  function setMode(next){
    mode=next;
    if(modeEl) modeEl.textContent=next;
    document.querySelectorAll("[data-drone-mode]").forEach(btn=>btn.classList.toggle("active",btn.dataset.droneMode===next));
  }

  function setTrajectoryState(label){
    if(trajectoryStateEl) trajectoryStateEl.textContent=label;
  }

  function refreshSelected(){
    if(selectedEl) selectedEl.textContent=selected().id;
  }

  function average(key){
    return drones.reduce((s,d)=>s+d[key],0)/drones.length;
  }

  function snapshot(d=selected()){
    return {x:d.x,y:d.y,z:d.z,heading:d.heading};
  }

  function beginRecording(){
    replay=null;
    recording=!recording;
    const btn=document.getElementById("droneRecordPath");
    btn?.classList.toggle("active",recording);
    if(recording){
      trajectoryPath=[snapshot()];
      lastRecordAt=0;
      setTrajectoryState("RECORDING");
      setMode("MANUAL");
    }else{
      setTrajectoryState(trajectoryPath.length>1?"PATH READY":"IDLE");
    }
  }

  function markWaypoint(){
    replay=null;
    const p=snapshot();
    waypoints.push(p);
    trajectoryPath.push(p);
    setTrajectoryState("WP "+waypoints.length);
  }

  function clearTrajectory(){
    recording=false;
    replay=null;
    trajectoryPath=[];
    waypoints=[];
    document.getElementById("droneRecordPath")?.classList.remove("active");
    setTrajectoryState("IDLE");
  }

  function replayTrajectory(){
    const points=trajectoryPath.length>1?trajectoryPath:waypoints;
    if(points.length<2){
      setTrajectoryState("NEED 2+ POINTS");
      return;
    }
    recording=false;
    document.getElementById("droneRecordPath")?.classList.remove("active");
    replay={
      points:points.map(p=>({...p})),
      started:performance.now(),
      duration:Math.max(2600,points.length*95)
    };
    setMode("REPLAY");
    setTrajectoryState("REPLAY");
  }

  function manualMove(action){
    replay=null;
    recording=recording;
    const d=selected();
    const step=.035;
    const zStep=.08;

    setMode("MANUAL");
    if(d.z<.05 && action!=="down") d.z=.18;

    if(action==="forward"){
      d.y=clamp(d.y-step,.10,.90);
      d.heading=-Math.PI/2;
    }else if(action==="back"){
      d.y=clamp(d.y+step,.10,.90);
      d.heading=Math.PI/2;
    }else if(action==="left"){
      d.x=clamp(d.x-step,.06,.94);
      d.heading=Math.PI;
    }else if(action==="right"){
      d.x=clamp(d.x+step,.06,.94);
      d.heading=0;
    }else if(action==="up"){
      d.z=clamp(d.z+zStep,0,1);
    }else if(action==="down"){
      d.z=clamp(d.z-zStep,0,1);
    }

    d.speed=(action==="up"||action==="down")?8:18;
    if(recording) trajectoryPath.push(snapshot(d));
  }

  function selectNext(){
    selectedIndex=(selectedIndex+1)%drones.length;
    replay=null;
    recording=false;
    document.getElementById("droneRecordPath")?.classList.remove("active");
    trajectoryPath=[];
    waypoints=[];
    refreshSelected();
    setTrajectoryState("IDLE");
  }

  function updateReplay(ts){
    if(!replay) return false;

    const d=selected();
    const n=replay.points.length;
    const p=clamp((ts-replay.started)/replay.duration,0,1);
    const scaled=p*(n-1);
    const i=Math.min(n-2,Math.floor(scaled));
    const local=scaled-i;
    const a=replay.points[i];
    const b=replay.points[i+1];

    d.x=a.x+(b.x-a.x)*local;
    d.y=a.y+(b.y-a.y)*local;
    d.z=a.z+(b.z-a.z)*local;
    d.heading=a.heading+(b.heading-a.heading)*local;
    d.speed=22;

    if(p>=1){
      replay=null;
      d.speed=0;
      setMode("MANUAL");
      setTrajectoryState("COMPLETE");
    }
    return true;
  }

  function update(dt,ts){
    const sec=ts*.001;
    const replaying=updateReplay(ts);

    for(let i=0;i<drones.length;i++){
      const d=drones[i];
      if(replaying && i===selectedIndex) continue;

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
        d.z=0;
        d.speed=0;
      }else if(mode==="MANUAL" && i!==selectedIndex){
        d.speed=Math.max(0,d.speed-dt*.015);
      }

      if(d.z>0){
        d.battery=Math.max(12,d.battery-dt*.000045);
        if(!reduce && mode!=="MANUAL"){
          d.y+=Math.sin(sec*4+d.phase)*.0015;
        }
      }
    }

    if(recording && ts-lastRecordAt>120){
      const p=snapshot();
      const prior=trajectoryPath[trajectoryPath.length-1];
      if(!prior || Math.hypot(p.x-prior.x,p.y-prior.y, p.z-prior.z)>.004){
        trajectoryPath.push(p);
        if(trajectoryPath.length>260) trajectoryPath.shift();
      }
      lastRecordAt=ts;
    }

    if(mode==="HOME"&&drones.every(d=>Math.abs(d.x-d.homeX)<.015&&Math.abs(d.y-(d.homeY-.12))<.015)){
      setMode("FORMATION");
    }
  }

  function projectPoint(p){
    const altitude=18+p.z*48;
    const scale=.55+p.z*.55;
    return {x:p.x*w,y:p.y*h-altitude*.45,scale,shadowY:p.y*h+10};
  }

  function drawTrajectory(){
    if(trajectoryPath.length<2 && waypoints.length<2) return;
    const points=trajectoryPath.length>=2?trajectoryPath:waypoints;

    ctx.save();
    ctx.strokeStyle="rgba(255,193,94,.72)";
    ctx.lineWidth=1.5;
    ctx.setLineDash([5,5]);
    ctx.beginPath();
    points.forEach((p,i)=>{
      const q=projectPoint(p);
      if(i===0) ctx.moveTo(q.x,q.y);
      else ctx.lineTo(q.x,q.y);
    });
    ctx.stroke();
    ctx.setLineDash([]);

    for(const p of waypoints){
      const q=projectPoint(p);
      ctx.strokeStyle="#ffd166";
      ctx.beginPath();
      ctx.arc(q.x,q.y,5,0,Math.PI*2);
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawDrone(d,p,ts,isSelected=false){
    const s=11*p.scale;
    const rotor=4.8*p.scale;
    const spin=ts*.025+d.phase;

    ctx.save();
    ctx.translate(p.x,p.y);
    ctx.rotate(d.heading+Math.PI/2);
    ctx.strokeStyle=isSelected?"#ffd166":"#82e8ff";
    ctx.fillStyle=isSelected?"rgba(255,209,102,.13)":"rgba(130,232,255,.10)";
    ctx.lineWidth=isSelected?2:1.5;
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

    ctx.fillStyle=isSelected?"#ffd166":"#9cffaa";
    ctx.fillRect(-3*p.scale,-3*p.scale,6*p.scale,6*p.scale);
    ctx.restore();

    ctx.fillStyle="rgba(0,0,0,.25)";
    ctx.beginPath();
    ctx.ellipse(p.x,p.shadowY,10*p.scale,4*p.scale,0,0,Math.PI*2);
    ctx.fill();

    ctx.fillStyle=isSelected?"#ffd166":"#9eb4a4";
    ctx.font="7px monospace";
    ctx.fillText(d.id+(isSelected?" // PILOT":""),p.x+10,p.y-8);
  }

  function drawWorld(ts){
    ctx.clearRect(0,0,w,h);
    const horizon=h*.42;

    ctx.fillStyle="#07130c";
    ctx.fillRect(0,0,w,horizon);
    ctx.fillStyle="#031009";
    ctx.fillRect(0,horizon,w,h-horizon);

    const grad=ctx.createLinearGradient(0,0,0,h);
    grad.addColorStop(0,"rgba(124,231,255,.055)");
    grad.addColorStop(.5,"rgba(124,231,255,.018)");
    grad.addColorStop(1,"rgba(156,255,170,.025)");
    ctx.fillStyle=grad;
    ctx.fillRect(0,0,w,h);

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

    drawTrajectory();

    if(cockpit){
      ctx.strokeStyle="rgba(130,232,255,.22)";
      ctx.beginPath();ctx.moveTo(w*.5-42,h*.58);ctx.lineTo(w*.5+42,h*.58);ctx.stroke();
      ctx.fillStyle="#82e8ff";
      ctx.font="8px monospace";
      ctx.fillText("SIM FPV // NORMALIZED XYZ // GEO-LINK OFF",10,h-12);
    }

    drones.forEach((d,i)=>drawDrone(d,projectPoint(d),ts,i===selectedIndex));
  }

  function updateHud(){
    fleetEl.textContent=String(drones.length);
    altEl.textContent=Math.round(average("z")*80)+" sim-m";
    speedEl.textContent=Math.round(average("speed"))+" sim-km/h";
    batteryEl.textContent=Math.round(average("battery"))+"%";
    refreshSelected();
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
    replay=null;

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

  document.querySelectorAll("[data-drone-pilot]").forEach(btn=>{
    btn.addEventListener("click",()=>manualMove(btn.dataset.dronePilot));
  });

  document.getElementById("droneSelectNext")?.addEventListener("click",selectNext);
  document.getElementById("droneRecordPath")?.addEventListener("click",beginRecording);
  document.getElementById("droneMarkWaypoint")?.addEventListener("click",markWaypoint);
  document.getElementById("droneReplayPath")?.addEventListener("click",replayTrajectory);
  document.getElementById("droneClearPath")?.addEventListener("click",clearTrajectory);

  addEventListener("keydown",event=>{
    if(bay.hidden) return;
    const tag=(event.target?.tagName||"").toLowerCase();
    if(tag==="input"||tag==="textarea"||tag==="select") return;

    const keys={
      w:"forward",
      a:"left",
      s:"back",
      d:"right",
      e:"up",
      q:"down"
    };
    const action=keys[event.key.toLowerCase()];
    if(!action) return;
    event.preventDefault();
    manualMove(action);
  });

  toggle.addEventListener("click",()=>setOpen(bay.hidden));
  closeBtn.addEventListener("click",()=>setOpen(false));
  document.addEventListener("maven:camera-open",()=>setOpen(false));

  window.addEventListener("message",evt=>{
    if(!["https://xunia.org","https://www.xunia.org"].includes(evt.origin)) return;
    if(evt.data?.type!=="maven-ui") return;
    if(evt.data.action==="open-drone"){
      setOpen(true);
      setMode(drones.every(d=>d.z<.02)?"GROUND":"FORMATION");
    }
  });

  setOpen(false);
  refreshSelected();
  setTrajectoryState("IDLE");
  resize();
  requestAnimationFrame(frame);
})();