import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { WebSocketServer } from 'ws';
import { ProjectStore, safeProjectPath } from './lib/store.mjs';
import { RuntimeManager, parseAllowedCommands } from './lib/runtime.mjs';

const HERE=path.dirname(fileURLToPath(import.meta.url));
const PORT=Number(process.env.PORT||8787); const HOST=process.env.HOST||'0.0.0.0';
const DATA=path.resolve(process.env.GRIM_DATA_DIR||path.join(HERE,'data'));
const store=new ProjectStore(DATA,{maxFileBytes:Number(process.env.GRIM_MAX_FILE_BYTES||2_000_000)}); await store.init();
const runtime=new RuntimeManager({root:DATA,allowedCommands:parseAllowedCommands(process.env.GRIM_ALLOWED_COMMANDS),maxPerProject:Number(process.env.GRIM_MAX_PROCESSES_PER_PROJECT||3),timeoutMs:Number(process.env.GRIM_PROCESS_TIMEOUT_MS||3_600_000)});

const MIME={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.ico':'image/x-icon'};

function json(res,status,data){res.writeHead(status,{'content-type':'application/json; charset=utf-8','cache-control':'no-store'});res.end(JSON.stringify(data));}
async function body(req){const chunks=[];let n=0;for await(const c of req){n+=c.length;if(n>4_000_000)throw Object.assign(new Error('request too large'),{status:413});chunks.push(c)}if(!chunks.length)return{};try{return JSON.parse(Buffer.concat(chunks).toString('utf8'))}catch{throw Object.assign(new Error('invalid JSON'),{status:400})}}
function match(url,re){const m=url.pathname.match(re);return m&&m.slice(1).map(decodeURIComponent)}

const server=http.createServer(async(req,res)=>{
  const url=new URL(req.url,'http://local');
  try{
    if(url.pathname==='/api/health')return json(res,200,{schema:'GRIM_RUNTIME_V1',status:'ok',runtime:'node',projects:(await store.listProjects()).length,processes:runtime.list().length});
    if(url.pathname==='/api/projects'&&req.method==='GET')return json(res,200,{projects:await store.listProjects()});
    if(url.pathname==='/api/projects'&&req.method==='POST'){const b=await body(req);return json(res,201,{project:await store.createProject(b)});}
    let m;
    if((m=match(url,/^\/api\/projects\/([^/]+)$/))){const[id]=m;if(req.method==='GET')return json(res,200,{project:await store.getProject(id),processes:runtime.list(id),checkpoints:await store.listCheckpoints(id)});if(req.method==='DELETE'){for(const p of runtime.list(id))runtime.stop(p.id);await store.deleteProject(id);return json(res,200,{ok:true});}}
    if((m=match(url,/^\/api\/projects\/([^/]+)\/files$/))){const[id]=m;if(req.method==='GET')return json(res,200,{files:await store.listFiles(id)});}
    if((m=match(url,/^\/api\/projects\/([^/]+)\/file$/))){const[id]=m;const rel=url.searchParams.get('path')||'';if(req.method==='GET'){const content=await store.readFile(id,rel);res.writeHead(200,{'content-type':'text/plain; charset=utf-8','cache-control':'no-store'});return res.end(content)}if(req.method==='PUT'){const b=await body(req);await store.writeFile(id,rel,b.content??'');return json(res,200,{ok:true})}if(req.method==='DELETE'){await store.deleteFile(id,rel);return json(res,200,{ok:true})}}
    if((m=match(url,/^\/api\/projects\/([^/]+)\/checkpoints$/))){const[id]=m;if(req.method==='GET')return json(res,200,{checkpoints:await store.listCheckpoints(id)});if(req.method==='POST'){const b=await body(req);return json(res,201,{checkpoint:await store.checkpoint(id,b.label)});}}
    if((m=match(url,/^\/api\/projects\/([^/]+)\/checkpoints\/([^/]+)\/restore$/))&&req.method==='POST'){const[id,cid]=m;return json(res,200,await store.restoreCheckpoint(id,cid));}
    if((m=match(url,/^\/api\/projects\/([^/]+)\/processes$/))){const[id]=m;if(req.method==='GET')return json(res,200,{processes:runtime.list(id)});if(req.method==='POST'){const b=await body(req);const p=await runtime.spawn(id,String(b.command||''),Array.isArray(b.args)?b.args.map(String):[],{port:b.port?Number(b.port):null});return json(res,201,{process:p})}}
    if((m=match(url,/^\/api\/projects\/([^/]+)\/start$/))&&req.method==='POST'){const[id]=m;return json(res,201,{process:await runtime.startDetected(id)});}
    if((m=match(url,/^\/api\/processes\/([^/]+)\/stop$/))&&req.method==='POST'){return json(res,200,{ok:runtime.stop(m[0])});}
    if((m=match(url,/^\/api\/processes\/([^/]+)\/logs$/))&&req.method==='GET'){return json(res,200,{logs:runtime.logs(m[0])});}
    if((m=match(url,/^\/api\/projects\/([^/]+)\/agent$/))&&req.method==='POST'){const[id]=m;const b=await body(req);return json(res,200,await runAgent(id,String(b.prompt||''),String(b.mode||'build')));}
    if((m=match(url,/^\/preview\/([^/]+)(\/.*)?$/))){const[id,rest='/' ]=m;const live=runtime.list(id).filter(p=>p.status==='running'&&p.command!=='bash'&&p.command!=='sh').at(-1);if(live)return proxyPreview(req,res,live.port,rest+url.search);return serveProjectStatic(res,id,rest||'/');}
    return servePublic(res,url.pathname);
  }catch(err){console.error(err);return json(res,err.status||500,{error:err.message||'internal error'});}
});

const wss=new WebSocketServer({noServer:true});
server.on('upgrade',(req,socket,head)=>{const url=new URL(req.url,'http://local');const m=url.pathname.match(/^\/ws\/projects\/([^/]+)\/terminal$/);if(!m)return socket.destroy();wss.handleUpgrade(req,socket,head,ws=>wss.emit('connection',ws,decodeURIComponent(m[1])));});
wss.on('connection',async(ws,projectId)=>{let processId=null;try{const shell=process.platform==='win32'?'cmd':'bash';const p=await runtime.spawn(projectId,shell,[],{});processId=p.id;runtime.attach(processId,ws);ws.send(JSON.stringify({type:'ready',process:p}));ws.on('message',raw=>{try{const msg=JSON.parse(String(raw));if(msg.type==='stdin')runtime.write(processId,String(msg.data||''));if(msg.type==='stop')runtime.stop(processId)}catch(e){ws.send(JSON.stringify({type:'error',message:e.message}))}});ws.on('close',()=>processId&&runtime.stop(processId));}catch(e){ws.send(JSON.stringify({type:'error',message:e.message}));ws.close();}});

async function servePublic(res,pathname){const rel=pathname==='/'?'index.html':pathname.replace(/^\//,'');const root=path.resolve(HERE,'public');const file=path.resolve(root,rel);if(!file.startsWith(root+path.sep)&&file!==root)return json(res,400,{error:'invalid path'});try{const data=await fs.readFile(file);res.writeHead(200,{'content-type':MIME[path.extname(file)]||'application/octet-stream'});res.end(data)}catch{return json(res,404,{error:'not found'})}}
async function serveProjectStatic(res,id,pathname){const rel=(pathname==='/'?'index.html':pathname.replace(/^\//,''));const {resolved}=safeProjectPath(DATA,id,rel);try{const data=await fs.readFile(resolved);res.writeHead(200,{'content-type':MIME[path.extname(resolved)]||'application/octet-stream','cache-control':'no-store'});res.end(data)}catch{return json(res,404,{error:'preview file not found'})}}
function proxyPreview(req,res,port,pathname){const p=http.request({hostname:'127.0.0.1',port,path:pathname,method:req.method,headers:{...req.headers,host:`127.0.0.1:${port}`}},up=>{res.writeHead(up.statusCode||502,up.headers);up.pipe(res)});p.on('error',e=>json(res,502,{error:`preview unavailable: ${e.message}`}));req.pipe(p)}

async function runAgent(projectId,prompt,mode){
  if(!prompt.trim())throw Object.assign(new Error('prompt required'),{status:400});
  const key=process.env.OPENAI_API_KEY;const model=process.env.OPENAI_MODEL;
  if(!key||!model)return deterministicAgent(projectId,prompt,mode);
  await store.checkpoint(projectId,`Before AI ${mode}`);
  const files=await store.listFiles(projectId);const context=[];
  for(const f of files.slice(0,40)){try{const c=await store.readFile(projectId,f);context.push(`FILE:${f}\n${c.slice(0,12000)}`)}catch{}}
  const instructions=`You are GrimTheBuilder's coding agent. Return ONLY JSON with keys message and operations. operations is an array of {op:\"write_file\",path,content} or {op:\"delete_file\",path}. Never use absolute paths or .. . Mode=${mode}. ${mode==='plan'||mode==='explain'?'Do not modify files; return operations:[].':'Make the requested implementation directly.'}`;
  const response=await fetch('https://api.openai.com/v1/responses',{method:'POST',headers:{authorization:`Bearer ${key}`,'content-type':'application/json'},body:JSON.stringify({model,input:`${instructions}\n\nUSER:\n${prompt}\n\nPROJECT:\n${context.join('\n\n')}`})});
  if(!response.ok)throw Object.assign(new Error(`agent provider ${response.status}: ${(await response.text()).slice(0,500)}`),{status:502});
  const data=await response.json();const text=data.output_text||data.output?.flatMap(x=>x.content||[]).map(x=>x.text||'').join('')||'';
  let parsed;try{parsed=JSON.parse(text.replace(/^```json\s*|```$/g,''))}catch{throw Object.assign(new Error('agent returned invalid JSON'),{status:502})}
  await applyOperations(projectId,parsed.operations||[]);return {provider:'openai',message:parsed.message||'Complete',operations:parsed.operations||[]};
}
async function applyOperations(id,ops){for(const op of ops.slice(0,80)){if(op.op==='write_file')await store.writeFile(id,String(op.path),String(op.content??''));else if(op.op==='delete_file')await store.deleteFile(id,String(op.path));}}
async function deterministicAgent(id,prompt,mode){if(mode==='plan'||mode==='explain')return{provider:'local',message:`${mode.toUpperCase()}: ${prompt}`,operations:[]};await store.checkpoint(id,`Before local ${mode}`);const lower=prompt.toLowerCase();const ops=[];if(lower.includes('landing')||lower.includes('website')||lower.includes('page')){ops.push({op:'write_file',path:'index.html',content:`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Grim Build</title><link rel="stylesheet" href="style.css"></head><body><main><small>BUILT WITH GRIMTHEBUILDER</small><h1>${escapeHtml(prompt.slice(0,90))}</h1><button id="go">Launch</button><p id="out"></p></main><script src="script.js"></script></body></html>`},{op:'write_file',path:'style.css',content:'body{margin:0;min-height:100vh;display:grid;place-items:center;background:#090b0f;color:#eef2f8;font:16px system-ui}main{width:min(900px,90vw)}h1{font-size:clamp(48px,8vw,96px);line-height:.95}button{padding:12px 18px}'},{op:'write_file',path:'script.js',content:`document.querySelector('#go').onclick=()=>document.querySelector('#out').textContent='Running.';`});}else{ops.push({op:'write_file',path:'README.md',content:`# GrimTheBuilder change\n\nRequest: ${prompt}\n\nConnect an AI provider for arbitrary code generation; the local engine preserves the project and records this request.`});}await applyOperations(id,ops);return{provider:'local',message:'Local zero-cost build applied and checkpointed.',operations:ops};}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));}

server.listen(PORT,HOST,()=>console.log(`GrimTheBuilder runtime listening on http://${HOST}:${PORT}`));
