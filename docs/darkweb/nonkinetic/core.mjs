// XUNIA Glass Onion / public non-kinetic capability ontology.
// Models only openly documented program milestones. No military telemetry.
const STATUSES=["Operational capability declared","Operationally accepted","Fielded","Fleet-installed","Reported operational use","Production contract awarded","Demonstrated","Prototype agreement"];
const SAFE_KEYS=["id","name","branch","domain","role","status","evidence_date","assessment","source","telemetry","activation"];
export const EVIDENCE_STATE="NOT_PUBLICLY_VERIFIED";
const allowedHosts=new Set(["www.navair.navy.mil","www.ssc.spaceforce.mil","innovation.army.mil","paemaritime.navy.mil","www.navy.mil","www.army.mil","www.afrl.af.mil","cpeisw.army.mil"]);
export function validateOntology(data){
 if(data?.schema!=="XUNIA_PUBLIC_NONKINETIC_ONTOLOGY_V1"||data.palantir_connection!=="NOT_CONNECTED"||data.live_activation_feeds!==0||data.authorized_systems_connected!==0)throw Error("Unverified access claims in ontology");
 if(!Array.isArray(data.programs)||!data.programs.length||data.programs.length>100)throw Error("Invalid public program catalog");
 if(JSON.stringify(data).length>200000)throw Error("Registry too large");
 if(!data.status?.includes("OPEN_SOURCE")||!Array.isArray(data.object_types)||!Array.isArray(data.link_types))throw Error("Invalid ontology declaration");
 const ids=new Set();
 for(const p of data.programs){
  if(!p||typeof p!=="object"||Object.keys(p).some(k=>!SAFE_KEYS.includes(k)))throw Error("Unknown system fields");
  if(!/^[a-z0-9-]{2,40}$/.test(p.id)||ids.has(p.id))throw Error("Duplicate or unsafe program id");
  ids.add(p.id);
  if(![p.name,p.branch,p.domain,p.role,p.assessment].every(x=>typeof x==="string"&&x.length>=3&&x.length<=400))throw Error("Invalid descriptive field");
  if(!data.services.includes(p.branch)||!data.domains.includes(p.domain)||!STATUSES.includes(p.status))throw Error("Unknown ontology class/status");
  if(!/^\d{4}-\d{2}-\d{2}$/.test(p.evidence_date)||Number.isNaN(Date.parse(p.evidence_date))||p.evidence_date>data.as_of)throw Error("Invalid public evidence date");
  if(p.telemetry!=="NOT_CONNECTED"||p.activation!==EVIDENCE_STATE)throw Error("Active arsenal status cannot be asserted");
  const u=new URL(p.source?.url||"https://invalid.example");
  if(u.protocol!=="https:"||!allowedHosts.has(u.hostname)||u.username||u.password||u.hash)throw Error("Unapproved public evidence URL");
  if(!["U.S. Army","U.S. Navy","Space Systems Command","Air Force Research Laboratory"].includes(p.source.publisher))throw Error("Unexpected source publisher");
 }
 return data;
}
export function viewSystems(data,filters={}){
 const o=validateOntology(data);
 const q=String(filters.query||"").trim().toLowerCase().slice(0,120);
 return o.programs.filter(p=>
   (!filters.branch||filters.branch==="all"||p.branch===filters.branch)
   &&(!filters.domain||filters.domain==="all"||p.domain===filters.domain)
   &&(!filters.status||filters.status==="all"||p.status===filters.status)
   &&(!q||[p.name,p.branch,p.domain,p.role,p.status,p.assessment].some(x=>x.toLowerCase().includes(q)))
 ).sort((a,b)=>b.evidence_date.localeCompare(a.evidence_date)||a.name.localeCompare(b.name));
}
export function ontologyGraph(data,filters={}){
 const selected=viewSystems(data,filters);
 const nodes=[],edges=[],keys=new Set();
 const add=(id,kind,label)=>{if(!keys.has(id)){nodes.push({id,kind,label});keys.add(id);}};
 for(const p of selected){
  add("sys:"+p.id,"CapabilitySystem",p.name);
  add("service:"+p.branch,"ServiceBranch",p.branch);
  add("domain:"+p.domain,"CapabilityDomain",p.domain);
  add("status:"+p.status,"PublicReadinessState",p.status);
  add("source:"+p.id,"EvidenceRecord",p.source.publisher+" / "+p.evidence_date);
  for(const [to,type] of [["service:"+p.branch,"SYSTEM_BELONGS_TO_BRANCH"],["domain:"+p.domain,"SYSTEM_HAS_DOMAIN"],["status:"+p.status,"SYSTEM_REPORTED_STATUS"],["source:"+p.id,"SYSTEM_SUPPORTED_BY_EVIDENCE"]])
    edges.push({from:"sys:"+p.id,to,type});
 }
 return {nodes,edges,coverage:"PUBLIC_NON_EXHAUSTIVE",activeTelemetry:false};
}
export function stats(data,filters={}){
 const selected=viewSystems(data,filters);
 return {systems:selected.length,branches:new Set(selected.map(p=>p.branch)).size,domains:new Set(selected.map(p=>p.domain)).size,verifiedLive:0};
}
