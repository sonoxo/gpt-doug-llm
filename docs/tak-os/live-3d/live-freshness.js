/* GPT-Doug real-source freshness ontology.
 * Public provider summaries are exportable. Private TAK admin summaries exist
 * only in volatile memory and MUST NOT join the public graph or browser archive.
 */
(function(root,factory){
 const api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 else root.TAKLiveFreshness=api;
})(typeof globalThis==='object'?globalThis:this,function(){
 'use strict';
 const CONTEXT=Object.freeze({
  prov:'http://www.w3.org/ns/prov#',
  schema:'https://schema.org/',
  tak:'https://xunia.org/ontology/tak-os#'
 });
 const VALID_STATES=new Set(['OK','ERROR','STALE','NOT_CONNECTED']);
 const PRIVATE_FIELDS=Object.freeze(['numClients','bytesRead','bytesWritten','numReads','numWrites']);
 const MAX_FUTURE_MS=60000;
 function iso(value,nowMs){
  if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value))return null;
  const ms=Date.parse(value);
  return Number.isFinite(ms)&&ms<=nowMs+MAX_FUTURE_MS?new Date(ms).toISOString():null;
 }
 function nonnegativeAge(date,nowMs){
  if(!date)return null;
  const value=(nowMs-Date.parse(date))/1000;
  return Number.isFinite(value)?Math.max(0,Math.round(value)):null;
 }
 function utcClock(nowMs=Date.now()){
  if(!Number.isFinite(nowMs))throw Error('invalid browser clock');
  return new Date(nowMs).toISOString().slice(0,19).replace('T',' ')+' UTC';
 }
 function publicSnapshot(store,providers,nowMs=Date.now()){
  if(!store||!providers||typeof store.status!=='function'||typeof store.current!=='function'||!Number.isFinite(nowMs))throw Error('invalid ontology arguments');
  const retrievedAtUtc=new Date(nowMs).toISOString(),sourceRows=[],graph=[];
  for(const [key,provider] of Object.entries(providers)){
   if(!/^[a-z][a-z0-9-]{0,30}$/.test(key))continue;
   const raw=store.status(key)||{};
   const fetchedAtUtc=iso(raw.fetchedAt,nowMs);
   const status=VALID_STATES.has(raw.state)?raw.state:'NOT_CONNECTED';
   const validStatus=status==='OK'&&fetchedAtUtc===null?'ERROR':status;
   const records=validStatus==='OK'?store.current(key):[];
   const latest=Array.isArray(records)?records.reduce((acc,record)=>{
    const observedAt=iso(record&&record.observationTime,nowMs);
    return observedAt&&(!acc||observedAt>acc)?observedAt:acc;
   },null):null;
   const sourceId='urn:tak-os:source:'+key;
   const source={
    id:key,label:String(provider.label||key).slice(0,100),sourceUrl:provider.url||null,
    state:validStatus,fetchedAtUtc,fetchAgeSeconds:nonnegativeAge(fetchedAtUtc,nowMs),
    latestObservationAtUtc:latest,latestObservationAgeSeconds:nonnegativeAge(latest,nowMs),
    currentRecordCount:Array.isArray(records)?records.length:0,
    onDemand:provider.intervalMs===0
   };
   sourceRows.push(source);
   graph.push({
    '@id':sourceId,'@type':'prov:Entity',
    'schema:name':source.label,'schema:url':source.sourceUrl,
    'tak:status':source.state,'tak:fetchedAt':source.fetchedAtUtc,
    'tak:fetchAgeSeconds':source.fetchAgeSeconds,
    'tak:lastObservationAt':source.latestObservationAtUtc,
    'tak:lastObservationAgeSeconds':source.latestObservationAgeSeconds,
    'tak:currentRecordCount':source.currentRecordCount,
    'tak:onDemand':source.onDemand,
    'prov:generatedAtTime':retrievedAtUtc
   });
  }
  const continuous=sourceRows.filter(x=>!x.onDemand);
  return {
   schema:'gpt-doug.live-source-ontology.v1',scope:'public_read_only',
   generatedAtUtc:retrievedAtUtc,privateTakIncluded:false,
   connectedContinuous:continuous.filter(x=>x.state==='OK').length,
   continuousTotal:continuous.length,
   sources:sourceRows,
   '@context':CONTEXT,'@graph':graph
  };
 }
 function privateSnapshot(info,nowMs=Date.now()){
  if(!info||typeof info!=='object'||!Number.isFinite(nowMs)||
     info.schema!=='gpt-doug.tak-private-metrics.v1'||
     info.status!=='current'||info.sourceScope!=='aggregate_all_tak_clients'||
     info.mTLSVerifiedByPrivateGateway!==true)throw Error('unverified private metrics');
  const timestamp=iso(info.sampledAtUtc,nowMs),age=info.sampleAgeSeconds;
  if(!timestamp||typeof age!=='number'||!Number.isFinite(age)||age<0)throw Error('invalid source timestamp');
  const readings={};
  for(const key of PRIVATE_FIELDS){
   const value=info.metrics&&info.metrics[key];
   if(!Number.isSafeInteger(value)||value<0)throw Error('invalid aggregate count');
   readings[key]=value;
  }
  const clockAge=nonnegativeAge(timestamp,nowMs);
  const effectiveAgeSeconds=Math.max(age,clockAge==null?0:clockAge);
  const freshness=effectiveAgeSeconds<=30?'CURRENT':'STALE';
  const sourceId='urn:tak-os:private-source:takserver-aggregate';
  const graph=[{
   '@id':sourceId,'@type':'prov:Entity',
   'schema:name':'Authorized TAK Server aggregate administrative measurements',
   'tak:scope':'all_client_types','tak:clientKindsKnown':false,
   'tak:observationAtUtc':timestamp,'tak:sampleAgeSeconds':effectiveAgeSeconds,
   'tak:freshness':freshness
  }];
  for(const [key,value] of Object.entries(readings))graph.push({
   '@id':'urn:tak-os:private-metric:'+key,
   '@type':'tak:ServerAggregateMetric',
   'prov:wasDerivedFrom':{'@id':sourceId},
   'prov:generatedAtTime':timestamp,
   'tak:name':key,'tak:value':value,'tak:freshness':freshness
  });
  return {
   schema:'gpt-doug.private-tak-ontology.v1',scope:'private_ephemeral',
   sourceScope:'aggregate_all_tak_clients',
   sampledAtUtc:timestamp,effectiveAgeSeconds,freshness,
   itakOnlyClientCount:null,clientIdentitiesIncluded:false,
   locationIncluded:false,privateDataExportable:false,
   readings,'@context':CONTEXT,'@graph':graph
  };
 }
 return Object.freeze({utcClock,publicSnapshot,privateSnapshot});
});
