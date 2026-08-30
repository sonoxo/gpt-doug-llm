import 'dotenv/config';
import { z } from 'zod';

const boolish = z.string().optional();

const schema = z.object({
  CAMERA_URL: z.string().min(1),
  CAMERA_NAME: z.string().default('living-room'),
  FFMPEG_PATH: z.string().default('ffmpeg'),
  FRAME_FPS: z.coerce.number().min(0.2).max(10).default(2),
  FRAME_WIDTH: z.coerce.number().int().min(320).max(1920).default(640),
  DOG_CONFIDENCE: z.coerce.number().min(0).max(1).default(0.55),
  EVENT_THRESHOLD: z.coerce.number().min(0).max(1).default(0.72),
  EVENT_HOLD_MS: z.coerce.number().int().min(500).max(30000).default(3000),
  ALERT_COOLDOWN_MS: z.coerce.number().int().min(1000).default(60000),
  FLOOR_ZONE: z.string().default('0,0.30,1,1'),
  ALERT_MODE: z.enum(['console', 'webhook', 'mqtt']).default('console'),
  ALERT_WEBHOOK_URL: z.string().url().optional().or(z.literal('')),
  ALERT_WEBHOOK_TOKEN: z.string().optional(),
  MQTT_URL: z.string().default('mqtt://127.0.0.1:1883'),
  MQTT_TOPIC: z.string().default('home/living-room/dog-poop-alarm'),
  MQTT_USERNAME: z.string().optional(),
  MQTT_PASSWORD: z.string().optional(),
  HOST: z.string().default('127.0.0.1'),
  PORT: z.coerce.number().int().min(1).max(65535).default(8787),
  LOG_FRAMES: boolish,
});

const raw = schema.parse(process.env);

function parseZone(value: string): [number, number, number, number] {
  const parts = value.split(',').map(Number);
  if (parts.length !== 4 || parts.some((n) => !Number.isFinite(n) || n < 0 || n > 1)) {
    throw new Error('FLOOR_ZONE must be normalized x1,y1,x2,y2 values between 0 and 1');
  }
  const [x1, y1, x2, y2] = parts as [number, number, number, number];
  if (x1 >= x2 || y1 >= y2) throw new Error('FLOOR_ZONE requires x1<x2 and y1<y2');
  return [x1, y1, x2, y2];
}

export const config = {
  cameraUrl: raw.CAMERA_URL,
  cameraName: raw.CAMERA_NAME,
  ffmpegPath: raw.FFMPEG_PATH,
  frameFps: raw.FRAME_FPS,
  frameWidth: raw.FRAME_WIDTH,
  dogConfidence: raw.DOG_CONFIDENCE,
  eventThreshold: raw.EVENT_THRESHOLD,
  eventHoldMs: raw.EVENT_HOLD_MS,
  alertCooldownMs: raw.ALERT_COOLDOWN_MS,
  floorZone: parseZone(raw.FLOOR_ZONE),
  alertMode: raw.ALERT_MODE,
  alertWebhookUrl: raw.ALERT_WEBHOOK_URL || undefined,
  alertWebhookToken: raw.ALERT_WEBHOOK_TOKEN,
  mqttUrl: raw.MQTT_URL,
  mqttTopic: raw.MQTT_TOPIC,
  mqttUsername: raw.MQTT_USERNAME,
  mqttPassword: raw.MQTT_PASSWORD,
  host: raw.HOST,
  port: raw.PORT,
  logFrames: raw.LOG_FRAMES === '1' || raw.LOG_FRAMES === 'true',
} as const;
