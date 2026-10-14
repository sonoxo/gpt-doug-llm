/* Real-data-only Cesium Earth 3D. NO mocked/seeded observations.
 * Public provider reports and SGP4-derived civil-orbit positions are distinct.
 */
(() => {
'use strict';
const $=id=>document.getElementById(id), cfg=window.TAKLiveOntology;
if(!cfg){$('global-status').textContent='ONTOLOGY MODULE FAILED TO LOAD';return;}
const {PROVIDERS,Ontology,parseEonet,parseUsgs,parseNoaa,parseOrbits,parseBuildings}=cfg;
const mobileTools=window.TAKIphoneGrid;
const mobileProfile=mobileTools?mobileTools.chooseProfile({
 width:window.innerWidth,dpr:window.devicePixelRatio,
 coarse:window.matchMedia?.('(pointer:coarse)').matches,
 iosPhone:/iPhone/i.test(navigator.userAgent),
 saveData:navigator.connection?.saveData,
 reducedMotion:window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}):{mobile:false,resolutionScale:1,tileCacheSize:110,maximumScreenSpaceError:2,orbitTickMs:12000,cameraDuration:1.4};
let gridVisible=false;
const store=new Ontology(), statusNodes=['usgs','eonet','noaa','orbit','buildings'];
const ui={enabled:{usgs:true,eonet:true,noaa:true,orbit:true,buildings:true},lastRequested:new Map(),inFlight:new Set(),lastFly:null,selected:null,orbitPositions:new Map(),camera:'earth',viewer:null,dataSources:{},serviceTimers:[],orbitLibrary:null,originError:null,imagery:null,imagesInError:0,buildingsRunAt:0,gridSource:null,baseLayer:null,streetsLayer:null,streetFailures:0};
const cities={richmond:{lat:37.5407,lon:-77.436},dc:{lat:38.9072,lon:-77.0369},nyc:{lat:40.7128,lon:-74.006},sf:{lat:37.7749,lon:-122.4194}};
const colors={usgs:'#ff897f',eonet:'#fac675',orbit:'#70fbef',buildings:'#a1e4ff'};
const countString=(n)=>Number(n).toLocaleString();
function text(id,value){const el=$(id);if(el)el.textContent=String(value);}
function stamp(d){if(!d)return'not recorded';const time=new Date(d);return Number.isNaN(time.getTime())?'not recorded':time.toISOString().replace('T',' ').replace(/\.\d+Z$/,' UTC');}
function age(iso){if(!iso)return'UNKNOWN AGE';const diff=Math.max(0,Date.now()-new Date(iso).getTime());if(!Number.isFinite(diff))return'UNKNOWN AGE';if(diff<60000)return`${Math.round(diff/1000)}s`;if(diff<3600000)return`${Math.floor(diff/60000)}m`;if(diff<86400000)return`${Math.floor(diff/3600000)}h`;return`${Math.floor(diff/86400000)}d`;}
let toastHandle;function toast(message){const el=$('toast');el.textContent=message;el.classList.add('show');clearTimeout(toastHandle);toastHandle=setTimeout(()=>el.classList.remove('show'),4500);}
function safeLink(url){try{const u=new URL(url);return u.protocol==='https:'?u.href:null;}catch(_){return null;}}
function download(name,data){const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/ld+json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);}
function formatStatus(state){return state==='OK'?'CURRENT':state==='ERROR'?'FAILED':state==='STALE'?'STALE':state==='CONNECTING'?'LOADING':state;}
function renderHealth(){
 const health=$('feed-health');health.replaceChildren();let current=0;
 for(const id of statusNodes){
  const m=store.status(id),enabled=ui.enabled[id];if(m.state==='OK')current++;
  const row=document.createElement('div'),label=document.createElement('span'),right=document.createElement('strong');
  label.textContent=PROVIDERS[id].label;right.textContent=`${!enabled?'HIDDEN · ':''}${formatStatus(m.state)}${m.state==='OK'?` · ${m.count}`:''}`;
  right.className=`health-${m.state==='OK'?'ok':m.state==='ERROR'?'error':'stale'}`;
  row.append(label,right);row.title=m.error||`Last ingested ${stamp(m.fetchedAt)}. Provider refresh status, not a guarantee of live telemetry.`;health.append(row);
  text('status-'+id,formatStatus(m.state));
 }
 const cloud=mobileTools?mobileTools.summarize(Object.fromEntries(['usgs','eonet','noaa','orbit'].map(id=>[id,store.status(id).state]))):{online:current,total:5,label:'PUBLIC CLOUD '+current+'/5'};
 text('cloud-grid-status',cloud.label+' · TAK SERVER: NOT CONNECTED');
 text('feed-count',`${cloud.online}/${cloud.total}`);const counts=store.counts();text('live-count',Object.values(counts).reduce((a,b)=>a+b,0));
 const kp=store.current('noaa')[0];text('global-kp',kp?Number(kp.properties.kp).toFixed(2):'—');
 const anyone=cloud.online>0;text('global-status',anyone?'PUBLIC FEEDS RECEIVED · INSPECT SOURCE AGES': 'NO VERIFIED LIVE FEED · CHECK CONNECTION');
 text('health-updated',new Date().toISOString().slice(11,19)+' UTC');
 $('ontology-stats').replaceChildren();
 for (const [title,value] of Object.entries({'source entities':5,'observation nodes':store.records.size,'active nodes':Object.values(counts).reduce((a,b)=>a+b,0)})){
   const el=document.createElement('span');el.textContent=`${title.toUpperCase()}: ${countString(value)}`;$('ontology-stats').append(el);
 }
}
function renderRecords(){
 const target=$('records');target.replaceChildren();const q=$('record-search').value.toLowerCase().trim(),filter=$('record-type').value;
 const all=store.all().filter(r=>(filter==='all'||r.type===filter||(filter==='NaturalHazard'&&r.provider==='eonet'))&&(!q||`${r.label} ${r.id} ${r.provider}`.toLowerCase().includes(q)));
 all.sort((a,b)=>Number(b.live)-Number(a.live)||new Date(b.observationTime||b.ingestedAt)-new Date(a.observationTime||a.ingestedAt));
 if(!all.length){let el=document.createElement('p');el.textContent='No matching sourced records. Nothing has been fabricated.';target.append(el);return;}
 for(const r of all.slice(0,60)){
  const b=document.createElement('button');b.type='button';b.className='record';const t=document.createElement('b'),s=document.createElement('small');t.textContent=r.label;s.textContent=`${r.live?'CURRENT':'STALE / ARCHIVED'} · ${r.provider.toUpperCase()} · ${r.observationTime?age(r.observationTime)+' old':'source timestamp unavailable'}`;b.append(t,s);
  b.onclick=()=>inspect(r);target.append(b);
 }
}
function inspect(r){
 if(!r)return;ui.selected=r.id;
 const el=$('entity-inspector');el.replaceChildren();const h=document.createElement('strong');h.textContent=r.label;el.append(h);
 const list=document.createElement('dl');const feed=store.status(r.provider),fields=[
  ['Ontology type',r.type],['Source',PROVIDERS[r.provider]?.label||r.provider],['State',feed.state],['Observed at',stamp(r.observationTime)],['Ingested at',stamp(r.ingestedAt)],
  ['Method',r.methodology],['Uncertainty',r.accuracy],['Record id',r.id]
 ];
 const orbit=ui.orbitPositions.get(r.id);if(orbit){fields.push(['ORBIT STATE','SGP4 MODEL, NOT LIVE TRACK'],['Computed at',stamp(orbit.calculatedAt)],['Model latitude',orbit.lat.toFixed(3)+'°'],['Model longitude',orbit.lon.toFixed(3)+'°'],['Model height',Math.round(orbit.altitudeMeters/1000)+' km']);}
 for(const [key,value] of fields){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=key;dd.textContent=value??'unavailable';list.append(dt,dd);}el.append(list);
 const link=safeLink(r.sourceUrl);if(link){let a=document.createElement('a');a.href=link;a.target='_blank';a.rel='noopener noreferrer';a.textContent='OPEN ORIGINAL PROVIDER RECORD ↗';a.style.cssText='display:block;margin-top:11px;font-size:10px';el.append(a);}
 const p=r.geometry?.point;if(p&&ui.viewer){ui.viewer.camera.flyTo({destination:window.Cesium.Cartesian3.fromDegrees(p.lon,p.lat,r.type==='BuildingFootprint'?2400:950000),duration:mobileProfile.cameraDuration});}
 else if(orbit && ui.viewer){ui.viewer.camera.flyTo({destination:window.Cesium.Cartesian3.fromDegrees(orbit.lon,orbit.lat,orbit.altitudeMeters+1200000),duration:mobileProfile.cameraDuration});}
}
function rendererReady(){return Boolean(ui.viewer&&window.Cesium);}
function sourceData(id){const C=window.Cesium;return new C.CustomDataSource(id);}
function cart(p,height=0){return window.Cesium.Cartesian3.fromDegrees(p.lon,p.lat,height);}
function rebuildSource(id){
 if(!rendererReady() || !ui.dataSources[id])return;
 const C=window.Cesium,entities=ui.dataSources[id].entities;entities.removeAll();
 if(!ui.enabled[id])return;
 for(const r of store.current(id)){
  if(id==='orbit'||id==='noaa')continue;
  const p=r.geometry?.point;if(!p)continue;
  const color=C.Color.fromCssColorString(colors[id]||'#56d9df');
  const props={id:r.id,name:r.label,description:'Provider-backed observation. Open ontology inspector for source timestamp.'};
  if(id==='buildings' && r.geometry.type==='Polygon'){
    const height=r.properties?.heightMeters;
    const degrees=r.geometry.points.flatMap(x=>[x.lon,x.lat]);
    if(degrees.length<6)continue;
    props.polygon={hierarchy:C.Cartesian3.fromDegreesArray(degrees),height:0,extrudedHeight:height===null?undefined:height,
      material:color.withAlpha(height===null?.17:.65),outline:true,outlineColor:color.withAlpha(.85)};
  }else if(r.geometry.type==='Polygon'){
    const degrees=r.geometry.points.flatMap(x=>[x.lon,x.lat]);
    if(degrees.length<6)continue;
    props.polygon={hierarchy:C.Cartesian3.fromDegreesArray(degrees),height:0,material:color.withAlpha(.18),outline:true,outlineColor:color};
    props.position=cart(p);props.point={pixelSize:9,color:outlineSafe(color),outlineColor:C.Color.BLACK,outlineWidth:1,heightReference:C.HeightReference.NONE};
  }else{
    props.position=cart(p);props.point={pixelSize:id==='usgs'?Math.max(6,Math.min(19,6+Math.max(0,Number(r.properties.magnitude)||0)*1.6)):11,color,
      outlineColor:C.Color.fromCssColorString('#031019'),outlineWidth:2};
  }
  entities.add(props);
 }
 ui.viewer.scene.requestRender();
}
function outlineSafe(c){return c;}
let orbitRecords=[];
async function loadOrbitLibrary(){
 if(ui.orbitLibrary)return ui.orbitLibrary;
 try{
   const m=await import('https://esm.sh/satellite.js@7.1.0?bundle');
   if(!m.json2satrec||!m.propagate||!m.eciToGeodetic)throw Error('SGP4 library missing required functions');
   ui.orbitLibrary=m;return m;
 }catch(err){toast('Orbit elements loaded, but SGP4 library unavailable: no positions will be displayed');throw err;}
}
function orbitalRender(){
 if(!rendererReady()||!ui.enabled.orbit||!ui.orbitLibrary)return;
 const C=window.Cesium,orb=ui.dataSources.orbit.entities;orb.removeAll();ui.orbitPositions.clear();
 const lib=ui.orbitLibrary,when=new Date();
 for(const r of store.current('orbit')){
   try{
    const satellite=lib.json2satrec(r.properties.omm);
    const state=lib.propagate(satellite,when);
    if(!state||!state.position||!Number.isFinite(state.position.x))continue;
    const location=lib.eciToGeodetic(state.position,lib.gstime(when));
    const lat=lib.degreesLat(location.latitude),lon=lib.degreesLong(location.longitude),alt=location.height*1000;
    if(!cfg.validCoord(lat,lon)||!Number.isFinite(alt)||alt<100000||alt>50000000)continue;
    ui.orbitPositions.set(r.id,{lat,lon,altitudeMeters:alt,calculatedAt:when.toISOString()});
    orb.add({id:r.id,name:r.label,position:C.Cartesian3.fromDegrees(lon,lat,alt),
      point:{pixelSize:10,color:C.Color.fromCssColorString('#70fbef'),outlineColor:C.Color.BLACK,outlineWidth:2},
      label:{text:r.label,scale:.35,pixelOffset:new C.Cartesian2(0,-15),fillColor:C.Color.fromCssColorString('#c7ffff'),showBackground:true,
        distanceDisplayCondition:new C.DistanceDisplayCondition(0,14000000)},
      description:'CelesTrak public OMM + SGP4 computed state; NOT live GPS telemetry.'});
   }catch(_){/* Invalid TLE/OMM never generates a fabricated satellite position. */}
 }
 ui.viewer.scene.requestRender();
}
function updateOntology(){renderHealth();renderRecords();if(ui.selected){const r=store.records.get(ui.selected);if(r)inspectNoFly(r);}}
function inspectNoFly(r){const previously=ui.viewer;ui.viewer=null;inspect(r);ui.viewer=previously;}
store.subscribe(updateOntology);
async function readJson(url, timeout=14000){
 const controller=new AbortController(),kill=setTimeout(()=>controller.abort(),timeout);
 try{const res=await fetch(url,{mode:'cors',cache:'no-store',headers:{Accept:'application/json'},signal:controller.signal,referrerPolicy:'no-referrer'});
   if(!res.ok)throw Error(`HTTP ${res.status}`);const ct=res.headers.get('content-type')||'';if(!ct.includes('json'))throw Error(`Not JSON (${ct||'no content-type'})`);
   return await res.json();
 }finally{clearTimeout(kill);}
}
async function refresh(id,force=false){
 if(ui.inFlight.has(id))return;
 const conf=PROVIDERS[id],last=ui.lastRequested.get(id)||0;if(!force&&Date.now()-last<conf.intervalMs)return;
 ui.lastRequested.set(id,Date.now());ui.inFlight.add(id);
 // The source is not shown as healthy until a well-formed response is received.
 const sourceState=store.health.get(id);
 if(!sourceState)store.health.set(id,{state:'CONNECTING',count:0});renderHealth();
 try{
  let response,records;
  if(id==='usgs'){response=await readJson(conf.url);records=parseUsgs(response);}
  else if(id==='eonet'){response=await readJson(conf.url);records=parseEonet(response);}
  else if(id==='noaa'){response=await readJson(conf.url);records=parseNoaa(response);}
  else if(id==='orbit'){
    const [stations,weather]=await Promise.all([readJson(conf.url,20000),readJson('https://celestrak.org/NORAD/elements/gp.php?GROUP=WEATHER&FORMAT=JSON',20000)]);
    const stationsOnly=stations.filter(x=>/ISS|ZARYA|TIANHE|TIANGONG/i.test(String(x.OBJECT_NAME||'')));
    const weatherOnly=weather.filter(x=>/NOAA|METOP|JPSS|SUOMI/i.test(String(x.OBJECT_NAME||'')));
    records=parseOrbits([...stationsOnly,...weatherOnly]);
    // Element sets are raw public source data; plotting is disabled if propagation lib is unavailable.
    orbitRecords=records;
  }else return;
  store.ingest(id,records);rebuildSource(id);
  if(id==='orbit')try{await loadOrbitLibrary();orbitalRender();}catch(_){ /* Source is valid but rendering the model is unavailable. */ }
  if(rendererReady())text('render-status','CESIUM 3D ACTIVE');
 }catch(err){store.failure(id,err);rebuildSource(id);if(id==='orbit'){ui.dataSources.orbit?.entities.removeAll();ui.orbitPositions.clear();}
  toast(`${PROVIDERS[id].label}: ${err.message||'feed unavailable'}. No replacement data.`);
 }finally{ui.inFlight.delete(id);renderHealth();}
}
async function refreshAll(force=false){await Promise.all(['usgs','eonet','noaa','orbit'].map(k=>refresh(k,force)));}
function setCamera(target){
 if(!rendererReady())return;
 const C=window.Cesium;
 const views={earth:{lon:-22,lat:18,height:21000000},'north-america':{lon:-95,lat:38,height:7000000},atlantic:{lon:-37,lat:30,height:12500000},city:{...cities[$('city-select').value],height:13000}};
 const p=views[target]||views.earth;
 ui.viewer.camera.flyTo({destination:C.Cartesian3.fromDegrees(p.lon,p.lat,p.height),duration:mobileProfile.cameraDuration});
}
function initGlobe(){
 const C=window.Cesium;
 if(!C){text('render-status','3D ENGINE: CDN UNAVAILABLE');text('imagery-state','NO ENGINE: NO FALLBACK IMAGE');return;}
 try{
 const wms=new C.WebMapServiceImageryProvider({url:'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi',layers:'BlueMarble_NextGeneration',
  parameters:{service:'WMS',format:'image/jpeg',transparent:false,version:'1.1.1'},tilingScheme:new C.GeographicTilingScheme(),credit:new C.Credit('NASA GIBS / Blue Marble Next Generation historical composite')});
 wms.errorEvent.addEventListener(()=>{text('imagery-state','BASE IMAGERY TILE ERROR — CHECK NASA GIBS');});
 ui.viewer=new C.Viewer('globe',{baseLayer:new C.ImageryLayer(wms),terrainProvider:new C.EllipsoidTerrainProvider(),timeline:false,animation:false,
  baseLayerPicker:false,geocoder:false,homeButton:false,fullscreenButton:false,sceneModePicker:false,navigationHelpButton:false,
  selectionIndicator:true,infoBox:false,requestRenderMode:true,maximumRenderTimeChange:Infinity});
 ui.viewer.resolutionScale=mobileProfile.resolutionScale;
 ui.viewer.scene.globe.tileCacheSize=mobileProfile.tileCacheSize;
 ui.viewer.scene.globe.maximumScreenSpaceError=mobileProfile.maximumScreenSpaceError;
 ui.baseLayer=ui.viewer.imageryLayers.get(0);
 if(mobileProfile.mobile){
   ui.viewer.scene.fog.enabled=false;
   if(ui.viewer.scene.skyAtmosphere)ui.viewer.scene.skyAtmosphere.show=false;
 }
 ui.viewer.scene.globe.baseColor=C.Color.fromCssColorString('#152334');ui.viewer.scene.globe.depthTestAgainstTerrain=false;
 ui.viewer.scene.requestRenderMode=true;
 const ds=ui.dataSources;for(const id of ['usgs','eonet','orbit','buildings']){ds[id]=sourceData(id);ui.viewer.dataSources.add(ds[id]);}
 const reference=new C.CustomDataSource('wgs84-reference-grid');
 if(mobileTools){
  for(const degrees of mobileTools.graticule(30)){
   reference.entities.add({polyline:{positions:C.Cartesian3.fromDegreesArray(degrees),width:1,material:C.Color.fromCssColorString('#77e8ed').withAlpha(.32)}});
  }
 }
 ui.viewer.dataSources.add(reference);
 reference.show=false;
 ui.gridSource=reference;
 ui.viewer.selectedEntityChanged.addEventListener(entity=>{if(entity){const r=store.records.get(entity.id);if(r)inspectNoFly(r);}});
 ui.viewer.camera.moveEnd.addEventListener(updateCameraReadout);
 text('render-status',mobileProfile.mobile?'3D ACTIVE · iPHONE':'CESIUM 3D ACTIVE');text('imagery-state','NASA HISTORICAL BASE REQUESTED');
 setCamera(mobileProfile.mobile?'north-america':'earth');updateCameraReadout();
 }catch(err){text('render-status','CESIUM ERROR');text('imagery-state','GLOBE UNAVAILABLE');toast(`Cesium failed: ${err.message}`);}
}
function overlayImagery(){
 if(!rendererReady())return;
 const C=window.Cesium,checked=$('imagery-overlay').checked,date=$('imagery-date').value;
 if(ui.imagery){ui.viewer.imageryLayers.remove(ui.imagery,true);ui.imagery=null;}
 if(!checked){text('imagery-note','NASA MODIS overlay OFF. Base uses historical composite, not live video.');return;}
 if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||date>new Date().toISOString().slice(0,10)){text('imagery-note','Choose a valid past observation date.');$('imagery-overlay').checked=false;return;}
 try{
  const provider=new C.WebMapServiceImageryProvider({url:'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi',layers:'MODIS_Terra_CorrectedReflectance_TrueColor',
    parameters:{service:'WMS',format:'image/png',transparent:true,version:'1.1.1',time:date},tilingScheme:new C.GeographicTilingScheme(),
    credit:new C.Credit(`NASA GIBS MODIS Terra requested observation day ${date}`)});
  ui.imagery=ui.viewer.imageryLayers.add(new C.ImageryLayer(provider,{alpha:.92}));
  provider.errorEvent.addEventListener(()=>{text('imagery-note',`NASA MODIS ${date}: tile request failed; imagery unavailable.`);});
  text('imagery-note',`Requested ${date} from NASA. Coverage may be delayed or absent; no fallback imagery invented.`);
  ui.viewer.scene.requestRender();
 }catch(err){text('imagery-note',`Imagery cannot be loaded: ${err.message}`);}
}
async function loadBuildings(){
 if(ui.inFlight.has('buildings'))return;
 const now=Date.now();if(now-ui.buildingsRunAt<60000){toast('Respect Overpass usage limits: please wait 60 seconds between building requests.');return;}
 ui.buildingsRunAt=now;ui.inFlight.add('buildings');const c=cities[$('city-select').value],v=.004;
 const q=`[out:json][timeout:18];way["building"](${(c.lat-v).toFixed(6)},${(c.lon-v).toFixed(6)},${(c.lat+v).toFixed(6)},${(c.lon+v).toFixed(6)});out geom;`;
 text('building-note','Requesting actual OSM building geometry; results may be limited or rate controlled.');
 try{
   const data=await readJson(`${PROVIDERS.buildings.url}?data=${encodeURIComponent(q)}`,25000);
   const buildings=parseBuildings(data);store.ingest('buildings',buildings);rebuildSource('buildings');setCamera('city');
   const measured=buildings.filter(x=>x.properties.heightMeters!==null).length;
   text('building-note',`${buildings.length} actual OSM footprints received; ${measured} have recorded height tags and are extruded. ${buildings.length-measured} stay flat. Community data is not surveyed truth.`);
 }catch(err){store.failure('buildings',err);rebuildSource('buildings');text('building-note',`OSM Overpass unavailable: ${err.message}. No estimated heights generated.`);
 }finally{ui.inFlight.delete('buildings');renderHealth();}
}
function updateCameraReadout(){
 if(!rendererReady())return;
 const c=ui.viewer.camera.positionCartographic,C=window.Cesium;
 if(!c)return;
 const latitude=C.Math.toDegrees(c.latitude),longitude=C.Math.toDegrees(c.longitude);
 const altitude=Math.max(0,c.height)/1000;
 text('mobile-camera-readout','CAMERA '+Math.abs(latitude).toFixed(1)+'°'+(latitude<0?'S':'N')+' · '+Math.abs(longitude).toFixed(1)+'°'+(longitude<0?'W':'E')+' · '+altitude.toFixed(altitude<100?1:0)+' km ALT');
}
function toggleStreets(){
 if(!rendererReady()){toast('3D map unavailable.');return;}
 const C=window.Cesium;
 if(ui.streetsLayer){
  ui.viewer.imageryLayers.remove(ui.streetsLayer,true);ui.streetsLayer=null;
  if(ui.baseLayer)ui.baseLayer.show=true;
  $('street-toggle').textContent='OSM STREETS OFF';
  $('street-mobile').textContent='STREETS';
  $('street-toggle').setAttribute('aria-pressed','false');
  $('street-mobile').setAttribute('aria-pressed','false');
  text('streets-note','OSM street tiles OFF. NASA GIBS historical composite selected.');
 }else{
  try{
   const provider=new C.UrlTemplateImageryProvider({
    url:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    tilingScheme:new C.WebMercatorTilingScheme(),maximumLevel:18,
    credit:new C.Credit('© OpenStreetMap contributors')
   });
   provider.errorEvent.addEventListener(()=>{
    ui.streetFailures++;
    if(ui.streetFailures===1){
     text('streets-note','OSM imagery request failed; check network or tile service. No replacement tiles generated.');
     toast('OSM tile request failed. Check source access.');
    }
   });
   ui.streetFailures=0;
   ui.streetsLayer=ui.viewer.imageryLayers.addImageryProvider(provider);
   if(ui.baseLayer)ui.baseLayer.show=false;
   $('street-toggle').textContent='OSM STREETS ON';
   $('street-mobile').textContent='STREETS ON';
   $('street-toggle').setAttribute('aria-pressed','true');
   $('street-mobile').setAttribute('aria-pressed','true');
   text('streets-note','OSM street tiles requested for this view only. © OpenStreetMap contributors. Network and usage policy apply.');
   if(mobileProfile.mobile)setCamera('city'); // Preset city, not device GPS.
  }catch(err){toast('OSM streets unavailable: '+err.message);}
 }
 ui.viewer.scene.requestRender();
}
function moveCamera(action){
 if(!rendererReady())return;
 if(action==='center'){setCamera('north-america');return;}
 const height=ui.viewer.camera.positionCartographic?.height;
 if(!Number.isFinite(height))return;
 const step=Math.max(300,Math.min(6000000,Math.abs(height)*0.33));
 if(action==='zoom-in')ui.viewer.camera.zoomIn(step);
 else if(action==='zoom-out')ui.viewer.camera.zoomOut(step);
 ui.viewer.scene.requestRender();updateCameraReadout();
}
function switchMobilePanel(panel){
 const left=document.querySelector('.leftpanel'),right=document.querySelector('.rightpanel');
 left.classList.toggle('mobile-open',panel==='layers');
 right.classList.toggle('mobile-open',panel==='intel');
 document.querySelectorAll('[data-mobile-panel]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.mobilePanel===panel)));
 if(rendererReady())ui.viewer.scene.requestRender();
}
function toggleReferenceGrid(){
 if(!ui.gridSource){toast('3D map unavailable: cannot draw coordinate grid.');return;}
 gridVisible=!gridVisible;ui.gridSource.show=gridVisible;
 $('grid-toggle').textContent=gridVisible?'30° GRID ON':'30° GRID OFF';
 $('grid-toggle').setAttribute('aria-pressed',String(gridVisible));
 $('grid-mobile').textContent=gridVisible?'GRID ON':'GRID OFF';
 $('grid-mobile').setAttribute('aria-pressed',String(gridVisible));
 ui.viewer.scene.requestRender();
}
function registerShell(){
 if('serviceWorker' in navigator && (location.protocol==='https:'||['localhost','127.0.0.1'].includes(location.hostname))){
  navigator.serviceWorker.register('./sw.js',{scope:'./'}).catch(()=>{});
 }
}
function bind(){
 $('refresh-all').addEventListener('click',()=>refreshAll(true));
 $('export-ontology').addEventListener('click',()=>download('gpt-doug-real-earth-ontology.jsonld',store.exportJsonLD()));
 $('record-search').addEventListener('input',renderRecords);$('record-type').addEventListener('change',renderRecords);
 for(const id of ['usgs','eonet','noaa','orbit'])$('toggle-'+id).addEventListener('change',event=>{
   ui.enabled[id]=event.target.checked;
   if(ui.dataSources[id])ui.dataSources[id].show=ui.enabled[id];
   renderHealth();renderRecords();
 });
 $('imagery-overlay').addEventListener('change',overlayImagery);$('imagery-apply').addEventListener('click',()=>{$('imagery-overlay').checked=true;overlayImagery();});
 $('buildings-load').addEventListener('click',loadBuildings);
 document.querySelectorAll('[data-camera]').forEach(btn=>btn.addEventListener('click',()=>setCamera(btn.dataset.camera)));
 $('reset-camera').addEventListener('click',()=>setCamera('earth'));
 document.querySelectorAll('[data-mobile-panel]').forEach(button=>button.addEventListener('click',()=>switchMobilePanel(button.dataset.mobilePanel)));
 $('grid-toggle').addEventListener('click',toggleReferenceGrid);
 $('street-toggle').addEventListener('click',toggleStreets);
 $('street-mobile').addEventListener('click',toggleStreets);
 document.querySelectorAll('[data-map-action]').forEach(button=>button.addEventListener('click',()=>moveCamera(button.dataset.mapAction)));
 document.querySelectorAll('[data-close-panel]').forEach(button=>button.addEventListener('click',()=>switchMobilePanel('map')));
 $('grid-mobile').addEventListener('click',toggleReferenceGrid);
 $('toggle-hud').addEventListener('click',()=>switchMobilePanel('intel'));
 document.addEventListener('visibilitychange',()=>{if(!document.hidden){renderHealth();refreshAll(false);orbitalRender();}});
}
function init(){
 text('utc-clock',new Date().toISOString().slice(11,19)+' UTC');
 $('imagery-date').value=new Date(Date.now()-2*86400000).toISOString().slice(0,10);
 $('imagery-date').max=new Date().toISOString().slice(0,10);
 bind();switchMobilePanel('map');initGlobe();registerShell();renderHealth();renderRecords();store.restoreArchive().catch(()=>{});
 if(mobileProfile.mobile){
  refresh('usgs',true);refresh('eonet',true);
  setTimeout(()=>{if(!document.hidden){refresh('noaa',true);refresh('orbit',true);}},1600);
 }else refreshAll(true);
 setInterval(()=>text('utc-clock',new Date().toISOString().slice(11,19)+' UTC'),1000);
 setInterval(()=>{if(!document.hidden)refreshAll(false);renderHealth();},30000);
 setInterval(()=>{if(!document.hidden)orbitalRender();},mobileProfile.orbitTickMs);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
