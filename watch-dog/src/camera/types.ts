export type FrameHandler = (jpeg: Buffer, capturedAt: number) => Promise<void> | void;

export interface FrameSource {
  start(onFrame: FrameHandler): void | Promise<void>;
  stop(): void | Promise<void>;
}
