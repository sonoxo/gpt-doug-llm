import type { DogDetection } from '../vision/coco.js';

export type BathroomState = {
  score: number;
  suspected: boolean;
  inFloorZone: boolean;
  lowMotion: boolean;
  heldMs: number;
  reason: string[];
};

type Track = {
  centerX: number;
  centerY: number;
  width: number;
  height: number;
  firstStableAt: number;
  lastAt: number;
};

export class BathroomEventScorer {
  private track?: Track;

  constructor(
    private readonly floorZone: readonly [number, number, number, number],
    private readonly holdMs: number,
    private readonly threshold: number,
  ) {}

  update(detection: DogDetection | null, now = Date.now()): BathroomState {
    if (!detection) {
      this.track = undefined;
      return {
        score: 0,
        suspected: false,
        inFloorZone: false,
        lowMotion: false,
        heldMs: 0,
        reason: ['no-dog'],
      };
    }

    const [x, y, w, h] = detection.box;
    const cx = (x + w / 2) / detection.frameWidth;
    const cy = (y + h / 2) / detection.frameHeight;
    const nw = w / detection.frameWidth;
    const nh = h / detection.frameHeight;
    const bottom = (y + h) / detection.frameHeight;
    const aspect = w / Math.max(h, 1);
    const [zx1, zy1, zx2, zy2] = this.floorZone;
    const inFloorZone = cx >= zx1 && cx <= zx2 && bottom >= zy1 && bottom <= zy2;

    let lowMotion = false;
    let heldMs = 0;
    let firstStableAt = now;

    if (this.track) {
      const dx = cx - this.track.centerX;
      const dy = cy - this.track.centerY;
      const sizeDelta = Math.abs(nw - this.track.width) + Math.abs(nh - this.track.height);
      const motion = Math.hypot(dx, dy) + sizeDelta * 0.5;
      lowMotion = motion < 0.045;
      firstStableAt = lowMotion ? this.track.firstStableAt : now;
      heldMs = lowMotion ? now - firstStableAt : 0;
    }

    this.track = {
      centerX: cx,
      centerY: cy,
      width: nw,
      height: nh,
      firstStableAt,
      lastAt: now,
    };

    const confidenceScore = Math.min(1, detection.score);
    const floorScore = inFloorZone ? 1 : 0;
    const stillScore = lowMotion ? 1 : 0;
    const holdScore = Math.min(1, heldMs / this.holdMs);

    // Generic dog detectors do not understand defecation. This posture component is deliberately
    // weak: a compact/hunched box can contribute evidence, but cannot trigger by itself.
    const postureScore = aspect >= 0.75 && aspect <= 2.6 && cy >= 0.45 ? 1 : 0.25;

    const score =
      confidenceScore * 0.15 +
      floorScore * 0.25 +
      stillScore * 0.20 +
      holdScore * 0.30 +
      postureScore * 0.10;

    const reason: string[] = [];
    if (inFloorZone) reason.push('floor-zone');
    if (lowMotion) reason.push('low-motion');
    if (heldMs >= this.holdMs) reason.push('held-posture');
    if (postureScore === 1) reason.push('compact-posture');

    return {
      score,
      suspected: inFloorZone && heldMs >= this.holdMs && score >= this.threshold,
      inFloorZone,
      lowMotion,
      heldMs,
      reason,
    };
  }
}
