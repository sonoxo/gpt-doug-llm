import { spawn } from 'node:child_process';
import crypto from 'node:crypto';
import net from 'node:net';
import path from 'node:path';
import fs from 'node:fs/promises';
import { safeProjectPath } from './store.mjs';

export function parseAllowedCommands(raw='npm,npx,node,pnpm,python,python3,pip,pip3,git,bash,sh') {
  return new Set(String(raw).split(',').map(x=>x.trim()).filter(Boolean));
}

export async function allocatePort(start=3100,end=3999) {
  for (let port=start; port<=end; port++) {
    const free = await new Promise(resolve=>{ const s=net.createServer(); s.once('error',()=>resolve(false)); s.listen(port,'127.0.0.1',()=>s.close(()=>resolve(true))); });
    if (free) return port;
  }
  throw new Error('no preview ports available');
}

export class RuntimeManager {
  constructor({ root, allowedCommands, maxPerProject=3, timeoutMs=3_600_000 }) {
    this.root = path.resolve(root); this.allowedCommands = allowedCommands; this.maxPerProject=maxPerProject; this.timeoutMs=timeoutMs;
    this.processes = new Map();
  }

  list(projectId) {
    return [...this.processes.values()].filter(x=>!projectId || x.projectId===projectId).map(publicProcess);
  }

  async spawn(projectId, command, args=[], { port=null }={}) {
    if (!this.allowedCommands.has(command)) throw Object.assign(new Error(`command not allowed: ${command}`), { status: 403 });
    const active = this.list(projectId).filter(x=>x.status==='running');
    if (active.length >= this.maxPerProject) throw Object.assign(new Error('process limit reached'), { status: 429 });
    const { projectRoot } = safeProjectPath(this.root, projectId);
    await fs.access(projectRoot).catch(()=>{ throw Object.assign(new Error('project not found'), { status:404 }); });
    const assignedPort = port || await allocatePort();
    const id = crypto.randomUUID();
    const record = { id, projectId, command, args:[...args], port:assignedPort, status:'starting', startedAt:new Date().toISOString(), logs:[], clients:new Set(), child:null };
    const child = spawn(command, args, { cwd:projectRoot, env:{...process.env, PORT:String(assignedPort), HOST:'0.0.0.0', BROWSER:'none'}, shell:false, stdio:['pipe','pipe','pipe'] });
    record.child=child; record.status='running'; this.processes.set(id,record);
    const push=(stream,chunk)=>{ const text=String(chunk); const evt={stream,text,time:new Date().toISOString()}; record.logs.push(evt); record.logs=record.logs.slice(-500); for(const ws of record.clients) if(ws.readyState===1) ws.send(JSON.stringify({type:'terminal',processId:id,...evt})); };
    child.stdout.on('data',d=>push('stdout',d)); child.stderr.on('data',d=>push('stderr',d));
    child.once('exit',(code,signal)=>{record.status='exited';record.exitCode=code;record.signal=signal;for(const ws of record.clients)if(ws.readyState===1)ws.send(JSON.stringify({type:'exit',processId:id,code,signal}));});
    child.once('error',err=>{record.status='error';push('stderr',err.message)});
    const timer=setTimeout(()=>{ if(record.status==='running') this.stop(id,'SIGTERM'); },this.timeoutMs); timer.unref?.();
    return publicProcess(record);
  }

  write(processId, data) { const r=this.processes.get(processId); if(!r?.child || r.status!=='running') throw Object.assign(new Error('process not running'),{status:404}); r.child.stdin.write(data); }
  stop(processId, signal='SIGTERM') { const r=this.processes.get(processId); if(!r?.child) return false; r.child.kill(signal); return true; }
  logs(processId) { const r=this.processes.get(processId); if(!r) throw Object.assign(new Error('process not found'),{status:404}); return r.logs; }
  attach(processId, ws) { const r=this.processes.get(processId); if(!r) throw new Error('process not found'); r.clients.add(ws); ws.on('close',()=>r.clients.delete(ws)); for(const evt of r.logs.slice(-100)) ws.send(JSON.stringify({type:'terminal',processId,...evt})); }

  async detectStart(projectId) {
    const { projectRoot } = safeProjectPath(this.root, projectId);
    let pkg=null; try{pkg=JSON.parse(await fs.readFile(path.join(projectRoot,'package.json'),'utf8'))}catch{}
    if(pkg?.scripts?.dev){
      const deps={...pkg.dependencies,...pkg.devDependencies};
      if(deps.next) return {command:'npm',args:['run','dev','--','-H','0.0.0.0','-p','__PORT__']};
      if(deps.vite) return {command:'npm',args:['run','dev','--','--host','0.0.0.0','--port','__PORT__']};
      return {command:'npm',args:['run','dev']};
    }
    if(pkg?.scripts?.start) return {command:'npm',args:['start']};
    if(await fileExists(path.join(projectRoot,'app.py'))) return {command:'python3',args:['app.py']};
    if(await fileExists(path.join(projectRoot,'main.py'))) return {command:'python3',args:['main.py']};
    return null;
  }

  async startDetected(projectId) {
    const spec=await this.detectStart(projectId); if(!spec) throw Object.assign(new Error('no runnable backend detected; static preview is available'),{status:422});
    const port=await allocatePort(); const args=spec.args.map(x=>x==='__PORT__'?String(port):x);
    return this.spawn(projectId,spec.command,args,{port});
  }
}

function publicProcess(r){return {id:r.id,projectId:r.projectId,command:r.command,args:r.args,port:r.port,status:r.status,startedAt:r.startedAt,exitCode:r.exitCode??null,signal:r.signal??null};}
async function fileExists(p){try{await fs.access(p);return true}catch{return false}}
