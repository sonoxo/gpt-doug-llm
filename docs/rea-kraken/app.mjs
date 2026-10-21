const LIMIT_MANIFEST = 1024 * 1024;
const LIMIT_EVIDENCE = 64 * 1024 * 1024;
const HEX = /^[0-9a-f]{64}$/;
const ID = /^[0-9]{2}$/;
const enc = new TextEncoder();

export async function digest(bytes) {
  const data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('');
}

export async function verifyBundle(files) {
  const selected = [...files];
  const unique = new Map();
  for (const file of selected) {
    if (!file || typeof file.name !== 'string' || unique.has(file.name)) {
      throw new Error('Choose one manifest and unique evidence files from one local run');
    }
    unique.set(file.name, file);
  }
  const source = unique.get('manifest.json');
  if (!source || source.size === 0 || source.size > LIMIT_MANIFEST) {
    throw new Error('A manifest.json under 1 MiB is required');
  }
  let manifest;
  try { manifest = JSON.parse(await source.text()); }
  catch { throw new Error('Manifest must be valid JSON'); }
  if (!manifest || manifest.system !== 'SONOXO_GPT_CHAOS_REA_SWARM' || manifest.schema_version !== 1) {
    throw new Error('Unrecognized REA Kraken manifest format');
  }
  const rows = manifest.results;
  if (!Array.isArray(rows) || rows.length < 1 || rows.length > 8 ||
      !['PASS', 'BLOCKED'].includes(manifest.state)) {
    throw new Error('Invalid job inventory or run state');
  }
  const ids = new Set();
  const outcomes = [];
  let verified = 0;
  let blocked = 0;
  for (const job of rows) {
    if (!job || typeof job !== 'object' || !ID.test(job.id) || ids.has(job.id)) {
      throw new Error('Invalid or duplicate job identifier');
    }
    ids.add(job.id);
    if (job.state === 'BLOCKED') {
      if ('evidence' in job || 'sha256' in job) throw new Error('Blocked job cannot claim evidence');
      blocked++;
      outcomes.push({ id: job.id, status: 'BLOCKED' });
      continue;
    }
    if (job.state !== 'PASS' || job.evidence !== job.id + '.json' || !HEX.test(job.sha256)) {
      throw new Error('Invalid job state, filename, or hash');
    }
    if (!Number.isSafeInteger(job.bytes) || job.bytes < 1 || job.bytes > LIMIT_EVIDENCE) {
      throw new Error('Invalid evidence length');
    }
    const file = unique.get(job.evidence);
    if (!file || file.size !== job.bytes || file.size > LIMIT_EVIDENCE) {
      throw new Error('Missing or size-mismatched evidence for job ' + job.id);
    }
    const raw = new Uint8Array(await file.arrayBuffer());
    if (await digest(raw) !== job.sha256) throw new Error('Evidence digest mismatch for job ' + job.id);
    let decoded;
    try { decoded = JSON.parse(new TextDecoder().decode(raw)); }
    catch { throw new Error('Invalid evidence JSON for job ' + job.id); }
    if (!decoded || typeof decoded !== 'object') throw new Error('Evidence root must be an object or array');
    verified++;
    outcomes.push({ id: job.id, status: 'VERIFIED', bytes: file.size });
  }
  if ((blocked === 0) !== (manifest.state === 'PASS')) {
    throw new Error('Inconsistent manifest and job states');
  }
  return {status: blocked ? 'PARTIAL' : 'VERIFIED', jobCount: rows.length,
          verified, blocked, outcomes, manifestSha256: await digest(enc.encode(await source.text()))};
}

function text(id, value) { const element = document.getElementById(id); if (element) element.textContent = value; }
function render(label, state, message, outcome) {
  const list = document.getElementById('runs');
  const article = document.createElement('article');
  article.className = 'run';
  const heading = document.createElement('h3');
  heading.textContent = label;
  const tag = document.createElement('span');
  tag.className = 'state ' + (state === 'VERIFIED' ? 'pass' : state === 'PARTIAL' ? 'partial' : 'blocked');
  tag.textContent = state;
  const detail = document.createElement('p');
  detail.textContent = message;
  article.append(heading, tag, detail);
  if (outcome) {
    const fine = document.createElement('p');
    fine.className = 'muted';
    fine.textContent = outcome.verified + '/' + outcome.jobCount + ' evidence files verified. Manifest SHA-256: ' + outcome.manifestSha256.slice(0, 16) + '...';
    article.append(fine);
  }
  list.prepend(article);
  text('run-count', String(list.children.length));
  text('last-state', state);
  text('last-state-note', state === 'VERIFIED' ? 'Integrity verified, authenticity not established' : message);
}

if (typeof document !== 'undefined') {
  const input = document.getElementById('local-files');
  input.addEventListener('change', async () => {
    if (!input.files?.length) return;
    const count = input.files.length;
    try {
      const result = await verifyBundle(input.files);
      render('LOCAL BUNDLE', result.status, count + ' files processed locally; no upload performed', result);
    } catch (error) {
      render('LOCAL BUNDLE', 'BLOCKED', error instanceof Error ? error.message : 'Unexpected validation error');
    } finally { input.value = ''; }
  });
  document.getElementById('demo').addEventListener('click', async () => {
    const evidence = JSON.stringify({kind: 'synthetic-fixture', source: 'Sonoxo', remoteActions: 0});
    const data = enc.encode(evidence);
    const file = new File([data], '01.json', {type: 'application/json'});
    const manifest = new File([JSON.stringify({
      system: 'SONOXO_GPT_CHAOS_REA_SWARM', schema_version: 1, state: 'PASS',
      results: [{id: '01', state: 'PASS', evidence: '01.json', bytes: data.length, sha256: await digest(data)}],
    })], 'manifest.json', {type: 'application/json'});
    try {
      const result = await verifyBundle([file, manifest]);
      render('SYNTHETIC DEMO', result.status, 'Generated browser-side example, not live agent telemetry', result);
    } catch (error) { render('SYNTHETIC DEMO', 'BLOCKED', String(error)); }
  });
  document.getElementById('clear').addEventListener('click', () => {
    document.getElementById('runs').replaceChildren();
    text('run-count', '0');
    text('last-state', 'NOT CONNECTED');
    text('last-state-note', 'No local evidence loaded');
  });
}
