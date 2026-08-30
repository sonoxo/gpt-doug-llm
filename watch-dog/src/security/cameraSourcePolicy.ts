function isPrivateIpv4(host: string): boolean {
  const parts = host.split('.').map(Number);
  if (parts.length !== 4 || parts.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) return false;
  const [a, b] = parts;
  return (
    a === 10 ||
    a === 127 ||
    (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168)
  );
}

function isPrivateIpv6(host: string): boolean {
  const normalized = host.toLowerCase();
  return normalized === '::1' || normalized.startsWith('fc') || normalized.startsWith('fd') || normalized.startsWith('fe80:');
}

export function assertAuthorizedLocalCameraUrl(rawUrl: string): void {
  let url: URL;
  try {
    url = new URL(rawUrl);
  } catch {
    throw new Error('CAMERA_URL must be a valid RTSP URL for an explicitly authorized local camera');
  }

  if (url.protocol !== 'rtsp:' && url.protocol !== 'rtsps:') {
    throw new Error('PUBLIC_CCTV_BLOCKED: only RTSP/RTSPS local camera sources are accepted');
  }

  const host = url.hostname.replace(/^\[|\]$/g, '').toLowerCase();
  const localHostname =
    host === 'localhost' ||
    host.endsWith('.local') ||
    host.endsWith('.lan') ||
    isPrivateIpv4(host) ||
    isPrivateIpv6(host);

  if (!localHostname) {
    throw new Error(
      `PUBLIC_CCTV_BLOCKED: '${host}' is not a private/local camera address. ` +
      'Watch Dog does not ingest public CCTV or arbitrary internet camera feeds.',
    );
  }
}

export const cameraPrivacyPolicy = Object.freeze({
  publicCctv: 'BLOCKED',
  arbitraryInternetCameraUrls: 'BLOCKED',
  discovery: 'DISABLED',
  permittedSources: ['explicit-private-RTSP/RTSPS', 'authenticated-Osaio-account-device'],
});
