// XUNIA GLASS ONION — original, non-affiliated defensive research catalog.
// Reference names identify the tools in the user's source image, not clones or endorsements.
export const TOOLS = Object.freeze([
  {id:"tor-browser",name:"Tor Browser",group:"Privacy",kind:"external",engine:"privacy",glyph:"◎",description:"Open the authentic Tor Project browser. Tor circuits and .onion browsing cannot be embedded in GitHub Pages.",source:"https://www.torproject.org/download/",sourceLabel:"Tor Project"},
  {id:"ahmia",name:"Ahmia",group:"Discovery",kind:"integration",engine:"discovery",glyph:"A",description:"Launch an attributed query against Ahmia's public search interface. Results remain on the original site.",source:"https://ahmia.fi/",sourceLabel:"Ahmia"},
  {id:"haystack",name:"HayStack",group:"Discovery",kind:"reference",engine:"discovery",glyph:"⌕",description:"Reference search-engine entry. Use the XUNIA query workbench and approved public-source search; no copied index."},
  {id:"tor66",name:"Tor66",group:"Discovery",kind:"reference",engine:"discovery",glyph:"66",description:"Reference search-engine entry. Original provider infrastructure is not replicated or represented as connected."},
  {id:"torch",name:"Torch",group:"Discovery",kind:"reference",engine:"discovery",glyph:"T",description:"Reference search-engine entry. Use verified public adapters without exposing Tor or bypassing access controls."},
  {id:"onion-engine",name:"Onion Engine",group:"Discovery",kind:"reference",engine:"discovery",glyph:"◉",description:"Search-engine reference represented by a public-source research workbench, not an unverified hidden-service gateway."},
  {id:"telemetry",name:"Telemetry",group:"Communications",kind:"workspace",engine:"evidence",glyph:"➤",description:"Investigate public or consented Telegram-related records that you import; no Telegram account scraping or bot credentials."},
  {id:"library-of-leaks",name:"Library of Leaks",group:"Exposure",kind:"restricted",engine:"evidence",glyph:"▤",description:"Local incident-evidence library. No stolen credentials, leak dumps, or unauthorized breach databases are hosted."},
  {id:"haveibeenpwned",name:"Have I Been Pwned",group:"Exposure",kind:"integration",engine:"exposure",glyph:"#",description:"Free Pwned Passwords k-anonymity lookup: only the first five SHA-1 characters go to HIBP. Account search stays at HIBP.",source:"https://haveibeenpwned.com/",sourceLabel:"Have I Been Pwned"},
  {id:"dehashed",name:"DeHashed",group:"Exposure",kind:"external",engine:"evidence",glyph:"⌗",description:"Third-party account-breach service reference. XUNIA offers a local, user-supplied exposure-evidence search instead.",source:"https://dehashed.com/",sourceLabel:"DeHashed"},
  {id:"leakosint",name:"LeakOSINT",group:"Exposure",kind:"restricted",engine:"evidence",glyph:"◇",description:"Search only records you are authorized to hold; no leaked-credential database or third-party bot is duplicated."},
  {id:"universal-searchbot",name:"UniversalSearchBot",group:"Communications",kind:"reference",engine:"evidence",glyph:"✺",description:"Telegram-bot reference. XUNIA provides a local searchable dataset without impersonating a bot or contacting users."},
  {id:"deepdarkcti",name:"DeepDarkCTI",group:"Threat Intel",kind:"integration",engine:"threat",glyph:"◈",description:"CISA Known Exploited Vulnerabilities public feed plus evidence intake. No claims of access to the named third-party CTI collection.",source:"https://www.cisa.gov/known-exploited-vulnerabilities-catalog",sourceLabel:"CISA KEV"},
  {id:"darkwebdaily",name:"DarkwebDaily.live",group:"Threat Intel",kind:"workspace",engine:"threat",glyph:"D",description:"Public risk bulletin workspace backed by attributed CISA vulnerability records; not a mirror of a hidden-site directory."},
  {id:"onionlive",name:"Onion.live",group:"Directories",kind:"reference",engine:"directory",glyph:"O",description:"Curated, verifiable privacy and security sources; no unverified .onion directory or automatic link forwarding."},
  {id:"torlink",name:"Tor.link",group:"Directories",kind:"reference",engine:"directory",glyph:"∞",description:"Source-attributed bookmarks for authorized research; avoids deceptive redirects and anonymous proxy gateways."},
  {id:"hidden-wiki",name:"The Hidden Wiki",group:"Directories",kind:"reference",engine:"directory",glyph:"◍",description:"Independent directory workbench for trustworthy public educational resources, not an exact Hidden Wiki mirror."},
  {id:"torcrawl",name:"TorCrawl.py",group:"Collection",kind:"native",engine:"collection",glyph:"⌘",description:"Bundled Python site-audit crawler with explicit host allowlisting, robots.txt checks, limits, and JSONL output."},
  {id:"aleph",name:"Aleph",group:"Discovery",kind:"integration",engine:"discovery",glyph:"A",description:"Launch an official OCCRP Aleph public-document search. Data and query results remain on the original service.",source:"https://aleph.occrp.org/",sourceLabel:"OCCRP Aleph"},
  {id:"tor2web",name:"TOR2web",group:"Privacy",kind:"restricted",engine:"privacy",glyph:"⊘",description:"Safety briefing only. Proxying onion services through clearnet can reveal metadata; no TOR2web proxy is offered."},
  {id:"pgp",name:"PGP Tool",group:"Cryptography",kind:"native",engine:"pgp",glyph:"⛨",description:"OpenPGP key generation, encryption, decryption, signing, and verification in your browser via pinned OpenPGP.js.",source:"https://github.com/openpgpjs/openpgpjs",sourceLabel:"OpenPGP.js"}
]);
export const GROUPS = Object.freeze(["All","Discovery","Exposure","Threat Intel","Directories","Communications","Collection","Cryptography","Privacy"]);
export const VERIFIED_LINKS = Object.freeze([
  {name:"Tor Project",url:"https://www.torproject.org/",group:"Privacy",detail:"Official privacy browser and documentation"},
  {name:"Ahmia",url:"https://ahmia.fi/",group:"Discovery",detail:"Public Tor-related search interface"},
  {name:"OCCRP Aleph",url:"https://aleph.occrp.org/",group:"Discovery",detail:"Public records and document search"},
  {name:"Have I Been Pwned",url:"https://haveibeenpwned.com/",group:"Exposure",detail:"Account and password exposure information"},
  {name:"CISA KEV Catalog",url:"https://www.cisa.gov/known-exploited-vulnerabilities-catalog",group:"Threat Intel",detail:"Official known exploited vulnerability catalog"},
  {name:"CISA KEV Source",url:"https://github.com/cisagov/kev-data",group:"Threat Intel",detail:"Public machine-readable CC0 mirror"},
  {name:"EFF Surveillance Self-Defense",url:"https://ssd.eff.org/",group:"Privacy",detail:"Defensive privacy guidance"},
  {name:"OpenPGP.js",url:"https://github.com/openpgpjs/openpgpjs",group:"Cryptography",detail:"Open-source OpenPGP implementation"}
]);
export function searchToolCatalog(query="",group="All"){
  const q=String(query).trim().toLocaleLowerCase();
  return TOOLS.filter(t=>(group==="All"||t.group===group)&&(!q||[t.name,t.group,t.kind,t.description].join(" ").toLocaleLowerCase().includes(q)));
}
export function searchEvidence(records,query=""){
  const q=String(query).trim().toLocaleLowerCase();
  return (Array.isArray(records)?records:[]).filter(r=>!q||[r.title,r.source,r.category,r.notes,r.url].join(" ").toLocaleLowerCase().includes(q));
}
export function safeUrl(value){
  try{
    const parsed=new URL(String(value));
    if(parsed.protocol!=="https:")return "";
    if(!parsed.hostname||parsed.username||parsed.password)return "";
    return parsed.toString();
  }catch{return "";}
}
export function publicQueryUrl(provider,query){
  const q=String(query).trim().slice(0,240);
  if(!q)return "";
  if(provider==="ahmia")return "https://ahmia.fi/search/?q="+encodeURIComponent(q);
  if(provider==="aleph")return "https://aleph.occrp.org/search?q="+encodeURIComponent(q);
  return "";
}
export function normalizeEvidence(input){
  if(!input||typeof input!=="object"||Array.isArray(input))return null;
  const title=String(input.title||input.name||"").trim().slice(0,180);
  if(!title)return null;
  const source=String(input.source||"User supplied").trim().slice(0,120);
  const notes=String(input.notes||input.summary||"").slice(0,3500);
  const category=String(input.category||"Observation").trim().slice(0,90);
  const url=safeUrl(input.url||"");
  const occurred=String(input.occurred||input.date||"").trim().slice(0,45);
  return {title,source,notes,category,url,occurred};
}
export function parseCsv(csv){
  const raw=String(csv).replace(/^\uFEFF/,"");
  const rows=[];let row=[],field="",quoted=false;
  for(let i=0;i<raw.length;i++){
    const char=raw[i];
    if(quoted&&char==='"'&&raw[i+1]==='"'){field+='"';i++;continue;}
    if(char==='"'){quoted=!quoted;continue;}
    if(!quoted&&char===","){row.push(field);field="";continue;}
    if(!quoted&&(char==="\n"||char==="\r")){
      if(char==="\r"&&raw[i+1]==="\n")i++;
      row.push(field);field="";
      if(row.some(v=>v.trim()))rows.push(row);
      row=[];continue;
    }
    field+=char;
  }
  if(quoted)throw new Error("CSV contains an unclosed quoted field.");
  row.push(field);if(row.some(v=>v.trim()))rows.push(row);
  if(!rows.length)return [];
  const headers=rows.shift().map(x=>x.trim().toLocaleLowerCase());
  if(!headers.includes("title")&&!headers.includes("name"))throw new Error("CSV must contain a title or name header.");
  return rows.slice(0,500).map(vals=>Object.fromEntries(headers.map((h,i)=>[h,vals[i]||""])));
}
export function parseEvidenceImport(text,fileName="data.json"){
  if(String(text).length>1500000)throw new Error("Import limit is 1.5 MB.");
  let incoming;
  if(/\.csv$/i.test(fileName))incoming=parseCsv(text);
  else{
    const data=JSON.parse(text);
    incoming=Array.isArray(data)?data:data&&data.records;
  }
  if(!Array.isArray(incoming))throw new Error("Expected an array or { records: [...] }.");
  return incoming.slice(0,500).map(normalizeEvidence).filter(Boolean);
}
export function hibpCount(rangeResponse,sha1Hex){
  const value=String(sha1Hex).toUpperCase();
  if(!/^[0-9A-F]{40}$/.test(value))throw new Error("Expected a 40-character SHA-1 digest.");
  const wanted=value.slice(5);
  for(const line of String(rangeResponse).split(/\r?\n/)){
    const [suffix,count]=line.trim().split(":");
    if(suffix&&suffix.toUpperCase()===wanted)return Math.max(0,Number.parseInt(count,10)||0);
  }
  return 0;
}
export function parseKev(data){
  if(!data||!Array.isArray(data.vulnerabilities))throw new Error("Invalid CISA KEV response.");
  return data.vulnerabilities.filter(v=>v&&typeof v.cveID==="string").map(v=>({
    cve:v.cveID,
    vendor:String(v.vendorProject||"Unknown"),
    product:String(v.product||""),
    name:String(v.vulnerabilityName||""),
    added:String(v.dateAdded||""),
    action:String(v.requiredAction||""),
    link:"https://www.cve.org/CVERecord?id="+encodeURIComponent(v.cveID)
  })).sort((a,b)=>b.added.localeCompare(a.added));
}
export function filterKev(vulnerabilities,query=""){
  const q=String(query).trim().toLocaleLowerCase();
  return vulnerabilities.filter(v=>!q||[v.cve,v.vendor,v.product,v.name,v.action].join(" ").toLocaleLowerCase().includes(q));
}


// Authorized, local-only Telegram Desktop JSON archive research.
// Importing an archive does not authorize publishing any messages.
export function parseTelegramArchive(data, maxMessages=2000) {
  if (!data || typeof data !== "object") throw new Error("Expected a Telegram Desktop JSON export.");
  const chats = Array.isArray(data?.chats?.list) ? data.chats.list : Array.isArray(data?.messages) ? [data] : [];
  if (!chats.length) throw new Error("No Telegram chats/messages found in the selected archive.");
  const limit=Math.min(2000,Math.max(1,Number(maxMessages)||2000));
  const result=[];
  for(const chat of chats) {
    const name=String(chat.name||chat.title||"Unnamed chat").slice(0,120);
    for(const msg of (Array.isArray(chat.messages)?chat.messages:[])) {
      if(result.length>=limit)return result;
      if(!msg||typeof msg!=="object")continue;
      const content=typeof msg.text==="string" ? msg.text :
        Array.isArray(msg.text)?msg.text.map(item=>typeof item==="string"?item:typeof item?.text==="string"?item.text:"").join("") : "";
      if(!content.trim())continue;
      result.push({
        chat:name,
        date:String(msg.date||"").slice(0,40),
        sender:String(msg.from||"Unknown").slice(0,120),
        text:content.slice(0,3500)
      });
    }
  }
  return result;
}
export function searchTelegramArchive(rows, query="") {
  const q=String(query).trim().toLocaleLowerCase();
  return (Array.isArray(rows)?rows:[]).filter(x=>!q||[x.chat,x.sender,x.date,x.text].join(" ").toLocaleLowerCase().includes(q));
}
export function normalizeBookmark(input) {
  if(!input||typeof input!=="object")return null;
  const url=safeUrl(input.url||"");
  const title=String(input.title||"").trim().slice(0,120);
  if(!title||!url)return null;
  return {title,url,notes:String(input.notes||"").slice(0,500)};
}
export function privacyDiagnostics(info) {
  return [
    {label:"HTTPS / secure context",pass:!!info.secureContext,note:"Required for Web Crypto API"},
    {label:"Browser cryptography",pass:!!info.webCrypto,note:"Necessary for exposure hashing and key operations"},
    {label:"Persistent browser storage",pass:!!info.localStorage,note:"Local evidence records are not encrypted"},
    {label:"Tor anonymity",pass:false,note:"A standard web page is not Tor Browser and cannot provide Tor routing"}
  ];
}
