import {test,expect} from "@playwright/test";
import {readFile} from "node:fs/promises";
const base="/darkweb/fieldlab/";
const endpoints={
 wind:"https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json",
 mag:"https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json",
 kp:"https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
 xray:"https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json",
 aurora:"https://services.swpc.noaa.gov/json/ovation_aurora_latest.json",
 usgs:"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
 nasa:"https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=200"
};
async function mockFeeds(page,{failed=[],stale=[]}={}){
 const now=Date.now(),current=new Date(now-60000).toISOString(),old=new Date(now-4*86400000).toISOString();
 const stamp=k=>stale.includes(k)?old:current;
 const fixtures={
  wind:[{time_tag:stamp("wind"),speed:500,density:4},{time_tag:new Date(now-120000).toISOString(),speed:430,density:5}],
  mag:[{time_tag:stamp("mag"),bz_gsm:-12,bt:17}],
  kp:[{time_tag:stamp("kp"),Kp:5.33}],
  xray:[{time_tag:stamp("xray"),energy:"0.1-0.8nm",flux:2.0e-5}],
  aurora:{"Observation Time":stamp("aurora"),"Forecast Time":current,coordinates:[[220,65,76],[10,-50,29],[40,10,4]]},
  usgs:{type:"FeatureCollection",metadata:{generated:stale.includes("usgs")?now-3*86400000:now},
   features:[{id:"test-quake-1",type:"Feature",properties:{title:"M 5.6 - Public earthquake test",mag:5.6,time:now-120000,url:"https://earthquake.usgs.gov/earthquakes/eventpage/test-quake-1"},
    geometry:{type:"Point",coordinates:[-65,20,15]}}]},
  nasa:{events:[{id:"EONET-TEST-1",title:"Public NASA event test",categories:[{title:"Wildfires"}],
   geometry:[{type:"Point",coordinates:[-10,45],date:new Date(now-4*86400000).toISOString()}]}]}
 };
 for(const [key,url] of Object.entries(endpoints)){
  await page.route(url,route=>failed.includes(key)?route.abort("failed"):route.fulfill({
   status:200,contentType:"application/json",headers:{"access-control-allow-origin":"*"},body:JSON.stringify(fixtures[key])
  }));
 }
}
test("real mathematical model, source markers, and canvas respond to actual feed fixtures",async({page})=>{
 await page.setViewportSize({width:1440,height:1100});
 await mockFeeds(page);await page.goto(base);
 await expect(page.locator("#health")).toHaveText("ALL PUBLIC SOURCES");
 await expect(page.locator("#source-count")).toHaveText("7/7 VALIDATED/CATALOG SOURCES");
 await expect(page.locator("#speed")).toHaveText("500");
 await expect(page.locator("#density")).toHaveText("4.0");
 await expect(page.locator("#bz")).toHaveText("-12.0");
 await expect(page.locator("#kp")).toHaveText("5.33");
 await expect(page.locator("#flare")).toHaveText("M2.0");
 await expect(page.locator("#pressure")).toHaveText("1.67");
 await expect(page.locator("#dyn-pressure")).toHaveText("1.67");
 await expect(page.locator("#standoff")).not.toHaveText("—");
 await expect(page.locator("#transit")).toHaveText("50.0");
 await expect(page.locator("#map-record-count")).toContainText("2 PUBLIC EVENTS MAPPED + 2 AURORA MODEL CELLS");
 await expect(page.locator("#signals .signal")).toHaveCount(4); // Kp, Bz, X-ray, and one USGS event
 await expect(page.locator("#feeds .feed")).toHaveCount(7);
 await expect(page.locator("#model-curve")).toHaveAttribute("d",/^M/);
 await expect.poll(async()=>page.locator("#earth").evaluate(c=>{
   const ctx=c.getContext("2d"),d=ctx.getImageData(Math.floor(c.width/2),Math.floor(c.height*.52),1,1).data;
   return d[2]>10&&d[3]===255;
 })).toBe(true);
 const bounds=await page.locator("#earth").boundingBox();
 await page.locator("#earth").click({position:{x:bounds.width/2,y:bounds.height*.52}});
 await expect(page.locator("#inspected h3")).toHaveText("M 5.6 - Public earthquake test");
 await expect(page.locator("#inspected a")).toHaveAttribute("href",/earthquake\.usgs\.gov/);
 await page.locator("#rotate-right").click();await page.locator("#zoom-in").click();
 await page.locator("#auto-orbit").click();await expect(page.locator("#auto-orbit")).toHaveAttribute("aria-pressed","true");
 await page.locator("#reset-camera").click();await expect(page.locator("#auto-orbit")).toHaveAttribute("aria-pressed","false");
});
test("isolated hypothetical parameters change derived pressure, not observed sensor readouts",async({page})=>{
 await mockFeeds(page);await page.goto(base);
 await expect(page.locator("#pressure")).toHaveText("1.67");
 await page.locator("#scenario-mode").check();
 await expect(page.locator("#hyp-speed")).toBeEnabled();
 await page.locator("#hyp-speed").fill("1000");
 await page.locator("#hyp-density").fill("10");
 await expect(page.locator("#model-state")).toContainText("SCENARIO");
 await expect(page.locator("#pressure")).toHaveText("16.73");
 await expect(page.locator("#speed")).toHaveText("500");
 await expect(page.locator("#density")).toHaveText("4.0");
 await page.locator("#scenario-mode").uncheck();
 await expect(page.locator("#pressure")).toHaveText("1.67");
 await expect(page.locator("#hyp-speed")).toBeDisabled();
 const downloadReady=page.waitForEvent("download");await page.locator("#export").click();
 const file=await downloadReady;
 const json=JSON.parse(await readFile(await file.path(),"utf8"));
 expect(json.military_telemetry).toBe("NONE");
 expect(json.palantir_foundry_connection).toBe("NONE");
 expect(json.snapshot.measured.speed).toBe(500);
 expect(json.snapshot.model.pressure).toBeCloseTo(1.67262192);
 expect(json.latest_events).toHaveLength(2);
});
test("unavailable and stale sources fail closed; no invented current instrument values",async({page})=>{
 await mockFeeds(page,{failed:["wind","mag","xray","nasa"],stale:["kp","aurora","usgs"]});
 await page.goto(base);
 await expect(page.locator("#health")).toHaveText("NO VERIFIED FEEDS");
 await expect(page.locator("#source-count")).toHaveText("0/7 VALIDATED/CATALOG SOURCES");
 for(const id of ["speed","density","bz","kp","flare","pressure","standoff","transit"])
  await expect(page.locator("#"+id)).toHaveText("—");
 await expect(page.locator("#map-record-count")).toContainText("0 AURORA MODEL CELLS");
 await expect(page.locator("#signals")).toContainText("No recent qualified measurements");
 await expect(page.locator("#feeds .feed")).toHaveCount(7);
 await expect(page.locator("#feeds .feed").filter({hasText:"L1 PLASMA"})).toContainText("FAILED");
 await expect(page.locator("#feeds .feed").filter({hasText:"OVATION AURORA"})).toContainText("STALE");
});
