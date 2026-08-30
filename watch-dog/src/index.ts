import Fastify from 'fastify';
import { config } from './config.js';
import { FfmpegCamera } from './camera/ffmpeg.js';
import { OsaioEventCamera } from './camera/osaio.js';
import type { FrameSource } from './camera/types.js';
import { CocoDogDetector } from './vision/coco.js';
import { BathroomEventScorer } from './logic/poopScore.js';
import { createAlerter, type AlarmEvent } from './alerts/index.js';

const detector = new CocoDogDetector();
console.log('[watch-dog] loading local dog detector...');
await detector.load();
console.log('[watch-dog] detector ready');

const scorer = new BathroomEventScorer(
  config.floorZone,
  config.eventHoldMs,
  config.eventThreshold,
);

const alerter = await createAlerter({
  mode: config.alertMode,
  webhookUrl: config.alertWebhookUrl,
  webhookToken: config.alertWebhookToken,
  mqttUrl: config.mqttUrl,
  mqttTopic: config.mqttTopic,
  mqttUsername: config.mqttUsername,
  mqttPassword: config.mqttPassword,
});

let lastAlertAt = 0;
let lastFrameAt = 0;
let lastDogScore = 0;
let lastBathroomScore = 0;
let lastReasons: string[] = [];
let lastHeldMs = 0;
let frames = 0;
let sourceError: string | null = null;

async function sendAlarm(event: AlarmEvent): Promise<boolean> {
  const now = Date.now();
  if (event.type !== 'manual-test' && now - lastAlertAt < config.alertCooldownMs) return false;
  await alerter.fire(event);
  lastAlertAt = now;
  return true;
}

async function processFrame(jpeg: Buffer, capturedAt: number): Promise<void> {
  frames += 1;
  lastFrameAt = capturedAt;

  const dog = await detector.detect(jpeg, config.dogConfidence);
  const state = scorer.update(dog, capturedAt);
  lastDogScore = dog?.score ?? 0;
  lastBathroomScore = state.score;
  lastReasons = state.reason;
  lastHeldMs = state.heldMs;

  if (config.logFrames) {
    console.log(
      `[watch] dog=${lastDogScore.toFixed(2)} bathroom=${state.score.toFixed(2)} held=${state.heldMs}ms ${state.reason.join(',')}`,
    );
  }

  if (state.suspected) {
    await sendAlarm({
      type: 'suspected-dog-bathroom-event',
      camera: config.cameraName,
      score: state.score,
      heldMs: state.heldMs,
      reasons: state.reason,
      timestamp: new Date(capturedAt).toISOString(),
    });
  }
}

let camera: FrameSource;
if (config.cameraSource === 'osaio') {
  camera = new OsaioEventCamera(config.osaio);
} else {
  camera = new FfmpegCamera(
    config.ffmpegPath,
    config.cameraUrl,
    config.frameFps,
    config.frameWidth,
  );
}

try {
  await camera.start(processFrame);
  sourceError = null;
} catch (error) {
  sourceError = error instanceof Error ? error.message : String(error);
  console.error(`[watch-dog] source startup failed: ${sourceError}`);
}

const app = Fastify({ logger: false, bodyLimit: 12 * 1024 * 1024 });
app.addContentTypeParser('image/jpeg', { parseAs: 'buffer' }, (_request, body, done) => {
  done(null, body);
});

app.get('/health', async (_request, reply) => {
  const ok = !sourceError;
  return reply.code(ok ? 200 : 503).send({
    ok,
    source: config.cameraSource,
    sourceError,
    camera: config.cameraName,
    frames,
    lastFrameAt: lastFrameAt ? new Date(lastFrameAt).toISOString() : null,
  });
});

app.get('/status', async () => ({
  source: config.cameraSource,
  sourceError,
  camera: config.cameraName,
  frames,
  dogConfidence: lastDogScore,
  bathroomScore: lastBathroomScore,
  heldMs: lastHeldMs,
  reasons: lastReasons,
  lastAlertAt: lastAlertAt ? new Date(lastAlertAt).toISOString() : null,
  cooldownRemainingMs: Math.max(0, config.alertCooldownMs - (Date.now() - lastAlertAt)),
}));

app.post('/frame', async (request, reply) => {
  const body = request.body;
  if (!Buffer.isBuffer(body) || body.length < 4) {
    return reply.code(400).send({ ok: false, error: 'POST a JPEG with Content-Type: image/jpeg' });
  }
  await processFrame(body, Date.now());
  return { ok: true, frames };
});

app.post('/alarm/test', async () => {
  await sendAlarm({
    type: 'manual-test',
    camera: config.cameraName,
    score: 1,
    heldMs: 0,
    reasons: ['manual-test'],
    timestamp: new Date().toISOString(),
  });
  return { ok: true };
});

await app.listen({ host: config.host, port: config.port });
console.log(`[watch-dog] API http://${config.host}:${config.port}`);
console.log(`[watch-dog] source=${config.cameraSource} camera=${config.cameraName} alert=${config.alertMode}`);
if (sourceError) {
  console.log('[watch-dog] API is up; fix source configuration, then restart to begin automatic detection.');
}

let shuttingDown = false;
async function shutdown(signal: string) {
  if (shuttingDown) return;
  shuttingDown = true;
  console.log(`[watch-dog] ${signal}: shutting down`);
  await camera.stop();
  await app.close().catch(() => undefined);
  await alerter.close().catch(() => undefined);
  process.exit(0);
}

process.on('SIGINT', () => void shutdown('SIGINT'));
process.on('SIGTERM', () => void shutdown('SIGTERM'));
