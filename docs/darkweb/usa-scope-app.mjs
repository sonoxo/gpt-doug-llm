import {validateDefenseScope,createDefensePlan,summarizePlan} from "./usa-scope.mjs";
const $=id=>document.getElementById(id);
let registry=null,lastPlan=null;
function node(tag,text,className=""){
 const el=document.createElement(tag);if(className)el.className=className;
 if(text!==undefined)el.textContent=String(text);return el;
}
function options(select,rows){
 select.replaceChildren();
 for(const row of rows){const option=document.createElement("option");option.value=row.id;option.textContent=row.label;select.append(option);}
}
function render(plan){
 const list=$("usa-plan-steps");list.replaceChildren();
 for(const step of plan.steps){
  const card=node("article",undefined,"usa-plan-card");
  const header=node("h4",step.category+" / "+step.objective);
  const actions=node("ol");
  for(const value of step.actions){actions.append(node("li",value));}
  const note=node("small",step.implementation_status.replaceAll("_"," "));
  card.append(header,actions,note);list.append(card);
 }
 const totals=summarizePlan(plan);
 $("usa-plan-title").textContent=plan.sector;
 $("usa-plan-summary").textContent=totals.functions+" NIST functions · "+totals.actions+" defensive planning actions · "+totals.implemented+" verified implementations";
 $("usa-plan-boundary").textContent=plan.boundary;
 $("usa-export-plan").disabled=false;
 $("usa-scope-status").textContent="PLAN GENERATED / LOCAL / PLANNING ONLY";
}
function regenerate(){
 if(!registry)return;
 try{
  lastPlan=createDefensePlan(registry,{
   sector:$("usa-sector").value,
   profile:$("usa-profile").value,
   phase:$("usa-function").value,
  });
  render(lastPlan);
 }catch(error){
  lastPlan=null;$("usa-export-plan").disabled=true;
  $("usa-scope-status").textContent="PLAN ERROR / "+error.message;
 }
}
function download(){
 if(!lastPlan)return;
 const documentObject={
  ...lastPlan,generated_at:new Date().toISOString(),
  exported_by:"XUNIA GLASS ONION / LOCAL PLANNING WORKSPACE",
 };
 const blob=new Blob([JSON.stringify(documentObject,null,2)+"\n"],{type:"application/json"});
 const url=URL.createObjectURL(blob),link=document.createElement("a");
 link.href=url;link.download="glass-onion-usa-defense-scope.json";
 document.body.append(link);link.click();link.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1500);
 $("usa-scope-status").textContent="PLAN EXPORTED LOCALLY / NO INFORMATION SUBMITTED";
}
async function initialize(){
 $("usa-generate-plan").addEventListener("click",regenerate);
 $("usa-export-plan").addEventListener("click",download);
 try{
  const response=await fetch("./usa-defense-scope.json",{credentials:"omit",cache:"no-cache"});
  if(!response.ok)throw Error("Source registry HTTP "+response.status);
  registry=validateDefenseScope(await response.json());
  options($("usa-sector"),[
   {id:"cross-sector",label:"ALL 16 SECTORS / PUBLIC OVERVIEW"},
   ...registry.sectors.map(s=>({id:s,label:s}))
  ]);
  options($("usa-profile"),registry.profiles);
  options($("usa-function"),[
   {id:"all",label:"ALL SIX FUNCTIONS"},
   ...registry.functions.map(f=>({id:f.id,label:f.label}))
  ]);
  $("usa-sector-count").textContent=String(registry.sectors.length);
  $("usa-function-count").textContent=String(registry.functions.length);
  const sources=$("usa-source-list");sources.replaceChildren();
  for(const item of registry.sources){
   const link=node("a",item.name+" ↗");
   link.href=item.url;link.rel="noopener noreferrer";link.target="_blank";sources.append(link);
  }
  $("usa-scope-status").textContent="OFFICIAL-SOURCE SCOPE READY / NO NETWORK DEFENSE CONNECTED";
  regenerate();
 }catch(error){
  $("usa-scope-status").textContent="SCOPE REGISTRY UNAVAILABLE / "+error.message;
  $("usa-generate-plan").disabled=true;
  $("usa-export-plan").disabled=true;
  $("usa-plan-boundary").textContent="The scope registry did not load. No plans or protection claims were fabricated.";
 }
}
initialize();
