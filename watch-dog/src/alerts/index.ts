import { spawn } from 'node:child_process';
import mqtt from 'mqtt';

export type AlarmEvent = {
  type: 'suspected-dog-bathroom-event' | 'manual-test';
  camera: string;
  score: number;
  heldMs: number;
  reasons: string[];
  timestamp: string;
};

export type AlertConfig = {
  mode: 'console' | 'webhook' | 'mqtt' | 'macos';
  webhookUrl?: string;
  webhookToken?: string;
  mqttUrl: string;
  mqttTopic: string;
  mqttUsername?: string;
  mqttPassword?: string;
};

export interface Alerter {
  fire(event: AlarmEvent): Promise<void>;
  close(): Promise<void>;
}

function consoleAlarm(event: AlarmEvent): void {
  process.stderr.write('\u0007');
  console.error('\n🚨 WATCH DOG ALARM 🚨', JSON.stringify(event, null, 2));
}

async function runMacCommand(command: string, args: string[], label: string): Promise<boolean> {
  if (process.platform !== 'darwin') return false;

  return await new Promise<boolean>((resolve) => {
    const child = spawn(command, args, { stdio: ['ignore', 'ignore', 'pipe'] });
    let stderr = '';

    child.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString();
    });

    const timer = setTimeout(() => {
      child.kill('SIGTERM');
      console.error(`[alarm] ${label} timed out`);
      resolve(false);
    }, 10_000);

    child.once('error', (error) => {
      clearTimeout(timer);
      console.error(`[alarm] ${label} failed: ${error.message}`);
      resolve(false);
    });

    child.once('exit', (code) => {
      clearTimeout(timer);
      if (code === 0) {
        resolve(true);
      } else {
        console.error(`[alarm] ${label} exited ${code ?? 'null'}${stderr.trim() ? `: ${stderr.trim()}` : ''}`);
        resolve(false);
      }
    });
  });
}

async function audibleAlarmOnMac(message: string): Promise<void> {
  if (process.platform !== 'darwin') {
    console.error('[alarm] macOS audible mode requested on a non-macOS host');
    return;
  }

  const soundPaths = [
    '/System/Library/Sounds/Sosumi.aiff',
    '/System/Library/Sounds/Glass.aiff',
    '/System/Library/Sounds/Ping.aiff',
  ];

  let soundPlayed = false;
  for (const path of soundPaths) {
    soundPlayed = await runMacCommand('/usr/bin/afplay', [path], `afplay ${path}`);
    if (soundPlayed) break;
  }

  const spoke = await runMacCommand('/usr/bin/say', ['-r', '235', message], 'say');

  if (!soundPlayed && !spoke) {
    console.error('[alarm] WARNING: macOS audible alarm could not produce sound; check output device and mute/volume settings');
  } else {
    console.error(`[alarm] macOS audible result sound=${soundPlayed ? 'ok' : 'failed'} speech=${spoke ? 'ok' : 'failed'}`);
  }
}

export async function createAlerter(config: AlertConfig): Promise<Alerter> {
  if (config.mode === 'console') {
    return {
      async fire(event) {
        consoleAlarm(event);
      },
      async close() {},
    };
  }

  if (config.mode === 'macos') {
    return {
      async fire(event) {
        consoleAlarm(event);
        await audibleAlarmOnMac(
          event.type === 'manual-test'
            ? 'Watch Dog alarm test. Audio alarm is working.'
            : 'Watch Dog alarm. Dog bathroom behavior detected in the living room.',
        );
      },
      async close() {},
    };
  }

  if (config.mode === 'webhook') {
    if (!config.webhookUrl) throw new Error('ALERT_WEBHOOK_URL is required for webhook mode');
    return {
      async fire(event) {
        const response = await fetch(config.webhookUrl!, {
          method: 'POST',
          headers: {
            'content-type': 'application/json',
            ...(config.webhookToken ? { authorization: `Bearer ${config.webhookToken}` } : {}),
          },
          body: JSON.stringify(event),
          signal: AbortSignal.timeout(5000),
        });
        if (!response.ok) throw new Error(`Alarm webhook failed: HTTP ${response.status}`);
      },
      async close() {},
    };
  }

  const client = mqtt.connect(config.mqttUrl, {
    username: config.mqttUsername,
    password: config.mqttPassword,
    reconnectPeriod: 2000,
  });

  await new Promise<void>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('MQTT connect timeout')), 7000);
    client.once('connect', () => {
      clearTimeout(timer);
      resolve();
    });
    client.once('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
  });

  return {
    async fire(event) {
      await new Promise<void>((resolve, reject) => {
        client.publish(config.mqttTopic, JSON.stringify(event), { qos: 1 }, (error) => {
          if (error) reject(error);
          else resolve();
        });
      });
    },
    async close() {
      await new Promise<void>((resolve) => client.end(false, {}, () => resolve()));
    },
  };
}
