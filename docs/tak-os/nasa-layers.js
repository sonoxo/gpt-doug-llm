/* NASA / Satellites public-science layer. No military tracking, tasking, or external TAK connections.
 * All remote network access is opt-in. Off-line mode exposes only sourced mission metadata.
 */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const FEEDS = Object.freeze({
    events: 'https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=40&days=30',
    spaceweather: 'https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json',
  });
  const MISSIONS = Object.freeze([
    {name:'Landsat 9', country:'US', agency:'NASA / USGS', mission:'Land-cover change and repeat imagery', orbit:'Near-polar, sun-synchronous', data:'Open multispectral science archive', source:'https://science.nasa.gov/mission/landsat-9/'},
    {name:'Aqua', country:'US', agency:'NASA', mission:'Atmosphere, oceans, water cycle', orbit:'Earth observation orbit', data:'Long-duration public Earth science observations', source:'https://science.nasa.gov/mission/aqua/'},
    {name:'Fengyun-4C', country:'CN', agency:'China Meteorological Administration', mission:'Geostationary meteorology', orbit:'Geostationary', data:'WMO mission and sensor metadata', source:'https://space.oscar.wmo.int/satellites/view/fy_4c'},
    {name:'Fengyun-4B', country:'CN', agency:'China Meteorological Administration', mission:'Geostationary weather and space weather', orbit:'Geostationary', data:'WMO mission record; individual sensor status may change', source:'https://space.oscar.wmo.int/satellites/view/fy_4b'},
    {name:'Meteor-M N2-4', country:'RU', agency:'RosHydroMet / Roscosmos', mission:'Operational meteorology and land observation', orbit:'Near-polar, sun-synchronous', data:'WMO public mission record', source:'https://space.oscar.wmo.int/satellites/view/meteor_m_n2_4'},
    {name:'Meteor-M N2-3', country:'RU', agency:'RosHydroMet / Roscosmos', mission:'Weather and atmospheric observations', orbit:'Near-polar, sun-synchronous', data:'WMO public mission record; operational limitations reported', source:'https://space.oscar.wmo.int/satellites/view/meteor_m_n2_3'},
  ]);
  const imageryLayers = new Set([
    'VIIRS_SNPP_CorrectedReflectance_TrueColor',
    'VIIRS_NOAA20_CorrectedReflectance_TrueColor',
    'MODIS_Terra_CorrectedReflectance_TrueColor',
  ]);
  const state = {events:null, kp:null, retrievedAt:null, errors:[], pending:null, imagery:false, displayEvents:true, signature:'', map:null, tilesFailed:0};
  const safeText = (x, limit = 120) => String(x ?? '').trim().slice(0,limit);
  const validCoord = (lat,lon) => Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 85 && Math.abs(lon) <= 180;
  const utcDate = (daysAgo) => new Date(Date.now() - daysAgo*86400000).toISOString().slice(0,10);
  function dateValid(text) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return false;
    const day = new Date(`${text}T00:00:00.000Z`);
    return !Number.isNaN(day.getTime()) && day.toISOString().slice(0,10) === text && day <= new Date() && day >= new Date('2015-01-01T00:00:00Z');
  }
  function normalizeEvents(raw) {
    if (!raw || !Array.isArray(raw.events)) throw new Error('NASA EONET response schema mismatch');
    return raw.events.slice(0,40).flatMap((event) => {
      const geo = Array.isArray(event.geometry) ? [...event.geometry].reverse().find((point)=>point.type==='Point' && Array.isArray(point.coordinates)) : null;
      if (!geo) return []; // no inferred point for polygon-only events
      const [lon,lat] = geo.coordinates.map(Number);
      if (!validCoord(lat,lon)) return [];
      const id = safeText(event.id,64);
      const title = safeText(event.title,125);
      if (!id || !title) return [];
      const categories = Array.isArray(event.categories) ? event.categories.map(x => safeText(x.title || x.id,35)).slice(0,2) : [];
      const time = typeof geo.date==='string' && !Number.isNaN(Date.parse(geo.date)) ? new Date(geo.date).toISOString() : null;
      return [{id,title,lat,lon,category:categories.join(' / ') || 'Natural event',observedAt:time,source:'NASA EONET v3',sourceUrl:`https://eonet.gsfc.nasa.gov/api/v3/events/${encodeURIComponent(id)}`}];
    });
  }
  function normalizeKp(data) {
    if (!Array.isArray(data) || !Array.isArray(data[0])) throw new Error('NOAA Kp response schema mismatch');
    const columns = data[0].map(x => String(x).toLowerCase());
    const kpIndex = columns.findIndex(x => x === 'kp' || x === 'kp_index' || x === 'kp index');
    const timeIndex = columns.findIndex(x => x === 'time_tag' || x === 'time');
    if (kpIndex < 0 || timeIndex < 0) throw new Error('NOAA Kp columns unavailable');
    const valid = data.slice(1).filter(row => Array.isArray(row) && Number.isFinite(Number(row[kpIndex])) && Number(row[kpIndex])>=0 && Number(row[kpIndex])<=9 && !Number.isNaN(Date.parse(row[timeIndex])));
    if (!valid.length) throw new Error('NOAA Kp data unavailable');
    const entry = valid[valid.length-1];
    return {kp:Number(entry[kpIndex]),observedAt:new Date(entry[timeIndex]).toISOString(),source:'NOAA SWPC',sourceUrl:'https://www.spaceweather.gov/products/planetary-k-index'};
  }
  function webMercator(lat,lon,zoom) {
    const size=256*2**zoom, phi=Math.max(-85.0511,Math.min(85.0511,lat))*Math.PI/180;
    return {x:(lon+180)/360*size, y:(1-Math.log(Math.tan(phi)+1/Math.cos(phi))/Math.PI)/2*size};
  }
  function eventPoint(event,viewport) {
    const mid=webMercator(viewport.center.lat,viewport.center.lon,viewport.zoom);
    const location=webMercator(event.lat,event.lon,viewport.zoom);
    return {x:viewport.width/2+location.x-mid.x,y:viewport.height/2+location.y-mid.y};
  }
  function getViewport() { return window.TAKOSApp?.publicMapViewport?.() || state.map; }
  function imageSettings() {
    const layer=$('#nasa-imagery-select').value, date=$('#nasa-date').value;
    return {layer:imageryLayers.has(layer)?layer:null,date:dateValid(date)?date:null,opacity:Number($('#nasa-opacity').value)/100};
  }
  function renderImages(force=false) {
    const layer=$('#nasa-imagery-tiles');
    if (!state.imagery) {layer.replaceChildren();state.signature='';$('#nasa-map-credit').hidden=true;return;}
    const vp=getViewport(), s=imageSettings();
    if (!vp || !vp.width || !vp.height || !s.layer || !s.date) {layer.replaceChildren();$('#nasa-map-credit').hidden=true;$('#nasa-imagery-feedback').textContent='Select an available UTC date and imagery source.';return;}
    if (vp.zoom>9) {layer.replaceChildren();$('#nasa-map-credit').hidden=true;$('#nasa-imagery-feedback').textContent='NASA GIBS zoom range here is 2–9. Zoom out to show imagery.';state.signature='';return;}
    const signature=[vp.center.lat.toFixed(5),vp.center.lon.toFixed(5),vp.zoom,vp.width,vp.height,s.layer,s.date,s.opacity].join(':');
    if (!force && signature===state.signature) return;
    state.signature=signature; state.tilesFailed=0;$('#nasa-map-credit').hidden=false;$('#nasa-map-date').textContent=s.date+' UTC (NOT LIVE)';
    layer.replaceChildren();
    const mid=webMercator(vp.center.lat,vp.center.lon,vp.zoom), total=2**vp.zoom;
    const x0=Math.floor((mid.x-vp.width/2)/256),x1=Math.floor((mid.x+vp.width/2)/256);
    const y0=Math.floor((mid.y-vp.height/2)/256),y1=Math.floor((mid.y+vp.height/2)/256);
    let count=0;
    for(let x=x0;x<=x1;x++) for(let y=y0;y<=y1;y++){
      if(y<0 || y>=total || count>=50)continue;
      const tile=document.createElement('img'); tile.alt='';tile.draggable=false;tile.loading='lazy';
      tile.style.left=`${x*256-mid.x+vp.width/2}px`;tile.style.top=`${y*256-mid.y+vp.height/2}px`;tile.style.opacity=String(s.opacity);
      tile.src=`https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${s.layer}/default/${s.date}/GoogleMapsCompatible_Level9/${vp.zoom}/${y}/${((x%total)+total)%total}.jpg`;
      tile.onerror=()=>{tile.remove();state.tilesFailed++;$('#nasa-imagery-feedback').textContent='Some dated NASA tiles are unavailable at this location. Try a different date or layer.';};
      layer.appendChild(tile);count++;
    }
    $('#nasa-imagery-feedback').textContent=count?`NASA ${s.layer.replaceAll('_',' ')} · ${s.date} · ${count} requested public tiles (not live video).`:'No NASA imagery tiles in this viewport.';
  }
  function renderMarkers() {
    const layer=$('#nasa-map-markers');layer.replaceChildren();
    if(!state.displayEvents || !state.events?.length)return;
    const vp=getViewport(); if(!vp||!vp.width||!vp.height)return;
    state.events.forEach(event=>{
      const p=eventPoint(event,vp);
      if(p.x<-20||p.x>vp.width+20||p.y<-20||p.y>vp.height+20)return;
      const button=document.createElement('button');button.className='nasa-map-event';button.type='button';
      button.style.left=`${p.x}px`;button.style.top=`${p.y}px`;
      button.title=`Reported NASA EONET event: ${event.title}`;
      button.setAttribute('aria-label',`View reported event: ${event.title}`);
      button.textContent='◎';
      button.addEventListener('click',(click)=>{click.stopPropagation();window.TAKOSApp?.navigateView('nasa');selectEvent(event);});
      layer.appendChild(button);
    });
  }
  function selectEvent(event) {
    const box=$('#nasa-feed-feedback');
    box.textContent=`NASA EONET · ${event.title} · ${event.category} · ${event.observedAt||'Observation time not supplied'} · ${event.lat.toFixed(3)}, ${event.lon.toFixed(3)}. Public report, not tactical tracking.`;
  }
  function renderMissions() {
    const filter=$('#nasa-country-filter').value, grid=$('#nasa-mission-list');grid.replaceChildren();
    MISSIONS.filter(m=>filter==='all'||m.country===filter).forEach(m=>{
      const article=document.createElement('article');article.className='nasa-mission';
      const country=document.createElement('small');country.className='nasa-mission-country';country.textContent=({'US':'UNITED STATES','CN':'CHINA','RU':'RUSSIA'})[m.country]+' · CIVIL EO';
      const h=document.createElement('h3');h.textContent=m.name;
      const agency=document.createElement('p');agency.textContent=m.agency;
      const role=document.createElement('p');role.textContent=m.mission;
      const orbit=document.createElement('div');orbit.className='nasa-mission-detail';orbit.textContent=`Orbit category: ${m.orbit}`;
      const data=document.createElement('div');data.className='nasa-mission-detail';data.textContent=m.data;
      const link=document.createElement('a');link.href=m.source;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Verified mission reference ↗';
      article.append(country,h,agency,role,orbit,data,link);grid.appendChild(article);
    });
    $('#nasa-mission-count').textContent=String(MISSIONS.length);
  }
  function renderPublicEvents() {
    const parent=$('#nasa-events-list');parent.replaceChildren();
    if(state.events===null) {const p=document.createElement('p');p.className='body-copy';p.textContent='NASA EONET not loaded.';parent.appendChild(p);return;}
    if(!state.events.length) {const p=document.createElement('p');p.className='body-copy';p.textContent='No point reports returned in selected public feed window.';parent.appendChild(p);return;}
    state.events.slice(0,12).forEach(event=>{
      const row=document.createElement('div');row.className='nasa-event-row';
      const info=document.createElement('div');const b=document.createElement('b');b.textContent=event.title;
      const small=document.createElement('small');small.textContent=`${event.category} · ${event.observedAt||'Date unavailable'} · NASA EONET`;
      info.append(b,small);
      const button=document.createElement('button');button.type='button';button.className='tiny-button';button.textContent='Locate ↗';button.addEventListener('click',()=>{selectEvent(event);window.TAKOSApp?.focusPublicObservation(event.lat,event.lon);});
      row.append(info,button);parent.appendChild(row);
    });
  }
  async function loadJson(url,signal) {
    const response=await fetch(url,{method:'GET',mode:'cors',credentials:'omit',redirect:'error',cache:'no-store',signal,headers:{Accept:'application/json'}});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const length=Number(response.headers.get('Content-Length') || 0);
    if(length>900000)throw new Error('Feed exceeds public-data size cap');
    const text=await response.text();
    if(text.length>900000)throw new Error('Feed exceeds public-data size cap');
    return JSON.parse(text);
  }
  async function refreshFeeds() {
    if(state.pending)return;
    const controller=new AbortController();state.pending=controller;
    const stopper=setTimeout(()=>controller.abort(),9000);
    $('#nasa-load-feeds').disabled=true;$('#nasa-source-status').textContent='PUBLIC DATA / REQUESTING';
    $('#nasa-feed-feedback').textContent='Requesting NASA EONET and NOAA SWPC; real public records only.';
    const outcomes=await Promise.allSettled([
      loadJson(FEEDS.events,controller.signal).then(normalizeEvents),
      loadJson(FEEDS.spaceweather,controller.signal).then(normalizeKp)
    ]);
    clearTimeout(stopper);state.pending=null;$('#nasa-load-feeds').disabled=false;
    if(controller.signal.aborted){$('#nasa-source-status').textContent='PUBLIC DATA / CANCELED';$('#nasa-feed-feedback').textContent='Requests canceled or timed out. Previous readings (if any) remain labeled by their original retrieval time.';return;}
    state.errors=[];
    if(outcomes[0].status==='fulfilled'){state.events=outcomes[0].value;$('#nasa-event-count').textContent=String(state.events.length);}else {state.events=null;$('#nasa-event-count').textContent='—';state.errors.push('NASA EONET unavailable');}
    if(outcomes[1].status==='fulfilled'){state.kp=outcomes[1].value;$('#nasa-kp').textContent=state.kp.kp.toFixed(1);}else {state.kp=null;$('#nasa-kp').textContent='—';state.errors.push('NOAA SWPC unavailable');}
    const successes=2-state.errors.length;
    if(successes){state.retrievedAt=new Date().toISOString();$('#nasa-fetched-at').textContent=state.retrievedAt.slice(0,19).replace('T',' ')+'Z';}else{state.retrievedAt=null;$('#nasa-fetched-at').textContent='Unavailable';}
    $('#nasa-source-status').textContent=successes===2?'PUBLIC DATA / LOADED':successes===1?'PUBLIC DATA / PARTIAL':'PUBLIC DATA / OFFLINE';
    const kpTime=state.kp?.observedAt ? `NOAA observation ${state.kp.observedAt}` : 'No validated Kp observation';
    $('#nasa-feed-feedback').textContent=`${successes}/2 official feeds verified. ${kpTime}. ${state.errors.join('; ')||'Reported-event locations are approximate; no source is military tracking.'}`;
    renderPublicEvents();renderMarkers();
  }
  function exportData() {
    const bundle={disclaimer:'Civil Earth observation only; no tactical or military tracking',retrievedAt:state.retrievedAt,events:state.events||[],spaceWeather:state.kp,missions:MISSIONS,sourceUrls:FEEDS};
    const url=URL.createObjectURL(new Blob([JSON.stringify(bundle,null,2)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='tak-os-nasa-public-sources.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function init() {
    const date=$('#nasa-date');date.max=utcDate(0);date.value=utcDate(3);
    renderMissions();renderPublicEvents();
    $('#nasa-imagery-toggle').addEventListener('change',e=>{state.imagery=e.target.checked;state.signature='';renderImages(true);});
    $('#nasa-events-toggle').addEventListener('change',e=>{state.displayEvents=e.target.checked;renderMarkers();});
    $('#nasa-imagery-select').addEventListener('change',()=>{state.signature='';renderImages(true);});
    date.addEventListener('change',()=>{state.signature='';renderImages(true);});
    $('#nasa-opacity').addEventListener('input',e=>{$('#nasa-opacity-value').textContent=`${e.target.value}%`;state.signature='';renderImages(true);});
    $('#nasa-open-map').addEventListener('click',()=>{window.TAKOSApp?.navigateView('map');renderImages(true);});
    $('#nasa-restore-map').addEventListener('click',()=>window.TAKOSApp?.resetPublicView());
    $('#nasa-load-feeds').addEventListener('click',refreshFeeds);
    $('#nasa-stop-feeds').addEventListener('click',()=>{if(state.pending)state.pending.abort();});
    $('#nasa-export').addEventListener('click',exportData);
    $('#nasa-country-filter').addEventListener('change',renderMissions);
    window.addEventListener('takos:map-render',(e)=>{state.map=e.detail;renderImages();renderMarkers();});
    // No automatic fetch: user controls the use of public imagery and JSON services.
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
  window.TAKOSNASA=Object.freeze({normalizeEvents,normalizeKp,webMercator,dateValid,missions:MISSIONS,refreshFeeds});
})();
