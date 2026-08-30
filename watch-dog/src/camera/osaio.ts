import { createHash, createHmac } from 'node:crypto';
import os from 'node:os';
import type { FrameHandler, FrameSource } from './types.js';

const APP_ID = '3dab98eee85b7ae8';
const GLOBAL_BASE_URL = 'https://global.osaio.net/v2';

type OsaioOptions = {
  email?: string;
  password?: string;
  secret: string;
  deviceName?: string;
  uuid?: string;
  baseUrl?: string;
  uid?: string;
  apiToken?: string;
  phoneCode?: string;
  pollMs: number;
  timeZone: string;
  zone: number;
};

type AuthState = {
  baseUrl: string;
  uid: string;
  apiToken: string;
};

type OsaioEnvelope<T> = {
  code?: number;
  msg?: string;
  data?: T;
};

function joinUrl(base: string, path: string): string {
  return `${base.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
}

function dateForZone(timeZone: string): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date());
  const get = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? '';
  return `${get('year')}-${get('month')}-${get('day')}`;
}

export class OsaioEventCamera implements FrameSource {
  private stopped = false;
  private timer?: NodeJS.Timeout;
  private auth?: AuthState;
  private resolvedUuid?: string;
  private lastEventKey?: string;
  private running = false;

  constructor(private readonly options: OsaioOptions) {
    if (!options.secret) {
      throw new Error('OSAIO_SECRET is required for OSAIO cloud signing');
    }
  }

  async start(onFrame: FrameHandler): Promise<void> {
    if (this.running) throw new Error('OSAIO source already started');
    this.running = true;
    this.stopped = false;
    await this.ensureAuth();
    await this.resolveDevice();

    const tick = async () => {
      if (this.stopped) return;
      try {
        await this.pollLatestEvent(onFrame);
      } catch (error) {
        console.error('[osaio] poll failed', error);
      } finally {
        if (!this.stopped) this.timer = setTimeout(() => void tick(), this.options.pollMs);
      }
    };

    void tick();
  }

  stop(): void {
    this.stopped = true;
    this.running = false;
    if (this.timer) clearTimeout(this.timer);
    this.timer = undefined;
  }

  private signature(secret: string, timestamp: string, uid = '', apiToken = ''): string {
    const message = APP_ID + timestamp + uid + apiToken;
    const hex = createHmac('sha256', secret).update(message).digest('hex');
    return Buffer.from(hex, 'utf8').toString('base64');
  }

  private async request<T>(
    baseUrl: string,
    path: string,
    init: RequestInit & { query?: Record<string, string | number> } = {},
    auth?: Pick<AuthState, 'uid' | 'apiToken'>,
  ): Promise<OsaioEnvelope<T>> {
    const url = new URL(joinUrl(baseUrl, path));
    for (const [key, value] of Object.entries(init.query ?? {})) {
      url.searchParams.set(key, String(value));
    }

    const timestamp = Math.floor(Date.now() / 1000).toString();
    const uid = auth?.uid ?? '';
    const apiToken = auth?.apiToken ?? '';
    const headers = new Headers(init.headers);
    headers.set('User-Agent', 'OSAIO_ANDROID_4.4.0_657');
    headers.set('appid', APP_ID);
    headers.set('ApiSignType', uid && apiToken ? '2' : '1');
    headers.set('timestamp', timestamp);
    headers.set('sign', this.signature(this.options.secret, timestamp, uid, apiToken));
    headers.set('timeout', '10');
    if (uid && apiToken) {
      headers.set('uid', uid);
      headers.set('api-token', apiToken);
    }
    if (init.body && !headers.has('content-type')) headers.set('content-type', 'application/json');

    const response = await fetch(url, {
      ...init,
      headers,
      signal: AbortSignal.timeout(10_000),
    });
    if (!response.ok) throw new Error(`OSAIO HTTP ${response.status} ${response.statusText}`);
    return (await response.json()) as OsaioEnvelope<T>;
  }

  private async ensureAuth(force = false): Promise<void> {
    if (this.auth && !force) return;

    if (this.options.baseUrl && this.options.uid && this.options.apiToken) {
      this.auth = {
        baseUrl: this.options.baseUrl,
        uid: this.options.uid,
        apiToken: this.options.apiToken,
      };
      return;
    }

    if (!this.options.email || !this.options.password) {
      throw new Error(
        'OSAIO source requires either OSAIO_BASE_URL+OSAIO_UID+OSAIO_API_TOKEN or OSAIO_EMAIL+OSAIO_PASSWORD',
      );
    }

    const bootstrap = await this.request<{ web?: string }>(GLOBAL_BASE_URL, '/account/get-baseurl', {
      method: 'GET',
      query: { account: this.options.email, country: '1' },
    });
    const baseUrl = bootstrap.data?.web;
    if (!baseUrl) throw new Error(`OSAIO bootstrap failed: ${bootstrap.msg ?? bootstrap.code ?? 'no web URL'}`);

    const phoneCode =
      this.options.phoneCode ??
      createHash('md5').update(`${os.hostname()}:gpt-doug-watch-dog`).digest('hex');

    const login = await this.request<{ api_token?: string; uid?: string }>(baseUrl, '/login/login', {
      method: 'POST',
      body: JSON.stringify({
        account: this.options.email,
        country: '1',
        password: createHash('md5').update(this.options.password).digest('hex'),
        phone_brand: 'watch-dog',
        phone_code: phoneCode,
        timezone_name: this.options.timeZone,
        zone: this.options.zone,
      }),
    });

    if (login.code !== 1000 || !login.data?.api_token || !login.data.uid) {
      throw new Error(`OSAIO login failed: code=${login.code ?? 'unknown'} ${login.msg ?? ''}`.trim());
    }

    this.auth = { baseUrl, uid: login.data.uid, apiToken: login.data.api_token };
  }

  private async resolveDevice(): Promise<void> {
    if (this.options.uuid) {
      this.resolvedUuid = this.options.uuid;
      return;
    }
    if (!this.auth) throw new Error('OSAIO is not authenticated');

    const response = await this.request<{
      data?: Array<{ uuid?: string; name?: string }>;
    }>(
      this.auth.baseUrl,
      '/device/list',
      { method: 'GET', query: { page: 1, per_page: 100 } },
      this.auth,
    );

    if (response.code === 1006) {
      await this.ensureAuth(true);
      return this.resolveDevice();
    }

    const devices = response.data?.data ?? [];
    const wanted = (this.options.deviceName ?? 'Living Room').trim().toLowerCase();
    const device = devices.find((item) => item.name?.trim().toLowerCase() === wanted);
    if (!device?.uuid) {
      const names = devices.map((item) => item.name).filter(Boolean).join(', ');
      throw new Error(`OSAIO device '${this.options.deviceName ?? 'Living Room'}' not found. Available: ${names || 'none'}`);
    }
    this.resolvedUuid = device.uuid;
  }

  private async pollLatestEvent(onFrame: FrameHandler): Promise<void> {
    if (!this.auth || !this.resolvedUuid) return;

    const response = await this.request<Array<Record<string, unknown>>>(
      this.auth.baseUrl,
      '/msg/device/all',
      {
        method: 'GET',
        query: {
          uuids: this.resolvedUuid,
          date: dateForZone(this.options.timeZone),
          rows: 10,
          zone: this.options.zone,
          direction: 'desc',
          sort: 1,
          contain_start_id: 0,
        },
      },
      this.auth,
    );

    if (response.code === 1006) {
      await this.ensureAuth(true);
      return;
    }

    const item = response.data?.[0];
    if (!item) return;
    const files = typeof item.files === 'string' ? item.files : undefined;
    if (!files) return;
    const key = String(item.id ?? item.start_id ?? item.msg_id ?? files);
    if (key === this.lastEventKey) return;

    const image = await fetch(files, { signal: AbortSignal.timeout(10_000) });
    if (!image.ok) throw new Error(`OSAIO snapshot HTTP ${image.status}`);
    const contentType = image.headers.get('content-type') ?? '';
    if (contentType && !contentType.startsWith('image/')) {
      throw new Error(`OSAIO snapshot returned ${contentType}, expected image/*`);
    }

    this.lastEventKey = key;
    const jpeg = Buffer.from(await image.arrayBuffer());
    await onFrame(jpeg, Date.now());
  }
}
