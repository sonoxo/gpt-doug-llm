(() => {
  const state=window.ZYRAState;
  const radioAudio=document.querySelector('#radioAudio');
  const radioResults=document.querySelector('#radioResults');
  const radioStatus=document.querySelector('#radioStatus');
  const APIS=['https://de1.api.radio-browser.info','https://nl1.api.radio-browser.info','https://at1.api.radio-browser.info'];
  const setRadioStatus=(t,c='')=>{radioStatus.textContent=t;radioStatus.className='status '+c};
  const esc=s=>String(s??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));

  async function apiFetch(path){
    let last=null;
    for(const base of APIS){
      try{const r=await fetch(base+path,{headers:{Accept:'application/json'}});if(!r.ok)throw new Error('HTTP '+r.status);return {base,data:await r.json()}}catch(e){last=e}
    }
    throw last||new Error('Radio directory unavailable');
  }

  function stationItem(s){
    return {
      kind:'radio',
      id:s.stationuuid||s.id||s.url_resolved||s.url,
      url:s.url_resolved||s.url,
      title:s.name||s.title||'Live Radio',
      subtitle:[s.countrycode||s.country,s.tags].filter(Boolean).join(' • '),
      countrycode:s.countrycode||'',
      tags:s.tags||'',
      station:s.station||s
    };
  }

  async function clickStation(uuid){
    if(!uuid)return;
    for(const base of APIS){try{await fetch(base+'/json/url/'+encodeURIComponent(uuid));break}catch(_){}}
  }

  window.ZYRAPlayRadio=function(raw){
    const s=raw.station||raw,item=stationItem(s),url=item.url;
    if(!url)return setRadioStatus('Station has no playable stream.','error');
    audio.pause();
    try{if(typeof ytPlayer!=='undefined'&&ytPlayer?.pauseVideo)ytPlayer.pauseVideo()}catch(_){}
    radioAudio.src=url;
    if(window.ZYRASetCurrent)ZYRASetCurrent(item);
    state.activeKind='radio';
    if(typeof externalPlaying!=='undefined'){externalPlaying=true;externalProvider='LIVE RADIO'}
    radioAudio.play().then(()=>{
      if(typeof startVisuals==='function')startVisuals('LINKED TRIP • LIVE RADIO','LIVE RADIO');
      setRadioStatus('LIVE: '+item.title,'ok');
      clickStation(s.stationuuid);
      if(window.ZYRAUpdateController)ZYRAUpdateController();
    }).catch(e=>setRadioStatus('Could not start this station: '+e.message,'error'));
  };

  radioAudio.addEventListener('play',()=>{
    state.activeKind='radio';
    if(typeof externalPlaying!=='undefined')externalPlaying=true;
    if(typeof startVisuals==='function')startVisuals('LINKED TRIP • LIVE RADIO','LIVE RADIO');
    if(window.ZYRAUpdateController)ZYRAUpdateController();
  });
  radioAudio.addEventListener('pause',()=>{
    if(typeof externalPlaying!=='undefined')externalPlaying=false;
    if(window.ZYRAUpdateController)ZYRAUpdateController();
    if(audio.paused&&typeof manualTrip!=='undefined'&&!manualTrip&&typeof stopVisuals==='function')stopVisuals('RADIO PAUSED');
  });
  radioAudio.addEventListener('error',()=>setRadioStatus('This station stream failed in the browser. Try another station.','error'));

  function renderStations(stations){
    radioResults.innerHTML='';
    if(!stations.length){radioResults.innerHTML='<div class="empty-state">No browser-safe HTTPS stations found. Try another search.</div>';return}
    stations.forEach(s=>{
      const row=document.createElement('div');row.className='result';
      const info=document.createElement('div');
      const meta=[s.countrycode,s.codec,s.bitrate?`${s.bitrate}kbps`:'',s.tags].filter(Boolean).join(' • ');
      info.innerHTML=(s.favicon?'<img class="station-logo" src="'+esc(s.favicon)+'" alt="" onerror="this.style.display=\'none\'">':'')+'<strong>'+esc(s.name||'Live Radio')+'</strong><small>'+esc(meta)+'</small>';
      const actions=document.createElement('div');actions.className='result-actions';
      const play=document.createElement('button');play.textContent='📻 PLAY';play.onclick=()=>{const item=stationItem(s);window.addQueue(item);state.queueIndex=state.queue.findIndex(q=>(q.id||q.url)===item.id);window.ZYRAPlayRadio(s)};
      const save=document.createElement('button');save.textContent='★ SAVE';save.onclick=()=>{
        const item=stationItem(s);
        if(window.ZYRASaveItem)window.ZYRASaveItem(item);
        setRadioStatus('Station saved.','ok');
      };
      actions.append(play,save);row.append(info,actions);radioResults.append(row);
    });
  }

  async function searchRadio({top=false}={}){
    const q=document.querySelector('#radioSearch').value.trim(),country=document.querySelector('#radioCountry').value;
    setRadioStatus(top?'Loading top live stations...':'Searching live radio...');radioResults.innerHTML='';
    try{
      let stations=[];
      if(top){
        ({data:stations}=await apiFetch('/json/stations/topclick/60?hidebroken=true'));
      }else if(q){
        const extra='&hidebroken=true&limit=50&order=clickcount&reverse=true'+(country?'&countrycode='+encodeURIComponent(country):'');
        const [a,b]=await Promise.allSettled([
          apiFetch('/json/stations/search?name='+encodeURIComponent(q)+extra),
          apiFetch('/json/stations/search?tag='+encodeURIComponent(q)+extra)
        ]);
        const merged=[...(a.status==='fulfilled'?a.value.data:[]),...(b.status==='fulfilled'?b.value.data:[])],seen=new Set();
        stations=merged.filter(s=>{const k=s.stationuuid||s.url_resolved||s.url;if(!k||seen.has(k))return false;seen.add(k);return true});
      }else{
        ({data:stations}=await apiFetch('/json/stations/search?hidebroken=true&limit=60&order=clickcount&reverse=true'+(country?'&countrycode='+encodeURIComponent(country):'')));
      }
      stations=stations.filter(s=>s.lastcheckok!==0&&/^https:\/\//i.test(s.url_resolved||s.url||'')).slice(0,50);
      renderStations(stations);setRadioStatus(stations.length+' HTTPS live stations ready.','ok');
    }catch(e){setRadioStatus('Live radio search failed: '+e.message,'error')}
  }

  document.querySelector('#radioSearchBtn').addEventListener('click',()=>searchRadio());
  document.querySelector('#radioTopBtn').addEventListener('click',()=>searchRadio({top:true}));
  document.querySelector('#radioSearch').addEventListener('keydown',e=>{if(e.key==='Enter')searchRadio()});
  document.querySelector('#liveRadioBtn').addEventListener('click',()=>{
    document.querySelector('#radioPanel').scrollIntoView({behavior:'smooth',block:'start'});
    if(!radioResults.children.length)searchRadio({top:true});
  });
})();
