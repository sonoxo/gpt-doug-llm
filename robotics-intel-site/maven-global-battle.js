(() => {
  "use strict";

  const canvas=document.getElementById("globalBattleCanvas");
  const logEl=document.getElementById("globalBattleLog");
  if(!canvas||!logEl) return;

  const ctx=canvas.getContext("2d");
  let w=1,h=1,dpr=1,last=performance.now();
  let stance="defense";
  const layers={land:true,air:true,sea:true};
  const liveLayers={weather:true,quakes:true,events:true,marine:true};
  const effects=[];

  const liveData={
    weather:[],
    quakes:[],
    events:[],
    marine:[],
    updatedAt:null
  };

  const weatherNodes=[
    ["New York",40.71,-74.01],["Mexico City",19.43,-99.13],["São Paulo",-23.55,-46.63],
    ["London",51.51,-0.13],["Cairo",30.04,31.24],["Nairobi",-1.29,36.82],
    ["Cape Town",-33.92,18.42],["Mumbai",19.08,72.88],["Singapore",1.35,103.82],
    ["Tokyo",35.68,139.69],["Sydney",-33.87,151.21],["Honolulu",21.31,-157.86]
  ];

  const marineNodes=[
    ["North Atlantic",42,-35],["Gulf of Mexico",24,-90],["South Atlantic",-25,-20],
    ["Mediterranean",35,18],["Indian Ocean",-15,75],["South China Sea",12,114],
    ["North Pacific",35,-150],["South Pacific",-28,-130]
  ];

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
    w=Math.max(1,r.width);
    h=Math.max(1,r.height);
    canvas.width=Math.round(w*dpr);
    canvas.height=Math.round(h*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  new ResizeObserver(resize).observe(canvas);

  function log(msg){
    const row=document.createElement("div");
    row.textContent="["+new Date().toLocaleTimeString()+"] "+msg;
    logEl.prepend(row);
    while(logEl.children.length>28) logEl.removeChild(logEl.lastChild);
  }

  function coarse(value){
    return Math.round(Number(value)*10)/10;
  }

  function worldToXY(lon,lat){
    return [(Number(lon)+180)/360*w,(90-Number(lat))/180*h];
  }

  async function fetchJson(url,timeout=10000){
    const ctl=new AbortController();
    const timer=setTimeout(()=>ctl.abort(),timeout);
    try{
      const response=await fetch(url,{cache:"no-store",signal:ctl.signal,headers:{Accept:"application/json"}});
      if(!response.ok) throw new Error("HTTP "+response.status);
      return await response.json();
    }finally{
      clearTimeout(timer);
    }
  }

  function setStance(next){
    stance=next;
    document.getElementById("battleStance").textContent=next.toUpperCase()+" SIM";
    document.querySelectorAll("[data-stance]").forEach(b=>b.classList.toggle("active",b.dataset.stance===next));
    log("Synthetic "+next+" posture enabled; live public context remains read-only");
  }

  function setLayer(domain){
    layers[domain]=!layers[domain];
    document.querySelector('[data-domain="'+domain+'"]')?.classList.toggle("active",layers[domain]);
    log(domain.toUpperCase()+" synthetic domain "+(layers[domain]?"enabled":"hidden"));
  }

  function setLiveLayer(name){
    liveLayers[name]=!liveLayers[name];
    document.querySelector('[data-live-layer="'+name+'"]')?.classList.toggle("active",liveLayers[name]);
    log(name.toUpperCase()+" live context "+(liveLayers[name]?"visible":"hidden"));
  }

  function addEffect(type){
    effects.push({type,start:performance.now(),duration:type==="fortify"?6500:type==="advance"?5000:4200});
    log(type.replaceAll("-"," ").toUpperCase()+" deployed in synthetic space only");
  }

  async function loadWeather(){
    const out=[];
    for(const [name,lat,lon] of weatherNodes){
      try{
        const url="https://api.open-meteo.com/v1/forecast?latitude="+encodeURIComponent(lat)+
          "&longitude="+encodeURIComponent(lon)+
          "&current=temperature_2m,wind_speed_10m,wind_direction_10m&timezone=UTC";
        const d=await fetchJson(url);
        const cur=d.current||{};
        out.push({
          name,
          lat:coarse(lat),
          lon:coarse(lon),
          temp:Number(cur.temperature_2m),
          wind:Number(cur.wind_speed_10m),
          dir:Number(cur.wind_direction_10m)
        });
      }catch{}
    }
    liveData.weather=out;
    document.getElementById("liveWeatherCount").textContent=String(out.length);
    return out.length;
  }

  async function loadQuakes(){
    try{
      const d=await fetchJson("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson");
      liveData.quakes=(d.features||[]).slice(0,50).map(f=>{
        const c=f.geometry&&f.geometry.coordinates;
        if(!Array.isArray(c)||c.length<2) return null;
        return {
          lat:coarse(c[1]),
          lon:coarse(c[0]),
          mag:Number(f.properties&&f.properties.mag),
          place:String((f.properties&&f.properties.place)||"Earthquake")
        };
      }).filter(Boolean);
    }catch{
      liveData.quakes=[];
    }
    document.getElementById("liveQuakeCount").textContent=String(liveData.quakes.length);
    return liveData.quakes.length;
  }

  function eventCoords(geometry){
    if(!geometry) return null;
    const g=geometry.coordinates;
    if(geometry.type==="Point"&&Array.isArray(g)) return g;
    if(geometry.type==="Polygon"&&Array.isArray(g?.[0]?.[0])) return g[0][0];
    if(geometry.type==="MultiPolygon"&&Array.isArray(g?.[0]?.[0]?.[0])) return g[0][0][0];
    return null;
  }

  async function loadEvents(){
    try{
      const d=await fetchJson("https://eonet.gsfc.nasa.gov/api/v3/events/geojson?status=open&limit=80");
      liveData.events=(d.features||[]).slice(0,60).map(f=>{
        const c=eventCoords(f.geometry);
        if(!c) return null;
        return {
          lat:coarse(c[1]),
          lon:coarse(c[0]),
          title:String((f.properties&&f.properties.title)||"Open natural event")
        };
      }).filter(x=>x&&Number.isFinite(x.lat)&&Number.isFinite(x.lon));
    }catch{
      liveData.events=[];
    }
    document.getElementById("liveEventCount").textContent=String(liveData.events.length);
    return liveData.events.length;
  }

  async function loadMarine(){
    const out=[];
    for(const [name,lat,lon] of marineNodes){
      try{
        const url="https://marine-api.open-meteo.com/v1/marine?latitude="+encodeURIComponent(lat)+
          "&longitude="+encodeURIComponent(lon)+
          "&current=wave_height,sea_surface_temperature,ocean_current_velocity,ocean_current_direction&timezone=UTC";
        const d=await fetchJson(url);
        const cur=d.current||{};
        out.push({
          name,
          lat:coarse(lat),
          lon:coarse(lon),
          wave:Number(cur.wave_height),
          sst:Number(cur.sea_surface_temperature),
          current:Number(cur.ocean_current_velocity),
          dir:Number(cur.ocean_current_direction)
        });
      }catch{}
    }
    liveData.marine=out;
    document.getElementById("liveMarineCount").textContent=String(out.length);
    return out.length;
  }

  let refreshing=false;
  async function refreshLiveWorld(){
    if(refreshing) return;
    refreshing=true;
    const status=document.getElementById("liveWorldStatus");
    status.textContent="LIVE WORLD REFRESHING";
    status.classList.remove("degraded");
    const counts=await Promise.all([loadWeather(),loadQuakes(),loadEvents(),loadMarine()]);
    liveData.updatedAt=Date.now();
    const total=counts.reduce((a,b)=>a+b,0);
    const healthy=counts.filter(n=>n>0).length;
    status.textContent=healthy>=3?"LIVE WORLD ONLINE":"LIVE WORLD PARTIAL";
    status.classList.toggle("degraded",healthy<3);
    log("Live public context refreshed: "+total+" coarse observations across "+healthy+"/4 source layers");
    refreshing=false;
  }

  function drawWorld(){
    ctx.fillStyle="#020604";
    ctx.fillRect(0,0,w,h);
    ctx.strokeStyle="rgba(130,232,255,.045)";
    ctx.lineWidth=1;

    for(let lon=-180;lon<=180;lon+=30){
      const [x]=worldToXY(lon,0);
      ctx.beginPath();
      ctx.moveTo(x,0);
      ctx.lineTo(x,h);
      ctx.stroke();
    }
    for(let lat=-60;lat<=60;lat+=30){
      const [,y]=worldToXY(0,lat);
      ctx.beginPath();
      ctx.moveTo(0,y);
      ctx.lineTo(w,y);
      ctx.stroke();
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
      poly.forEach(([lon,lat],i)=>{
        const [x,y]=worldToXY(lon,lat);
        i?ctx.lineTo(x,y):ctx.moveTo(x,y);
      });
      ctx.closePath();
      ctx.fill();
    }
  }

  function drawLiveWeather(){
    if(!liveLayers.weather) return;
    for(const p of liveData.weather){
      const [x,y]=worldToXY(p.lon,p.lat);
      ctx.save();
      ctx.translate(x,y);
      ctx.strokeStyle="rgba(130,232,255,.78)";
      ctx.fillStyle="rgba(130,232,255,.14)";
      ctx.lineWidth=1.2;
      ctx.beginPath();
      ctx.arc(0,0,4.5,0,Math.PI*2);
      ctx.fill();
      ctx.stroke();

      if(Number.isFinite(p.dir)&&Number.isFinite(p.wind)){
        const a=(p.dir-90)*Math.PI/180;
        const len=8+Math.min(12,p.wind*.22);
        ctx.beginPath();
        ctx.moveTo(0,0);
        ctx.lineTo(Math.cos(a)*len,Math.sin(a)*len);
        ctx.stroke();
      }
      ctx.fillStyle="#82e8ff";
      ctx.font="7px monospace";
      if(Number.isFinite(p.temp)) ctx.fillText(Math.round(p.temp)+"°C",7,-5);
      ctx.restore();
    }
  }

  function drawLiveQuakes(){
    if(!liveLayers.quakes) return;
    for(const q of liveData.quakes){
      const [x,y]=worldToXY(q.lon,q.lat);
      const radius=Math.max(3.5,Math.min(8,Number.isFinite(q.mag)?q.mag:4.5));
      ctx.strokeStyle="rgba(255,140,90,.8)";
      ctx.fillStyle="rgba(255,140,90,.10)";
      ctx.lineWidth=1.2;
      ctx.beginPath();
      ctx.arc(x,y,radius,0,Math.PI*2);
      ctx.fill();
      ctx.stroke();
    }
  }

  function drawLiveEvents(){
    if(!liveLayers.events) return;
    for(const e of liveData.events){
      const [x,y]=worldToXY(e.lon,e.lat);
      ctx.save();
      ctx.translate(x,y);
      ctx.rotate(Math.PI/4);
      ctx.strokeStyle="rgba(215,255,100,.74)";
      ctx.strokeRect(-3.5,-3.5,7,7);
      ctx.restore();
    }
  }

  function drawLiveMarine(){
    if(!liveLayers.marine) return;
    for(const p of liveData.marine){
      const [x,y]=worldToXY(p.lon,p.lat);
      ctx.strokeStyle="rgba(200,164,255,.82)";
      ctx.fillStyle="rgba(200,164,255,.10)";
      ctx.lineWidth=1.2;
      ctx.beginPath();
      ctx.arc(x,y,5.5,0,Math.PI*2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle="#c8a4ff";
      ctx.font="7px monospace";
      if(Number.isFinite(p.wave)) ctx.fillText(p.wave.toFixed(1)+"m",7,-5);
    }
  }

  function drawLiveWorld(){
    drawLiveWeather();
    drawLiveQuakes();
    drawLiveEvents();
    drawLiveMarine();
  }

  function drawUnit(u){
    if(!layers[u.domain]) return;
    const x=u.x*w,y=u.y*h;
    const color=u.domain==="land"?"#9cffaa":u.domain==="air"?"#82e8ff":"#c8a4ff";

    ctx.save();
    ctx.translate(x,y);
    ctx.strokeStyle=color;
    ctx.fillStyle=color;
    ctx.lineWidth=1.25;

    if(u.domain==="land"){
      ctx.strokeRect(-5,-4,10,8);
      ctx.beginPath();
      ctx.moveTo(-7,5);
      ctx.lineTo(7,5);
      ctx.stroke();
    }else if(u.domain==="air"){
      ctx.beginPath();
      ctx.moveTo(-8,0);
      ctx.lineTo(8,0);
      ctx.moveTo(0,-6);
      ctx.lineTo(3,5);
      ctx.stroke();
    }else{
      ctx.beginPath();
      ctx.moveTo(-8,3);
      ctx.lineTo(7,3);
      ctx.lineTo(3,7);
      ctx.lineTo(-5,7);
      ctx.closePath();
      ctx.stroke();
    }

    ctx.font="7px monospace";
    ctx.fillText(u.id,9,-6);
    ctx.restore();
  }

  function update(dt){
    const pace=stance==="offense"?1.25:.72;
    for(const u of units){
      u.x+=u.vx*pace*dt/1000;
      u.y+=u.vy*pace*dt/1000;
      if(u.x<.03||u.x>.97) u.vx*=-1;
      if(u.y<.08||u.y>.92) u.vy*=-1;
    }

    const now=performance.now();
    for(let i=effects.length-1;i>=0;i--){
      if(now-effects[i].start>effects[i].duration) effects.splice(i,1);
    }
  }

  function drawEffects(ts){
    for(const e of effects){
      const p=Math.min(1,(ts-e.start)/e.duration);

      if(e.type==="fortify"){
        ctx.strokeStyle="rgba(156,255,170,"+(1-p)+")";
        ctx.lineWidth=2;
        for(let i=0;i<4;i++){
          ctx.beginPath();
          ctx.arc(w*(.2+i*.2),h*.5,28+Math.sin(ts*.004+i)*5,0,Math.PI*2);
          ctx.stroke();
        }
      }else if(e.type==="intercept"){
        ctx.strokeStyle="rgba(130,232,255,"+(1-p)+")";
        for(let i=0;i<8;i++){
          ctx.beginPath();
          ctx.moveTo(w*.5,h*.5);
          ctx.lineTo((i/7)*w,(i%2?0:h));
          ctx.stroke();
        }
      }else if(e.type==="decoy"){
        ctx.fillStyle="rgba(130,232,255,"+(1-p)+")";
        for(let i=0;i<18;i++){
          const a=i*.7+ts*.001;
          ctx.beginPath();
          ctx.arc(w*.5+Math.cos(a)*w*.28,h*.5+Math.sin(a)*h*.24,2,0,Math.PI*2);
          ctx.fill();
        }
      }else if(e.type==="repair"){
        ctx.fillStyle="rgba(156,255,170,"+(1-p)*.1+")";
        ctx.fillRect(0,0,w,h);
      }else if(e.type==="advance"){
        ctx.strokeStyle="rgba(255,177,29,"+(1-p)+")";
        ctx.lineWidth=2;
        for(let i=0;i<6;i++){
          const y=h*(.18+i*.12);
          ctx.beginPath();
          ctx.moveTo(w*.1,y);
          ctx.lineTo(w*(.1+.75*p),y);
          ctx.stroke();
        }
      }else if(e.type==="flank"){
        ctx.strokeStyle="rgba(255,177,29,"+(1-p)+")";
        ctx.beginPath();
        ctx.arc(w*.5,h*.5,p*Math.min(w,h)*.62,Math.PI*.15,Math.PI*1.4);
        ctx.stroke();
      }else if(e.type==="pressure"){
        ctx.strokeStyle="rgba(255,140,90,"+(1-p)+")";
        ctx.beginPath();
        ctx.arc(w*.5,h*.5,p*Math.min(w,h)*.68,0,Math.PI*2);
        ctx.stroke();
      }else if(e.type==="breakthrough"){
        ctx.strokeStyle="rgba(255,209,102,"+(1-p)+")";
        ctx.lineWidth=3;
        ctx.beginPath();
        ctx.moveTo(w*.15,h*.78);
        ctx.lineTo(w*(.15+.7*p),h*.22);
        ctx.stroke();
      }
    }
  }

  function frame(ts){
    const dt=Math.min(40,ts-last);
    last=ts;
    drawWorld();
    drawLiveWorld();
    update(dt);
    drawEffects(ts);
    units.forEach(drawUnit);
    requestAnimationFrame(frame);
  }

  document.querySelectorAll("[data-stance]").forEach(b=>b.addEventListener("click",()=>setStance(b.dataset.stance)));
  document.querySelectorAll("[data-domain]").forEach(b=>b.addEventListener("click",()=>setLayer(b.dataset.domain)));
  document.querySelectorAll("[data-live-layer]").forEach(b=>b.addEventListener("click",()=>setLiveLayer(b.dataset.liveLayer)));
  document.querySelectorAll("[data-action]").forEach(b=>b.addEventListener("click",()=>addEffect(b.dataset.action)));
  document.getElementById("refreshLiveWorld")?.addEventListener("click",refreshLiveWorld);

  document.getElementById("landCount").textContent=String(units.filter(u=>u.domain==="land").length);
  document.getElementById("airCount").textContent=String(units.filter(u=>u.domain==="air").length);
  document.getElementById("seaCount").textContent=String(units.filter(u=>u.domain==="sea").length);

  resize();
  setStance("defense");
  refreshLiveWorld();
  setInterval(refreshLiveWorld,10*60*1000);
  requestAnimationFrame(frame);
})();
