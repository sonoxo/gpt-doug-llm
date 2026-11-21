/* XUNIA / CL1 Telemetry Engine — deterministic synthetic signal derivation.
 * Interprets a local Physarum graph; no sensors, physical kinematics, robotics,
 * clinical neurotelemetry, provider API, live hardware or remote network.
 */
(function(root,factory){
"use strict";
const api=factory();
if(typeof module==="object"&&module.exports)module.exports=api;
else root.CL1TelemetryEngine=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
"use strict";
const SCHEMA="xunia.cl1.telemetry-snapshot.v1";
const METRICS=["flux","tubes","conductance","energy","motion","delta","pressure"];
const CAP=240;
const round=(x,places=6)=>Number(Number.isFinite(x)?x.toFixed(places):"0");
function measure(graph,previous=null){
 if(!graph||!Array.isArray(graph.nodes)||!Array.isArray(graph.edges))throw Error("Invalid Physarum graph");
 let count=0,flux=0,energy=0,conductance=0,active=0,maxq=0,minPressure=Infinity,maxPressure=-Infinity;
 for(const n of graph.nodes){
   if(n.blocked)continue;
   const p=Number(n.pressure);
   if(Number.isFinite(p)){minPressure=Math.min(minPressure,p);maxPressure=Math.max(maxPressure,p);}
 }
 for(const e of graph.edges){
   if(graph.nodes[e.a]?.blocked||graph.nodes[e.b]?.blocked)continue;
   if(!Number.isFinite(e.d)||!Number.isFinite(e.q))throw Error("Nonfinite model edge");
   count++;
   const q=Math.abs(e.q);flux+=q;energy+=q*q;
   maxq=Math.max(maxq,q);conductance+=e.d;
   if(e.d>=.26)active++;
 }
 const prior=previous&&Number.isFinite(previous.flux)?previous.flux:flux;
 return {
   step:graph.tick,
   flux:round(flux),tubes:active,
   conductance:round(count?conductance/count:0),
   energy:round(energy),motion:round(count?flux/count:0),
   delta:round(flux-prior),
   pressure:round(maxPressure>=minPressure?maxPressure-minPressure:0),
   maxFlux:round(maxq),edges:count,
   food:graph.food.length,obstacles:graph.nodes.filter(n=>n.blocked).length
 };
}
function append(history,row,cap=CAP){
 if(!Array.isArray(history)||!row||!Number.isInteger(row.step))throw Error("Invalid telemetry history");
 const last=history[history.length-1];
 if(last&&row.step<last.step)throw Error("Out-of-order telemetry tick");
 if(last&&row.step===last.step){history[history.length-1]=row;return history;}
 history.push(row);if(history.length>cap)history.splice(0,history.length-cap);
 return history;
}
function capture(graph,history){
 const last=history[history.length-1]||null;
 const sample=measure(graph,last);
 append(history,sample);
 return sample;
}
function vectors(graph,cap=150){
 if(!graph||!Array.isArray(graph.edges))throw Error("Invalid graph");
 const valid=graph.edges.filter(e=>!graph.nodes[e.a]?.blocked&&!graph.nodes[e.b]?.blocked&&Number.isFinite(e.q)&&Number.isFinite(e.d));
 valid.sort((a,b)=>Math.abs(b.q)-Math.abs(a.q)||a.a-b.a||a.b-b.b);
 const strongest=Math.max(1e-9,...valid.slice(0,cap).map(e=>Math.abs(e.q)));
 return valid.slice(0,cap).map(e=>({
  from:e.q>=0?e.a:e.b,to:e.q>=0?e.b:e.a,
  magnitude:Math.abs(e.q),direction:e.q>=0?1:-1,
  relativeSpeed:Math.min(1,Math.abs(e.q)/strongest),
  conductivity:e.d
 }));
}
function exportJSON(history,registry,graph){
 const metrics=registry?.metrics?.map(m=>({id:m.id,unit:m.unit,evidence:m.evidence}))||[];
 return JSON.stringify({
  schema:SCHEMA,
  source:"PhysarumModel / Tero-inspired dimensionless browser simulation",
  evidence:"SIMULATED_NOT_MEASURED",units:"No physical units; step is numerical solver iteration",
  model_graph:"../physarum/model.js",ontology:"../physarum/ontology.json",
  metrics,history:[...history],latest:history[history.length-1]||null,
  topology:{nodes:graph.nodes.length,edges:graph.edges.length,origin:graph.origin,food:[...graph.food]},
  warning:"No hardware, neural data, physical velocity, laboratory telemetry, or remote provider."
 },null,2)+"\n";
}
function exportCSV(history){
 const headers=["step",...METRICS,"maxFlux","edges","food","obstacles"];
 return [headers.join(","),...history.map(row=>headers.map(k=>{
  const v=Number(row[k]);return Number.isFinite(v)?String(v):"";
 }).join(","))].join("\n")+"\n";
}
return {SCHEMA,METRICS,CAP,measure,append,capture,vectors,exportJSON,exportCSV};
});