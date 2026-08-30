import { spawn } from 'node:child_process';
import { readFile, unlink } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import type { FrameHandler, FrameSource } from './types.js';

export type MacScreenOptions = {
  pollMs: number;
  region?: string;
};

export class MacScreenCamera implements FrameSource {
  private stopped = false;
  private timer?: NodeJS.Timeout;
  private busy = false;

  constructor(private readonly options: MacScreenOptions) {}

  async start(onFrame: FrameHandler): Promise<void> {
    if (process.platform !== 'darwin') {
      throw new Error('macos-screen source requires macOS');
    }
    this.stopped = false;

    const tick = async () => {
      if (this.stopped) return;
      if (!this.busy) {
        this.busy = true;
        try {
          const jpeg = await this.capture();
          await onFrame(jpeg, Date.now());
        } catch (error) {
          console.error('[macos-screen] capture failed', error);
        } finally {
          this.busy = false;
        }
      }
      if (!this.stopped) this.timer = setTimeout(() => void tick(), this.options.pollMs);
    };

    void tick();
  }

  stop(): void {
    this.stopped = true;
    if (this.timer) clearTimeout(this.timer);
    this.timer = undefined;
  }

  private async capture(): Promise<Buffer> {
    const file = path.join(os.tmpdir(), `watch-dog-${randomUUID()}.jpg`);
    const args = ['-x', '-t', 'jpg'];
    if (this.options.region?.trim()) args.push('-R', this.options.region.trim());
    args.push(file);

    try {
      await new Promise<void>((resolve, reject) => {
        const child = spawn('/usr/sbin/screencapture', args, { stdio: ['ignore', 'ignore', 'pipe'] });
        let stderr = '';
        child.stderr.on('data', (chunk: Buffer) => { stderr += chunk.toString(); });
        child.once('error', reject);
        child.once('exit', (code) => {
          if (code === 0) resolve();
          else reject(new Error(`screencapture exited ${code ?? 'null'}${stderr.trim() ? `: ${stderr.trim()}` : ''}`));
        });
      });
      return await readFile(file);
    } finally {
      await unlink(file).catch(() => undefined);
    }
  }
}
