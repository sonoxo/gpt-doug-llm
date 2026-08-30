import Fastify from 'fastify';
import { config } from './config.js';
import { FfmpegCamera } from './camera/ffmpeg.js';
import { CocoDogDetector } from './vision/coco.js';
import { BathroomEventScorer } from './logic/poopScore.js';
import { createAlerter, type AlarmEvent } from './alerts/index.js';

const detector = new CocoDogDetector();
await detector.load();

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

async function sendAlarm(event: AlarmEvent): Promise<boolean> {
  const now = Date.now();
  if (event.type !== 'manual-test' && now - lastAlertAt < config.alertCooldownMs) return false;
  await alerter.fire(event);
  lastAlertAt = now;
  return true;
}

const camera = new FfmpegCamera(
  config.ffmpegPath,
  config.cameraUrl,
  config.frameFps,
  config.frameWidth,
);

camera.start(async (jpeg, capturedAt) => {
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
});

const app = Fastify({ logger: false });

app.get('/health', async () => ({
  ok: true,
  camera: config.cameraName,
  frames,
  lastFrameAt: lastFrameAt ? new Date(lastFrameAt).toISOString() : null,
}));

app.get('/status', async () => ({
  camera: config.cameraName,
  frames,
  dogConfidence: lastDogScore,
  bathroomScore: lastBathroomScore,
  heldMs: lastHeldMs,
  reasons: lastReasons,
  lastAlertAt: lastAlertAt ? new Date(lastAlertAt).toISOString() : null,
  cooldownRemainingMs: Math.max(0, config.alertCooldownMs - (Date.now() - lastAlertAt)),
}));

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
console.log(`[watch-dog] watching ${config.cameraName}; alert mode=${config.alertMode}`);

let shuttingDown = false;
async function shutdown(signal: string) {
  if (shuttingDown) return;
  shuttingDown = true;
  console.log(`[watch-dog] ${signal}: shutting down`);
  camera.stop();
  await app.close().catch(() => undefined);
  await alerter.close().catch(() => undefined);
  process.exit(0);
}

process.on('SIGINT', () => void shutdown('SIGINT'));
process.on('SIGTERM', () => void shutdown('SIGTERM'));
