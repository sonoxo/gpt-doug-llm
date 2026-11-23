// Canvas-based 3-D orthographic Earth. Geography = Natural Earth public domain.
// Illumination = UTC solar ephemeris; event positions = USGS/NASA/NOAA published coordinates.
// The gently rotating camera, outline and glow are *display effects*, not sensor data.
import {projectOrthographic,subsolarPoint,finite} from "./model-core.mjs";

const PI=Math.PI,rad=PI/180,clamp=(n,a,b)=>Math.min(b,Math.max(a,n));
function markerColor(e){return e.kind==="earthquake"?"#ffc061":"#4bedef";}
export class EarthRenderer{
 constructor(canvas,onSelect=()=>{}){
  this.canvas=canvas;this.ctx=canvas.getContext("2d",{alpha:false});
  if(!this.ctx)throw Error("2D canvas unsupported");
  this.onSelect=onSelect;this.camera={lat:20,lon:-65,zoom:1};
  this.layers={aurora:true,earthquakes:true,natural:true,graticule:true};
  this.cells=[];this.events=[];this.targets=[];
  this.running=true;this.autoRotate=false;this.dirty=true;this.lastTick=0;this.sunTick=0;
  this.tW=1000;this.tH=500;this.texPixels=null;this.time=Date.now();this.sun=subsolarPoint(this.time);
  this.res=420;
  this.sphere=document.createElement("canvas");this.sphere.width=this.res;this.sphere.height=this.res;
  this.sphereCtx=this.sphere.getContext("2d",{willReadFrequently:false});
  this.geo=new Float32Array(this.res*this.res*3);
  const r=this.res/2-2;
  for(let j=0;j<this.res;j++)for(let i=0;i<this.res;i++){
   const x=(i+0.5-this.res/2)/r,y=(this.res/2-j-0.5)/r,z2=1-x*x-y*y,k=(j*this.res+i)*3;
   this.geo[k]=x;this.geo[k+1]=y;this.geo[k+2]=z2>0?Math.sqrt(z2):-1;
  }
  this.loadTexture();this.bind();this.resize();
  this.resizeObserver=typeof ResizeObserver!=="undefined"?new ResizeObserver(()=>this.resize()):null;
  this.resizeObserver?.observe(this.canvas);
  this.frame=this.frame.bind(this);requestAnimationFrame(this.frame);
 }
 loadTexture(){
  const img=new Image();
  img.onload=()=>{
   try{
    const tex=document.createElement("canvas");tex.width=this.tW;tex.height=this.tH;
    const c=tex.getContext("2d",{willReadFrequently:true});c.clearRect(0,0,this.tW,this.tH);
    c.drawImage(img,0,0,this.tW,this.tH);
    this.texPixels=c.getImageData(0,0,this.tW,this.tH).data;this.dirty=true;
   }catch{this.texPixels=null;}
  };
  img.onerror=()=>{this.texPixels=null;this.dirty=true;};
  img.src="../global/world-land.svg";
 }
 bind(){
  const c=this.canvas;let pointer=null;
  c.addEventListener("pointerdown",e=>{pointer={x:e.clientX,y:e.clientY,id:e.pointerId,moved:false};c.setPointerCapture(e.pointerId);});
  c.addEventListener("pointermove",e=>{
   if(!pointer||e.pointerId!==pointer.id)return;
   const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;
   if(Math.abs(dx)+Math.abs(dy)>0){pointer.moved=pointer.moved||Math.abs(dx)+Math.abs(dy)>2;
    this.camera.lon=((this.camera.lon-dx*.38+540)%360)-180;
    this.camera.lat=clamp(this.camera.lat+dy*.30,-78,78);
    this.autoRotate=false;this.dirty=true;}
   pointer.x=e.clientX;pointer.y=e.clientY;
  });
  c.addEventListener("pointerup",e=>{
   if(!pointer||pointer.id!==e.pointerId)return;
   if(!pointer.moved)this.pick(e);
   pointer=null;
  });
  c.addEventListener("pointercancel",()=>{pointer=null;});
  c.addEventListener("wheel",e=>{
   e.preventDefault();this.camera.zoom=clamp(this.camera.zoom-e.deltaY*.001,.72,1.50);this.dirty=true;
  },{passive:false});
  c.addEventListener("keydown",e=>{
   const moves={ArrowLeft:[0,-9],ArrowRight:[0,9],ArrowUp:[8,0],ArrowDown:[-8,0]};
   if(moves[e.key]){e.preventDefault();this.rotate(...moves[e.key]);}
   else if(e.key==="+"){this.zoom(0.1);}
   else if(e.key==="-"){this.zoom(-0.1);}
  });
 }
 resize(){
  const rect=this.canvas.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);
  const w=Math.max(340,Math.round(rect.width*dpr)),h=Math.max(280,Math.round(rect.height*dpr));
  if(this.canvas.width!==w||this.canvas.height!==h){this.canvas.width=w;this.canvas.height=h;this.dirty=true;}
 }
 setData(cells,events){this.cells=Array.isArray(cells)?cells.slice(0,2200):[];this.events=Array.isArray(events)?events.slice(0,200):[];}
 setLayer(name,val){if(Object.hasOwn(this.layers,name)){this.layers[name]=!!val;this.dirty=true;}}
 rotate(lat,lon){this.camera.lat=clamp(this.camera.lat+lat,-78,78);this.camera.lon=((this.camera.lon+lon+540)%360)-180;this.dirty=true;}
 zoom(amount){this.camera.zoom=clamp(this.camera.zoom+amount,.72,1.50);this.dirty=true;}
 reset(){this.camera={lat:20,lon:-65,zoom:1};this.dirty=true;this.autoRotate=false;}
 setOrbit(flag){this.autoRotate=!!flag;}
 setPaused(paused){this.running=!paused;this.dirty=true;}
 position(lat,lon){
  const p=projectOrthographic(lat,lon,this.camera.lat,this.camera.lon);
  if(!p?.visible)return null;
  const W=this.canvas.width,H=this.canvas.height,R=Math.min(W*.43,H*.46)*this.camera.zoom;
  return {x:W*.5+p.x*R,y:H*.52-p.y*R,z:p.z,r:R};
 }
 pick(e){
  const rect=this.canvas.getBoundingClientRect();
  const x=(e.clientX-rect.left)*this.canvas.width/rect.width,y=(e.clientY-rect.top)*this.canvas.height/rect.height;
  let best=null,dist=20*(this.canvas.width/rect.width);
  for(const t of this.targets){const d=Math.hypot(x-t.x,y-t.y);if(d<dist){dist=d;best=t.item;}}
  if(best)this.onSelect(best);
 }
 repaintSphere(){
  const N=this.res,image=this.sphereCtx.createImageData(N,N),out=image.data;
  const a=this.camera.lat*rad,b=this.camera.lon*rad;
  const sinA=Math.sin(a),cosA=Math.cos(a),sinB=Math.sin(b),cosB=Math.cos(b);
  const east=[cosB,0,-sinB],north=[-sinA*sinB,cosA,-sinA*cosB],front=[cosA*sinB,sinA,cosA*cosB];
  const ss=this.sun.lat*rad,sl=this.sun.lon*rad;
  const sun=[Math.cos(ss)*Math.sin(sl),Math.sin(ss),Math.cos(ss)*Math.cos(sl)];
  const tex=this.texPixels,W=this.tW,H=this.tH;
  for(let j=0;j<N*N;j++){
   const k=j*3,x=this.geo[k],y=this.geo[k+1],z=this.geo[k+2],o=j*4;
   if(z<0){out[o+3]=0;continue;}
   const px=x*east[0]+y*north[0]+z*front[0];
   const py=x*east[1]+y*north[1]+z*front[1];
   const pz=x*east[2]+y*north[2]+z*front[2];
   const lat=Math.asin(clamp(py,-1,1)),lon=Math.atan2(px,pz);
   const tx=clamp(Math.floor((lon/PI+.999999)*W/2),0,W-1);
   const ty=clamp(Math.floor((.5-lat/PI)*H),0,H-1);
   const land=tex?tex[(ty*W+tx)*4+3]>45:false;
   const dot=px*sun[0]+py*sun[1]+pz*sun[2];
   const light=.21+.78*clamp(dot+.06,0,1);
   const rim=Math.pow(1-z,4)*.3;
   let r=land?29:8,g=land?103:49,blue=land?93:92;
   if(land&&Math.abs(lat)>1.1){r=49;g=89;blue=94;}
   const sheen=!land?Math.pow(Math.max(0,dot),24)*33:0;
   out[o]=Math.min(255,Math.floor(r*light+rim*19+sheen));
   out[o+1]=Math.min(255,Math.floor(g*light+rim*65+sheen));
   out[o+2]=Math.min(255,Math.floor(blue*light+rim*106+sheen));
   out[o+3]=255;
  }
  this.sphereCtx.putImageData(image,0,0);this.dirty=false;
 }
 drawGraticule(ctx){
  if(!this.layers.graticule)return;
  ctx.save();ctx.lineWidth=1;ctx.strokeStyle="rgba(99,208,213,.17)";
  for(let lat=-60;lat<=60;lat+=30)this.traceLine(ctx,i=>projectOrthographic(lat,i,this.camera.lat,this.camera.lon),-180,180,3);
  for(let lon=-180;lon<180;lon+=30)this.traceLine(ctx,i=>projectOrthographic(i,lon,this.camera.lat,this.camera.lon),-89,89,3);
  ctx.restore();
 }
 traceLine(ctx,calc,from,to,step){
  let opened=false;ctx.beginPath();
  const W=this.canvas.width,H=this.canvas.height,R=Math.min(W*.43,H*.46)*this.camera.zoom;
  for(let x=from;x<=to;x+=step){
   const p=calc(x);
   if(!p?.visible){opened=false;continue;}
   const sx=W*.5+p.x*R,sy=H*.52-p.y*R;
   if(!opened){ctx.moveTo(sx,sy);opened=true;}else ctx.lineTo(sx,sy);
  }
  ctx.stroke();
 }
 drawMarkers(ctx,now){
  this.targets=[];
  const W=this.canvas.width,H=this.canvas.height,scale=W/Math.max(400,this.canvas.clientWidth);
  if(this.layers.aurora){
   ctx.save();ctx.globalCompositeOperation="screen";
   for(const c of this.cells){
    if(c.intensity<12)continue;
    const p=this.position(c.lat,c.lon);if(!p)continue;
    ctx.beginPath();ctx.fillStyle=c.intensity>55?"rgba(197,255,100,.56)":c.intensity>30?"rgba(85,243,198,.35)":"rgba(68,197,231,.22)";
    ctx.arc(p.x,p.y,Math.max(.7,1.15*scale+(c.intensity/100)*1.5*scale),0,PI*2);ctx.fill();
   }
   ctx.restore();
  }
  for(const e of this.events){
   if((e.kind==="earthquake"&&!this.layers.earthquakes)||(e.kind==="natural"&&!this.layers.natural))continue;
   const p=this.position(e.lat,e.lon);if(!p)continue;
   const base=(e.kind==="earthquake"?3.5+Math.max(0,(e.value||0)-4)*1.3:4.3)*scale;
   const phase=((now/1000+(e.observed%10000)/10000)%2.7)/2.7;
   ctx.strokeStyle=e.kind==="earthquake"?"rgba(255,180,93,.45)":"rgba(113,248,230,.42)";
   ctx.lineWidth=1.1*scale;ctx.beginPath();ctx.arc(p.x,p.y,base+phase*10*scale,0,2*PI);ctx.stroke();
   ctx.fillStyle=markerColor(e);ctx.beginPath();ctx.arc(p.x,p.y,Math.max(2,base),0,2*PI);ctx.fill();
   this.targets.push({x:p.x,y:p.y,item:e});
  }
 }
 drawFrame(now){
  const c=this.ctx,W=this.canvas.width,H=this.canvas.height;
  c.fillStyle="#06111e";c.fillRect(0,0,W,H);
  const gx=c.createRadialGradient(W*.5,H*.5,5,W*.5,H*.5,Math.max(W,H)*.57);
  gx.addColorStop(0,"#0e3345");gx.addColorStop(.6,"#071a28");gx.addColorStop(1,"#050d16");
  c.fillStyle=gx;c.fillRect(0,0,W,H);
  const R=Math.min(W*.43,H*.46)*this.camera.zoom,cx=W*.5,cy=H*.52;
  c.save();c.shadowColor="#18b9c8";c.shadowBlur=28;c.strokeStyle="rgba(48,207,225,.53)";
  c.lineWidth=Math.max(1,W/650);c.beginPath();c.arc(cx,cy,R,0,2*PI);c.stroke();c.restore();
  c.drawImage(this.sphere,cx-R,cy-R,2*R,2*R);
  if(!this.texPixels){c.fillStyle="rgba(15,22,29,.85)";c.font=(W/80)+"px monospace";c.fillText("LAND TEXTURE LOADING / NOT VERIFIED",16,H-20);}
  this.drawGraticule(c);this.drawMarkers(c,now);
  c.save();c.fillStyle="#a2e2dd";c.font=Math.max(11,W/88)+"px monospace";
  c.fillText("WGS84 / TRUE SOURCE COORDINATES",18,25);
  c.textAlign="right";c.fillText("UTC SOLAR ILLUMINATION / MODEL",W-18,25);
  c.textAlign="left";c.fillStyle="#739ca8";c.fillText("DRAG: ROTATE  •  SCROLL: ZOOM  •  CLICK: SOURCE",18,H-16);c.restore();
 }
 frame(now){
  if(this.running){
   if(now-this.lastTick>70){
    const stamp=Date.now();
    if(stamp-this.sunTick>60000){this.sun=subsolarPoint(stamp);this.sunTick=stamp;this.dirty=true;}
    if(this.autoRotate){this.camera.lon=((this.camera.lon+.11+540)%360)-180;this.dirty=true;}
    if(this.dirty)this.repaintSphere();
    this.drawFrame(now);this.lastTick=now;
   }
  }
  requestAnimationFrame(this.frame);
 }
}
