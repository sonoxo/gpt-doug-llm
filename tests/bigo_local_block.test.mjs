import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const root=new URL("../tools/bigo-local-block/",import.meta.url);
const read=(file)=>readFileSync(new URL(file,root),"utf8");
const manifest=JSON.parse(read("manifest.json"));
const rules=JSON.parse(read("rules.json"));
test("Manifest V3 requests only local blocking permission, not surveillance or code injection",()=>{
 assert.equal(manifest.manifest_version,3);
 assert.deepEqual(manifest.permissions,["declarativeNetRequest"]);
 assert.equal(manifest.action.default_popup,"popup.html");
 assert.equal(manifest.declarative_net_request.rule_resources.length,1);
 assert.deepEqual(manifest.declarative_net_request.rule_resources[0],{id:"bigo",enabled:true,path:"rules.json"});
 for(const forbidden of ["host_permissions","content_scripts","background","externally_connectable","web_accessible_resources"])assert.equal(manifest[forbidden],undefined);
});
test("one rule blocks only BIGO web domain requests, with no redirects, attack payloads, or broad third-party blocks",()=>{
 assert.equal(rules.length,1);
 const rule=rules[0];
 assert.equal(rule.id,1);
 assert.equal(rule.priority,1);
 assert.equal(rule.action.type,"block");
 assert.deepEqual(rule.condition.requestDomains,["bigo.tv"]);
 assert.ok(rule.condition.resourceTypes.includes("main_frame"));
 for(const field of ["urlFilter","regexFilter","initiatorDomains","excludedRequestDomains"])assert.equal(rule.condition[field],undefined);
});
test("popup safely and reversibly enables and disables only the static local ruleset",()=>{
 const js=read("popup.js");
 const html=read("popup.html");
 assert.match(js,/getEnabledRulesets\(\)/);
 assert.match(js,/updateEnabledRulesets/);
 assert.match(js,/enableRulesetIds:\[RULESET_ID\]/);
 assert.match(js,/disableRulesetIds:\[RULESET_ID\]/);
 assert.match(html,/No other websites are affected/);
 for(const forbidden of ["fetch(","WebSocket(","XMLHttpRequest","innerHTML","chrome.tabs.","chrome.scripting.","chrome.history.","chrome.cookies.","eval("])
  assert.equal(js.includes(forbidden),false,forbidden);
});
