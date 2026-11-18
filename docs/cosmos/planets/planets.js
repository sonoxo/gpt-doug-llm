/* XUNIA CL1 Planetary Forge / non-kinetic, same-origin digital twin model.
 * Reference: NASA NSSDC physical facts + JPL approximate J2000 orbital elements, 1800-2050.
 * Orbit renderer uses log-compressed spacing. Globe is procedural, not photographic.
 */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
const PI=Math.PI,TAU=PI*2,RAD=PI/180,DAY=86400000,J2000=Date.UTC(2000,0,1,12);
const MIN=Date.parse("1800-01-01T00:00:00Z"),MAX=Date.parse("2050-12-31T00:00:00Z");
const clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,v));
const d2r=v=>v*RAD;
const fmt=(v,d=0)=>Number(v).toLocaleString("en-US",{maximumFractionDigits:d});
const state={planets:[],byId:new Map(),planet:"earth",clones:[],nextClone:1,activeCloneId:null,
  dateMs:Date.UTC(2026,10,17),playing:false,speed:30,zoom:1,yaw:.24,pitch:.72,
  panX:0,panY:0,labels:true,globeYaw:0,orbitPoints:[],drag:null,globeDrag:null,
  frame:0,lastTime:0,lastDraw:0,ready:false,dirty:true};
const orrery=$("orrery"),globe=$("globe");
const oc=orrery.getContext("2d"),gc=globe.getContext("2d");
const texture=document.createElement("canvas");texture.width=216;texture.height=216;
const tc=texture.getContext("2d");
function message(value){$("commandStatus").textContent=String(value)}
function labMessage(value){$("cloneMessage").textContent=String(value)}
function planet(){return state.byId.get(state.planet)}
function activeClone(){return state.clones.find(c=>c.id===state.activeCloneId)||null}
function mark(){state.dirty=true}
function formatDate(ms){return new Date(ms).toISOString().slice(0,10)}
function setDate(value){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;
  const ms=Date.parse(value+"T00:00:00Z");
  if(!Number.isFinite(ms)||ms<MIN||ms>MAX||formatDate(ms)!==value)return false;
  state.dateMs=ms;state.playing=false;updatePlayButton();$("epochDate").value=value;mark();return true;
}
function elementsAt(p,ms){
  const T=(ms-J2000)/DAY/36525;
  return p.elements_j2000.map((v,i)=>v+p.rates_per_century[i]*T);
}
function orbitalCoords(p,ms,Eoverride){
  const [a,e,inc,L,peri,node]=elementsAt(p,ms);
  const incR=d2r(inc),om=d2r(peri-node),nodeR=d2r(node);
  let E=Eoverride;
  if(E===undefined){
    const M=d2r(((L-peri)%360+360)%360);
    E=M;
    for(let i=0;i<12;i++){
      const delta=(E-e*Math.sin(E)-M)/(1-e*Math.cos(E));
      E-=delta;if(Math.abs(delta)<1e-12)break;
    }
  }
  const xp=a*(Math.cos(E)-e),yp=a*Math.sqrt(1-e*e)*Math.sin(E);
  const co=Math.cos(om),so=Math.sin(om),cn=Math.cos(nodeR),sn=Math.sin(nodeR);
  const ci=Math.cos(incR),si=Math.sin(incR);
  return [ (co*cn-so*sn*ci)*xp+(-so*cn-co*sn*ci)*yp,
           (co*sn+so*cn*ci)*xp+(-so*sn+co*cn*ci)*yp,
           (so*si)*xp+(co*si)*yp ];
}
function resizeCanvas(canvas,ctx){
  const r=canvas.getBoundingClientRect(),dpr=Math.min(window.devicePixelRatio||1,2);
  const w=Math.max(120,Math.round(r.width)),h=Math.max(120,Math.round(r.height));
  if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){
    canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
  }
  ctx.setTransform(dpr,0,0,dpr,0,0);
  return [w,h];
}
function project(xyz,w,h){
  const [x,y,z]=xyz;
  const distance=Math.hypot(x,y,z)||1;
  const factor=Math.log1p(distance*1.4)/distance;
  const X=x*factor,Y=y*factor,Z=z*factor;
  const xr=X*Math.cos(state.yaw)-Y*Math.sin(state.yaw);
  const yr=X*Math.sin(state.yaw)+Y*Math.cos(state.yaw);
  const scale=Math.min(w,h)*.117*state.zoom;
  return {x:w/2+state.panX+xr*scale,y:h/2+state.panY-(yr*Math.sin(state.pitch)+Z*Math.cos(state.pitch))*scale,
    depth:yr*Math.cos(state.pitch)-Z*Math.sin(state.pitch)};
}
function renderOrbits(){
  if(!oc)return;
  const [w,h]=resizeCanvas(orrery,oc);oc.clearRect(0,0,w,h);
  for(let i=0;i<125;i++){
    const sx=((i*1723+13)%977)/977*w,sy=((i*2719+17)%991)/991*h;
    oc.fillStyle="rgba(172,214,221,"+(0.12+(i%5)*.04)+")";
    oc.fillRect(sx,sy,i%11===0?2:1,1);
  }
  const center=project([0,0,0],w,h);
  const grad=oc.createRadialGradient(center.x,center.y,2,center.x,center.y,75);
  grad.addColorStop(0,"rgba(251,221,179,.49)");grad.addColorStop(.2,"rgba(232,187,126,.13)");
  grad.addColorStop(1,"rgba(233,184,120,0)");
  oc.fillStyle=grad;oc.beginPath();oc.arc(center.x,center.y,75,0,TAU);oc.fill();
  oc.fillStyle="#fff1cc";oc.beginPath();oc.arc(center.x,center.y,6,0,TAU);oc.fill();
  oc.font="10px Menlo,monospace";oc.fillStyle="#e5d6b4";oc.fillText("SUN",center.x+10,center.y-12);
  for(const p of state.planets){
    oc.beginPath();
    for(let i=0;i<=126;i++){
      const pos=project(orbitalCoords(p,state.dateMs,i/126*TAU),w,h);
      if(i===0)oc.moveTo(pos.x,pos.y);else oc.lineTo(pos.x,pos.y);
    }
    oc.strokeStyle=p.id===state.planet?"rgba(195,236,229,.41)":"rgba(119,155,169,.23)";
    oc.lineWidth=p.id===state.planet?1.5:.8;oc.stroke();
  }
  state.orbitPoints=[];
  for(const p of state.planets){
    const spot=project(orbitalCoords(p,state.dateMs),w,h);
    const selected=p.id===state.planet;
    const radius=selected?8:clamp(3+Math.log(p.diameter_km/4000),4,8);
    const palette=p.render_palette;
    oc.save();
    oc.shadowBlur=selected?18:8;oc.shadowColor=palette[0];
    oc.fillStyle=palette[0];oc.beginPath();oc.arc(spot.x,spot.y,radius,0,TAU);oc.fill();
    oc.shadowBlur=0;oc.strokeStyle=selected?"#ebfff8":"rgba(236,255,249,.4)";
    oc.lineWidth=selected?2:1;oc.beginPath();oc.arc(spot.x,spot.y,radius+2,0,TAU);oc.stroke();
    if(state.labels||selected){oc.font=(selected?"bold ":"")+"10px Menlo,monospace";
      oc.fillStyle=selected?"#ecfff5":"#a6c0c9";oc.fillText(p.name,spot.x+radius+8,spot.y-7);}
    oc.restore();
    state.orbitPoints.push({...spot,id:p.id,radius});
  }
  orrery.dataset.renderedPlanets=String(state.orbitPoints.length);
  orrery.dataset.activePlanet=state.planet;
  orrery.dataset.renderFrames=String(++state.frame);
  $("coords").textContent="CAMERA "+(state.zoom*100).toFixed(0)+"% · SOURCE AU / VIEW LOG";
  $("orbitStatus").textContent=formatDate(state.dateMs)+" / APPROXIMATE KEPLER";
}
function rgb(hex){const s=hex.replace("#","");return [0,2,4].map(i=>parseInt(s.slice(i,i+2),16))}
function surfaceColor(p,lat,lon,noise,base,shade){
  let [r,g,b]=base;
  const a=Math.sin(lon*8+Math.sin(lat*15)*2.5);
  const n=Math.sin(lon*12+lat*19)*Math.sin(lon*31-lat*9)+noise*.35;
  if(p.id==="earth"){
    const land=Math.sin(lon*3.1+lat*4.2)+.46*Math.sin(lon*9.2-lat*6.2)+.24*n;
    if(land>.44){r=67+25*n;g=102+38*n;b=66+16*n;}else{r=29;g=87+18*n;b=146+32*n;}
    if(Math.abs(lat)>1.13){r=202;g=221;b=220;}
    if(Math.sin(lon*17+lat*22)*Math.sin(lat*24-lon*5)>.74){r=r*.62+235*.38;g=g*.62+242*.38;b=b*.62+250*.38;}
  }else if(p.id==="jupiter"||p.id==="saturn"){
    const bands=Math.sin(lat*(p.id==="jupiter"?40:54)+Math.sin(lon*2+lat*3)*.7)+.3*Math.sin(lat*89+lon*4);
    const amount=bands*26+n*9;
    r+=amount;g+=amount*.88;b+=amount*.65;
    if(p.id==="jupiter"){
      const spot=Math.hypot((lon-1.2)*1.3,(lat+.35)*3);
      if(spot<.28){r=173;g=85;b=67;}
    }
  }else if(p.id==="venus"){
    const swirls=Math.sin(lat*31+lon*5+Math.sin(lon*6+lat*4))*18+n*11;
    r+=swirls;g+=swirls*.7;b+=swirls*.4;
  }else if(p.id==="mars"){
    const dust=Math.sin(lon*11+lat*6)*Math.sin(lat*16-lon*7)*23+n*18;
    r+=dust;g+=dust*.62;b+=dust*.35;
    if(Math.abs(lat)>1.27){r=222;g=197;b=177;}
  }else if(p.id==="mercury"){
    const craters=Math.abs(Math.sin(lon*19+lat*13)*Math.cos(lat*25-lon*7));
    const amp=(craters>.90?-45:0)+n*18;r+=amp;g+=amp;b+=amp;
  }else if(p.id==="neptune"){
    const storms=Math.sin(lat*19+lon*4)+Math.sin(lat*44-lon*7)*.28;
    r+=storms*11;g+=storms*13;b+=storms*16;
  }else if(p.id==="uranus"){const band=Math.sin(lat*20+lon*2)*5;r+=band;g+=band;b+=band;}
  const lit=shade;
  return [clamp(r*lit,0,255),clamp(g*lit,0,255),clamp(b*lit,0,255)];
}
function renderGlobe(){
  if(!gc||!tc||!planet())return;
  const p=planet(),cl=activeClone();
  const [w,h]=resizeCanvas(globe,gc);gc.clearRect(0,0,w,h);
  const centerX=w/2,centerY=h/2;
  const radius=Math.min(w*.28,h*.38)*Math.min(cl?.diameterScale||1,1.42);
  const pal=rgb(p.render_palette[0]);
  const glow=(cl?.glow??50)/100;
  const spinMultiplier=cl?.spin??1;
  const rot=((state.dateMs-J2000)/3600000/p.rotation_hours*spinMultiplier*TAU+state.globeYaw)%TAU;
  if(p.ring_system){
    gc.save();gc.translate(centerX,centerY);gc.rotate(-.29);
    for(let i=0;i<4;i++){
      gc.beginPath();gc.ellipse(0,0,radius*(1.35+i*.17),radius*(.35+i*.04),0,0,TAU);
      gc.lineWidth=i%2?4:6;gc.strokeStyle=i%2?"rgba(200,198,170,.2)":"rgba(216,214,194,.33)";gc.stroke();
    }gc.restore();
  }
  const texW=texture.width,texH=texture.height,mid=texW/2,R=mid-1;
  const pixels=tc.createImageData(texW,texH);
  const til=d2r(p.axial_tilt_deg);
  for(let y=0;y<texH;y++)for(let x=0;x<texW;x++){
    const nx=(x-mid+.5)/R,ny=-(y-mid+.5)/R,rr=nx*nx+ny*ny;
    const idx=(y*texW+x)*4;
    if(rr>1){pixels.data[idx+3]=0;continue;}
    const nz=Math.sqrt(1-rr);
    const axisY=ny*Math.cos(til)+nx*Math.sin(til);
    const lat=Math.asin(clamp(axisY,-1,1));
    const lon=Math.atan2(nx,nz)+rot;
    const noise=Math.sin(lon*29+lat*7)*Math.cos(lat*37-lon*8);
    const light=clamp(nx*(-.52)+ny*.24+nz*.79,0,1);
    const lit=.23+.77*light;
    const base=surfaceColor(p,lat,lon,noise,pal,lit);
    const edge=clamp((1-rr)*20,0,1);
    pixels.data[idx]=base[0];pixels.data[idx+1]=base[1];
    pixels.data[idx+2]=base[2];pixels.data[idx+3]=Math.round(edge*255);
  }
  tc.putImageData(pixels,0,0);
  gc.save();gc.shadowBlur=30+glow*30;gc.shadowColor=p.render_palette[0];
  gc.drawImage(texture,centerX-radius,centerY-radius,radius*2,radius*2);
  gc.restore();
  gc.strokeStyle="rgba(179,224,227,"+(.08+glow*.34).toFixed(2)+")";
  gc.lineWidth=1;gc.beginPath();gc.arc(centerX,centerY,radius+.7,0,TAU);gc.stroke();
  if(p.ring_system){
    gc.save();gc.translate(centerX,centerY);gc.rotate(-.29);
    for(let i=0;i<3;i++){
      gc.beginPath();gc.ellipse(0,0,radius*(1.37+i*.19),radius*(.35+i*.04),0,0,PI);
      gc.strokeStyle=i===1?"rgba(240,231,198,.70)":"rgba(220,222,208,.42)";
      gc.lineWidth=i===1?3:6;gc.stroke();
    }gc.restore();
  }
  globe.dataset.renderedGlobe=p.id;
  globe.dataset.cloned=String(!!cl);
}
function renderList(){
  const list=$("planetList");list.replaceChildren();
  for(let i=0;i<state.planets.length;i++){
    const p=state.planets[i],b=document.createElement("button");
    b.type="button";b.className="planet-entry";b.dataset.planetId=p.id;
    b.setAttribute("aria-pressed",String(state.planet===p.id&&!activeClone()));
    const dot=document.createElement("span");dot.className="dot";
    dot.style.background="radial-gradient(circle at 28% 27%,"+p.render_palette[0]+","+p.render_palette[1]+")";
    const label=document.createElement("span");
    const strong=document.createElement("strong");strong.textContent=p.name;
    const small=document.createElement("small");small.textContent=p.kind.toUpperCase()+" / "+String(i+1).padStart(2,"0");
    label.append(strong,small);b.append(dot,label);
    b.addEventListener("click",()=>selectPlanet(p.id));
    list.appendChild(b);
  }
}
function updateInspector(){
  const p=planet();if(!p)return;
  const cl=activeClone(),factor=cl?.diameterScale||1;
  $("planetName").textContent=cl?cl.name:p.name;
  $("planetClass").textContent=p.kind.toUpperCase();
  $("planetOrder").textContent=String(state.planets.findIndex(x=>x.id===p.id)+1).padStart(2,"0")+" / 08";
  $("recordType").textContent=cl?"SANDBOX / HYPOTHETICAL":"NASA / REFERENCE";
  $("planetDescription").textContent=(cl?"Hypothetical clone of "+p.name+". ":"")+p.description;
  $("diameter").textContent=fmt(p.diameter_km*factor,1)+" km"+(cl?" (virtual)":"");
  $("gravity").textContent=fmt(p.gravity_ms2,1)+" m/s² · SOURCE";
  $("period").textContent=fmt(p.orbital_period_days,1)+" days";
  const [x,y,z]=orbitalCoords(p,state.dateMs);
  $("solarDistance").textContent=fmt(Math.hypot(x,y,z),3)+" AU (approx)";
  const spin=cl?.spin??1;
  $("rotation").textContent=spin===0?"0 / FROZEN (virtual)":fmt(p.rotation_hours/spin,1)+" hours"+(cl?" (virtual)":"");
  $("tilt").textContent=fmt(p.axial_tilt_deg,2)+"°";
}
function updateClonePanel(){
  const list=$("cloneList");list.replaceChildren();
  const active=activeClone();
  $("cloneCount").textContent=String(state.clones.length);
  $("removeClone").disabled=!active;$("exportClone").disabled=!active;
  $("createClone").disabled=state.clones.length>=4;
  for(const id of ["cloneRadius","cloneSpin","cloneGlow"])$(id).disabled=!active;
  $("cloneRadius").value=String(active?.diameterScale??1);
  $("cloneSpin").value=String(active?.spin??1);
  $("cloneGlow").value=String(active?.glow??50);
  $("radiusOut").textContent=Number($("cloneRadius").value).toFixed(2)+"×";
  $("spinOut").textContent=Number($("cloneSpin").value).toFixed(2)+"×";
  $("glowOut").textContent=$("cloneGlow").value+"%";
  if(state.clones.length===0){
    const t=document.createElement("p");t.className="empty";
    t.textContent="No clones. Create one from a planet to experiment.";list.appendChild(t);
  }
  for(const cl of state.clones){
    const b=document.createElement("button");b.type="button";
    b.textContent=cl.name+" · "+cl.diameterScale.toFixed(2)+"×";
    b.setAttribute("aria-pressed",String(cl.id===state.activeCloneId));
    b.addEventListener("click",()=>selectClone(cl.id));list.appendChild(b);
  }
}
function syncView(){
  renderList();updateInspector();updateClonePanel();mark();
}
function selectPlanet(id){
  if(!state.byId.has(id))return false;
  state.planet=id;state.activeCloneId=null;state.globeYaw=0;syncView();
  labMessage("REFERENCE / "+planet().name+" selected. Source data immutable.");
  return true;
}
function selectClone(id){
  const cl=state.clones.find(c=>c.id===id);if(!cl)return false;
  state.activeCloneId=id;state.planet=cl.sourceId;state.globeYaw=0;syncView();
  labMessage(cl.name+" / virtual sandbox active; source unchanged.");
  return true;
}
function clonePlanet(){
  if(state.clones.length>=4){labMessage("MAXIMUM FOUR SANDBOX CLONES");return null;}
  const p=planet();if(!p)return null;
  const n=state.nextClone++;
  const cl={id:"clone-"+n,name:p.name+" CL1-"+String(n).padStart(2,"0"),
    sourceId:p.id,diameterScale:1,spin:1,glow:50};
  state.clones.push(cl);selectClone(cl.id);
  labMessage("VIRTUAL CLONE CREATED / "+cl.name+" · source record read-only");
  return cl;
}
function removeClone(){
  const id=state.activeCloneId;if(!id){labMessage("SELECT A CLONE TO DELETE");return;}
  state.clones=state.clones.filter(c=>c.id!==id);state.activeCloneId=null;
  syncView();labMessage("SANDBOX CLONE DELETED / no source records modified.");
}
function exportClone(){
  const cl=activeClone();if(!cl){labMessage("SELECT A CLONE TO EXPORT");return;}
  const data={schema:"xunia.cl1.virtual-planet-clone.v1",kind:"nonphysical-simulation",
    source_catalog:"xunia.cl1.planet-twins.v1",source_planet:cl.sourceId,
    cloned_settings:{diameter_scale:cl.diameterScale,rotation_multiplier:cl.spin,cloud_glow_percent:cl.glow},
    simulation_date:formatDate(state.dateMs),scientific_accuracy:"Original physical numbers are sourced; edits are hypothetical. Not an engineering plan."};
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+"\n"],{type:"application/json"}));
  const a=document.createElement("a");a.href=url;a.download="cl1-"+cl.id+".json";
  document.body.appendChild(a);a.click();a.remove();
  window.setTimeout(()=>URL.revokeObjectURL(url),1500);
  labMessage("CLONE JSON GENERATED LOCALLY / "+cl.name);
}
function tune(which,raw){
  const cl=activeClone();if(!cl){labMessage("CREATE OR SELECT A CLONE FIRST");return false;}
  const value=Number(raw);if(!Number.isFinite(value))return false;
  if(which==="radius"&&value>=.5&&value<=2){cl.diameterScale=value;
  }else if(which==="spin"&&value>=-2&&value<=2){cl.spin=value;
  }else if(which==="glow"&&value>=0&&value<=100){cl.glow=value;
  }else{return false;}
  updateInspector();updateClonePanel();mark();
  labMessage(cl.name+" / "+which.toUpperCase()+" = "+value+" / virtual only.");
  return true;
}
function updatePlayButton(){
  $("playPause").setAttribute("aria-pressed",String(state.playing));
  $("playPause").textContent=state.playing?"PAUSE ORBITS":"PLAY ORBITS";
}
function togglePlay(){
  state.playing=!state.playing;updatePlayButton();mark();
}
function setZoom(z){if(!Number.isFinite(z)||z<.45||z>2.7)return false;state.zoom=z;mark();return true}
function dispatch(raw){
  const line=String(raw||"").trim().replace(/^\//,"");
  const sp=line.indexOf(" "),command=(sp<0?line:line.slice(0,sp)).toLowerCase();
  const arg=sp<0?"":line.slice(sp+1).trim();
  if(command==="help"){message("/planet NAME · /clone · /select ID · /delete · /radius 0.5–2 · /spin −2–2 · /glow 0–100 · /date YYYY-MM-DD · /speed 1|30|365 · /zoom 0.45–2.7 · /play · /pause · /export · /reset");return;}
  if(command==="planet"){
    const found=state.planets.find(p=>p.id===arg.toLowerCase()||p.name.toLowerCase()===arg.toLowerCase());
    message(found&&selectPlanet(found.id)?"REFERENCE PLANET / "+found.name:"PLANET NOT FOUND / choose Mercury–Neptune");return;
  }
  if(command==="clone"){const cl=clonePlanet();message(cl?"CLONED IN SESSION / "+cl.name:"SANDBOX LIMIT / 4 CLONES");return;}
  if(command==="select"){message(selectClone(arg.toLowerCase())?"SANDBOX CLONE SELECTED":"UNKNOWN CLONE ID");return;}
  if(command==="delete"){removeClone();message("SANDBOX DELETE REQUEST COMPLETE");return;}
  if(command==="radius"||command==="spin"||command==="glow"){
    message(tune(command,arg)?"VIRTUAL "+command.toUpperCase()+" UPDATED":"INVALID "+command.toUpperCase()+" OR NO ACTIVE CLONE");return;
  }
  if(command==="date"){message(setDate(arg)?"SIMULATION DATE / "+arg:"DATE MUST BE VALID / 1800–2050");return;}
  if(command==="speed"){
    const v=Number(arg);
    if(!["1","30","365"].includes(arg)){message("SPEED MUST BE 1, 30 OR 365 d/s");return;}
    state.speed=v;$("timeSpeed").value=String(v);message("SIMULATION SPEED / "+v+" DAYS/SECOND");return;
  }
  if(command==="zoom"){message(arg&&setZoom(Number(arg))?"CAMERA ZOOM / "+state.zoom.toFixed(2):"ZOOM RANGE / 0.45–2.7");return;}
  if(command==="play"){state.playing=true;updatePlayButton();message("ORBIT PLAYBACK ACTIVE");mark();return;}
  if(command==="pause"){state.playing=false;updatePlayButton();message("ORBIT PLAYBACK PAUSED");return;}
  if(command==="export"){exportClone();message("EXPORT / see CL1 sandbox status");return;}
  if(command==="reset"){state.playing=false;updatePlayButton();Object.assign(state,{zoom:1,yaw:.24,pitch:.72,panX:0,panY:0,globeYaw:0});
    state.activeCloneId=null;syncView();message("VIEW RESET / SOURCE CATALOG INTACT");return;}
  message("UNKNOWN COMMAND / ENTER /help");
}
function wire(){
  $("createClone").addEventListener("click",clonePlanet);
  $("removeClone").addEventListener("click",removeClone);
  $("exportClone").addEventListener("click",exportClone);
  for(const [id,key] of [["cloneRadius","radius"],["cloneSpin","spin"],["cloneGlow","glow"]]){
    $(id).addEventListener("input",e=>tune(key,e.target.value));
  }
  $("epochDate").addEventListener("change",e=>{if(!setDate(e.target.value))message("INVALID DATE / 1800–2050")});
  $("nowDate").addEventListener("click",()=>{const today=new Date().toISOString().slice(0,10);if(!setDate(today))message("SYSTEM DATE OUTSIDE VALIDITY RANGE");});
  $("stepDate").addEventListener("click",()=>{const ms=Math.min(MAX,state.dateMs+30*DAY);setDate(formatDate(ms));});
  $("playPause").addEventListener("click",togglePlay);
  $("timeSpeed").addEventListener("change",e=>{state.speed=Number(e.target.value)});
  $("zoomOut").addEventListener("click",()=>setZoom(clamp(state.zoom/1.18,.45,2.7)));
  $("zoomIn").addEventListener("click",()=>setZoom(clamp(state.zoom*1.18,.45,2.7)));
  $("viewReset").addEventListener("click",()=>{state.zoom=1;state.yaw=.24;state.pitch=.72;state.panX=0;state.panY=0;mark()});
  $("labelsToggle").addEventListener("click",()=>{
    state.labels=!state.labels;$("labelsToggle").textContent="LABELS "+(state.labels?"ON":"OFF");
    $("labelsToggle").setAttribute("aria-pressed",String(state.labels));mark();
  });
  $("commandForm").addEventListener("submit",e=>{
    e.preventDefault();dispatch($("commandInput").value);$("commandInput").value="";
  });
  document.addEventListener("keydown",e=>{
    const tag=document.activeElement?.tagName||"",editing=["INPUT","TEXTAREA","SELECT"].includes(tag);
    if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){
      e.preventDefault();$("commandInput").focus();
    }else if(e.key==="Escape"&&document.activeElement===$("commandInput")){
      e.preventDefault();orrery.focus();
    }else if(!editing&&e.key>="1"&&e.key<="8"){
      const index=Number(e.key)-1;if(state.planets[index]){e.preventDefault();selectPlanet(state.planets[index].id);}
    }else if(!editing&&e.code==="Space"){e.preventDefault();togglePlay();}
  });
  function coord(e,canvas){const r=canvas.getBoundingClientRect();return [e.clientX-r.left,e.clientY-r.top]}
  orrery.addEventListener("pointerdown",e=>{
    if(e.button!==0)return;
    const [x,y]=coord(e,orrery);
    state.drag={x,y,total:0,id:e.pointerId};orrery.setPointerCapture(e.pointerId);orrery.focus();
  });
  orrery.addEventListener("pointermove",e=>{
    if(!state.drag)return;const [x,y]=coord(e,orrery);
    const dx=x-state.drag.x,dy=y-state.drag.y;
    state.drag.total+=Math.hypot(dx,dy);state.drag.x=x;state.drag.y=y;
    if(state.drag.total>=5){
      state.yaw+=dx*.006;state.pitch=clamp(state.pitch+dy*.004,.10,1.48);mark();
    }
  });
  orrery.addEventListener("pointerup",e=>{
    if(!state.drag)return;const drag=state.drag;state.drag=null;
    if(drag.total>5)return;
    const [x,y]=coord(e,orrery);
    let nearest=null,best=18;
    for(const p of state.orbitPoints){
      const distance=Math.hypot(x-p.x,y-p.y);
      if(distance<best){best=distance;nearest=p;}
    }
    if(nearest)selectPlanet(nearest.id);
  });
  for(const name of ["pointercancel","lostpointercapture"]){
    orrery.addEventListener(name,()=>{state.drag=null});
  }
  orrery.addEventListener("wheel",e=>{
    e.preventDefault();setZoom(clamp(state.zoom*(e.deltaY<0?1.11:.90),.45,2.7));
  },{passive:false});
  orrery.addEventListener("keydown",e=>{
    const idx=state.planets.findIndex(p=>p.id===state.planet);
    if(e.key==="ArrowRight")selectPlanet(state.planets[(idx+1)%8].id);
    else if(e.key==="ArrowLeft")selectPlanet(state.planets[(idx+7)%8].id);
    else if(e.key==="ArrowUp")state.pitch=clamp(state.pitch+.10,.1,1.48);
    else if(e.key==="ArrowDown")state.pitch=clamp(state.pitch-.10,.1,1.48);
    else return;e.preventDefault();mark();
  });
  globe.addEventListener("pointerdown",e=>{
    if(e.button!==0)return;state.globeDrag=e.clientX;globe.setPointerCapture(e.pointerId);
  });
  globe.addEventListener("pointermove",e=>{
    if(state.globeDrag===null)return;
    state.globeYaw+=(e.clientX-state.globeDrag)*.022;state.globeDrag=e.clientX;mark();
  });
  for(const name of ["pointerup","pointercancel","lostpointercapture"]){
    globe.addEventListener(name,()=>{state.globeDrag=null});
  }
  window.addEventListener("resize",mark);
}
function loop(time){
  if(!state.ready)return;
  const dt=state.lastTime?Math.min(.1,(time-state.lastTime)/1000):0;
  state.lastTime=time;
  if(state.playing){
    state.dateMs+=dt*state.speed*DAY;
    if(state.dateMs>=MAX){state.dateMs=MAX;state.playing=false;updatePlayButton();message("JPL APPROXIMATION LIMIT / 2050-12-31");}
    state.dirty=true;
  }
  if(state.dirty && time-state.lastDraw>=80){
    state.lastDraw=time;state.dirty=false;
    $("epochDate").value=formatDate(state.dateMs);
    renderOrbits();updateInspector();renderGlobe();
  }
  window.requestAnimationFrame(loop);
}
async function boot(){
  wire();
  if(!oc||!gc||!tc){message("CANVAS UNSUPPORTED / BROWSER RENDERING UNAVAILABLE");return;}
  try{
    const response=await fetch("./catalog.json",{credentials:"omit",cache:"no-store"});
    if(!response.ok)throw Error("PLANETARY REFERENCE DATA MISSING");
    const catalog=await response.json();
    if(catalog.schema!=="xunia.cl1.planet-twins.v1"||!Array.isArray(catalog.planets)||
       catalog.planets.length!==8)throw Error("INVALID CL1 ONTOLOGY");
    for(const p of catalog.planets){
      if(!p.id||!p.name||!Array.isArray(p.elements_j2000)||p.elements_j2000.length!==6||
         !Array.isArray(p.rates_per_century)||p.rates_per_century.length!==6||
         !p.elements_j2000.every(Number.isFinite)||!p.rates_per_century.every(Number.isFinite)||
         !Number.isFinite(p.diameter_km)||p.diameter_km<=0||state.byId.has(p.id)){
        throw Error("CORRUPTED PLANET REFERENCE");
      }
      state.byId.set(p.id,p);
    }
    state.planets=catalog.planets;
    const today=new Date().toISOString().slice(0,10);
    if(setDate(today)){state.playing=false;updatePlayButton();}
    state.ready=true;syncView();message("CL1 PLANETARY FORGE / 8 NASA/JPL REFERENCE PLANETS LOADED");
    window.requestAnimationFrame(loop);
  }catch(err){message("CL1 CATALOG LOAD FAILED / "+String(err.message).slice(0,120));$("orbitStatus").textContent="DATA UNAVAILABLE";}
}
boot();
})();
