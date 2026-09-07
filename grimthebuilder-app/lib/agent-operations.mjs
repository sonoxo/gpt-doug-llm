const DEFAULT_MAX_OPERATIONS = 80;
const DEFAULT_MAX_PATH_CHARS = 500;
const DEFAULT_MAX_FILE_BYTES = 2_000_000;
const DEFAULT_MAX_TOTAL_BYTES = 3_500_000;

function badRequest(message, status = 400) {
  return Object.assign(new Error(message), { status });
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

export function normalizeAgentPath(value, { maxPathChars = DEFAULT_MAX_PATH_CHARS } = {}) {
  if (typeof value !== 'string') throw badRequest('operation path must be a string');
  const raw = value.trim().replaceAll('\\', '/');
  if (!raw) throw badRequest('operation path is required');
  if (raw.length > maxPathChars) throw badRequest('operation path is too long');
  if (raw.includes('\0')) throw badRequest('operation path contains an invalid character');
  if (raw.startsWith('/') || /^[A-Za-z]:\//.test(raw)) {
    throw badRequest('absolute operation paths are not allowed');
  }

  const parts = raw.split('/').filter(Boolean);
  if (!parts.length || parts.some(part => part === '.' || part === '..')) {
    throw badRequest('operation path traversal is not allowed');
  }
  if (parts[0] === '.grim') throw badRequest('reserved operation path');
  return parts.join('/');
}

export function normalizeAgentOperations(rawOperations, options = {}) {
  const maxOperations = Number(options.maxOperations ?? DEFAULT_MAX_OPERATIONS);
  const maxFileBytes = Number(options.maxFileBytes ?? DEFAULT_MAX_FILE_BYTES);
  const maxTotalBytes = Number(options.maxTotalBytes ?? DEFAULT_MAX_TOTAL_BYTES);

  if (!Array.isArray(rawOperations)) throw badRequest('operations must be an array');
  if (rawOperations.length > maxOperations) {
    throw badRequest(`too many operations; maximum is ${maxOperations}`, 413);
  }

  let totalBytes = 0;
  return rawOperations.map((raw, index) => {
    if (!isPlainObject(raw)) throw badRequest(`operation ${index + 1} must be an object`);
    const op = String(raw.op || '');
    const path = normalizeAgentPath(raw.path, options);

    if (op === 'write_file') {
      if (typeof raw.content !== 'string') {
        throw badRequest(`write_file operation ${index + 1} requires string content`);
      }
      const bytes = Buffer.byteLength(raw.content, 'utf8');
      if (bytes > maxFileBytes) throw badRequest(`operation ${index + 1} file is too large`, 413);
      totalBytes += bytes;
      if (totalBytes > maxTotalBytes) throw badRequest('agent operation payload is too large', 413);
      return { op, path, content: raw.content };
    }

    if (op === 'delete_file') return { op, path };
    throw badRequest(`unsupported operation ${index + 1}: ${op || '(missing)'}`);
  });
}
