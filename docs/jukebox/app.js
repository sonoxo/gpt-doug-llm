const $=s=>document.querySelector(s);
const audio=$('#audio'),viz=$('#viz'),ctx=viz.getContext('2d'),status=$('#status'),results=$('#results'),queueEl=$('#queue'),now=$('#nowPlaying');
const vizMode=$('#vizMode'),autoTrip=$('#autoTrip'),vizWrap=$('#vizWrap'),vizBadge=$('#vizBadge'),vizEnergy=$('#vizEnergy'),vizStatus=$('#vizStatus'),tripBtn=$('#tripBtn');
let ac=null,analyser=null,source=null,raf=0,queue=[],manualTrip=false,externalPlaying=false,externalProvider='',ytPlayer=null,pendingYouTube=null;
const reducedMotion=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const stars=Array.from({length:150},()=>({x:Math.random()*2-1,y:Math.random()*2-1,z:Math.random()*.95+.05}));
const drops=Array.from({length:46},()=>({y:Math.random()*viz.height,s:2+Math.random()*8}));
const particles=Array.from({length:120},()=>({a:Math.random()*Math.PI*2,r:Math.random()*220,s:.6+Math.random()*2.4,z:Math.random()}));

function setStatus(t,c=''){status.textContent=t;status.className='status '+c}
function ensureAudio(){
  if(ac)return;
  const AC=window.AudioContext||window.webkitAudioContext;
  if(!AC){setStatus('Web Audio API unavailable in this browser.','error');return}
  ac=new AC();analyser=ac.createAnalyser();analyser.fftSize=2048;analyser.smoothingTimeConstant=.82;
  source=ac.createMediaElementSource(audio);source.connect(analyser);analyser.connect(ac.destination);
}
async function resumeAudio(){ensureAudio();if(ac&&ac.state==='suspended')try{await ac.resume()}catch(_){}}
function playUrl(url,title,{crossOrigin=false}={}){
  audio.pause();
  if(crossOrigin)audio.crossOrigin='anonymous';else audio.removeAttribute('crossorigin');
  audio.src=url;now.textContent=title||url;
  resumeAudio().then(()=>audio.play()).catch(()=>setStatus('Press play in the audio controls to start playback.','error'));
}
function addQueue(item){
  queue.push(item);queueEl.innerHTML='';
  queue.forEach(q=>{const li=document.createElement('li');li.textContent=q.title;li.tabIndex=0;
    const go=()=>playUrl(q.url,q.title,{crossOrigin:q.crossOrigin});
    li.addEventListener('click',go);li.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}});
    queueEl.append(li);
  });
}
function hue(h,a=1,l=55,s=100){return `hsla(${((h%360)+360)%360},${s}%,${l}%,${a})`}
function syntheticFeatures(t){
  const pulse=Math.max(0,Math.sin(t*3.7))*.24;
  const swing=(Math.sin(t*1.11)+Math.sin(t*2.37)+2)/8;
  const energy=.28+swing+pulse;
  return {energy,bass:.25+.25*Math.sin(t*2.1)**2,mid:.3+.22*Math.sin(t*3.3+.8)**2,treble:.24+.24*Math.sin(t*5.7+2)**2,freq:null,wave:null};
}
function liveFeatures(){
  if(!analyser)return syntheticFeatures(performance.now()/1000);
  const freq=new Uint8Array(analyser.frequencyBinCount),wave=new Uint8Array(analyser.fftSize);
  analyser.getByteFrequencyData(freq);analyser.getByteTimeDomainData(wave);
  const avg=(a,b)=>{let s=0,n=0;for(let i=a;i<b&&i<freq.length;i++){s+=freq[i];n++}return n?s/(n*255):0};
  const bass=avg(1,18),mid=avg(18,90),treble=avg(90,260),energy=Math.min(1,bass*.48+mid*.34+treble*.18);
  return {energy,bass,mid,treble,freq,wave};
}
function startVisuals(kind='MANUAL TRIP',provider=''){
  if(autoTrip.checked)vizMode.value='trip';
  externalProvider=provider||externalProvider;
  if(kind.startsWith('LINKED'))externalPlaying=true;
  manualTrip=kind==='MANUAL TRIP'?true:manualTrip;
  vizBadge.textContent='RETROVIZ 95 // '+kind;
  vizStatus.textContent=kind.startsWith('LINKED')
    ?`${provider} playback linked. Visuals stay active using an ambient trip engine because embedded players do not expose raw audio samples.`
    :'True audio-reactive visualization active.';
  cancelAnimationFrame(raf);raf=requestAnimationFrame(draw);
}
function stopVisuals(kind='PAUSED'){
  if(!audio.paused||externalPlaying||manualTrip)return;
  cancelAnimationFrame(raf);drawIdle(kind);
}
function drawIdle(label='IDLE'){
  ctx.fillStyle='#000';ctx.fillRect(0,0,viz.width,viz.height);
  const g=ctx.createRadialGradient(viz.width/2,viz.height/2,20,viz.width/2,viz.height/2,viz.width*.55);
  g.addColorStop(0,'#17214f');g.addColorStop(.45,'#19002d');g.addColorStop(1,'#000');
  ctx.fillStyle=g;ctx.fillRect(0,0,viz.width,viz.height);
  ctx.textAlign='center';ctx.fillStyle='#79ff9a';ctx.font='700 48px "Courier New",monospace';ctx.fillText('RETROVIZ 95',viz.width/2,viz.height/2-20);
  ctx.fillStyle='#d5b9ff';ctx.font='22px "Courier New",monospace';ctx.fillText('PLAY MUSIC • ENTER TRIP MODE',viz.width/2,viz.height/2+30);
  ctx.textAlign='left';vizBadge.textContent='RETROVIZ 95 // '+label;vizEnergy.textContent='ENERGY 000';
}
function background(t,F){
  const h=(t*28+F.mid*160)%360,cx=viz.width*(.5+.1*Math.sin(t*.4)),cy=viz.height*(.5+.1*Math.cos(t*.31));
  const g=ctx.createRadialGradient(cx,cy,20,cx,cy,viz.width*.72);
  g.addColorStop(0,hue(h+80,.95,45+F.energy*20));
  g.addColorStop(.32,hue(h+20,.88,30));
  g.addColorStop(.68,hue(h+190,.78,20));
  g.addColorStop(1,'#000');
  ctx.fillStyle=g;ctx.fillRect(0,0,viz.width,viz.height);
}
function drawCircularWave(t,F,scale=1){
  const cx=viz.width/2,cy=viz.height/2,n=180,base=110+F.bass*170;
  ctx.save();ctx.translate(cx,cy);ctx.rotate(t*.12);ctx.beginPath();
  for(let i=0;i<=n;i++){
    const a=i/n*Math.PI*2;
    let amp=F.freq?F.freq[(i*3)%F.freq.length]/255:(.45+.35*Math.sin(i*.38+t*5));
    const r=(base+amp*(80+F.energy*130))*scale;
    const x=Math.cos(a)*r,y=Math.sin(a)*r;
    i?ctx.lineTo(x,y):ctx.moveTo(x,y);
  }
  ctx.closePath();ctx.strokeStyle=hue(t*70+F.treble*160,.82,67);ctx.lineWidth=2+F.energy*5;ctx.shadowBlur=20;ctx.shadowColor=ctx.strokeStyle;ctx.stroke();ctx.restore();
}
function drawTunnel(t,F){
  background(t,F);const cx=viz.width/2,cy=viz.height/2;
  ctx.save();ctx.translate(cx,cy);ctx.globalCompositeOperation='lighter';
  for(let i=0;i<24;i++){
    const p=((i/24+t*(.18+F.bass*.35))%1),r=20+p*650,w=1+8*(1-p);
    ctx.strokeStyle=hue(t*54+i*15+F.treble*120,.68,58);ctx.lineWidth=w;ctx.beginPath();
    ctx.ellipse(Math.sin(t*.7+i)*18,Math.cos(t*.53+i)*12,r,r*(.52+.16*Math.sin(t+i*.22)),t*.12+i*.035,0,Math.PI*2);ctx.stroke();
  }
  ctx.restore();drawCircularWave(t,F,.82);
}
function drawKaleido(t,F){
  background(t,F);const cx=viz.width/2,cy=viz.height/2;ctx.save();ctx.translate(cx,cy);ctx.globalCompositeOperation='lighter';
  const spokes=24;
  for(let i=0;i<spokes;i++){
    const a=i/spokes*Math.PI*2+t*(.08+F.mid*.18);ctx.save();ctx.rotate(a);
    const len=180+F.energy*430+100*Math.sin(t*2+i);
    const grd=ctx.createLinearGradient(0,0,len,0);grd.addColorStop(0,hue(t*65+i*17,.08,60));grd.addColorStop(.45,hue(t*52+i*23,.78,55));grd.addColorStop(1,hue(t*80+i*11,0,55));
    ctx.fillStyle=grd;ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(len,-18-F.bass*60);ctx.lineTo(len,18+F.treble*60);ctx.closePath();ctx.fill();ctx.restore();
  }
  ctx.restore();drawCircularWave(t,F,.72);
}
function drawPlasma(t,F){
  background(t,F);ctx.save();ctx.globalCompositeOperation='lighter';
  for(let i=0;i<70;i++){
    const a=i*.77+t*(.25+F.mid*.4),r=60+(i%14)*42+F.bass*100;
    const x=viz.width/2+Math.cos(a*1.7)*r,y=viz.height/2+Math.sin(a*1.19)*r*.62;
    const size=12+F.energy*55+(i%7)*4,g=ctx.createRadialGradient(x,y,0,x,y,size);
    g.addColorStop(0,hue(t*80+i*13,.72,68));g.addColorStop(1,hue(t*60+i*19,0,50));
    ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,size,0,Math.PI*2);ctx.fill();
  }
  ctx.restore();drawCircularWave(t,F,.9);
}
function drawStars(t,F){
  ctx.fillStyle='#020005';ctx.fillRect(0,0,viz.width,viz.height);const cx=viz.width/2,cy=viz.height/2;
  ctx.save();ctx.globalCompositeOperation='lighter';
  for(const st of stars){
    st.z-=reducedMotion?0:(.004+F.energy*.04+F.bass*.03);
    if(st.z<.025){st.x=Math.random()*2-1;st.y=Math.random()*2-1;st.z=1}
    const q=1/st.z,x=cx+st.x*q*145,y=cy+st.y*q*145,size=Math.min(8,(1-st.z)*7+1);
    if(x<0||x>viz.width||y<0||y>viz.height){st.z=1;continue}
    ctx.fillStyle=hue(t*45+(1-st.z)*220,.92,72);ctx.fillRect(x,y,size,size);
  }
  ctx.restore();drawCircularWave(t,F,.72);
}
function drawBinary(t,F){
  ctx.fillStyle='rgba(0,0,0,.32)';ctx.fillRect(0,0,viz.width,viz.height);
  ctx.font='24px "Courier New",monospace';const cw=viz.width/drops.length;
  drops.forEach((d,i)=>{d.y+=(reducedMotion?0:d.s*(.55+F.energy*4));if(d.y>viz.height+250)d.y=-Math.random()*500;
    for(let j=0;j<22;j++){const y=d.y-j*30;if(y<0||y>viz.height)continue;ctx.fillStyle=hue(105+F.treble*95,Math.max(.05,1-j/22),55);ctx.fillText(Math.random()>.5?'1':'0',i*cw,y)}
  });
  drawCircularWave(t,F,.72);
}
function drawBars(F){
  ctx.fillStyle='#000';ctx.fillRect(0,0,viz.width,viz.height);if(!F.freq)return drawCircularWave(performance.now()/1000,F);
  const bins=96,bw=viz.width/bins;
  for(let i=0;i<bins;i++){const v=F.freq[Math.floor(i*F.freq.length/bins*.75)]/255,h=v*(viz.height-30);ctx.fillStyle=hue(i*2.7+v*100,.9,48+v*20);ctx.fillRect(i*bw+1,viz.height-h,bw-2,h)}
}
function drawScope(F){
  ctx.fillStyle='#000';ctx.fillRect(0,0,viz.width,viz.height);
  const wave=F.wave;if(!wave)return drawCircularWave(performance.now()/1000,F);
  ctx.strokeStyle=hue(120+F.treble*100,.95,65);ctx.lineWidth=4;ctx.shadowBlur=18;ctx.shadowColor=ctx.strokeStyle;ctx.beginPath();
  wave.forEach((v,i)=>{const x=i/(wave.length-1)*viz.width,y=v/255*viz.height;i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke();ctx.shadowBlur=0;
}
function drawTrip(t,F){
  background(t,F);
  const cx=viz.width/2,cy=viz.height/2;ctx.save();ctx.translate(cx,cy);ctx.globalCompositeOperation='lighter';
  for(let i=0;i<18;i++){const p=((i/18+t*(.12+F.bass*.25))%1),r=40+p*600;ctx.strokeStyle=hue(t*60+i*22,.28+F.energy*.45,62);ctx.lineWidth=1+5*(1-p);ctx.beginPath();ctx.arc(0,0,r,0,Math.PI*2);ctx.stroke()}
  for(const p of particles){p.r+=(reducedMotion?0:p.s*(1+F.energy*5));p.a+=.002+F.treble*.012;if(p.r>650){p.r=10;p.a=Math.random()*Math.PI*2}
    const x=Math.cos(p.a+t*.08)*p.r,y=Math.sin(p.a*1.07-t*.05)*p.r*.58,s=2+p.z*6+F.energy*7;ctx.fillStyle=hue(t*80+p.z*220,.45+p.z*.5,65);ctx.fillRect(x,y,s,s)}
  ctx.restore();
  drawKaleidoOverlay(t,F);drawCircularWave(t,F,.75);
}
function drawKaleidoOverlay(t,F){
  const cx=viz.width/2,cy=viz.height/2;ctx.save();ctx.translate(cx,cy);ctx.globalCompositeOperation='lighter';ctx.globalAlpha=.35+.35*F.energy;
  for(let i=0;i<16;i++){ctx.save();ctx.rotate(i/16*Math.PI*2+t*.04);const len=120+F.mid*360;ctx.fillStyle=hue(t*50+i*29,.38,55);ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(len,-10-F.bass*45);ctx.lineTo(len,10+F.treble*45);ctx.closePath();ctx.fill();ctx.restore()}
  ctx.restore();ctx.globalAlpha=1;
}
function draw(ts){
  const t=ts/1000,reactive=!audio.paused&&analyser;
  const F=reactive?liveFeatures():syntheticFeatures(t);
  const mode=vizMode.value;
  if(mode==='trip')drawTrip(t,F);else if(mode==='tunnel')drawTunnel(t,F);else if(mode==='kaleido')drawKaleido(t,F);else if(mode==='plasma')drawPlasma(t,F);else if(mode==='stars')drawStars(t,F);else if(mode==='binary')drawBinary(t,F);else if(mode==='bars')drawBars(F);else drawScope(F);
  vizEnergy.textContent='ENERGY '+String(Math.round(F.energy*999)).padStart(3,'0');
  if(!audio.paused||externalPlaying||manualTrip)raf=requestAnimationFrame(draw);else drawIdle('PAUSED');
}
audio.addEventListener('play',()=>{resumeAudio();externalPlaying=false;manualTrip=false;startVisuals('AUDIO REACTIVE')});
audio.addEventListener('pause',()=>{if(!externalPlaying){manualTrip=false;stopVisuals('PAUSED')}});
audio.addEventListener('ended',()=>{if(!externalPlaying){manualTrip=false;stopVisuals('TRACK COMPLETE')}});
$('#localFile').addEventListener('change',e=>{const f=e.target.files[0];if(!f)return;playUrl(URL.createObjectURL(f),f.name,{crossOrigin:false})});
$('#searchBtn').addEventListener('click',searchArchive);
$('#searchInput').addEventListener('keydown',e=>{if(e.key==='Enter')searchArchive()});
vizMode.addEventListener('change',()=>{if(!audio.paused||externalPlaying||manualTrip){cancelAnimationFrame(raf);raf=requestAnimationFrame(draw)}});
tripBtn.addEventListener('click',()=>{manualTrip=!manualTrip;externalPlaying=false;if(manualTrip){vizMode.value='trip';tripBtn.textContent='STOP TRIP';startVisuals('MANUAL TRIP')}else{tripBtn.textContent='START TRIP';cancelAnimationFrame(raf);drawIdle('IDLE')}});
$('#fullscreenBtn').addEventListener('click',async()=>{try{if(!document.fullscreenElement)await vizWrap.requestFullscreen();else await document.exitFullscreen()}catch(e){setStatus('Fullscreen unavailable: '+e.message,'error')}});
document.addEventListener('fullscreenchange',()=>{$('#fullscreenBtn').textContent=document.fullscreenElement?'EXIT FULL SCREEN':'FULL SCREEN'});

async function searchArchive(){
  const q=$('#searchInput').value.trim();if(!q)return;
  setStatus('Searching Internet Archive...');results.innerHTML='';
  try{
    const u='https://archive.org/advancedsearch.php?q='+encodeURIComponent('mediatype:audio AND ('+q+')')+'&fl[]=identifier,title,creator&rows=20&page=1&output=json';
    const r=await fetch(u);if(!r.ok)throw new Error('Search request failed');const j=await r.json();
    for(const d of j.response.docs){
      const row=document.createElement('div');row.className='result';const info=document.createElement('div');
      info.innerHTML='<strong>'+escapeHtml(d.title||d.identifier)+'</strong><small>'+escapeHtml(d.creator||'Internet Archive')+'</small>';
      const b=document.createElement('button');b.textContent='PLAY + TRIP';b.onclick=()=>resolveArchive(d);row.append(info,b);results.append(row);
    }
    setStatus(j.response.numFound+' archive results found.','ok');
  }catch(e){setStatus('Archive search failed: '+e.message,'error')}
}
async function resolveArchive(d){
  setStatus('Resolving audio file...');
  try{
    const r=await fetch('https://archive.org/metadata/'+encodeURIComponent(d.identifier));if(!r.ok)throw new Error('Metadata request failed');const j=await r.json();
    const f=j.files.find(x=>/\.(mp3|ogg|m4a)$/i.test(x.name||''));if(!f)throw new Error('No browser-playable audio found');
    const url='https://archive.org/download/'+encodeURIComponent(d.identifier)+'/'+encodeURIComponent(f.name).replace(/%2F/g,'/'),title=d.title||d.identifier;
    playUrl(url,title,{crossOrigin:true});addQueue({url,title,crossOrigin:true});setStatus('Playing from Internet Archive with RetroViz.','ok');
  }catch(e){setStatus(e.message,'error')}
}
document.querySelectorAll('[data-provider]').forEach(b=>b.addEventListener('click',()=>{
  const q=$('#searchInput').value.trim()||'music',p=b.dataset.provider,base={soundcloud:'https://soundcloud.com/search?q=',youtube:'https://www.youtube.com/results?search_query=',bandcamp:'https://bandcamp.com/search?q=',audius:'https://audius.co/search/',jamendo:'https://www.jamendo.com/search?q='}[p];
  if(p==='archive'){searchArchive();return}window.open(base+encodeURIComponent(q),'_blank','noopener,noreferrer');
}));

function loadScript(src,id){
  if(document.getElementById(id))return;
  const s=document.createElement('script');s.id=id;s.src=src;s.async=true;document.head.appendChild(s);
}
function linkedPlay(provider){audio.pause();externalPlaying=true;manualTrip=false;tripBtn.textContent='START TRIP';startVisuals('LINKED TRIP • '+provider,provider)}
function linkedPause(provider){externalPlaying=false;if(audio.paused&&!manualTrip){cancelAnimationFrame(raf);drawIdle(provider+' PAUSED')}}
function bindSoundCloud(iframe){
  let tries=0;const attempt=()=>{tries++;if(window.SC&&SC.Widget){
    const widget=SC.Widget(iframe);widget.bind(SC.Widget.Events.PLAY,()=>linkedPlay('SOUNDCLOUD'));widget.bind(SC.Widget.Events.PAUSE,()=>linkedPause('SOUNDCLOUD'));widget.bind(SC.Widget.Events.FINISH,()=>linkedPause('SOUNDCLOUD'));
  }else if(tries<30)setTimeout(attempt,150)};attempt();
}
function createYouTube(videoId){
  pendingYouTube=videoId;const h=$('#embedHost');h.innerHTML='<div id="ytPlayer"></div>';
  if(window.YT&&YT.Player){
    if(ytPlayer&&ytPlayer.destroy)try{ytPlayer.destroy()}catch(_){}
    ytPlayer=new YT.Player('ytPlayer',{height:'220',width:'100%',videoId,playerVars:{playsinline:1},events:{onStateChange:e=>{if(e.data===YT.PlayerState.PLAYING)linkedPlay('YOUTUBE');if(e.data===YT.PlayerState.PAUSED||e.data===YT.PlayerState.ENDED)linkedPause('YOUTUBE')}}});
  }
}
window.onYouTubeIframeAPIReady=()=>{if(pendingYouTube)createYouTube(pendingYouTube)};
loadScript('https://w.soundcloud.com/player/api.js','soundcloud-widget-api');
loadScript('https://www.youtube.com/iframe_api','youtube-iframe-api');

$('#embedForm').addEventListener('submit',e=>{
  e.preventDefault();const u=$('#embedUrl').value.trim(),h=$('#embedHost');
  if(/^https?:\/\/(?:www\.)?soundcloud\.com\//i.test(u)){
    h.innerHTML='<iframe id="scPlayer" title="SoundCloud player" allow="autoplay" src="https://w.soundcloud.com/player/?url='+encodeURIComponent(u)+'&auto_play=false&visual=true"></iframe>';
    const iframe=$('#scPlayer');iframe.addEventListener('load',()=>bindSoundCloud(iframe),{once:true});bindSoundCloud(iframe);vizStatus.textContent='SoundCloud loaded. RetroViz will enter linked ambient Trip Mode when playback starts.';
  }else{
    const m=u.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|shorts\/|embed\/))([A-Za-z0-9_-]{6,})/);
    if(m){createYouTube(m[1]);vizStatus.textContent='YouTube loaded. RetroViz will enter linked ambient Trip Mode when playback starts.'}
    else h.textContent='Unsupported link. Use a SoundCloud or YouTube URL.';
  }
});
function escapeHtml(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
drawIdle();
