/* Real public-source ontology: no example observations or fabricated geometry.
 * UMD wrapper keeps parser/graph usable in plain Node tests and browsers.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.TAKLiveOntology = factory();
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const PROVIDERS = Object.freeze({
    usgs: Object.freeze({label:'USGS Earthquake Hazards',url:'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson',intervalMs:120000,maxAgeMs:86400000}),
    eonet: Object.freeze({label:'NASA EONET v3',url:'https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=120',intervalMs:600000,maxAgeMs:86400000 * 14}),
    noaa: Object.freeze({label:'NOAA SWPC Kp index',url:'https://services.swpc.noaa.gov/json/planetary_k_index_1m.json',intervalMs:300000,maxAgeMs:3600000}),
    orbit: Object.freeze({label:'CelesTrak public stations/weather OMM',url:'https://celestrak.org/NORAD/elements/gp.php?GROUP=STATIONS&FORMAT=JSON',intervalMs:2700000,maxAgeMs:86400000 * 3}),
    buildings: Object.freeze({label:'OpenStreetMap via Overpass',url:'https://overpass-api.de/api/interpreter',intervalMs:0,maxAgeMs:86400000 * 90}),
  });
  const categoryType = Object.freeze({wildfires:'Wildfire',severeStorms:'SevereStorm',volcanoes:'Volcano',floods:'Flood',drought:'Drought',seaLakeIce:'CryosphereEvent'});
  // NOAA SWPC and CelesTrak OMM zone-less timestamps are UTC by provider convention.
  // A desktop's local timezone must never change an observation or SGP4 epoch.
  const epoch = x => {
    let value=x;
    if(typeof value==='string'){
      value=value.trim();
      if(/^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(value))
        value=value.replace(' ','T')+'Z';
    }
    const n=new Date(value).getTime();
    return Number.isFinite(n)?n:NaN;
  };
  const validCoord = (lat, lon) => Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
  const safeString = (value, max = 220) => String(value == null ? '' : value).slice(0, max).trim();
  const validPoint = raw => {
    if (!Array.isArray(raw) || raw.length < 2) return null;
    const lon = Number(raw[0]), lat = Number(raw[1]);
    return validCoord(lat, lon) ? {lat,lon} : null;
  };
  function centroid(ring) {
    if (!Array.isArray(ring)) return null;
    const points = ring.map(validPoint).filter(Boolean);
    if (points.length < 3) return null;
    return { lat:points.reduce((s,p)=>s+p.lat,0)/points.length, lon:points.reduce((s,p)=>s+p.lon,0)/points.length };
  }
  function hazardGeometry(g) {
    if (!g || !g.type) return null;
    if (g.type === 'Point') { const point=validPoint(g.coordinates); return point && {type:'Point',point}; }
    if (g.type === 'Polygon') {
      const ring=g.coordinates && g.coordinates[0];
      const points=Array.isArray(ring) ? ring.map(validPoint).filter(Boolean).slice(0,512) : [];
      if(points.length < 3) return null;
      return {type:'Polygon',points,point:centroid(ring),geometryDerived:'centroid_for_label_only'};
    }
    return null;
  }
  function parseEonet(payload, receivedAt = new Date().toISOString()) {
    if (!payload || !Array.isArray(payload.events)) throw Error('NASA EONET events array missing');
    const records=[];
    for (const event of payload.events.slice(0,150)) {
      if (!event || !event.id || !Array.isArray(event.geometry)) continue;
      const latest=event.geometry.slice().filter(g=>g && Number.isFinite(epoch(g.date))).sort((a,b)=>epoch(b.date)-epoch(a.date))[0];
      if(!latest) continue;
      const geometry=hazardGeometry(latest); if(!geometry) continue;
      const categories=Array.isArray(event.categories)?event.categories.map(x=>safeString(x.id,60)).filter(Boolean):[];
      records.push({id:'eonet:'+safeString(event.id,90),type:categoryType[categories[0]]||'NaturalHazard',provider:'eonet',label:safeString(event.title),
        observationTime:new Date(latest.date).toISOString(),ingestedAt:receivedAt,sourceUrl:`https://eonet.gsfc.nasa.gov/api/v3/events/${encodeURIComponent(event.id)}`,
        geometry,properties:{sourceStatus:event.closed?'closed':'open',categories,sourceNames:Array.isArray(event.sources)?event.sources.map(s=>safeString(s.id,64)):[]},
        methodology:'provider_reported_event_geometry',accuracy:'source_dependent'});
    }
    return records;
  }
  function parseUsgs(payload, receivedAt = new Date().toISOString()) {
    if (!payload || !Array.isArray(payload.features)) throw Error('USGS GeoJSON features missing');
    const records=[];
    for(const item of payload.features.slice(0,500)) {
      if(!item || !item.id || !item.geometry || item.geometry.type!=='Point')continue;
      const point=validPoint(item.geometry.coordinates), observed=item.properties&&item.properties.time;
      if(!point || !Number.isFinite(Number(observed)) || !Number.isFinite(epoch(Number(observed))))continue;
      const mag=Number(item.properties.mag);
      records.push({id:'usgs:'+safeString(item.id,80),type:'Earthquake',provider:'usgs',label:safeString(item.properties.place||'Earthquake observation'),
        observationTime:new Date(Number(observed)).toISOString(), ingestedAt:receivedAt,
        sourceUrl:safeUrl(item.properties.url,'https://earthquake.usgs.gov')||`https://earthquake.usgs.gov/earthquakes/eventpage/${encodeURIComponent(item.id)}`,
        geometry:{type:'Point',point},properties:{magnitude:Number.isFinite(mag)?mag:null,depthKm: Number.isFinite(Number(item.geometry.coordinates[2]))?Number(item.geometry.coordinates[2]):null,
          updated:Number.isFinite(epoch(Number(item.properties.updated)))?new Date(Number(item.properties.updated)).toISOString():null,reviewStatus:safeString(item.properties.status,32)},
        methodology:'provider_reported_hypocenter_2d_surface_projection',accuracy:'source_dependent'});
    }
    return records;
  }
  function safeUrl(url, prefix) {
    try {const u=new URL(url);return u.protocol==='https:'&&u.origin===prefix?u.href:null;}catch(_){return null;}
  }
  function parseNoaa(payload, receivedAt = new Date().toISOString()) {
    if(!Array.isArray(payload) || payload.length < 1) throw Error('NOAA Kp records missing');
    const candidates=[];
    // NOAA product endpoints return either object records or arrays with column headers.
    const rows=Array.isArray(payload[0]) && payload[0][0]==='time_tag' ? payload.slice(1).map(row=>Object.fromEntries(payload[0].map((k,i)=>[k,row[i]]))) : payload;
    for(const row of rows){
      if(!row)continue;
      const stamp=row.time_tag||row.time||row.timestamp, kp=Number(row.kp_index ?? row.kp ?? row.Kp);
      if(!Number.isFinite(epoch(stamp)) || !Number.isFinite(kp) || kp<0 || kp>9)continue;
      candidates.push({stamp:new Date(epoch(stamp)).toISOString(),kp});
    }
    if(!candidates.length)throw Error('NOAA feed contains no valid timestamped Kp record');
    candidates.sort((a,b)=>epoch(b.stamp)-epoch(a.stamp));
    const item=candidates[0];
    return [{id:'noaa:planetary-kp:'+item.stamp,type:'GeomagneticIndex',provider:'noaa',label:'Planetary Kp index',
      observationTime:item.stamp,ingestedAt:receivedAt,sourceUrl:PROVIDERS.noaa.url,geometry:null,
      properties:{kp:item.kp,units:'Kp',location:'global geomagnetic index'},methodology:'provider_reported_index_not_geolocatable',accuracy:'NOAA_reported'}];
  }
  const isCivilName=name=>/\b(ISS|ZARYA|TIANGONG|TIANHE|SHENZHOU|CYGNUS|DRAGON|NOAA|METOP|JPSS|SUOMI|DMSP-EXCLUDED)\b/i.test(name) && !/DMSP|DEB|ROCKET|R\/B|MILITARY|COSMOS/i.test(name);
  function parseOrbits(payload,receivedAt=new Date().toISOString(),nowMs=Date.now()){
    if(!Array.isArray(payload))throw Error('CelesTrak OMM JSON array missing');
    const result=[];
    for(const row of payload){
      if(!row || !row.NORAD_CAT_ID || !isCivilName(String(row.OBJECT_NAME||'')))continue;
      const observed=epoch(row.EPOCH);if(!Number.isFinite(observed)||nowMs-observed>PROVIDERS.orbit.maxAgeMs||observed>nowMs+600000)continue;
      if(!Number.isFinite(Number(row.MEAN_MOTION)) || Number(row.MEAN_MOTION)<=0)continue;
      const cat=Number(row.NORAD_CAT_ID);if(!Number.isInteger(cat)||cat<1)continue;
      result.push({id:'celestrak:'+cat,type:'CivilOrbitalElementSet',provider:'orbit',label:safeString(row.OBJECT_NAME,90),
        observationTime:new Date(observed).toISOString(),ingestedAt:receivedAt,
        sourceUrl:`https://celestrak.org/NORAD/elements/gp.php?CATNR=${cat}&FORMAT=JSON`,geometry:null,
        properties:{catalogNumber:cat,epoch:new Date(observed).toISOString(),omm:{...row,EPOCH:new Date(observed).toISOString()}},
        methodology:'public_general_perturbations_elements_requires_SGP4_propagation',accuracy:'predicted_not_live_position'});
      if(result.length>=24)break;
    }
    return result;
  }
  function heightMeters(text) {
    if(text == null) return null;
    const raw=String(text).trim();const match=raw.match(/^(\d+(?:\.\d+)?)\s*(m|meter|metres|meters|ft|feet|')?$/i);
    if(!match)return null;
    const v=Number(match[1]) * (/^(ft|feet|')$/i.test(match[2]||'')?0.3048:1);
    return Number.isFinite(v)&&v>=1&&v<=700?Math.round(v*100)/100:null;
  }
  function parseBuildings(payload,receivedAt=new Date().toISOString()) {
    if(!payload||!Array.isArray(payload.elements))throw Error('OSM Overpass elements missing');
    const records=[];
    for(const element of payload.elements.slice(0,1600)){
      if(element.type!=='way'||!element.tags?.building||!Array.isArray(element.geometry))continue;
      const points=element.geometry.map(g=>validPoint([g.lon,g.lat])).filter(Boolean).slice(0,128);
      if(points.length<3)continue;
      const height=heightMeters(element.tags.height); // Never manufacture unreported heights.
      records.push({id:'osm:way:'+element.id,type:'BuildingFootprint',provider:'buildings',label:safeString(element.tags.name||`OSM building ${element.id}`),
        observationTime:null,ingestedAt:receivedAt,sourceUrl:`https://www.openstreetmap.org/way/${element.id}`,
        geometry:{type:'Polygon',points,point:centroid(points.map(p=>[p.lon,p.lat]))},properties:{heightMeters:height,heightSource:height==null?'not_reported':'OSM_height_tag'},
        methodology:height==null?'recorded_footprint_no_height':'recorded_footprint_and_tagged_height',accuracy:'community_mapped_not_survey_verified'});
      if(records.length>=420)break;
    }
    return records;
  }
  class Ontology {
    constructor(clock=()=>Date.now()) {this.clock=clock;this.records=new Map();this.health=new Map();this.listeners=new Set();this.archived=false;}
    subscribe(fn){this.listeners.add(fn);return()=>this.listeners.delete(fn);}
    notify(){for(const f of this.listeners)try{f(this);}catch(_){/* UI callback */}}
    ingest(provider, records, receivedAt=new Date(this.clock()).toISOString()) {
      if(!PROVIDERS[provider]||!Array.isArray(records))throw Error('Unknown provider or invalid observations');
      // Remove old records for this provider: never mix prior snapshots into new live frames.
      for(const [key,v] of this.records)if(v.provider===provider)this.records.delete(key);
      for(const record of records)if(record.provider===provider && record.id && (record.geometry===null||record.geometry))this.records.set(record.id,Object.freeze({...record,ingestedAt:receivedAt}));
      this.health.set(provider,{state:'OK',fetchedAt:receivedAt,count:records.length,error:null});this.notify();this.saveArchive().catch(()=>{});
    }
    failure(provider, error){if(!PROVIDERS[provider])return;const old=this.health.get(provider)||{};this.health.set(provider,{...old,state:'ERROR',error:safeString(error?.message||error||'Source unavailable'),failedAt:new Date(this.clock()).toISOString()});this.notify();}
    status(provider){const config=PROVIDERS[provider], meta=this.health.get(provider);if(!config||!meta)return{state:'NOT_CONNECTED',count:0};
      if(meta.state==='ERROR')return{...meta,state:'ERROR'};
      const age=this.clock()-epoch(meta.fetchedAt);return age>config.intervalMs*2.5 && config.intervalMs ?{...meta,state:'STALE'}:{...meta,state:'OK'};
    }
    current(provider){const health=this.status(provider);return health.state==='OK'?[...this.records.values()].filter(r=>r.provider===provider && (r.observationTime===null || (this.clock()-epoch(r.observationTime))<=PROVIDERS[provider].maxAgeMs)) :[];}
    all(){return [...this.records.values()].map(r=>({...r,live:!!this.current(r.provider).find(x=>x.id===r.id)}));}
    counts(){return Object.fromEntries(Object.keys(PROVIDERS).map(k=>[k,this.current(k).length]));}
    async saveArchive(){
      if(typeof indexedDB==='undefined')return false;
      const db=await this.openArchive();
      const serialized=this.all().slice(0,1500).map(({live,...v})=>v);
      await new Promise((resolve,reject)=>{const transaction=db.transaction('snapshot','readwrite');transaction.objectStore('snapshot').put({id:'last_observations',savedAt:new Date(this.clock()).toISOString(),records:serialized});transaction.oncomplete=resolve;transaction.onerror=()=>reject(transaction.error);});
      db.close();return true;
    }
    async restoreArchive(){
      if(typeof indexedDB==='undefined')return false;
      const db=await this.openArchive();
      const archive=await new Promise((resolve,reject)=>{const tx=db.transaction('snapshot','readonly');const query=tx.objectStore('snapshot').get('last_observations');query.onsuccess=()=>resolve(query.result);query.onerror=()=>reject(query.error);});db.close();
      if(!archive?.records?.length)return false;
      for(const row of archive.records.slice(0,1500))if(row?.id&&PROVIDERS[row.provider]&&!this.records.has(row.id))this.records.set(row.id,Object.freeze({...row,restoredFromArchive:true}));
      this.archived=true;this.notify();return true; // Archived records are NEVER declared live until fresh provider fetch.
    }
    openArchive(){
      return new Promise((resolve,reject)=>{const request=indexedDB.open('gpt-doug-real-earth-ontology-v1',1);request.onupgradeneeded=()=>{const db=request.result;if(!db.objectStoreNames.contains('snapshot'))db.createObjectStore('snapshot',{keyPath:'id'});};request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});
    }
    exportJsonLD(){
      const context={prov:'http://www.w3.org/ns/prov#',schema:'https://schema.org/',geo:'https://www.opengis.net/ont/geosparql#',tak:'https://xunia.org/ontology/tak-os#'};
      const sources=Object.entries(PROVIDERS).map(([k,v])=>({'@id':`urn:tak-os:source:${k}`,'@type':'prov:Entity','schema:name':v.label,'schema:url':v.url,'tak:status':this.status(k).state,'tak:lastFetch':this.status(k).fetchedAt||null}));
      const entities=this.all().map(r=>({'@id':`urn:tak-os:observation:${r.id}`,'@type':`tak:${r.type}`,'schema:name':r.label,'prov:wasDerivedFrom':{'@id':`urn:tak-os:source:${r.provider}`},'prov:generatedAtTime':r.ingestedAt,'tak:observedAt':r.observationTime,
        'schema:url':r.sourceUrl,'tak:methodology':r.methodology,'tak:accuracy':r.accuracy,'tak:currentlyVerified':r.live,'tak:geometry':r.geometry,'tak:properties':r.properties}));
      return {'@context':context,'@graph':[...sources,...entities],exportedAt:new Date(this.clock()).toISOString(),disclaimer:'Provider reports and explicitly labeled calculated orbital positions. No synthetic data. No authority beyond cited source.'};
    }
  }
  return {PROVIDERS,Ontology,validPoint,heightMeters,parseEonet,parseUsgs,parseNoaa,parseOrbits,parseBuildings,validCoord};
});
