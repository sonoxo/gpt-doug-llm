import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { ProjectStore, safeProjectPath } from '../lib/store.mjs';
import { parseAllowedCommands } from '../lib/runtime.mjs';

test('blocks traversal',()=>{assert.throws(()=>safeProjectPath('/tmp/grim','abc','../../etc/passwd'),/traversal/)});

test('project lifecycle and checkpoint restore',async()=>{
  const root=await fs.mkdtemp(path.join(os.tmpdir(),'grim-'));
  const s=new ProjectStore(root);
  const p=await s.createProject({name:'Test'});
  assert.ok(p.files.includes('index.html'));
  await s.writeFile(p.id,'x.txt','one');
  const c=await s.checkpoint(p.id,'one');
  await s.writeFile(p.id,'x.txt','two');
  await s.restoreCheckpoint(p.id,c.id);
  assert.equal(await s.readFile(p.id,'x.txt'),'one');
  await fs.rm(root,{recursive:true,force:true});
});

test('command allowlist parses exactly',()=>{
  const a=parseAllowedCommands('npm,node,git');
  assert.equal(a.has('npm'),true);
  assert.equal(a.has('bash'),false);
});
