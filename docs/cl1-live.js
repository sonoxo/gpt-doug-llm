/* XUNIA HQ / CL1 LIVING CORE. Free, browser-only conceptual spatial simulation.
   No actual bio-sensors, RF transmission, external requests, or physical actuation.
   Shaggoth is fictional. Audio is original synthesis and requires explicit click.
*/
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const canvas = $("cl1-live-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    $("cl1-live-status").textContent = "CANVAS NOT AVAILABLE / USE PORTAL BUTTONS";
    return;
  }
  const TAU = Math.PI * 2;
  const portals = [
    {id:"cosmos", name:"XUNIA COSMOS", short:"COSMOS", url:"./cosmos/",
      description:"Explore our curated astronomical ontology, connected sources, and illustrative spatial relationships."},
    {id:"xenology", name:"CL1 XENOLOGY / SHAGGOTH", short:"SHAGGOTH", url:"./cosmos/xenology/",
      description:"Enter the fictional Shaggoth organism simulator, alien design gallery, and source-separated public UAP archive."},
    {id:"planets", name:"CL1 PLANETARY FORGE", short:"PLANETS", url:"./cosmos/planets/",
      description:"Rotate procedural planetary globes, explore approximate JPL orbits, and edit hypothetical planet clones."},
    {id:"biology", name:"CL1 BIOLOGICAL DATA CENTER", short:"BIO CENTER", url:"./biological-data-center/",
      description:"Inspect the interactive biological-compute ontology and its documented software module relationships."},
    {id:"glass-onion", name:"GLASS ONION", short:"GLASS ONION", url:"./darkweb/",
      description:"Enter the defensive public-source research environment with its documented tools and safeguards."},
    {id:"play", name:"XUNIA WORLD PROTOCOL", short:"XUNIA WORLD", url:"./play/",
      description:"Pilot the original free browser game through four playable worlds and linked museum gateways."},
    {id:"fleet", name:"ECOSYSTEM OBSERVATORY", short:"REPO FLEET", url:"./ecosystem-observatory/",
      description:"Navigate the public Sonoxo repository graph and evidence-labeled project relationships."},
    {id:"cinema", name:"GPT-DOUG CINEMA OS", short:"CINEMA OS", url:"./cinema-studio/",
      description:"Open the original local-video production studio and documented rendering tools."}
  ];
  const canvasParent = canvas.parentElement;
  const reduceQuery = window.matchMedia?.("(prefers-reduced-motion: reduce)");
  const state = {
    selected:0,mode:"ontology",energy:.65,zoom:1,yaw:.3,tilt:.72,
    phase:0,lastTime:0,lastDraw:0,frame:0,paused:!!reduceQuery?.matches,
    motionReduced:!!reduceQuery?.matches,drag:null,positions:[],dirty:true,
    sound:false,audio:null,oscillators:[],gain:null
  };
  const stars = Array.from({length:120}, (_, i) => {
    let x = ((i * 7919 + 1049) % 997) / 997;
    let y = ((i * 3413 + 2539) % 991) / 991;
    return {x,y,r:i%11===0?1.5:.75,a:.08+(i%6)*.07};
  });
  const clamp = (v,min,max) => Math.max(min,Math.min(max,v));
  const message = text => { $("cl1-live-message").textContent = text; };
  const redraw = () => { state.dirty = true; drawScene(); };
  function resize(){
    const r = canvas.getBoundingClientRect();
    const w = Math.max(250,Math.floor(r.width||600));
    const h = Math.max(240,Math.floor(r.height||480));
    const dpr = Math.min(window.devicePixelRatio||1,2);
    if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){
      canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
    }
    ctx.setTransform(dpr,0,0,dpr,0,0);
    return {w,h};
  }
  function project(i,w,h){
    const a = (i / portals.length) * TAU + state.yaw;
    const rx = Math.min(w*.34,330) * state.zoom;
    const ry = Math.min(h*.29,145) * state.zoom;
    const cx = w*.47,cy=h*.53;
    const z = Math.sin(a);
    const spread = clamp(state.tilt,.25,1.14);
    return {
      id:i,
      x:cx+Math.cos(a)*rx,
      y:cy+z*ry*spread,
      depth:z,
      radius:10+(z+1)*2.2
    };
  }
  function drawBackdrop(w,h,t){
    ctx.clearRect(0,0,w,h);
    const g = ctx.createRadialGradient(w*.49,h*.51,1,w*.49,h*.51,Math.max(w,h)*.65);
    g.addColorStop(0,"#18374a");
    g.addColorStop(.42,"#0b2134");
    g.addColorStop(1,"#030910");
    ctx.fillStyle=g;ctx.fillRect(0,0,w,h);
    ctx.lineWidth=.6;ctx.strokeStyle="rgba(181,229,239,.07)";
    const unit=36;
    for(let x=0;x<w;x+=unit){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}
    for(let y=0;y<h;y+=unit){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
    for(const star of stars){
      const pulse = state.paused||state.motionReduced?1:(.75+.25*Math.sin(t*.7+star.x*9));
      ctx.fillStyle="rgba(192,232,242,"+(star.a*pulse).toFixed(3)+")";
      ctx.fillRect(star.x*w,star.y*h,star.r,star.r);
    }
  }
  function drawRoutes(w,h,t){
    const cx=w*.47,cy=h*.53,points=state.positions;
    ctx.save();
    ctx.strokeStyle="rgba(183,227,235,.21)";
    ctx.lineWidth=1;
    ctx.beginPath();
    for(let i=0;i<=130;i++){
      const a=i/130*TAU+state.yaw;
      const x=cx+Math.cos(a)*Math.min(w*.34,330)*state.zoom;
      const y=cy+Math.sin(a)*Math.min(h*.29,145)*state.zoom*state.tilt;
      if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
    }ctx.stroke();
    for(let i=0;i<points.length;i++){
      const p=points[i],selected=state.selected===i;
      ctx.beginPath();ctx.moveTo(cx,cy);
      ctx.quadraticCurveTo((cx+p.x)/2,Math.min(cy,p.y)-17*(i%2===0?1:-1),p.x,p.y);
      ctx.strokeStyle=selected?"rgba(190,249,236,.67)":"rgba(119,186,207,.24)";
      ctx.lineWidth=selected?1.7:.9;ctx.stroke();
      const phase=(t*.18 + i*.173)%1;
      const x=cx+(p.x-cx)*phase;
      const y=cy+(p.y-cy)*phase+Math.sin(phase*Math.PI)*(-11*(i%2===0?1:-1));
      ctx.fillStyle=selected?"rgba(233,255,250,.92)":"rgba(139,220,226,.68)";
      ctx.beginPath();ctx.arc(x,y,selected?2.8:1.7,0,TAU);ctx.fill();
    }
    ctx.restore();
  }
  function drawCore(w,h,t){
    const cx=w*.47,cy=h*.53;
    const energy=state.energy;
    const k=state.mode==="shaggoth"?1.2:state.mode==="signal"?.7:1;
    const size=Math.min(w,h)*.104;
    ctx.save();
    ctx.translate(cx,cy);
    const halo=ctx.createRadialGradient(0,0,size*.12,0,0,size*2.7);
    halo.addColorStop(0,"rgba(230,251,247,.29)");
    halo.addColorStop(.32,"rgba(152,213,230,.16)");
    halo.addColorStop(1,"rgba(104,184,215,0)");
    ctx.fillStyle=halo;ctx.beginPath();ctx.arc(0,0,size*2.7,0,TAU);ctx.fill();
    for(let i=0;i<4;i++){
      const r=size*(1.20+i*.26+Math.sin(t*(.5+i*.13)+i)*.045*energy);
      ctx.beginPath();ctx.ellipse(0,0,r,r*(.40+.08*i),t*.09+i*.42,0,TAU);
      ctx.strokeStyle="rgba(182,231,236,"+(.20-i*.035).toFixed(3)+")";
      ctx.lineWidth=i===0?2:1;ctx.stroke();
    }
    if(state.mode==="shaggoth"){
      const count=12;
      for(let i=0;i<count;i++){
        const a=i/count*TAU+t*.08;
        const extent=size*(1.6+energy*.6);
        const endX=Math.cos(a)*extent,endY=Math.sin(a)*extent*.85;
        ctx.beginPath();ctx.moveTo(Math.cos(a)*size*.6,Math.sin(a)*size*.55);
        ctx.bezierCurveTo(Math.cos(a+.5)*size*1.5,Math.sin(a+.5)*size*1.5,
          endX-Math.sin(t*.63+i*1.3)*size*.3,endY+Math.cos(t*.73+i)*size*.3,endX,endY);
        ctx.lineCap="round";ctx.lineWidth=4+energy*4;
        ctx.strokeStyle=i%3===0?"rgba(205,231,238,.85)":"rgba(92,153,176,.75)";
        ctx.stroke();ctx.lineWidth=1;ctx.strokeStyle="rgba(226,253,253,.45)";ctx.stroke();
      }
    }else if(state.mode==="signal"){
      for(let i=0;i<4;i++){
        const spread=(t*.2+i/4)%1;
        ctx.beginPath();ctx.arc(0,0,size*(.8+spread*2.5),0,TAU);
        ctx.strokeStyle="rgba(181,250,242,"+((1-spread)*.43*energy).toFixed(3)+")";
        ctx.lineWidth=1.6;ctx.stroke();
      }
    }
    const spin=t*.16;
    const r=size*(1+.045*Math.sin(t*2)*energy)*k;
    const g=ctx.createRadialGradient(-r*.33,-r*.37,r*.04,0,0,r*1.22);
    g.addColorStop(0,"#f4fffc");g.addColorStop(.17,"#b6d8df");
    g.addColorStop(.45,"#456f83");g.addColorStop(.76,"#163143");g.addColorStop(1,"#06101c");
    ctx.shadowColor="rgba(174,242,242,.62)";ctx.shadowBlur=22+energy*26;
    ctx.fillStyle=g;ctx.beginPath();
    for(let i=0;i<=100;i++){
      const a=(i/100)*TAU;
      const rr=r*(1+.07*energy*Math.sin(a*7+spin)+.035*Math.sin(a*13-spin*.7));
      const x=Math.cos(a)*rr,y=Math.sin(a)*rr*.94;
      if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
    }
    ctx.closePath();ctx.fill();ctx.shadowBlur=0;
    ctx.strokeStyle="rgba(243,255,255,.74)";ctx.lineWidth=1.2;ctx.stroke();
    if(state.mode==="shaggoth"){
      for(const [ex,ey] of [[-.36,-.12],[.32,-.15],[0,.28]]){
        ctx.shadowColor="#aaf6ff";ctx.shadowBlur=14;
        ctx.fillStyle="#f3ffff";ctx.beginPath();
        ctx.ellipse(r*ex,r*ey,r*.14,r*.09,ex,0,TAU);ctx.fill();
      }
      ctx.shadowBlur=0;
    }else{
      for(let i=0;i<5;i++){
        ctx.beginPath();ctx.arc(0,0,r*(.25+i*.15),spin+i*.75,spin+i*.75+Math.PI*.7);
        ctx.strokeStyle="rgba(223,251,254,"+(.55-i*.09)+")";
        ctx.lineWidth=1.4;ctx.stroke();
      }
      ctx.fillStyle="#edffff";ctx.beginPath();ctx.arc(0,0,r*.10,0,TAU);ctx.fill();
    }
    ctx.fillStyle="rgba(229,251,255,.91)";ctx.font="bold 10px ui-monospace,Menlo,monospace";
    ctx.textAlign="center";ctx.fillText(state.mode==="shaggoth"?"CL1 / SHAGGOTH":"CL1 / CORE",0,r*1.60);
    ctx.restore();
  }
  function drawPortals(w,h,t){
    const pts=[...state.positions].sort((a,b)=>a.depth-b.depth);
    ctx.save();
    for(const p of pts){
      const portal=portals[p.id],selected=p.id===state.selected;
      const r=p.radius*(selected?1.35:1);
      const ambient=state.paused||state.motionReduced?1:.86+.14*Math.sin(t*2+p.id);
      ctx.shadowBlur=selected?24:12;
      ctx.shadowColor=selected?"#c6fff2":"#a1dce8";
      const gr=ctx.createRadialGradient(p.x-r*.3,p.y-r*.35,0,p.x,p.y,r);
      gr.addColorStop(0,"#f5fcfc");gr.addColorStop(.28,"#afc9d4");
      gr.addColorStop(1,selected?"#276275":"#102d42");
      ctx.fillStyle=gr;ctx.beginPath();ctx.arc(p.x,p.y,r*ambient,0,TAU);ctx.fill();
      ctx.shadowBlur=0;ctx.lineWidth=selected?2:1;
      ctx.strokeStyle=selected?"rgba(202,255,240,.95)":"rgba(168,224,236,.59)";
      ctx.beginPath();ctx.arc(p.x,p.y,r+4,0,TAU);ctx.stroke();
      if(selected){
        ctx.strokeStyle="rgba(173,241,239,.51)";
        ctx.beginPath();ctx.arc(p.x,p.y,r+10+t%TAU*.65,0,TAU);ctx.stroke();
      }
      ctx.font=(selected?"bold ":"")+"10px ui-monospace,Menlo,Consolas,monospace";
      ctx.textAlign=p.x>w*.55?"right":"left";
      ctx.fillStyle=selected?"#f1fff7":"#b4d1dd";
      const labelX=p.x+(p.x>w*.55?-r-12:r+12);
      const labelY=p.y-10;
      ctx.fillText(portal.short,labelX,labelY);
    }
    ctx.restore();
  }
  function drawScene(){
    const {w,h}=resize();
    const t=state.phase;
    state.positions=portals.map((_,i)=>project(i,w,h));
    drawBackdrop(w,h,t);
    drawRoutes(w,h,t);
    drawCore(w,h,t);
    drawPortals(w,h,t);
    canvas.dataset.renderedNodes=String(state.positions.length);
    canvas.dataset.selectedPortal=portals[state.selected].id;
    canvas.dataset.mode=state.mode;
    canvas.dataset.renderedFrames=String(++state.frame);
    state.dirty=false;
  }
  function select(index){
    if(!Number.isInteger(index)||index<0||index>=portals.length)return;
    state.selected=index;
    const current=portals[index];
    $("cl1-live-name").textContent=current.name;
    $("cl1-live-description").textContent=current.description;
    $("cl1-live-index").textContent=String(index+1).padStart(2,"0")+" / 08";
    const anchor=$("cl1-live-enter");
    anchor.href=current.url;
    anchor.firstChild.textContent="ENTER "+current.name+" ";
    document.querySelectorAll("[data-cl1-portal]").forEach(button=>
      button.setAttribute("aria-pressed",String(button.dataset.cl1Portal===current.id)));
    $("cl1-live-status").textContent="SELECTED / "+current.short;
    redraw();
  }
  function modeChange(mode){
    if(!["ontology","shaggoth","signal"].includes(mode))return;
    state.mode=mode;
    document.querySelectorAll("[data-cl1-mode]").forEach(button=>
      button.setAttribute("aria-pressed",String(button.dataset.cl1Mode===mode)));
    $("cl1-live-mode-label").textContent=mode.toUpperCase();
    message("CORE MODE / "+mode.toUpperCase()+" · NON-KINETIC VISUAL");
    redraw();
  }
  function pauseToggle(force){
    state.paused=typeof force==="boolean"?force:!state.paused;
    const button=$("cl1-live-pause");
    button.setAttribute("aria-pressed",String(state.paused));
    button.textContent=state.paused?"▶ RESUME MOTION":"Ⅱ PAUSE MOTION";
    message(state.paused?"SIMULATED MOTION PAUSED":"SIMULATED MOTION PLAYING");
    redraw();
  }
  function energyChange(value){
    state.energy=clamp(Number(value)/100,0,1);
    $("cl1-live-energy").value=String(Math.round(state.energy*100));
    $("cl1-live-energy-value").textContent=Math.round(state.energy*100)+"%";
    redraw();
  }
  function zoomBy(factor){state.zoom=clamp(state.zoom*factor,.65,1.55);redraw();}
  function resetCamera(){state.zoom=1;state.yaw=.3;state.tilt=.72;redraw();}
  function toggleFullscreen(){
    const target=canvasParent;
    if(document.fullscreenElement){
      document.exitFullscreen?.().catch(()=>message("FULLSCREEN EXIT UNAVAILABLE"));
    }else if(target.requestFullscreen){
      target.requestFullscreen().catch(()=>message("FULLSCREEN UNAVAILABLE / USE BROWSER FULLSCREEN"));
    }else{message("FULLSCREEN UNAVAILABLE / USE BROWSER FULLSCREEN");}
  }
  async function soundOff(){
    state.sound=false;
    $("cl1-live-audio").textContent="♪ SOUND OFF";
    $("cl1-live-audio").setAttribute("aria-pressed","false");
    const audio=state.audio;
    state.audio=null;state.oscillators=[];state.gain=null;
    if(audio){try{await audio.close();}catch(_){}}
  }
  async function soundToggle(){
    if(state.sound){await soundOff();message("ORIGINAL AMBIENT SOUND OFF");return;}
    const Audio=window.AudioContext||window.webkitAudioContext;
    if(!Audio){message("WEB AUDIO UNSUPPORTED");return;}
    try{
      const audio=new Audio();
      const gain=audio.createGain();
      gain.gain.value=.009;
      gain.connect(audio.destination);
      const oscillators=[];
      for(const [hz,wave] of [[55,"sine"],[82.41,"triangle"]]){
        const oscillator=audio.createOscillator();
        oscillator.type=wave;oscillator.frequency.value=hz;
        oscillator.connect(gain);oscillator.start();oscillators.push(oscillator);
      }
      state.audio=audio;state.gain=gain;state.oscillators=oscillators;state.sound=true;
      await audio.resume();
      $("cl1-live-audio").textContent="♪ SOUND ON";
      $("cl1-live-audio").setAttribute("aria-pressed","true");
      message("ORIGINAL SYNTH AMBIENCE / LOW VOLUME / LOCAL ONLY");
    }catch(_){await soundOff();message("AUDIO DISALLOWED IN THIS BROWSER");}
  }
  function savePng(){
    drawScene();
    try{
      canvas.toBlob(blob=>{
        if(!blob){message("PNG EXPORT UNAVAILABLE");return;}
        const url=URL.createObjectURL(blob),a=document.createElement("a");
        a.href=url;a.download="xunia-cl1-living-core.png";
        document.body.appendChild(a);a.click();a.remove();
        window.setTimeout(()=>URL.revokeObjectURL(url),1000);
        message("LIVING CORE PNG GENERATED / LOCAL BROWSER DOWNLOAD");
      },"image/png");
    }catch(_){message("PNG EXPORT UNAVAILABLE / CHECK BROWSER");}
  }
  const hitPoint=(x,y)=>{
    let best=null,dist=27;
    for(const p of state.positions){
      const gap=Math.hypot(x-p.x,y-p.y);
      if(gap<dist){best=p;dist=gap;}
    }
    return best;
  };
  function canvasPosition(event){
    const rect=canvas.getBoundingClientRect();
    return {x:event.clientX-rect.left,y:event.clientY-rect.top};
  }
  function init(){
    document.querySelectorAll("[data-cl1-portal]").forEach(button=>{
      const idx=portals.findIndex(p=>p.id===button.dataset.cl1Portal);
      if(idx>=0)button.addEventListener("click",()=>select(idx));
    });
    document.querySelectorAll("[data-cl1-mode]").forEach(button=>
      button.addEventListener("click",()=>modeChange(button.dataset.cl1Mode)));
    $("cl1-live-energy").addEventListener("input",e=>energyChange(e.target.value));
    $("cl1-live-pause").addEventListener("click",()=>pauseToggle());
    $("cl1-live-audio").addEventListener("click",soundToggle);
    $("cl1-live-zoom-in").addEventListener("click",()=>zoomBy(1.13));
    $("cl1-live-zoom-out").addEventListener("click",()=>zoomBy(1/1.13));
    $("cl1-live-recenter").addEventListener("click",resetCamera);
    $("cl1-live-fullscreen").addEventListener("click",toggleFullscreen);
    $("cl1-live-capture").addEventListener("click",savePng);
    canvas.addEventListener("pointerdown",event=>{
      if(event.button!==0)return;
      const point=canvasPosition(event);
      state.drag={...point,total:0};canvas.setPointerCapture?.(event.pointerId);
      canvas.focus();
    });
    canvas.addEventListener("pointermove",event=>{
      if(!state.drag)return;
      const point=canvasPosition(event);
      const dx=point.x-state.drag.x,dy=point.y-state.drag.y;
      state.drag.total+=Math.hypot(dx,dy);
      if(state.drag.total>4){
        state.yaw+=dx*.006;
        state.tilt=clamp(state.tilt+dy*.003,.28,1.14);
        redraw();
      }
      state.drag.x=point.x;state.drag.y=point.y;
    });
    canvas.addEventListener("pointerup",event=>{
      const drag=state.drag;state.drag=null;
      if(!drag||drag.total>=7)return;
      const point=canvasPosition(event),nearest=hitPoint(point.x,point.y);
      if(nearest)select(nearest.id);
    });
    for(const key of ["pointercancel","lostpointercapture"])canvas.addEventListener(key,()=>state.drag=null);
    canvas.addEventListener("wheel",event=>{
      event.preventDefault();zoomBy(event.deltaY<0?1.09:1/1.09);
    },{passive:false});
    canvas.addEventListener("dblclick",event=>{
      const point=canvasPosition(event),nearest=hitPoint(point.x,point.y);
      if(nearest)window.location.assign(portals[nearest.id].url);
    });
    canvas.addEventListener("keydown",event=>{
      if(event.key==="ArrowRight"||event.key==="ArrowDown"){
        event.preventDefault();select((state.selected+1)%portals.length);
      }else if(event.key==="ArrowLeft"||event.key==="ArrowUp"){
        event.preventDefault();select((state.selected+portals.length-1)%portals.length);
      }else if(event.key==="Enter"){
        event.preventDefault();$("cl1-live-enter").click();
      }else if(event.key===" "){
        event.preventDefault();pauseToggle();
      }
    });
    window.addEventListener("resize",redraw);
    if(window.ResizeObserver)new ResizeObserver(redraw).observe(canvasParent);
    document.addEventListener("visibilitychange",()=>{
      if(!state.audio)return;
      if(document.hidden)state.audio.suspend().catch(()=>{});
      else if(state.sound)state.audio.resume().catch(()=>{});
    });
    window.addEventListener("pagehide",()=>{if(state.sound)soundOff();});
    reduceQuery?.addEventListener?.("change",event=>{
      state.motionReduced=event.matches;
      if(event.matches){pauseToggle(true);if(state.sound)soundOff();}
      redraw();
    });
    if(state.motionReduced)pauseToggle(true);
    select(0);drawScene();
    $("cl1-live-fps").textContent="CANVAS ONLINE / NOT LIVE TELEMETRY";
    requestAnimationFrame(tick);
  }
  function tick(now){
    const dt=state.lastTime?Math.min(.08,(now-state.lastTime)/1000):0;
    state.lastTime=now;
    if(!state.paused&&!state.motionReduced&&!document.hidden){
      state.phase+=dt*(.45+state.energy*.55);
      state.dirty=true;
    }
    if(state.dirty&&now-state.lastDraw>=30){drawScene();state.lastDraw=now;}
    requestAnimationFrame(tick);
  }
  init();
})();
