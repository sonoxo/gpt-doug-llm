(() => {
  const STORE_QUEUE='zyra_jukebox_queue_v3';
  const STORE_FAVORITES='zyra_jukebox_favorites_v3';
  const STORE_SESSION='zyra_jukebox_session_v3';
  const safeLoad=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback}catch(_){return fallback}};
  const saveLocal=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value));return true}catch(_){return false}};
  const state=window.ZYRAState=window.ZYRAState||{
    currentItem:null,
    queue:safeLoad(STORE_QUEUE,[]),
    favorites:safeLoad(STORE_FAVORITES,[]),
    queueIndex:-1,
    activeKind:'none'
  };
  const radioAudio=document.querySelector('#radioAudio');
  const playPauseBtn=document.querySelector('#playPauseBtn');
  const volume=document.querySelector('#volume');
  const queueEl=document.querySelector('#queue');
  const savedItems=document.querySelector('#savedItems');
  const queueCount=document.querySelector('#queueCount');
  const savedCount=document.querySelector('#savedCount');

  const itemId=item=>item?.id||[item?.kind||'direct',item?.title||'',item?.url||''].join('|');
  const normalize=item=>({
    kind:item?.kind||'direct',
    id:item?.id||item?.url||item?.title||crypto.randomUUID?.()||String(Date.now()),
    url:item?.url||'',
    title:item?.title||'Untitled',
    subtitle:item?.subtitle||'',
    crossOrigin:!!item?.crossOrigin,
    countrycode:item?.countrycode||'',
    tags:item?.tags||'',
    station:item?.station
  });

  function setCurrent(item){
    state.currentItem=normalize(item);
    state.activeKind=state.currentItem.kind;
    const now=document.querySelector('#nowPlaying');
    now.textContent=state.currentItem.title+(state.currentItem.subtitle?' — '+state.currentItem.subtitle:'');
    updateMediaSession();
    updateController();
  }
  window.ZYRASetCurrent=setCurrent;

  const originalPlayUrl=window.playUrl;
  if(typeof originalPlayUrl==='function'){
    window.playUrl=function(url,title,opts={}){
      if(radioAudio)radioAudio.pause();
      const item=normalize({kind:'direct',url,title,subtitle:opts.subtitle||'',crossOrigin:!!opts.crossOrigin,id:opts.id||url});
      setCurrent(item);
      const out=originalPlayUrl(url,title,opts);
      const idx=state.queue.findIndex(q=>itemId(q)===itemId(item));
      if(idx>=0)state.queueIndex=idx;
      return out;
    };
  }

  function renderQueue(){
    queueEl.innerHTML='';
    queueCount.textContent='('+state.queue.length+')';
    if(!state.queue.length){queueEl.innerHTML='<li class="empty-state">Queue is empty.</li>';return}
    state.queue.forEach((raw,i)=>{
      const item=normalize(raw),li=document.createElement('li');
      li.textContent=item.title+(item.kind==='radio'?' 📻':'');
      li.tabIndex=0;
      const go=()=>{state.queueIndex=i;playItem(item)};
      li.addEventListener('click',go);
      li.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}});
      queueEl.append(li);
    });
  }

  window.addQueue=function(raw){
    const item=normalize(raw);
    if(!item.url)return;
    if(!state.queue.some(q=>itemId(q)===itemId(item)))state.queue.push(item);
    saveLocal(STORE_QUEUE,state.queue);
    if(state.currentItem&&itemId(state.currentItem)===itemId(item))state.queueIndex=state.queue.findIndex(q=>itemId(q)===itemId(item));
    renderQueue();
  };

  function playItem(raw){
    const item=normalize(raw);
    if(item.kind==='radio'&&typeof window.ZYRAPlayRadio==='function')return window.ZYRAPlayRadio(item.station||item);
    if(item.kind==='direct'&&typeof window.playUrl==='function')return window.playUrl(item.url,item.title,{crossOrigin:item.crossOrigin,subtitle:item.subtitle,id:item.id});
    if((item.kind==='soundcloud'||item.kind==='youtube')&&item.url){
      document.querySelector('#embedUrl').value=item.url;
      document.querySelector('#embedForm').requestSubmit();
    }
  }
  window.ZYRAPlayItem=playItem;

  function renderFavorites(){
    savedItems.innerHTML='';
    savedCount.textContent='('+state.favorites.length+')';
    if(!state.favorites.length){savedItems.innerHTML='<div class="empty-state">No saved tracks or stations yet.</div>';return}
    state.favorites.forEach((raw,i)=>{
      const item=normalize(raw),row=document.createElement('div');row.className='saved-item';
      const info=document.createElement('div');
      info.innerHTML='<strong>'+escapeHtml(item.title)+'</strong><small>'+escapeHtml(item.kind==='radio'?'LIVE RADIO':(item.subtitle||item.kind))+'</small>';
      const play=document.createElement('button');play.textContent='PLAY';play.onclick=()=>playItem(item);
      const del=document.createElement('button');del.textContent='×';del.title='Remove';del.onclick=()=>{state.favorites.splice(i,1);saveLocal(STORE_FAVORITES,state.favorites);renderFavorites()};
      row.append(info,play,del);savedItems.append(row);
    });
  }

  function saveItem(raw){
    if(!raw)return false;
    const item=normalize(raw);
    if(!state.favorites.some(x=>itemId(x)===itemId(item)))state.favorites.unshift(item);
    saveLocal(STORE_FAVORITES,state.favorites);
    renderFavorites();
    return true;
  }
  window.ZYRASaveItem=saveItem;

  function saveCurrent(){
    if(!state.currentItem)return setStatus('Nothing is playing to save.','error');
    saveItem(state.currentItem);
    setStatus('Saved in this browser.','ok');
  }

  function saveSession(){
    const session={savedAt:new Date().toISOString(),current:state.currentItem,queue:state.queue,favorites:state.favorites,visualMode:document.querySelector('#vizMode').value,volume:Number(volume.value)};
    const ok=saveLocal(STORE_SESSION,session);
    setStatus(ok?'Session saved locally.':'Browser storage unavailable.',ok?'ok':'error');
  }

  function exportLibrary(){
    const payload={app:'ZYRA JUKEBOX',version:3,exportedAt:new Date().toISOString(),current:state.currentItem,queue:state.queue,favorites:state.favorites};
    const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});
    const u=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=u;a.download='zyra-jukebox-library.json';document.body.append(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(u),1000);
    setStatus('Library exported as JSON.','ok');
  }

  async function togglePlay(){
    if(state.activeKind==='radio'&&radioAudio){if(radioAudio.paused)radioAudio.play().catch(()=>{});else radioAudio.pause();return}
    if(state.activeKind==='direct'){if(audio.paused)audio.play().catch(()=>{});else audio.pause();return}
    if(state.activeKind==='youtube'&&window.ytPlayer){try{const s=ytPlayer.getPlayerState();s===1?ytPlayer.pauseVideo():ytPlayer.playVideo()}catch(_){ }return}
    if(state.queue.length){state.queueIndex=Math.max(0,state.queueIndex);playItem(state.queue[state.queueIndex]);return}
    setStatus('Load music or a live station first.','error');
  }

  function stopPlayback(){
    if(state.activeKind==='radio'&&radioAudio)radioAudio.pause();
    else if(state.activeKind==='direct'){audio.pause();try{audio.currentTime=0}catch(_){}}
    else if(state.activeKind==='youtube'&&window.ytPlayer)try{ytPlayer.stopVideo()}catch(_){}
    if(typeof externalPlaying!=='undefined')externalPlaying=false;
    updateController();
    if(typeof stopVisuals==='function')stopVisuals('STOPPED');
  }

  function seekBy(seconds){
    if(state.activeKind==='direct'&&Number.isFinite(audio.duration))audio.currentTime=Math.max(0,Math.min(audio.duration,audio.currentTime+seconds));
    else if(state.activeKind==='youtube'&&window.ytPlayer?.getCurrentTime)try{ytPlayer.seekTo(Math.max(0,ytPlayer.getCurrentTime()+seconds),true)}catch(_){}
  }

  function stepQueue(delta){
    if(!state.queue.length)return setStatus('Queue is empty.','error');
    if(state.queueIndex<0&&state.currentItem)state.queueIndex=state.queue.findIndex(q=>itemId(q)===itemId(state.currentItem));
    state.queueIndex=(Math.max(-1,state.queueIndex)+delta+state.queue.length)%state.queue.length;
    playItem(state.queue[state.queueIndex]);
  }

  function updateController(){
    let playing=false;
    if(state.activeKind==='radio'&&radioAudio)playing=!radioAudio.paused;
    else if(state.activeKind==='direct')playing=!audio.paused;
    else if(state.activeKind==='youtube'||state.activeKind==='soundcloud')playing=typeof externalPlaying!=='undefined'&&externalPlaying;
    playPauseBtn.textContent=playing?'Ⅱ PAUSE':'▶ PLAY';
  }
  window.ZYRAUpdateController=updateController;

  function setVolume(v){
    const n=Math.max(0,Math.min(1,Number(v)));
    audio.volume=n;if(radioAudio)radioAudio.volume=n;
    if(window.ytPlayer?.setVolume)try{ytPlayer.setVolume(Math.round(n*100))}catch(_){}
  }

  function updateMediaSession(){
    if(!('mediaSession'in navigator)||!state.currentItem)return;
    try{navigator.mediaSession.metadata=new MediaMetadata({title:state.currentItem.title,artist:state.currentItem.subtitle||'',album:state.currentItem.kind==='radio'?'Live Radio':'ZYRA JUKEBOX'})}catch(_){}
  }

  document.querySelector('#playPauseBtn').addEventListener('click',togglePlay);
  document.querySelector('#stopBtn').addEventListener('click',stopPlayback);
  document.querySelector('#rewBtn').addEventListener('click',()=>seekBy(-10));
  document.querySelector('#fwdBtn').addEventListener('click',()=>seekBy(10));
  document.querySelector('#prevBtn').addEventListener('click',()=>stepQueue(-1));
  document.querySelector('#nextBtn').addEventListener('click',()=>stepQueue(1));
  volume.addEventListener('input',e=>setVolume(e.target.value));
  document.querySelector('#saveCurrentBtn').addEventListener('click',saveCurrent);
  document.querySelector('#saveQueueBtn').addEventListener('click',saveSession);
  document.querySelector('#exportBtn').addEventListener('click',exportLibrary);

  audio.addEventListener('play',()=>{state.activeKind='direct';updateController()});
  audio.addEventListener('pause',updateController);

  document.querySelector('#embedForm').addEventListener('submit',()=>{
    const u=document.querySelector('#embedUrl').value.trim();
    if(/soundcloud\.com/i.test(u))setCurrent({kind:'soundcloud',id:u,url:u,title:'SoundCloud',subtitle:'SOUNDCLOUD'});
    else{
      const m=u.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|shorts\/|embed\/))([A-Za-z0-9_-]{6,})/);
      if(m)setCurrent({kind:'youtube',id:m[1],url:u,title:'YouTube',subtitle:'YOUTUBE'});
    }
  });

  if('mediaSession'in navigator){
    try{
      navigator.mediaSession.setActionHandler('play',togglePlay);
      navigator.mediaSession.setActionHandler('pause',togglePlay);
      navigator.mediaSession.setActionHandler('previoustrack',()=>stepQueue(-1));
      navigator.mediaSession.setActionHandler('nexttrack',()=>stepQueue(1));
      navigator.mediaSession.setActionHandler('seekbackward',()=>seekBy(-10));
      navigator.mediaSession.setActionHandler('seekforward',()=>seekBy(10));
    }catch(_){}
  }

  const session=safeLoad(STORE_SESSION,null);
  if(session?.volume!=null){volume.value=session.volume;setVolume(session.volume)}
  if(session?.visualMode&&[...document.querySelector('#vizMode').options].some(o=>o.value===session.visualMode))document.querySelector('#vizMode').value=session.visualMode;
  renderQueue();renderFavorites();updateController();
})();
