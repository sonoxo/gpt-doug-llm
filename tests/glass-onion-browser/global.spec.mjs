import {test,expect} from "@playwright/test";
const usgs="https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson";
const nasa="https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=200";
const cisa="https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json";
const recent=Date.now()-120000;
async function mockSources(page,{failed=[]}={}){
 const fixtures={
  [usgs]:{type:"FeatureCollection",metadata:{generated:recent,count:2},features:[
   {id:"one",geometry:{type:"Point",coordinates:[-95,35]},properties:{title:"M 4.9 - TEST QUAKE",mag:4.9,time:recent,url:"https://earthquake.usgs.gov/earthquakes/eventpage/one"}},
   {id:"two",geometry:{type:"Point",coordinates:[100,15]},properties:{title:"M 1.0 - TEST MINOR",mag:1,time:recent-60000,url:"https://earthquake.usgs.gov/earthquakes/eventpage/two"}}]},
  [nasa]:{events:[
   {id:"fire-1",title:"TEST ACTIVE WILDFIRE",categories:[{title:"Wildfires"}],geometry:[{type:"Point",coordinates:[30,40],date:new Date(recent).toISOString()}]},
   {id:"polygon",title:"POLYGON EVENT",geometry:[{type:"Polygon",coordinates:[],date:new Date(recent).toISOString()}]}]},
  [cisa]:{vulnerabilities:[{cveID:"CVE-2026-90123",vulnerabilityName:"TEST KNOWN EXPLOITED VULNERABILITY",vendorProject:"FixtureCo",product:"Fixture",dateAdded:"2026-11-20"}]}
 };
 for(const [url,fixture] of Object.entries(fixtures))
  await page.route(url,route=>failed.includes(url)?route.abort("failed"):route.fulfill({status:200,contentType:"application/json",headers:{"access-control-allow-origin":"*"},body:JSON.stringify(fixture)}));
}
test("global map renders official feed positions, filters, selection, zoom and disjoint cyber intelligence",async({page})=>{
 await mockSources(page);await page.goto("/darkweb/global/");
 await expect(page.locator("#source-usgs")).toHaveText("RECEIVED");
 await expect(page.locator("#source-nasa")).toHaveText("RECEIVED");
 await expect(page.locator("#source-cisa")).toHaveText("RECEIVED");
 await expect(page.locator("#count-global")).toHaveText("3");
 await expect(page.locator("#count-cisa")).toHaveText("1");
 await expect(page.locator(".marker")).toHaveCount(3);
 await expect(page.locator(".cve")).toHaveCount(1);
 await expect(page.locator("#cisa-list")).toContainText("CVE-2026-90123");
 await expect(page.locator(".marker[aria-label*='CVE-']")).toHaveCount(0);
 await page.locator("#layer").selectOption("nasa");
 await expect(page.locator(".marker")).toHaveCount(1);
 await page.getByRole("button",{name:/TEST ACTIVE WILDFIRE/}).click();
 await expect(page.locator("#selected")).toContainText("TEST ACTIVE WILDFIRE");
 await expect(page.locator("#selected a")).toHaveAttribute("href","https://eonet.gsfc.nasa.gov/api/v3/events/fire-1");
 const original=await page.locator("#world").getAttribute("viewBox");
 await page.locator("#zoom-in").click();
 expect(await page.locator("#world").getAttribute("viewBox")).not.toBe(original);
 await page.locator("#zoom-reset").click();
 await expect(page.locator("#world")).toHaveAttribute("viewBox","0 0 1000 500");
 await page.locator("#layer").selectOption("usgs");
 await page.locator("#magnitude").selectOption("4.5");
 await expect(page.locator(".marker")).toHaveCount(1);
 await expect(page.locator("#event-list .event")).toHaveCount(1);
 await page.locator("#event-search").fill("DOES NOT EXIST");
 await expect(page.locator(".marker")).toHaveCount(0);
});
test("export includes only mapped source observations, not CISA vulnerabilities",async({page})=>{
 await mockSources(page);await page.goto("/darkweb/global/");
 await expect(page.locator("#source-cisa")).toHaveText("RECEIVED");
 const download=page.waitForEvent("download");
 await page.locator("#export").click();
 const file=await download;expect(file.suggestedFilename()).toBe("xunia-global-observatory.json");
 const path=await file.path();
 const {readFile}=await import("node:fs/promises");
 const exported=JSON.parse(await readFile(path,"utf8"));
 expect(exported.observations).toHaveLength(3);
 expect(exported.observations.every(x=>Array.isArray(x.coords))).toBe(true);
 expect(exported.observations.every(x=>x.feed!=="cisa")).toBe(true);
 expect(exported.scope).toContain("NOT_CYBER_ATTACK_TELEMETRY");
});
test("unavailable sources report independently; no simulated activity replaces failures",async({page})=>{
 await mockSources(page,{failed:[usgs,nasa,cisa]});await page.goto("/darkweb/global/");
 await expect(page.locator("#source-usgs")).toHaveText("FAILED");
 await expect(page.locator("#source-nasa")).toHaveText("FAILED");
 await expect(page.locator("#source-cisa")).toHaveText("FAILED");
 await expect(page.locator("#count-global")).toHaveText("0");
 await expect(page.locator(".marker")).toHaveCount(0);
 await expect(page.locator(".cve")).toHaveCount(0);
 await expect(page.locator("#export")).toBeDisabled();
 await expect(page.locator("#stream-status")).toContainText("No usable geographic sources");
});
