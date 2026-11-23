import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {validateOntology,viewSystems,ontologyGraph,stats} from "../docs/darkweb/nonkinetic/core.mjs";
const data=JSON.parse(readFileSync(new URL("../docs/darkweb/nonkinetic/ontology.json",import.meta.url),"utf8"));
test("ontology is verified public-source only and has zero Palantir or weapon-system connections",()=>{
 const valid=validateOntology(data);
 assert.equal(valid.status,"OPEN_SOURCE_EVIDENCE_ONLY");assert.equal(valid.palantir_connection,"NOT_CONNECTED");
 assert.equal(valid.authorized_systems_connected,0);assert.equal(valid.live_activation_feeds,0);
 assert.equal(valid.programs.length,11);
 assert.ok(valid.programs.every(p=>p.telemetry==="NOT_CONNECTED"&&p.activation==="NOT_PUBLICLY_VERIFIED"));
});
test("every publicly described named system carries allowed HTTPS government source and dated evidence",()=>{
 const validated=validateOntology(data);
 const ids=new Set(validated.programs.map(x=>x.id));assert.equal(ids.size,validated.programs.length);
 assert.ok(validated.programs.every(p=>p.source.url.startsWith("https://")&&p.evidence_date<="2026-11-22"));
 for(const required of ["ngj-mb","meadowlands","tls-manpack","sewip-blk3","helios","odin","m-hel","e-hel","thor","de-mshorad","tls-eab"])
  assert.ok(ids.has(required),required);
});
test("Palantir-style object and link taxonomy contains source, status, mission and service",()=>{
 const g=ontologyGraph(data);
 assert.ok(g.nodes.some(n=>n.kind==="EvidenceRecord"));assert.ok(g.nodes.some(n=>n.kind==="CapabilitySystem"));
 assert.ok(g.edges.some(e=>e.type==="SYSTEM_REPORTED_STATUS"));
 assert.ok(g.edges.some(e=>e.type==="SYSTEM_SUPPORTED_BY_EVIDENCE"));
 assert.equal(g.edges.length,data.programs.length*4);
 assert.equal(g.activeTelemetry,false);
});
test("filters narrow programs without producing fake active status",()=>{
 assert.equal(viewSystems(data,{branch:"Navy"}).length,4);
 assert.equal(viewSystems(data,{domain:"High-Energy Laser"}).length,4);
 assert.equal(viewSystems(data,{query:"meadowlands"}).length,1);
 assert.equal(viewSystems(data,{status:"Demonstrated"}).length,2);
 assert.equal(viewSystems(data,{branch:"no-such-service"}).length,0);
 assert.equal(stats(data).verifiedLive,0);
});
test("validation rejects forged telemetry, active status, source injection and modified type",()=>{
 assert.throws(()=>validateOntology({...data,palantir_connection:"CONNECTED"}),/access/);
 assert.throws(()=>validateOntology({...data,live_activation_feeds:100}),/access/);
 const mutated=patch=>({...data,programs:data.programs.map((p,i)=>i? p : {...p,...patch})});
 assert.throws(()=>validateOntology(mutated({activation:"ACTIVE_NOW"})),/Active arsenal/);
 assert.throws(()=>validateOntology(mutated({telemetry:"WEAPON_TACTICAL_FEED"})),/Active arsenal/);
 assert.throws(()=>validateOntology(mutated({source:{publisher:"U.S. Navy",url:"https://evil.invalid/weapon"}})),/Unapproved/);
 assert.throws(()=>validateOntology(mutated({latitude:38.3})),/Unknown system fields/);
 assert.throws(()=>validateOntology(mutated({status:"OPERATIONAL_AND_FIRING"})),/class/);
});
test("static interface is source-only, accessible and no active control or live map",()=>{
 const html=readFileSync(new URL("../docs/darkweb/nonkinetic/index.html",import.meta.url),"utf8");
 const app=readFileSync(new URL("../docs/darkweb/nonkinetic/app.mjs",import.meta.url),"utf8");
 for(const key of ['Content-Security-Policy','id="ontology-graph"','id="system-grid"','id="inspector"','id="export"','id="branch"'])
   assert.ok(html.includes(key),key);
 assert.match(html,/PALANTIR FOUNDRY: NOT CONNECTED/);
 assert.match(html,/LIVE OPERATIONAL STATUS: UNKNOWN/);
 for(const forbidden of ["innerHTML","WebSocket(","navigator.serial","navigator.usb","localStorage","sessionStorage","eval("])
   assert.ok(!app.includes(forbidden),forbidden);
});
