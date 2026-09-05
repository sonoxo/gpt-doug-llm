import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';

const ID_RE = /^[a-z0-9][a-z0-9-]{2,63}$/;

export function slugify(value='project') {
  const base = String(value).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48) || 'project';
  return `${base}-${crypto.randomBytes(3).toString('hex')}`;
}

export function assertProjectId(id) {
  if (!ID_RE.test(String(id || ''))) throw Object.assign(new Error('invalid project id'), { status: 400 });
  return id;
}

export function safeProjectPath(root, projectId, relative='') {
  assertProjectId(projectId);
  const projectRoot = path.resolve(root, 'projects', projectId);
  const resolved = path.resolve(projectRoot, String(relative || '').replace(/^[/\\]+/, ''));
  if (resolved !== projectRoot && !resolved.startsWith(projectRoot + path.sep)) {
    throw Object.assign(new Error('path traversal blocked'), { status: 400 });
  }
  return { projectRoot, resolved };
}

async function exists(file) { try { await fs.access(file); return true; } catch { return false; } }

async function walk(dir, base=dir) {
  const out = [];
  if (!(await exists(dir))) return out;
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.name === '.grim') continue;
    const abs = path.join(dir, entry.name);
    const rel = path.relative(base, abs).replaceAll(path.sep, '/');
    if (entry.isDirectory()) out.push(...await walk(abs, base));
    else out.push(rel);
  }
  return out.sort();
}

export class ProjectStore {
  constructor(root, { maxFileBytes = 2_000_000 } = {}) {
    this.root = path.resolve(root);
    this.maxFileBytes = maxFileBytes;
  }

  async init() {
    await fs.mkdir(path.join(this.root, 'projects'), { recursive: true });
  }

  async listProjects() {
    await this.init();
    const dirs = await fs.readdir(path.join(this.root, 'projects'), { withFileTypes: true });
    const projects = [];
    for (const d of dirs.filter(x => x.isDirectory())) {
      try { projects.push(await this.getProject(d.name)); } catch {}
    }
    return projects.sort((a,b) => String(b.updatedAt).localeCompare(String(a.updatedAt)));
  }

  async createProject({ name='Untitled App', template='static' }={}) {
    await this.init();
    const id = slugify(name);
    const { projectRoot } = safeProjectPath(this.root, id);
    await fs.mkdir(path.join(projectRoot, '.grim', 'checkpoints'), { recursive: true });
    const now = new Date().toISOString();
    const meta = { id, name: String(name).slice(0,100), template, createdAt: now, updatedAt: now };
    await fs.writeFile(path.join(projectRoot, '.grim', 'meta.json'), JSON.stringify(meta, null, 2));
    const starter = templateFiles(template, meta.name);
    for (const [file, content] of Object.entries(starter)) await this.writeFile(id, file, content, { touchMeta: false });
    await this.touch(id);
    return this.getProject(id);
  }

  async getProject(id) {
    const { projectRoot } = safeProjectPath(this.root, id);
    const raw = await fs.readFile(path.join(projectRoot, '.grim', 'meta.json'), 'utf8').catch(() => null);
    if (!raw) throw Object.assign(new Error('project not found'), { status: 404 });
    const meta = JSON.parse(raw);
    return { ...meta, files: await walk(projectRoot) };
  }

  async deleteProject(id) {
    const { projectRoot } = safeProjectPath(this.root, id);
    await fs.rm(projectRoot, { recursive: true, force: true });
  }

  async touch(id) {
    const { projectRoot } = safeProjectPath(this.root, id);
    const metaPath = path.join(projectRoot, '.grim', 'meta.json');
    const meta = JSON.parse(await fs.readFile(metaPath, 'utf8'));
    meta.updatedAt = new Date().toISOString();
    await fs.writeFile(metaPath, JSON.stringify(meta, null, 2));
  }

  async listFiles(id) {
    const { projectRoot } = safeProjectPath(this.root, id);
    if (!(await exists(projectRoot))) throw Object.assign(new Error('project not found'), { status: 404 });
    return walk(projectRoot);
  }

  async readFile(id, relative) {
    const { resolved } = safeProjectPath(this.root, id, relative);
    return fs.readFile(resolved, 'utf8').catch(err => { throw Object.assign(new Error(err.code === 'ENOENT' ? 'file not found' : err.message), { status: err.code === 'ENOENT' ? 404 : 500 }); });
  }

  async writeFile(id, relative, content, { touchMeta = true }={}) {
    const buf = Buffer.from(String(content ?? ''), 'utf8');
    if (buf.byteLength > this.maxFileBytes) throw Object.assign(new Error('file too large'), { status: 413 });
    const { resolved } = safeProjectPath(this.root, id, relative);
    if (String(relative).startsWith('.grim/')) throw Object.assign(new Error('reserved path'), { status: 400 });
    await fs.mkdir(path.dirname(resolved), { recursive: true });
    await fs.writeFile(resolved, buf);
    if (touchMeta) await this.touch(id);
  }

  async deleteFile(id, relative) {
    const { resolved } = safeProjectPath(this.root, id, relative);
    if (String(relative).startsWith('.grim/')) throw Object.assign(new Error('reserved path'), { status: 400 });
    await fs.rm(resolved, { recursive: true, force: true });
    await this.touch(id);
  }

  async checkpoint(id, label='Manual checkpoint') {
    const { projectRoot } = safeProjectPath(this.root, id);
    const checkpointId = `${Date.now()}-${crypto.randomBytes(2).toString('hex')}`;
    const dest = path.join(projectRoot, '.grim', 'checkpoints', checkpointId);
    await fs.mkdir(dest, { recursive: true });
    const files = await walk(projectRoot);
    for (const rel of files) {
      const src = path.join(projectRoot, rel); const out = path.join(dest, rel);
      await fs.mkdir(path.dirname(out), { recursive: true });
      await fs.copyFile(src, out);
    }
    await fs.writeFile(path.join(dest, 'checkpoint.json'), JSON.stringify({ id: checkpointId, label, createdAt: new Date().toISOString() }, null, 2));
    return { id: checkpointId, label };
  }

  async listCheckpoints(id) {
    const { projectRoot } = safeProjectPath(this.root, id);
    const dir = path.join(projectRoot, '.grim', 'checkpoints');
    const names = await fs.readdir(dir).catch(() => []);
    const out = [];
    for (const name of names) {
      try { out.push(JSON.parse(await fs.readFile(path.join(dir, name, 'checkpoint.json'), 'utf8'))); } catch {}
    }
    return out.sort((a,b) => String(b.createdAt).localeCompare(String(a.createdAt)));
  }

  async restoreCheckpoint(id, checkpointId) {
    if (!/^[a-z0-9-]+$/i.test(checkpointId)) throw Object.assign(new Error('invalid checkpoint'), { status: 400 });
    const { projectRoot } = safeProjectPath(this.root, id);
    const src = path.join(projectRoot, '.grim', 'checkpoints', checkpointId);
    if (!(await exists(path.join(src, 'checkpoint.json')))) throw Object.assign(new Error('checkpoint not found'), { status: 404 });
    const before = await this.checkpoint(id, 'Automatic backup before restore');
    for (const rel of await walk(projectRoot)) await fs.rm(path.join(projectRoot, rel), { force: true });
    for (const rel of await walk(src, src)) {
      if (rel === 'checkpoint.json') continue;
      const dest = path.join(projectRoot, rel);
      await fs.mkdir(path.dirname(dest), { recursive: true });
      await fs.copyFile(path.join(src, rel), dest);
    }
    await this.touch(id);
    return { restored: checkpointId, backup: before.id };
  }
}

function templateFiles(template, name) {
  if (template === 'node') return {
    'package.json': JSON.stringify({ name: slugify(name), version: '1.0.0', type: 'module', scripts: { dev: 'node server.mjs', start: 'node server.mjs' } }, null, 2),
    'server.mjs': `import http from 'node:http';\nconst port=Number(process.env.PORT||3000);\nhttp.createServer((req,res)=>{res.setHeader('content-type','text/html');res.end('<h1>${escapeJs(name)}</h1><p>Node app running.</p>')}).listen(port,'0.0.0.0',()=>console.log('listening',port));\n`
  };
  if (template === 'python') return {
    'app.py': `import os\nfrom http.server import BaseHTTPRequestHandler,HTTPServer\nclass H(BaseHTTPRequestHandler):\n def do_GET(self):\n  self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(b'<h1>${escapeJs(name)}</h1><p>Python app running.</p>')\nHTTPServer(('0.0.0.0',int(os.getenv('PORT','3000'))),H).serve_forever()\n`
  };
  return {
    'index.html': `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(name)}</title><link rel="stylesheet" href="style.css"></head><body><main><p>GRIMTHEBUILDER</p><h1>${escapeHtml(name)}</h1><button id="launch">Launch</button><p id="status">Ready.</p></main><script src="script.js"></script></body></html>`,
    'style.css': `:root{font-family:Inter,system-ui,sans-serif;color:#e8eef8;background:#0a0d12}body{margin:0;min-height:100vh;display:grid;place-items:center}main{width:min(720px,90vw)}h1{font-size:clamp(48px,9vw,100px);line-height:.9}button{padding:12px 18px}`,
    'script.js': `document.querySelector('#launch').onclick=()=>document.querySelector('#status').textContent='It works.';`
  };
}
function escapeHtml(s){ return String(s).replace(/[&<>"']/g,c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c])); }
function escapeJs(s){ return String(s).replace(/[\\'`$]/g, m=>'\\'+m); }
