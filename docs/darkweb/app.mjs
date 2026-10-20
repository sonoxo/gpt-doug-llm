import {TOOLS,GROUPS,VERIFIED_LINKS,searchToolCatalog,searchEvidence,safeUrl,publicQueryUrl,normalizeEvidence,parseEvidenceImport,hibpCount,parseKev,filterKev,parseTelegramArchive,searchTelegramArchive,normalizeBookmark,privacyDiagnostics} from "./core.mjs";
const $=id=>document.getElementById(id);
const storeKey="xunia_glass_onion_evidence_v1";
let chosen="ahmia",group="All",records=[],kev=[];
const statuses={native:"NATIVE",integration:"INTEGRATION",workspace:"WORKSPACE",external:"EXTERNAL",reference:"REFERENCE",restricted:"RESTRICTED"};
function element(tag,attributes={},value=""){const node=document.createElement(tag);for(const [k,v] of Object.entries(attributes))node.setAttribute(k,v);if(value)node.textContent=value;return node;}
function link(url,label,cls=""){const a=element("a",{href:url,target:"_blank",rel:"noopener noreferrer",class:cls},label);return a;}
function feedback(id,message){$(id).textContent=message;}
function safeRead(){try{const v=JSON.parse(localStorage.getItem(storeKey)||"[]");return Array.isArray(v)?v.slice(0,500).map(normalizeEvidence).filter(Boolean):[];}catch{return [];}}
function save(){try{localStorage.setItem(storeKey,JSON.stringify(records));return true;}catch{return false;}}
function filterButtons(){const parent=$("group-filters");parent.replaceChildren();for(const g of GROUPS){const count=g==="All"?TOOLS.length:TOOLS.filter(x=>x.group===g).length;const b=element("button",{class:"filter"+(g===group?" active":""),type:"button","aria-pressed":String(g===group)});b.textContent=g+" ";b.append(element("span",{},String(count)));b.addEventListener("click",()=>{group=g;filterButtons();renderTools();});parent.append(b);}}
function renderTools(){const found=searchToolCatalog($("tool-search").value,group);$("tool-count").textContent=found.length+" / "+TOOLS.length;$("tool-empty").hidden=found.length!==0;const out=$("tool-grid");out.replaceChildren();for(const tool of found){const b=element("button",{type:"button",class:"tool-card"+(tool.id===chosen?" selected":""),"aria-label":"Open "+tool.name,"aria-pressed":String(tool.id===chosen)});const h=element("div",{class:"tool-card-head"});h.append(element("span",{class:"tool-glyph","aria-hidden":"true"},tool.glyph),element("span",{class:"status status-"+tool.kind},statuses[tool.kind]));b.append(h,element("span",{class:"tool-card-name"},tool.name),element("span",{class:"tool-card-desc"},tool.description));const f=element("span",{class:"tool-card-foot"});f.append(element("span",{},tool.group.toUpperCase()),element("span",{class:"tool-card-arrow","aria-hidden":"true"},"↗"));b.append(f);b.addEventListener("click",()=>selectTool(tool.id));out.append(b);}}
function selectTool(id){const t=TOOLS.find(x=>x.id===id);if(!t)return;chosen=id;$("active-glyph").textContent=t.glyph;$("active-category").textContent=t.group.toUpperCase();$("active-title").textContent=t.name;$("active-description").textContent=t.description;const s=$("active-status");s.className="status status-"+t.kind;s.textContent=statuses[t.kind];for(const p of document.querySelectorAll(".engine-pane"))p.hidden=p.dataset.engine!==t.engine;renderTools();$("workspace").scrollIntoView({behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth"});}
function renderLinks(){const out=$("verified-links");for(const row of VERIFIED_LINKS){const a=link(row.url,"","directory-link");a.append(element("strong",{},row.name+" ↗"),element("small",{},row.group+" · "+row.detail));out.append(a);}}
function renderEvidence(){const filtered=searchEvidence(records,$("evidence-search").value);$("evidence-total").textContent=String(records.length);const out=$("evidence-list");out.replaceChildren();if(!filtered.length){out.append(element("p",{class:"helper"},records.length?"No matching records.":"No evidence records saved. Import or add authorized research notes."));return;}for(const r of filtered.slice().reverse()){const item=element("article",{class:"record"});item.append(element("strong",{},r.title),element("div",{class:"record-meta"},r.category+" / "+r.source+(r.occurred?" / "+r.occurred:"")));if(r.notes)item.append(element("p",{},r.notes));if(r.url)item.append(link(r.url,"View verified HTTPS source ↗"));out.append(item);}}
function renderKev(){const filtered=filterKev(kev,$("kev-query").value);const out=$("kev-results");out.replaceChildren();for(const v of filtered.slice(0,60)){const div=element("article",{class:"intel-item"});div.append(link(v.link,v.cve+" ↗"));div.append(element("strong",{},v.vendor+" / "+v.product),element("small",{},v.name+" · Added "+v.added));out.append(div);}if(kev.length)feedback("kev-feedback",filtered.length+" matching vulnerabilities / "+kev.length+" from CISA. Showing first 60. No cached fallback.");}
async function loadKev(){const button=$("load-kev");button.disabled=true;feedback("kev-feedback","Loading official CISA public dataset...");try{const response=await fetch("https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json",{cache:"no-store",signal:AbortSignal.timeout(18000)});if(!response.ok)throw new Error("HTTP "+response.status);kev=parseKev(await response.json());renderKev();}catch(err){kev=[];$("kev-results").replaceChildren();feedback("kev-feedback","Unable to load official CISA feed: "+err.message+". No results are simulated.");}finally{button.disabled=false;}}
async function checkPassword(event){event.preventDefault();const input=$("password-input");const value=input.value;input.value="";if(!value){feedback("password-feedback","Enter a non-production test password.");return;}try{if(!crypto.subtle)throw new Error("Secure browser context required");const buffer=await crypto.subtle.digest("SHA-1",new TextEncoder().encode(value));const sha=Array.from(new Uint8Array(buffer),v=>v.toString(16).padStart(2,"0")).join("").toUpperCase();const r=await fetch("https://api.pwnedpasswords.com/range/"+sha.slice(0,5),{headers:{"Add-Padding":"true"},cache:"no-store",signal:AbortSignal.timeout(12000)});if(!r.ok)throw new Error("API HTTP "+r.status);const count=hibpCount(await r.text(),sha);feedback("password-feedback",count?"This test password appears "+count.toLocaleString()+" times in the Pwned Passwords dataset. Do not use it.":"No matching hash found in the current dataset. This does not prove a password is safe.");}catch(err){feedback("password-feedback","Check unavailable: "+err.message);} }
function pgp(){if(!globalThis.openpgp)throw new Error("OpenPGP.js did not load. Network access to the pinned library is required.");return globalThis.openpgp;}
async function pgpRun(kind){const status=id=>feedback("pgp-feedback",id);const output=$("pgp-output");output.value="";const api=pgp();const message=$("pgp-input").value;const pub=$("pgp-public").value.trim(),priv=$("pgp-private").value.trim(),pass=$("pgp-passphrase").value;try{let result="";if(kind==="generate"){const name=$("pgp-name").value.trim()||"Researcher";const email=$("pgp-email").value.trim()||undefined;const userIDs=[email?{name,email}:{name}];const created=await api.generateKey({type:"ecc",curve:"curve25519",userIDs,passphrase:pass,format:"armored"});$("pgp-public").value=created.publicKey;$("pgp-private").value=created.privateKey;result="ECC key pair generated. Copy and securely back up the keys. The private key stays in this page's memory."; }else if(kind==="encrypt"){if(!pub||!message)throw new Error("Public key and message required.");const keys=await api.readKey({armoredKey:pub});result=await api.encrypt({message:await api.createMessage({text:message}),encryptionKeys:keys});}else if(kind==="decrypt"){if(!priv||!message)throw new Error("Private key and armored message required.");const k=await api.readPrivateKey({armoredKey:priv});const key=pass?await api.decryptKey({privateKey:k,passphrase:pass}):k;const v=await api.decrypt({message:await api.readMessage({armoredMessage:message}),decryptionKeys:key});result=v.data;}else if(kind==="sign"){if(!priv||!message)throw new Error("Private key and plain message required.");const k=await api.readPrivateKey({armoredKey:priv});const key=pass?await api.decryptKey({privateKey:k,passphrase:pass}):k;result=await api.sign({message:await api.createCleartextMessage({text:message}),signingKeys:key});}else if(kind==="verify"){if(!pub||!message)throw new Error("Public key and cleartext signed message required.");const k=await api.readKey({armoredKey:pub});const v=await api.verify({message:await api.readCleartextMessage({cleartextMessage:message}),verificationKeys:k});if(!v.signatures.length)throw new Error("No signature found.");await Promise.all(v.signatures.map(s=>s.verified));result="Signature verified successfully.\n\n"+v.data;}output.value=result;status(kind==="generate"?"Key pair generated locally. Never paste secret keys into untrusted sites.":kind==="verify"?"Valid signature for the provided public key.":kind+" complete in browser.");}catch(err){status("PGP error: "+err.message);}}
function download(name,content){const url=URL.createObjectURL(new Blob([content],{type:"application/json"}));const a=element("a",{href:url,download:name});document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}

const bookmarkKey="xunia_glass_onion_bookmarks_v1";
let telegramMessages=[], personalBookmarks=[];
function bookmarkRead() {
  try {
    const input=JSON.parse(localStorage.getItem(bookmarkKey)||"[]");
    return Array.isArray(input)?input.slice(0,60).map(normalizeBookmark).filter(Boolean):[];
  } catch {return [];}
}
function bookmarkSave() {
  try {localStorage.setItem(bookmarkKey,JSON.stringify(personalBookmarks));return true;}
  catch {return false;}
}
function renderBookmarks() {
  const out=$("bookmark-list");out.replaceChildren();
  if(!personalBookmarks.length){out.append(element("p",{class:"helper"},"No private bookmarks added."));return;}
  for(const item of personalBookmarks){
    const a=link(item.url,"","directory-link");
    a.append(element("strong",{},item.title+" ↗"),element("small",{},item.notes||item.url));
    out.append(a);
  }
}
function renderTelegram() {
  const out=$("telegram-results");out.replaceChildren();
  const filtered=searchTelegramArchive(telegramMessages,$("telegram-search").value);
  if(telegramMessages.length){
    feedback("telegram-feedback",filtered.length+" matching messages / "+telegramMessages.length+" locally loaded. Not persisted.");
  }
  for(const item of filtered.slice(0,80)){
    const entry=element("article",{class:"record"});
    entry.append(element("strong",{},item.chat+" / "+item.sender),
      element("span",{class:"record-meta"},item.date||"Undated"),
      element("p",{},item.text));
    out.append(entry);
  }
  if(filtered.length>80)out.append(element("p",{class:"helper"},"Showing first 80 matches. Refine search to inspect the remainder."));
}
function renderPrivacy() {
  const results=$("privacy-results");results.replaceChildren();
  let stored=false;
  try{const testKey="__xunia_storage_probe__";localStorage.setItem(testKey,"yes");stored=localStorage.getItem(testKey)==="yes";localStorage.removeItem(testKey);}catch{}
  const checks=privacyDiagnostics({secureContext:!!isSecureContext,webCrypto:!!globalThis.crypto?.subtle,localStorage:stored});
  for(const item of checks) {
    const entry=element("div",{class:"privacy-check"});
    const status=element("span",{class:"status status-"+(item.pass?"native":"restricted")},item.pass?"AVAILABLE":"NOT PROVIDED");
    const body=element("div");
    body.append(element("strong",{},item.label),element("small",{},item.note));
    entry.append(status,body);results.append(entry);
  }
}

document.addEventListener("DOMContentLoaded",()=>{
  records=safeRead();filterButtons();renderTools();renderLinks();renderEvidence();
  $("tool-search").addEventListener("input",renderTools);
  $("search-form").addEventListener("submit",e=>{e.preventDefault();const url=publicQueryUrl("ahmia",$("global-query").value);if(url)window.open(url,"_blank","noopener,noreferrer");});
  $("search-aleph").addEventListener("click",()=>{const url=publicQueryUrl("aleph",$("global-query").value);if(url)window.open(url,"_blank","noopener,noreferrer");else feedback("search-feedback","Enter a query first.");});
  $("search-local").addEventListener("click",()=>{$("evidence-search").value=$("global-query").value;renderEvidence();$("evidence").scrollIntoView();});
  $("quick-evidence-find").addEventListener("click",()=>{$("evidence-search").value=$("quick-evidence-query").value;renderEvidence();$("evidence").scrollIntoView();});
  $("password-form").addEventListener("submit",checkPassword);
  $("load-kev").addEventListener("click",loadKev);$("kev-query").addEventListener("input",renderKev);
  $("copy-crawl").addEventListener("click",async()=>{try{await navigator.clipboard.writeText($("crawl-command").textContent);feedback("copy-feedback","Command copied.");}catch{feedback("copy-feedback","Clipboard unavailable; select the command manually.");}});
  for(const action of ["generate","encrypt","decrypt","sign","verify"])$("pgp-"+action).addEventListener("click",async()=>{try{await pgpRun(action);}catch(err){feedback("pgp-feedback",err.message);}});
  $("evidence-form").addEventListener("submit",e=>{e.preventDefault();const obj=Object.fromEntries(new FormData(e.currentTarget));const rec=normalizeEvidence(obj);if(!rec)return;if(records.length>=500){feedback("evidence-feedback","Vault is limited to 500 records.");return;}records.push(rec);if(save()){e.currentTarget.reset();feedback("evidence-feedback","Stored in this browser only.");}else feedback("evidence-feedback","Browser storage unavailable or full; export records for backup.");renderEvidence();});
  $("evidence-search").addEventListener("input",renderEvidence);
  $("export-evidence").addEventListener("click",()=>download("xunia-glass-onion-evidence.json",JSON.stringify({schema:"xunia.glass.onion.evidence.v1",exportedAt:new Date().toISOString(),records},null,2)));
  $("clear-evidence").addEventListener("click",()=>{if(!records.length)return;if(confirm("Delete all locally saved research records from this browser?")){records=[];save();renderEvidence();feedback("evidence-feedback","Local evidence cleared.");}});
  $("import-evidence").addEventListener("change",async e=>{const f=e.target.files?.[0];if(!f)return;try{if(f.size>1500000)throw new Error("Import must be <= 1.5MB.");const imported=parseEvidenceImport(await f.text(),f.name);records=[...records,...imported].slice(0,500);if(!save())throw new Error("Browser storage unavailable; export your evidence instead.");renderEvidence();feedback("evidence-feedback",imported.length+" records imported locally (maximum 500 total).");}catch(err){feedback("evidence-feedback","Import failed: "+err.message);}finally{e.target.value="";}});

  personalBookmarks=bookmarkRead();renderBookmarks();
  $("telegram-file").addEventListener("change",async e=>{
    const file=e.target.files?.[0];if(!file)return;
    try{
      if(file.size>1_500_000)throw new Error("Archive must be at most 1.5 MB.");
      if(!/\.json$/i.test(file.name))throw new Error("Choose a Telegram Desktop JSON export.");
      const data=JSON.parse(await file.text());
      telegramMessages=parseTelegramArchive(data);
      $("telegram-search").value="";renderTelegram();
      if(!telegramMessages.length)feedback("telegram-feedback","No text messages in the selected export.");
    }catch(err){telegramMessages=[];$("telegram-results").replaceChildren();feedback("telegram-feedback","Import failed: "+err.message);}
    finally{e.target.value="";}
  });
  $("telegram-search").addEventListener("input",renderTelegram);
  $("telegram-clear").addEventListener("click",()=>{
    telegramMessages=[];$("telegram-results").replaceChildren();
    $("telegram-search").value="";feedback("telegram-feedback","Archive cleared from this page's memory.");
  });
  $("bookmark-form").addEventListener("submit",e=>{
    e.preventDefault();
    const bookmark=normalizeBookmark({title:$("bookmark-title").value,url:$("bookmark-url").value,notes:$("bookmark-notes").value});
    if(!bookmark){feedback("bookmark-feedback","Enter a title and a valid HTTPS URL without credentials.");return;}
    if(personalBookmarks.some(b=>b.url===bookmark.url)){feedback("bookmark-feedback","This source is already bookmarked.");return;}
    if(personalBookmarks.length>=60){feedback("bookmark-feedback","Maximum 60 bookmarks.");return;}
    personalBookmarks.push(bookmark);
    if(bookmarkSave()){e.currentTarget.reset();feedback("bookmark-feedback","Bookmark saved only in this browser.");}
    else feedback("bookmark-feedback","Storage unavailable. Bookmark was kept only in memory.");
    renderBookmarks();
  });
  $("privacy-run").addEventListener("click",renderPrivacy);
  const hash=location.hash.slice(1);if(hash==="pgp")selectTool("pgp");
});
