/* Public source health, iPhone resource budget and reference geometry; no synthetic observations. */
(function(root,factory){
 const moduleValue=factory();
 if(typeof module==='object'&&module.exports)module.exports=moduleValue;
 else root.TAKIphoneGrid=moduleValue;
})(typeof globalThis==='object'?globalThis:this,function(){
 'use strict';
 const FEEDS=Object.freeze(['usgs','eonet','noaa','orbit']);
 function chooseProfile(options={}){
  const width=Number(options.width)||1200;
  const mobile=Boolean(options.iosPhone||(options.coarse&&width<=850));
  const saver=Boolean(options.saveData||options.reducedMotion);
  const dpr=Math.min(4,Math.max(1,Number(options.dpr)||1));
  return Object.freeze({
   mobile,saver,
   resolutionScale:mobile?(saver?0.58:(dpr>=3?0.72:0.82)):(saver?0.8:1),
   tileCacheSize:mobile?48:110,
   maximumScreenSpaceError:mobile?4.5:2,
   orbitTickMs:mobile?30000:12000,
   cameraDuration:options.reducedMotion?0:(mobile?0.55:1.4)
  });
 }
 function summarize(states={}){
  let online=0,stale=0,failed=0;
  for(const id of FEEDS){
   const state=states[id]||'NOT_CONNECTED';
   if(state==='OK')online++;
   else if(state==='STALE')stale++;
   else if(state==='ERROR')failed++;
  }
  return Object.freeze({online,total:FEEDS.length,stale,failed,
   label:online?('PUBLIC CLOUD '+online+'/'+FEEDS.length+' SOURCES CURRENT')
     :'PUBLIC CLOUD: NO CURRENT SOURCES'});
 }
 function graticule(step=30){
  if(!Number.isInteger(step)||step<10||step>90||180%step!==0)throw Error('invalid grid interval');
  const lines=[];
  for(let lat=-90+step;lat<90;lat+=step){
   const coordinates=[];for(let lon=-180;lon<=180;lon+=5)coordinates.push(lon,lat);
   lines.push(coordinates);
  }
  for(let lon=-180;lon<180;lon+=step){
   const coordinates=[];for(let lat=-85;lat<=85;lat+=5)coordinates.push(lon,lat);
   lines.push(coordinates);
  }
  return lines;
 }
 return Object.freeze({FEEDS,chooseProfile,summarize,graticule});
});
