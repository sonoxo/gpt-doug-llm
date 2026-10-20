import test from "node:test";
import assert from "node:assert/strict";
import {TOOLS,GROUPS,VERIFIED_LINKS,searchToolCatalog,searchEvidence,publicQueryUrl,safeUrl,normalizeEvidence,parseEvidenceImport,hibpCount,parseKev,filterKev,parseTelegramArchive,searchTelegramArchive,normalizeBookmark,privacyDiagnostics} from "../docs/darkweb/core.mjs";
test("21 unique referenced tools and valid engine bindings",()=>{
  assert.equal(TOOLS.length,21);
  assert.equal(new Set(TOOLS.map(t=>t.id)).size,21);
  assert.deepEqual(new Set(TOOLS.map(t=>t.group)),new Set(GROUPS.slice(1)));
  const engines=new Set(["discovery","evidence","exposure","threat","directory","collection","privacy","pgp"]);
  for(const tool of TOOLS){assert.ok(engines.has(tool.engine));assert.ok(tool.name);assert.ok(tool.description);assert.ok(["native","external","reference","workspace","integration","restricted"].includes(tool.kind));}
});
test("search catalog is complete and responsive to category and text",()=>{
  assert.equal(searchToolCatalog().length,21);
  assert.equal(searchToolCatalog("tor").length>=3,true);
  assert.deepEqual(searchToolCatalog("PGP").map(t=>t.id),["pgp"]);
  assert.ok(searchToolCatalog("","Discovery").every(t=>t.group==="Discovery"));
  assert.equal(searchToolCatalog("no_such_reference").length,0);
});
test("URL validation excludes invalid and non-HTTPS authorities",()=>{
  assert.equal(safeUrl("javascript:alert(1)"),"");
  assert.equal(safeUrl("http://example.org"),"");
  assert.equal(safeUrl("https://u:p@example.org/"),"");
  assert.equal(safeUrl("https://example.org/a"),"https://example.org/a");
  for(const row of VERIFIED_LINKS)assert.ok(safeUrl(row.url));
});
test("queries are encoded and only official endpoints are launched",()=>{
  assert.equal(publicQueryUrl("ahmia","A & B"),"https://ahmia.fi/search/?q=A%20%26%20B");
  assert.equal(publicQueryUrl("aleph","CVE-2026"),"https://aleph.occrp.org/search?q=CVE-2026");
  assert.equal(publicQueryUrl("other","malware"),"");
  assert.equal(publicQueryUrl("ahmia","   "),"");
});
test("local evidence normalizes and searches without network",()=>{
  const record=normalizeEvidence({name:"Case 1",source:"user",notes:"Notes",url:"javascript:abc"});
  assert.equal(record.title,"Case 1");
  assert.equal(record.url,"");
  assert.equal(searchEvidence([record],"case").length,1);
  assert.equal(searchEvidence([record],"somethingelse").length,0);
  assert.equal(normalizeEvidence({notes:"no title"}),null);
});
test("JSON evidence import validates records",()=>{
  const items=parseEvidenceImport(JSON.stringify({records:[{title:"Case 1"},{name:"Case 2"}]}),"records.json");
  assert.equal(items.length,2);
  assert.throws(()=>parseEvidenceImport('{"records":{}}'));
});
test("CSV evidence handles escaped quotes and quoted newlines",()=>{
  const result=parseEvidenceImport('title,source,notes\n"Item ""A""",test,"first\nsecond"\n',"data.csv");
  assert.equal(result[0].title,'Item "A"');
  assert.equal(result[0].notes,"first\nsecond");
  assert.throws(()=>parseEvidenceImport("notes\nvalue","data.csv"));
});
test("HIBP suffix matching is exact and does not send raw password",()=>{
  const digest="ABCDE"+"F".repeat(35);
  assert.equal(hibpCount("F".repeat(35)+":92\n","ABCDE"+"F".repeat(35)),92);
  assert.equal(hibpCount("E".repeat(35)+":13\n",digest),0);
  assert.throws(()=>hibpCount("x","short"));
});
test("CISA KEV parsing rejects failures and preserves public source",()=>{
  const data={vulnerabilities:[{cveID:"CVE-2026-0001",vendorProject:"Vendor",product:"Product",vulnerabilityName:"Example",dateAdded:"2026-03-01"},{cveID:"CVE-2026-0002",vendorProject:"Vendor2",dateAdded:"2026-04-01"}]};
  const rows=parseKev(data);
  assert.equal(rows.length,2);
  assert.equal(rows[0].cve,"CVE-2026-0002");
  assert.equal(filterKev(rows,"vendor").length,2);
  assert.equal(filterKev(rows,"CVE-2026-0001").length,1);
  assert.throws(()=>parseKev({}));
});

test("consented Telegram Desktop chat export is locally parseable and search-enabled",()=>{
  const archive={chats:{list:[{name:"Public channel",messages:[
    {date:"2026-10-20T12:00:00",from:"Researcher",text:"Public vulnerability advisory"},
    {date:"2026-10-20T13:00:00",from:"Moderator",text:["Test ",{type:"bold",text:"message"}]},
    {text:[{type:"photo",media_type:"image"}]}]},
    {name:"Other chat",messages:[{from:"Reporter",text:"Second bulletin"}]}]}};
  const rows=parseTelegramArchive(archive);
  assert.equal(rows.length,3);
  assert.equal(rows[1].text,"Test message");
  assert.equal(searchTelegramArchive(rows,"reporter").length,1);
  assert.equal(searchTelegramArchive(rows,"advisory").length,1);
  assert.equal(parseTelegramArchive(archive,1).length,1);
  assert.throws(()=>parseTelegramArchive({}));
});
test("Telegram export does not retain attachments or privileged export metadata",()=>{
  const exportData={chats:{list:[{name:"A",messages:[
    {id:1,from:"Test",text:"Hello",file:"/secret/path",photo:"private"},
    {id:2,text:"",file:"/secret/only-media"}]}]}};
  assert.deepEqual(Object.keys(parseTelegramArchive(exportData)[0]).sort(),["chat","date","sender","text"]);
  assert.equal(parseTelegramArchive(exportData).length,1);
});
test("personal bookmarks refuse plaintext and credentialed URLs",()=>{
  assert.deepEqual(normalizeBookmark({title:"Source",url:"https://example.org/"}),{title:"Source",url:"https://example.org/",notes:""});
  assert.equal(normalizeBookmark({title:"Source",url:"http://example.org"}),null);
  assert.equal(normalizeBookmark({title:"Source",url:"https://username:secret@example.org"}),null);
  assert.equal(normalizeBookmark({title:"",url:"https://example.org"}),null);
});
test("privacy diagnostics never claim a normal web page is Tor",()=>{
  const checks=privacyDiagnostics({secureContext:true,webCrypto:true,localStorage:true});
  assert.equal(checks.length,4);
  assert.deepEqual(checks.slice(0,3).map(x=>x.pass),[true,true,true]);
  assert.equal(checks[3].pass,false);
});
