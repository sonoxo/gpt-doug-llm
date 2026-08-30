#!/usr/bin/env node

import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const tsx = path.join(root, 'node_modules', '.bin', 'tsx');
const api = 'http://127.0.0.1:8787';

const profile = {
  ...process.env,
  CAMERA_SOURCE: process.env.CAMERA_SOURCE || 'macos-screen',
  SCREEN_REGION: process.env.SCREEN_REGION || '1164,134,352,226',
  SCREEN_POLL_MS: process.env.SCREEN_POLL_MS || '750',
  DOG_CONFIDENCE: process.env.DOG_CONFIDENCE || '0.30',
  LOG_FRAMES: process.env.LOG_FRAMES || 'true',
};

async function request(pathname, init) {
  try {
    const res = await fetch(`${api}${pathname}`, init);
    const text = await res.text();
    console.log(text);
    process.exitCode = res.ok ? 0 : 1;
  } catch (error) {
    console.error(`[GSPO] Watch Dog API unavailable at ${api}: ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  }
}

const command = (process.argv[2] || 'start').toLowerCase();

if (command === 'status') {
  await request('/status');
} else if (command === 'test') {
  await request('/alarm/test', { method: 'POST' });
} else if (command === 'stop') {
  const result = spawnSync('pkill', ['-f', 'tsx src/index.ts'], { stdio: 'inherit' });
  if (result.status === 0) console.log('[GSPO] stopped');
  else console.log('[GSPO] no running Watch Dog process found');
} else if (command === 'start' || command === 'run') {
  console.log('[GSPO] WATCH DOG ONLINE PROFILE');
  console.log(`[GSPO] source=${profile.CAMERA_SOURCE} region=${profile.SCREEN_REGION} poll=${profile.SCREEN_POLL_MS}ms dog-confidence=${profile.DOG_CONFIDENCE}`);
  console.log('[GSPO] Ctrl+C to stop');

  const child = spawn(tsx, ['src/index.ts'], {
    cwd: root,
    env: profile,
    stdio: 'inherit',
  });

  child.on('error', (error) => {
    console.error(`[GSPO] failed to launch: ${error.message}`);
    console.error('[GSPO] run `npm install` in watch-dog, then try again.');
    process.exitCode = 1;
  });

  child.on('exit', (code, signal) => {
    if (signal) process.kill(process.pid, signal);
    else process.exitCode = code ?? 0;
  });
} else {
  console.log('GSPO commands:');
  console.log('  GSPO          Start Watch Dog');
  console.log('  GSPO status   Show Watch Dog status');
  console.log('  GSPO test     Test the alarm + ZYRA pipeline');
  console.log('  GSPO stop     Stop Watch Dog');
  process.exitCode = 2;
}
