import { createCipheriv, createDecipheriv, randomBytes } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import path from 'node:path';

type EncryptedEnvelope = {
  _xunia: 'encrypted-state-v1';
  alg: 'aes-256-gcm';
  iv: string;
  tag: string;
  data: string;
};

function parseKey(raw: string) {
  if (!raw.trim()) return undefined;
  const key = Buffer.from(raw.trim(), 'base64');
  if (key.length !== 32) throw new Error('state_encryption_key_must_be_base64_32_bytes');
  return key;
}

function isEnvelope(value: unknown): value is EncryptedEnvelope {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<EncryptedEnvelope>;
  return candidate._xunia === 'encrypted-state-v1'
    && candidate.alg === 'aes-256-gcm'
    && typeof candidate.iv === 'string'
    && typeof candidate.tag === 'string'
    && typeof candidate.data === 'string';
}

export class JsonState<T> {
  readonly file?: string;
  private memory: T | null = null;
  private lastError = '';
  private encryptionKey?: Buffer;
  private writeBlocked = false;

  constructor(file?: string, encryptionKey = process.env.XUNIA_STATE_ENCRYPTION_KEY ?? '') {
    this.file = file ? path.resolve(file) : undefined;
    try {
      this.encryptionKey = parseKey(encryptionKey);
    } catch (error) {
      this.lastError = error instanceof Error ? error.message : 'state_encryption_key_invalid';
      this.writeBlocked = true;
    }
  }

  private decrypt(envelope: EncryptedEnvelope): T {
    if (!this.encryptionKey) throw new Error('state_encryption_key_required');
    const decipher = createDecipheriv('aes-256-gcm', this.encryptionKey, Buffer.from(envelope.iv, 'base64'));
    decipher.setAuthTag(Buffer.from(envelope.tag, 'base64'));
    const plaintext = Buffer.concat([
      decipher.update(Buffer.from(envelope.data, 'base64')),
      decipher.final()
    ]).toString('utf8');
    return JSON.parse(plaintext) as T;
  }

  private encrypt(value: T): EncryptedEnvelope {
    if (!this.encryptionKey) throw new Error('state_encryption_key_required');
    const iv = randomBytes(12);
    const cipher = createCipheriv('aes-256-gcm', this.encryptionKey, iv);
    const encrypted = Buffer.concat([
      cipher.update(JSON.stringify(value), 'utf8'),
      cipher.final()
    ]);
    return {
      _xunia: 'encrypted-state-v1',
      alg: 'aes-256-gcm',
      iv: iv.toString('base64'),
      tag: cipher.getAuthTag().toString('base64'),
      data: encrypted.toString('base64')
    };
  }

  read(fallback: T): T {
    if (!this.file) return this.memory ?? fallback;
    try {
      if (!existsSync(this.file)) return fallback;
      const parsed = JSON.parse(readFileSync(this.file, 'utf8')) as unknown;
      const value = isEnvelope(parsed) ? this.decrypt(parsed) : parsed as T;
      this.lastError = '';
      this.writeBlocked = false;
      return value;
    } catch (error) {
      this.lastError = error instanceof Error ? error.message : 'state_read_failed';
      this.writeBlocked = true;
      return fallback;
    }
  }

  write(value: T): void {
    this.memory = value;
    if (!this.file) return;
    if (this.writeBlocked) throw new Error(`state_write_blocked:${this.lastError || 'previous_read_error'}`);
    try {
      const dir = path.dirname(this.file);
      mkdirSync(dir, { recursive: true, mode: 0o750 });
      const tmp = `${this.file}.${process.pid}.tmp`;
      const stored = this.encryptionKey ? this.encrypt(value) : value;
      writeFileSync(tmp, `${JSON.stringify(stored, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 });
      renameSync(tmp, this.file);
      this.lastError = '';
    } catch (error) {
      this.lastError = error instanceof Error ? error.message : 'state_write_failed';
      throw error;
    }
  }

  status() {
    return {
      mode: this.file ? 'file' : 'memory',
      file: this.file ?? null,
      encrypted: Boolean(this.encryptionKey),
      algorithm: this.encryptionKey ? 'aes-256-gcm' : null,
      ok: !this.lastError && !this.writeBlocked,
      error: this.lastError || null
    };
  }
}
