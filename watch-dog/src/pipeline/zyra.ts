import type { AlarmEvent } from '../alerts/index.js';

export type ZyraPipelineResult = {
  delivered: boolean;
  status?: number;
  error?: string;
};

export async function sendEventToZyra(
  url: string | undefined,
  token: string | undefined,
  event: AlarmEvent,
): Promise<ZyraPipelineResult> {
  if (!url) return { delivered: false, error: 'ZYRA pipeline disabled' };

  const payload = {
    schema: 'zyra.geovision.watchdog.v1',
    source: 'gpt-doug-lllm-watch-dog',
    privacy: {
      publicCctv: 'BLOCKED',
      identityRecognition: 'DISABLED',
      authorizedCameraOnly: true,
    },
    evidenceState: event.type === 'manual-test' ? 'MODELED' : 'LIVE',
    detection: event,
    palantir: {
      disposition: 'PENDING_HUMAN_APPROVAL',
      suggestedObjectType: 'Detection',
      suggestedAction: 'upsertWatchDogDetection',
    },
  };

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        ...(token ? { authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return { delivered: false, status: response.status, error: `ZYRA HTTP ${response.status}` };
    }

    return { delivered: true, status: response.status };
  } catch (error) {
    return { delivered: false, error: error instanceof Error ? error.message : String(error) };
  }
}
