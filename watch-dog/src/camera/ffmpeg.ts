import { spawn, type ChildProcess } from 'node:child_process';
import type { FrameHandler, FrameSource } from './types.js';

export class FfmpegCamera implements FrameSource {
  private process?: ChildProcess;
  private stopped = false;

  constructor(
    private readonly ffmpegPath: string,
    private readonly cameraUrl: string,
    private readonly fps: number,
    private readonly width: number,
  ) {}

  start(onFrame: FrameHandler): void {
    if (this.process) throw new Error('Camera already started');
    if (!this.cameraUrl) throw new Error('CAMERA_URL is required for rtsp source');
    this.stopped = false;

    const args = [
      '-hide_banner',
      '-loglevel', 'warning',
      '-rtsp_transport', 'tcp',
      '-i', this.cameraUrl,
      '-an',
      '-vf', `fps=${this.fps},scale=${this.width}:-2`,
      '-f', 'image2pipe',
      '-vcodec', 'mjpeg',
      'pipe:1',
    ];

    const child = spawn(this.ffmpegPath, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    this.process = child;

    let buffer = Buffer.alloc(0);
    let busy = false;
    let pending: Buffer | undefined;

    const dispatch = async (frame: Buffer) => {
      if (busy) {
        pending = frame;
        return;
      }
      busy = true;
      try {
        await onFrame(frame, Date.now());
      } catch (error) {
        console.error('[camera] frame handler error', error);
      } finally {
        busy = false;
        if (pending) {
          const latest = pending;
          pending = undefined;
          void dispatch(latest);
        }
      }
    };

    child.stdout?.on('data', (chunk: Buffer) => {
      buffer = Buffer.concat([buffer, chunk]);
      while (true) {
        const start = buffer.indexOf(Buffer.from([0xff, 0xd8]));
        if (start < 0) {
          if (buffer.length > 2_000_000) buffer = Buffer.alloc(0);
          break;
        }
        const end = buffer.indexOf(Buffer.from([0xff, 0xd9]), start + 2);
        if (end < 0) {
          if (start > 0) buffer = buffer.subarray(start);
          break;
        }
        const frame = buffer.subarray(start, end + 2);
        buffer = buffer.subarray(end + 2);
        void dispatch(frame);
      }
    });

    child.stderr?.on('data', (chunk: Buffer) => {
      const msg = chunk.toString().trim();
      if (msg) console.warn('[ffmpeg]', msg);
    });

    child.once('exit', (code, signal) => {
      this.process = undefined;
      if (!this.stopped) {
        console.error(`[camera] ffmpeg exited code=${code ?? 'null'} signal=${signal ?? 'null'}`);
      }
    });
  }

  stop(): void {
    this.stopped = true;
    this.process?.kill('SIGTERM');
    this.process = undefined;
  }
}
