import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {validateDefenseScope,createDefensePlan,summarizePlan} from "../docs/darkweb/usa-scope.mjs";

const source=JSON.parse(readFileSync(new URL("../docs/darkweb/usa-defense-scope.json",import.meta.url),"utf8"));
test("US scope registry exactly covers 16 CISA infrastructure sectors",()=>{
 const scope=validateDefenseScope(source);
 assert.equal(scope.sectors.length,16);
 assert.ok(scope.sectors.includes("Energy"));
 assert.ok(scope.sectors.includes("Healthcare and Public Health"));
 assert.ok(scope.sectors.includes("Water and Wastewater Systems"));
 assert.ok(scope.sectors.includes("Information Technology"));
 assert.equal(scope.status,"PLANNING_ONLY_NO_NATIONWIDE_PROTECTION");
 assert.equal(scope.jurisdiction,"United States");
});
test("NIST CSF 2.0 six functions produce unverified local planning actions",()=>{
 const scope=validateDefenseScope(source);
 assert.deepEqual(scope.functions.map(f=>f.id),["govern","identify","protect","detect","respond","recover"]);
 const plan=createDefensePlan(scope);
 assert.equal(plan.steps.length,6);
 assert.equal(summarizePlan(plan).actions,12);
 assert.equal(summarizePlan(plan).implemented,0);
 assert.ok(plan.steps.every(x=>x.implementation_status==="NOT_VERIFIED_OR_PERFORMED"));
 assert.match(plan.boundary,/no government affiliation/i);
 assert.match(plan.boundary,/no.*scanning/i);
 assert.equal(plan.evidence_status,"REFERENCE_GUIDANCE_NOT_A_SECURITY_ASSESSMENT");
});
test("scope filters by sector, role, and function without claiming operational access",()=>{
 const plan=createDefensePlan(source,{sector:"Energy",profile:"owner",phase:"detect"});
 assert.equal(plan.sector,"Energy");
 assert.equal(plan.profile,"Authorized owner / operator");
 assert.equal(plan.phase,"DETECT");
 assert.equal(plan.steps.length,1);
 assert.equal(plan.steps[0].actions.length,2);
 assert.ok(plan.steps[0].actions[0].includes("authorized"));
 assert.equal(plan.status,"PLANNING_ONLY_NO_NATIONWIDE_PROTECTION");
 assert.ok(plan.source_urls.includes("https://www.cisa.gov/report"));
 assert.ok(plan.source_urls.includes("https://www.nist.gov/cyberframework"));
});
test("reject unknown sector, role, phase and malicious registry changes",()=>{
 assert.throws(()=>createDefensePlan(source,{sector:"Nuclear launch codes"}),/Unknown sector/);
 assert.throws(()=>createDefensePlan(source,{profile:"national-cyber-command"}),/Unknown actor/);
 assert.throws(()=>createDefensePlan(source,{phase:"attack"}),/Unknown NIST/);
 assert.throws(()=>validateDefenseScope({...source,sectors:["Energy"]}),/16 distinct/);
 assert.throws(()=>validateDefenseScope({...source,status:"PROTECTION_ACTIVE"}),/Unrecognized/);
 assert.throws(()=>validateDefenseScope({...source,functions:[]}),/function registry/);
 assert.throws(()=>validateDefenseScope({...source,sources:[{url:"https://evil.example/"}]}),/source URLs/);
 assert.throws(()=>validateDefenseScope({...source,boundaries:{}}),/authorization boundaries/);
});
test("web UI is same-origin only, with no targeting or automatic incident submission",()=>{
 const html=readFileSync(new URL("../docs/darkweb/index.html",import.meta.url),"utf8");
 const app=readFileSync(new URL("../docs/darkweb/usa-scope-app.mjs",import.meta.url),"utf8");
 assert.match(html,/id="usa-defense"/);
 for(const id of ["usa-sector","usa-profile","usa-function","usa-generate-plan","usa-export-plan","usa-plan-steps","usa-scope-status","usa-source-list"])
   assert.ok(html.includes('id="'+id+'"'),id);
 assert.ok(html.includes('src="./usa-scope-app.mjs"'));
 assert.ok(app.includes('fetch("./usa-defense-scope.json"'));
 assert.ok(app.includes("replaceChildren()"));
 for(const forbidden of ["innerHTML","eval(","WebSocket(","navigator.usb","navigator.serial","navigator.mediaDevices","fetch('https://","localStorage","sessionStorage"]){
  assert.ok(!app.includes(forbidden),"unsafe app behavior: "+forbidden);
 }
});
