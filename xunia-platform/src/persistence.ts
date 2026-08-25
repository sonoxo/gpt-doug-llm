import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import path from 'node:path';

export class JsonState<T> {
  readonly file?: string;
  private memory: T | null = null;
  private lastError = '';

  constructor(file?: string) {
    this.file = file ? path.resolve(file) : undefined;
  }

  read(fallback: T): T {
    if (!this.file) return this.memory ?? fallback;
    try {
      if (!existsSync(this.file)) return fallback;
      return JSON.parse(readFileSync(this.file, 'utf8')) as T;
    } catch (error) {
      this.lastError = error instanceof Error ? error.message : 'state_read_failed';
      return fallback;
    }
  }

  write(value: T): void {
    this.memory = value;
    if (!this.file) return;
    try {
      const dir = path.dirname(this.file);
      mkdirSync(dir, { recursive: true, mode: 0o750 });
      const tmp = `${this.file}.${process.pid}.tmp`;
      writeFileSync(tmp, `${JSON.stringify(value, null, 2)}\n`, { encoding: 'utf8', mode: 0o640 });
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
      ok: !this.lastError,
      error: this.lastError || null
    };
  }
}
