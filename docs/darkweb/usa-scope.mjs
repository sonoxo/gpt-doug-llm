/* USA Defense Scope: read-only governance and defensive planning, not a monitor.
 * No scanning, device access, secrets, command execution or report submission.
 */
const SECTOR_COUNT=16;
const CSF_IDS=["govern","identify","protect","detect","respond","recover"];
const ALLOWED_STATUS="PLANNING_ONLY_NO_NATIONWIDE_PROTECTION";
const APPROVED_HOSTS=new Set(["www.cisa.gov","www.nist.gov","www.ic3.gov"]);
export function validateDefenseScope(source){
 if(!source||source.schema!=="xunia.glass-onion.usa-defense-scope.v1"||source.status!==ALLOWED_STATUS)throw Error("Unrecognized USA defensive scope registry");
 if(!Array.isArray(source.sectors)||source.sectors.length!==SECTOR_COUNT||new Set(source.sectors).size!==SECTOR_COUNT)throw Error("Expected 16 distinct official sectors");
 if(!Array.isArray(source.functions)||source.functions.length!==6||source.functions.some((f,i)=>f.id!==CSF_IDS[i]||!f.objective||!Array.isArray(f.actions)||f.actions.length!==2))throw Error("NIST CSF 2.0 function registry invalid");
 if(!Array.isArray(source.profiles)||source.profiles.length<4||source.profiles.some(p=>!p.id||!p.label)||new Set(source.profiles.map(p=>p.id)).size!==source.profiles.length)throw Error("Scope profiles invalid");
 if(!Array.isArray(source.sources)||source.sources.length<3||source.sources.some(s=>{try{const u=new URL(s.url);return u.protocol!=="https:"||!APPROVED_HOSTS.has(u.hostname)||!!u.username||!!u.password;}catch{return true;}}))throw Error("Official source URLs invalid");
 if(!source.boundaries?.active_testing||!source.boundaries?.automation||!source.boundaries?.data||!source.boundaries?.authority)throw Error("Defensive authorization boundaries missing");
 return source;
}
export function createDefensePlan(source,selection={}){
 const data=validateDefenseScope(source);
 const sector=selection.sector||"cross-sector",profile=selection.profile||"public",phase=selection.phase||"all";
 if(sector!=="cross-sector"&&!data.sectors.includes(sector))throw Error("Unknown sector");
 const actor=data.profiles.find(x=>x.id===profile);if(!actor)throw Error("Unknown actor profile");
 if(phase!=="all"&&!CSF_IDS.includes(phase))throw Error("Unknown NIST CSF function");
 const funcs=phase==="all"?data.functions:data.functions.filter(f=>f.id===phase);
 const steps=funcs.map(f=>({
  id:f.id,category:f.label,objective:f.objective,
  actions:[...f.actions],implementation_status:"NOT_VERIFIED_OR_PERFORMED",
 }));
 return {schema:"xunia.glass-onion.usa-defense-plan.v1",
  mission:data.mission,
  status:data.status,
  sector:sector==="cross-sector"?"All 16 CISA critical infrastructure sectors (planning overview)":sector,
  profile:actor.label,phase:phase==="all"?"All six NIST CSF 2.0 functions":funcs[0].label,
  steps,
  source_urls:data.sources.map(s=>s.url),
  boundary:"Planning only; no government affiliation, active scanning, nationwide protection, security validation, incident submission, or live endpoint telemetry.",
  evidence_status:"REFERENCE_GUIDANCE_NOT_A_SECURITY_ASSESSMENT"};
}
export function summarizePlan(plan){
 return {functions:plan.steps.length,actions:plan.steps.reduce((n,s)=>n+s.actions.length,0),implemented:0};
}
