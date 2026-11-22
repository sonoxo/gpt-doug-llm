import {test,expect} from "@playwright/test";
const base="/darkweb/cosmos/";
const noaa="https://services.swpc.noaa.gov";
const jpl="https://ssd-api.jpl.nasa.gov/cad.api";
const endpoints={
 wind:noaa+"/json/rtsw/rtsw_wind_1m.json",
 mag:noaa+"/json/rtsw/rtsw_mag_1m.json",
 kp:noaa+"/products/noaa-planetary-k-index.json",
 xray:noaa+"/json/goes/primary/xrays-1-day.json",
 aurora:noaa+"/json/ovation_aurora_latest.json",
 neo:jpl
};
async function mockAll(page,{fail=[]}={}){
 const timestamp=new Date(Date.now()-60000).toISOString(),forecast=new Date().toISOString();
 const fixtures={
  wind:[{time_tag:timestamp,speed:450,density:5.5},{time_tag:new Date(Date.now()-120000).toISOString(),speed:420,density:4.3}],
  mag:[{time_tag:timestamp,bz_gsm:-5.4,bt:9.1}],
  kp:[{time_tag:timestamp,Kp:3.33}],
  xray:[{time_tag:timestamp,energy:"0.1-0.8nm",flux:1.4e-5,satellite:"19"}],
  aurora:{"Observation Time":timestamp,"Forecast Time":forecast,coordinates:[[220,65,78],[34,-55,35],[10,10,3]]},
  neo:{signature:{source:"NASA/JPL"},fields:["des","cd","dist","v_rel"],data:[["2026 XX","2026-Nov-23 18:30","0.006","22.2"]]}
 };
 for(const [key,url] of Object.entries(endpoints))
  await page.route(url,route=>fail.includes(key)?route.abort("failed"):route.fulfill({status:200,contentType:"application/json",headers:{"access-control-allow-origin":"*"},body:JSON.stringify(fixtures[key])}));
 await page.route("https://sdo.gsfc.nasa.gov/assets/img/latest/latest_512_0193.jpg",route=>route.fulfill({status:200,contentType:"image/gif",body:Buffer.from("R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==","base64")}));
}
test("official source measurements render without inventing global sensor coverage",async({page})=>{
 await mockAll(page);await page.goto(base);
 await expect(page.locator("#overall-state")).toHaveText("6/6 SOURCES VALID");
 await expect(page.locator("#metric-speed")).toHaveText("450");
 await expect(page.locator("#metric-bz")).toHaveText("-5.4");
 await expect(page.locator("#metric-kp")).toHaveText("3.3");
 await expect(page.locator("#metric-flare")).toHaveText("M1.4");
 await expect(page.locator("#metric-aurora")).toHaveText("2");
 await expect(page.locator("#metric-neo")).toHaveText("1");
 await expect(page.locator("#aurora-points .aurora-dot")).toHaveCount(2);
 await expect(page.locator("#neo-list .neo-row")).toHaveCount(1);
 await expect(page.locator("#neo-list")).toContainText("2026 XX");
 await expect(page.locator("#feeds .feed")).toHaveCount(6);
 await expect(page.locator("#sun-status")).toContainText("acquisition age unknown");
 const before=await page.locator("#wind-line").getAttribute("points");expect(before).toBe("");
 await expect(page.locator("#kp-line")).toHaveAttribute("points",""); // single Kp reading: no invented trend
 await page.locator("#refresh").click();await expect(page.locator("#refresh")).toBeEnabled();
 await expect(page.locator("#overall-state")).toHaveText("6/6 SOURCES VALID");
});
test("failed sources clear all metric values and model cells",async({page})=>{
 await mockAll(page,{fail:Object.keys(endpoints)});await page.goto(base);
 await expect(page.locator("#overall-state")).toHaveText("0/6 SOURCES VALID");
 await expect(page.locator("#metric-speed")).toHaveText("—");
 await expect(page.locator("#metric-aurora")).toHaveText("—");
 await expect(page.locator("#aurora-points .aurora-dot")).toHaveCount(0);
 await expect(page.locator("#neo-list .neo-row")).toHaveCount(0);
 await expect(page.locator("#neo-state")).toContainText("unavailable");
 await expect(page.locator("#feeds .indicator.failed")).toHaveCount(6);
});
test("stale instrument timestamps cannot be presented as current",async({page})=>{
 const old=new Date(Date.now()-10*3600000).toISOString();
 await mockAll(page);
 await page.route(endpoints.wind,route=>route.fulfill({status:200,contentType:"application/json",headers:{"access-control-allow-origin":"*"},body:JSON.stringify([{time_tag:old,speed:989,density:5}])}));
 await page.goto(base);
 await expect(page.locator("#metric-speed")).toHaveText("—");
 await expect(page.locator("#wind-state")).toContainText("STALE");
 await expect(page.locator("#overall-state")).toHaveText("5/6 SOURCES VALID");
});
