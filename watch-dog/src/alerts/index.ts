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
  mode: 'console' | 'webhook' | 'mqtt';
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

export async function createAlerter(config: AlertConfig): Promise<Alerter> {
  if (config.mode === 'console') {
    return {
      async fire(event) {
        console.error('\n🚨 WATCH DOG ALARM 🚨', JSON.stringify(event, null, 2));
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
