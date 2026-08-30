#!/usr/bin/env node

import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { access, readFile, unlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import net from 'node:net';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const tsx = path.join(root, 'node_modules', '.bin', 'tsx');
const api = 'http://127.0.0.1:8787';
const zyraHost = '127.0.0.1';
const zyraPort = 5050;
const zyraRoot = process.env.ZYRA_ROOT || path.join(os.homedir(), 'zyra', 'apps', 'zyra-live-implement');
const zyraPidFile = path.join(os.tmpdir(), 'gspo-zyra.pid');
const zyraLog = path.join(os.tmpdir(), 'gspo-zyra.log');

const profile = {
  ...process.env,
  CAMERA_SOURCE: process.env.CAMERA_SOURCE || 'macos-screen',
  SCREEN_REGION: process.env.SCREEN_REGION || '1164,134,352,226',
  SCREEN_POLL_MS: process.env.SCREEN_POLL_MS || '750',
  DOG_CONFIDENCE: process.env.DOG_CONFIDENCE || '0.30',
  LOG_FRAMES: process.env.LOG_FRAMES || 'true',
};

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function portOpen(host, port, timeoutMs = 600) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host, port });
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      socket.destroy();
      resolve(value);
    };
    socket.setTimeout(timeoutMs);
    socket.once('connect', () => finish(true));
    socket.once('timeout', () => finish(false));
    socket.once('error', () => finish(false));
  });
}

async function ensureZyra() {
  if (await portOpen(zyraHost, zyraPort)) {
    console.log('[GSPO] ZYRA already online :5050');
    return true;
  }

  try {
    await access(path.join(zyraRoot, 'package.json'));
  } catch {
    console.error(`[GSPO] ZYRA not found at ${zyraRoot}`);
    console.error('[GSPO] set ZYRA_ROOT=/path/to/apps/zyra-live-implement if your repo lives elsewhere.');
    return false;
  }

  console.log('[GSPO] ZYRA offline — starting automatically...');
  const shellCommand = `cd ${JSON.stringify(zyraRoot)} && npm start >> ${JSON.stringify(zyraLog)} 2>&1`;
  const child = spawn('/bin/zsh', ['-lc', shellCommand], {
    detached: true,
    stdio: 'ignore',
  });
  child.unref();
  await writeFile(zyraPidFile, String(child.pid)).catch(() => undefined);

  for (let i = 0; i < 30; i += 1) {
    if (await portOpen(zyraHost, zyraPort)) {
      console.log('[GSPO] ZYRA online :5050');
      return true;
    }
    await sleep(500);
  }

  console.error(`[GSPO] ZYRA did not open :5050. Check ${zyraLog}`);
  return false;
}

async function stopAutoZyra() {
  try {
    const pid = Number((await readFile(zyraPidFile, 'utf8')).trim());
    if (Number.isInteger(pid) && pid > 1) {
      try {
        process.kill(-pid, 'SIGTERM');
        console.log('[GSPO] auto-started ZYRA stopped');
      } catch {
        // Process may already be gone.
      }
    }
  } catch {
    // No GSPO-owned ZYRA PID file.
  } finally {
    await unlink(zyraPidFile).catch(() => undefined);
  }
}

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
  console.log(`[GSPO] ZYRA :5050 ${await portOpen(zyraHost, zyraPort) ? 'ONLINE' : 'OFFLINE'}`);
  await request('/status');
} else if (command === 'test') {
  await request('/alarm/test', { method: 'POST' });
} else if (command === 'stop') {
  const result = spawnSync('pkill', ['-f', 'tsx src/index.ts'], { stdio: 'inherit' });
  if (result.status === 0) console.log('[GSPO] Watch Dog stopped');
  else console.log('[GSPO] no running Watch Dog process found');
  await stopAutoZyra();
} else if (command === 'start' || command === 'run') {
  console.log('[GSPO] AUTO STACK BOOT');
  const zyraReady = await ensureZyra();
  if (!zyraReady) console.warn('[GSPO] continuing with Watch Dog; ZYRA pipeline delivery may fail until :5050 is online.');

  console.log('[GSPO] WATCH DOG ONLINE PROFILE');
  console.log(`[GSPO] source=${profile.CAMERA_SOURCE} region=${profile.SCREEN_REGION} poll=${profile.SCREEN_POLL_MS}ms dog-confidence=${profile.DOG_CONFIDENCE}`);
  console.log('[GSPO] Ctrl+C to stop Watch Dog');

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
  console.log('  GSPO          Auto-start ZYRA if needed, then start Watch Dog');
  console.log('  GSPO status   Show ZYRA + Watch Dog status');
  console.log('  GSPO test     Test the alarm + ZYRA pipeline');
  console.log('  GSPO stop     Stop Watch Dog and GSPO-started ZYRA');
  process.exitCode = 2;
}
