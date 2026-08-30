import 'dotenv/config';
import { z } from 'zod';

const boolish = z.string().optional();

const schema = z.object({
  CAMERA_SOURCE: z.enum(['rtsp', 'osaio']).default('osaio'),
  CAMERA_URL: z.string().optional().default(''),
  CAMERA_NAME: z.string().default('Living Room'),
  FFMPEG_PATH: z.string().default('ffmpeg'),
  FRAME_FPS: z.coerce.number().min(0.2).max(10).default(2),
  FRAME_WIDTH: z.coerce.number().int().min(320).max(1920).default(640),
  DOG_CONFIDENCE: z.coerce.number().min(0).max(1).default(0.55),
  EVENT_THRESHOLD: z.coerce.number().min(0).max(1).default(0.72),
  EVENT_HOLD_MS: z.coerce.number().int().min(500).max(30000).default(3000),
  ALERT_COOLDOWN_MS: z.coerce.number().int().min(1000).default(60000),
  FLOOR_ZONE: z.string().default('0.18,0.40,0.98,1'),
  ALERT_MODE: z.enum(['console', 'webhook', 'mqtt', 'macos']).default('macos'),
  ALERT_WEBHOOK_URL: z.string().url().optional().or(z.literal('')),
  ALERT_WEBHOOK_TOKEN: z.string().optional(),
  MQTT_URL: z.string().default('mqtt://127.0.0.1:1883'),
  MQTT_TOPIC: z.string().default('home/living-room/dog-poop-alarm'),
  MQTT_USERNAME: z.string().optional(),
  MQTT_PASSWORD: z.string().optional(),
  OSAIO_EMAIL: z.string().email().optional(),
  OSAIO_PASSWORD: z.string().optional(),
  OSAIO_SECRET: z.string().optional().default(''),
  OSAIO_DEVICE_NAME: z.string().default('Living Room'),
  OSAIO_UUID: z.string().optional(),
  OSAIO_BASE_URL: z.string().url().optional(),
  OSAIO_UID: z.string().optional(),
  OSAIO_API_TOKEN: z.string().optional(),
  OSAIO_PHONE_CODE: z.string().optional(),
  OSAIO_POLL_MS: z.coerce.number().int().min(1000).max(60000).default(2000),
  OSAIO_TIMEZONE: z.string().default('America/New_York'),
  OSAIO_ZONE: z.coerce.number().min(-14).max(14).default(-4),
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
  cameraSource: raw.CAMERA_SOURCE,
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
  osaio: {
    email: raw.OSAIO_EMAIL,
    password: raw.OSAIO_PASSWORD,
    secret: raw.OSAIO_SECRET,
    deviceName: raw.OSAIO_DEVICE_NAME,
    uuid: raw.OSAIO_UUID,
    baseUrl: raw.OSAIO_BASE_URL,
    uid: raw.OSAIO_UID,
    apiToken: raw.OSAIO_API_TOKEN,
    phoneCode: raw.OSAIO_PHONE_CODE,
    pollMs: raw.OSAIO_POLL_MS,
    timeZone: raw.OSAIO_TIMEZONE,
    zone: raw.OSAIO_ZONE,
  },
  host: raw.HOST,
  port: raw.PORT,
  logFrames: raw.LOG_FRAMES === '1' || raw.LOG_FRAMES === 'true',
} as const;
