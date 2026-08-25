import { createHash, timingSafeEqual } from 'node:crypto';
import net from 'node:net';

export type SovereigntyMode = 'off' | 'enforced';
export type KeyAuthority = 'platform' | 'customer';

export type SovereigntyConfig = {
  mode: SovereigntyMode;
  realm: string;
  region: string;
  allowedRegions: string[];
  airGapped: boolean;
  allowedEgressOrigins: string[];
  keyAuthority: KeyAuthority;
  customerKeyId: string;
  requireEncryptedState: boolean;
  expectedFingerprint: string;
};

export type SovereigntyDecision = {
  allowed: boolean;
  reason: string;
  realm: string;
  region: string;
  target?: string;
  purpose?: string;
};

const csv = (raw: string) => raw.split(',').map((value) => value.trim()).filter(Boolean);

function exactEqual(a: string, b: string) {
  const left = Buffer.from(a);
  const right = Buffer.from(b);
  return left.length === right.length && timingSafeEqual(left, right);
}

function normalizeOrigin(value: string) {
  try { return new URL(value).origin.toLowerCase(); } catch { return ''; }
}

function normalizedHost(value: string) {
  return value.replace(/^\[/, '').replace(/\]$/, '').toLowerCase();
}

function isPrivateIpv4(host: string) {
  const parts = host.split('.').map(Number);
  if (parts.length !== 4 || parts.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) return false;
  return parts[0] === 10
    || parts[0] === 127
    || (parts[0] === 169 && parts[1] === 254)
    || (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31)
    || (parts[0] === 192 && parts[1] === 168);
}

function isInternalHost(rawHost: string) {
  const host = normalizedHost(rawHost);
  if (!host) return false;
  if (host === 'localhost' || host.endsWith('.localhost') || host.endsWith('.internal') || host.endsWith('.local')) return true;
  const version = net.isIP(host);
  if (version === 4) return isPrivateIpv4(host);
  if (version === 6) return host === '::1' || host.startsWith('fc') || host.startsWith('fd') || host.startsWith('fe80:');
  return !host.includes('.');
}

export class SovereigntyPolicy {
  readonly mode: SovereigntyMode;
  readonly realm: string;
  readonly region: string;
  readonly allowedRegions: string[];
  readonly airGapped: boolean;
  readonly allowedEgressOrigins: string[];
  readonly keyAuthority: KeyAuthority;
  readonly customerKeyId: string;
  readonly requireEncryptedState: boolean;
  readonly expectedFingerprint: string;

  constructor(input: Partial<SovereigntyConfig> = {}) {
    this.mode = input.mode ?? (process.env.XUNIA_SOVEREIGNTY_ENFORCED === '1' ? 'enforced' : 'off');
    this.realm = input.realm ?? process.env.XUNIA_REALM_ID?.trim() ?? 'xunia-default';
    this.region = input.region ?? process.env.XUNIA_REGION?.trim() ?? 'virginia-local';
    this.allowedRegions = input.allowedRegions ?? csv(process.env.XUNIA_ALLOWED_REGIONS ?? this.region);
    this.airGapped = input.airGapped ?? process.env.XUNIA_AIR_GAPPED === '1';
    this.allowedEgressOrigins = (input.allowedEgressOrigins ?? csv(process.env.XUNIA_EGRESS_ALLOWLIST ?? ''))
      .map(normalizeOrigin).filter(Boolean);
    this.keyAuthority = input.keyAuthority ?? (process.env.XUNIA_KEY_AUTHORITY === 'customer' ? 'customer' : 'platform');
    this.customerKeyId = input.customerKeyId ?? process.env.XUNIA_CUSTOMER_KEY_ID?.trim() ?? '';
    this.requireEncryptedState = input.requireEncryptedState ?? process.env.XUNIA_REQUIRE_ENCRYPTED_STATE === '1';
    this.expectedFingerprint = input.expectedFingerprint ?? process.env.XUNIA_SOVEREIGNTY_EXPECTED_SHA256?.trim() ?? '';
  }

  manifest() {
    return {
      version: 1,
      mode: this.mode,
      realm: this.realm,
      region: this.region,
      allowedRegions: [...this.allowedRegions].sort(),
      airGapped: this.airGapped,
      allowedEgressOrigins: [...this.allowedEgressOrigins].sort(),
      keyAuthority: this.keyAuthority,
      customerKeyId: this.customerKeyId || null,
      requireEncryptedState: this.requireEncryptedState
    };
  }

  fingerprint() {
    return createHash('sha256').update(JSON.stringify(this.manifest())).digest('hex');
  }

  evaluateRequest(requestRealm?: string, requestRegion?: string): SovereigntyDecision {
    if (this.mode === 'off') return { allowed: true, reason: 'sovereignty_off', realm: this.realm, region: this.region };
    if (requestRealm && requestRealm !== this.realm) {
      return { allowed: false, reason: 'realm_mismatch', realm: this.realm, region: this.region };
    }
    if (requestRegion && !this.allowedRegions.includes(requestRegion)) {
      return { allowed: false, reason: 'region_not_allowed', realm: this.realm, region: this.region };
    }
    return { allowed: true, reason: 'request_within_sovereign_boundary', realm: this.realm, region: this.region };
  }

  evaluateEgress(target: string, purpose = 'network'): SovereigntyDecision {
    if (this.mode === 'off') {
      return { allowed: true, reason: 'sovereignty_off', realm: this.realm, region: this.region, target, purpose };
    }
    let url: URL;
    try { url = new URL(target); } catch {
      return { allowed: false, reason: 'invalid_egress_target', realm: this.realm, region: this.region, target, purpose };
    }
    if (!['http:', 'https:'].includes(url.protocol)) {
      return { allowed: false, reason: 'egress_protocol_denied', realm: this.realm, region: this.region, target, purpose };
    }
    if (isInternalHost(url.hostname)) {
      return { allowed: true, reason: 'private_network_target', realm: this.realm, region: this.region, target: url.origin, purpose };
    }
    if (this.airGapped) {
      return { allowed: false, reason: 'air_gap_external_egress_denied', realm: this.realm, region: this.region, target: url.origin, purpose };
    }
    if (!this.allowedEgressOrigins.includes(url.origin.toLowerCase())) {
      return { allowed: false, reason: 'egress_origin_not_allowlisted', realm: this.realm, region: this.region, target: url.origin, purpose };
    }
    return { allowed: true, reason: 'egress_origin_allowlisted', realm: this.realm, region: this.region, target: url.origin, purpose };
  }

  assertEgress(target: string, purpose = 'network') {
    const decision = this.evaluateEgress(target, purpose);
    if (!decision.allowed) throw new Error(`sovereignty_${decision.reason}`);
    return decision;
  }

  ready(stateEncrypted = Boolean(process.env.XUNIA_STATE_ENCRYPTION_KEY?.trim())) {
    const checks: { name: string; ok: boolean; detail?: string }[] = [];
    if (this.mode === 'off') return { ok: true, checks: [{ name: 'mode', ok: true, detail: 'off' }], fingerprint: this.fingerprint() };
    checks.push({ name: 'realm', ok: Boolean(this.realm), detail: this.realm || 'missing' });
    checks.push({ name: 'region', ok: Boolean(this.region) && this.allowedRegions.includes(this.region), detail: this.region || 'missing' });
    checks.push({ name: 'customer_key_boundary', ok: this.keyAuthority !== 'customer' || Boolean(this.customerKeyId), detail: this.keyAuthority });
    checks.push({ name: 'encrypted_state', ok: !this.requireEncryptedState || stateEncrypted, detail: this.requireEncryptedState ? 'required' : 'optional' });
    const fingerprint = this.fingerprint();
    checks.push({ name: 'policy_fingerprint', ok: !this.expectedFingerprint || exactEqual(this.expectedFingerprint, fingerprint), detail: fingerprint });
    return { ok: checks.every((check) => check.ok), checks, fingerprint };
  }

  sanitized() {
    return {
      ...this.manifest(),
      fingerprint: this.fingerprint(),
      ready: this.ready().ok
    };
  }
}

export const sovereignty = new SovereigntyPolicy();
