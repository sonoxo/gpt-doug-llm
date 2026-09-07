const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '::1']);
const ALLOWED_ROLES = new Set(['system', 'user', 'assistant']);
const PROJECT_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const MAX_INPUT_CHARS = 22_000;
const MAX_OPERATIONS = 80;
const MAX_FILE_BYTES = 1_900_000;

function loopbackHostname(hostname) {
  return String(hostname || '').toLowerCase().replace(/^\[|\]$/g, '');
}

export function normalizeBridgeUrl(value) {
  const raw = String(value || '').trim().replace(/\/+$/, '');
  if (!raw) throw new Error('Bridge URL is required.');

  let parsed;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error('Bridge URL is invalid.');
  }

  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error('Bridge URL must use HTTP or HTTPS.');
  }
  if (parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new Error('Bridge URL cannot contain credentials, a query, or a fragment.');
  }
  if (parsed.pathname && parsed.pathname !== '/') {
    throw new Error('Bridge URL must be a base URL without a path.');
  }

  const host = loopbackHostname(parsed.hostname);
  const isLoopback = LOOPBACK_HOSTS.has(host) || host.startsWith('127.');
  if (parsed.protocol === 'http:' && !isLoopback) {
    throw new Error('Non-loopback bridge URLs must use HTTPS.');
  }
  return `${parsed.protocol}//${parsed.host}`;
}

function requestHeaders({ token = '', projectId = '', json = false } = {}) {
  const headers = { Accept: 'application/json' };
  if (json) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;
  if (projectId && PROJECT_RE.test(projectId)) headers['X-Doug-Project'] = projectId;
  return headers;
}

async function requestJson(fetchImpl, url, options = {}, timeoutMs = 15_000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetchImpl(url, { ...options, mode: 'cors', cache: 'no-store', signal: controller.signal });
    const text = await response.text();
    let payload = {};
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        throw new Error(`GPT Doug returned invalid JSON (${response.status}).`);
      }
    }
    if (!response.ok) throw new Error(payload.error || `GPT Doug request failed (${response.status}).`);
    return payload;
  } catch (error) {
    if (error?.name === 'AbortError') throw new Error('GPT Doug bridge request timed out.');
    if (error instanceof TypeError) {
      throw new Error('Cannot reach GPT Doug. Keep the bridge running and allow this page origin in DOUG_BRIDGE_ORIGINS.');
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export async function discoverGptDoug(config, fetchImpl = fetch) {
  const baseUrl = normalizeBridgeUrl(config?.baseUrl);
  const token = String(config?.token || '');
  const headers = requestHeaders({ token });
  const health = await requestJson(fetchImpl, `${baseUrl}/health`, { method: 'GET', headers });
  if (health.ok !== true || health.model_ready !== true) {
    throw new Error(health.error || health.detail || 'GPT Doug model is not ready.');
  }

  const tags = await requestJson(fetchImpl, `${baseUrl}/api/tags`, { method: 'GET', headers });
  const models = Array.isArray(tags.models)
    ? [...new Set(tags.models
        .map(item => typeof item === 'string' ? item : item?.name || item?.model || '')
        .filter(Boolean))]
    : [];
  if (!models.length) throw new Error('The bridge returned no installed, allowed models.');

  const requestedModel = String(config?.model || '');
  return {
    baseUrl,
    bridge: tags.bridge || health.bridge || 'black-house',
    model: models.includes(requestedModel) ? requestedModel : models[0],
    models,
    health,
  };
}

function validateMessages(messages) {
  if (!Array.isArray(messages) || messages.length < 1 || messages.length > 64) {
    throw new Error('Messages must contain between 1 and 64 entries.');
  }
  let count = 0;
  for (const message of messages) {
    if (!message || !ALLOWED_ROLES.has(message.role) || typeof message.content !== 'string') {
      throw new Error('Every message requires a supported role and text content.');
    }
    count += message.content.length;
  }
  if (count > MAX_INPUT_CHARS) throw new Error('GPT Doug request exceeds the bridge input limit.');
}

export async function chatGptDoug(config, messages, options = {}, fetchImpl = fetch) {
  validateMessages(messages);
  const baseUrl = normalizeBridgeUrl(config?.baseUrl);
  const model = String(config?.model || '').trim();
  if (!model) throw new Error('Select a GPT Doug model first.');

  const projectId = PROJECT_RE.test(String(options.projectId || '')) ? String(options.projectId) : '';
  const payload = {
    model,
    messages,
    stream: false,
    format: 'json',
    options: {
      temperature: 0.15,
      num_predict: 2048,
      num_ctx: 8192,
      ...(options.generation || {}),
    },
  };

  const result = await requestJson(fetchImpl, `${baseUrl}/api/chat`, {
    method: 'POST',
    headers: requestHeaders({ token: String(config?.token || ''), projectId, json: true }),
    body: JSON.stringify(payload),
  }, Number(options.timeoutMs || 180_000));

  if (result.done !== true || typeof result.message?.content !== 'string') {
    throw new Error('GPT Doug did not return a completed chat response.');
  }
  return result;
}

function cleanRelativePath(value) {
  const path = String(value || '').trim();
  if (!path || path.length > 240 || /[\u0000-\u001f\u007f]/.test(path) || path.includes('\\')) {
    throw new Error('GPT Doug returned an invalid file path.');
  }
  if (path.startsWith('/') || /^[A-Za-z]:/.test(path)) {
    throw new Error('GPT Doug returned an absolute file path.');
  }
  const parts = path.split('/');
  if (parts.some(part => !part || part === '.' || part === '..')) {
    throw new Error('GPT Doug returned an unsafe file path.');
  }
  if (parts[0] === '.grim') throw new Error('GPT Doug returned a reserved file path.');
  return path;
}

export function parseAgentResult(text) {
  const cleaned = String(text || '').trim()
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/, '');

  let value;
  try {
    value = JSON.parse(cleaned);
  } catch {
    throw new Error('GPT Doug returned invalid agent JSON.');
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('GPT Doug agent response must be a JSON object.');
  }

  const operations = Array.isArray(value.operations) ? value.operations : [];
  if (operations.length > MAX_OPERATIONS) throw new Error('GPT Doug returned too many file operations.');

  const normalized = operations.map(operation => {
    if (!operation || typeof operation !== 'object' || !['write_file', 'delete_file'].includes(operation.op)) {
      throw new Error('GPT Doug returned an unsupported file operation.');
    }
    const path = cleanRelativePath(operation.path);
    if (operation.op === 'delete_file') return { op: 'delete_file', path };
    if (typeof operation.content !== 'string') throw new Error(`GPT Doug returned invalid content for ${path}.`);
    if (new TextEncoder().encode(operation.content).length > MAX_FILE_BYTES) {
      throw new Error(`GPT Doug file is too large: ${path}`);
    }
    return { op: 'write_file', path, content: operation.content };
  });

  return {
    message: typeof value.message === 'string' && value.message.trim() ? value.message.trim() : 'Complete.',
    operations: normalized,
  };
}

export function createAgentMessages({ prompt, mode = 'build', files = [] }) {
  const request = String(prompt || '').trim();
  if (!request) throw new Error('Agent prompt is required.');
  if (request.length > 5_000) throw new Error('Agent prompt is too long.');
  if (!['build', 'fix', 'plan', 'explain'].includes(mode)) throw new Error('Unsupported agent mode.');

  const system = [
    "You are GrimTheBuilder's GPT Doug coding agent.",
    `Mode: ${mode}.`,
    'Return ONLY one JSON object with this exact shape:',
    '{"message":"brief result","operations":[{"op":"write_file","path":"relative/path","content":"complete file"},{"op":"delete_file","path":"relative/path"}]}',
    'Never use absolute paths, backslashes, .. path segments, or the reserved .grim directory.',
    'Use complete file contents, not patches.',
    mode === 'plan' || mode === 'explain'
      ? 'Do not modify files. Return operations as an empty array.'
      : 'Implement the request directly in the project files.',
  ].join('\n');

  let remaining = 15_000;
  const context = [];
  for (const file of Array.isArray(files) ? files.slice(0, 40) : []) {
    if (remaining <= 0) break;
    const path = String(file?.path || '').slice(0, 240);
    const content = String(file?.content || '');
    const prefix = `FILE:${path}\n`;
    const body = content.slice(0, Math.max(0, Math.min(4_000, remaining - prefix.length)));
    const block = `${prefix}${body}`;
    if (block.length > remaining) break;
    context.push(block);
    remaining -= block.length + 2;
  }

  return [
    { role: 'system', content: system },
    { role: 'user', content: `REQUEST:\n${request}\n\nPROJECT FILES:\n${context.join('\n\n') || '(no readable files)'}` },
  ];
}
