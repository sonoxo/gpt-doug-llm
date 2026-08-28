import { timingSafeEqual } from 'node:crypto';
import type { IncomingMessage, ServerResponse } from 'node:http';
import { sovereignty, type SovereigntyPolicy } from './sovereignty.js';

export type Role = 'viewer' | 'editor' | 'operator' | 'admin';
export type Principal = { subject: string; role: Role; authenticated: boolean; realm: string };

type KeyEntry = { token: string; role: Role; subject: string; realm?: string };
type SecurityHeaderOptions = { camera?: boolean; visionAssets?: boolean };
const ROLE_ORDER: Role[] = ['viewer', 'editor', 'operator', 'admin'];

function validRole(value: unknown): value is Role {
  return typeof value === 'string' && ROLE_ORDER.includes(value as Role);
}

function parseKeys(raw: string): KeyEntry[] {
  if (!raw.trim()) return [];
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    return Object.entries(parsed).flatMap(([token, value]) => {
      if (validRole(value)) return [{ token, role: value, subject: `api:${value}` }];
      if (value && typeof value === 'object') {
        const role = (value as Record<string, unknown>).role;
        const subject = (value as Record<string, unknown>).subject;
        const realm = (value as Record<string, unknown>).realm;
        if (validRole(role)) return [{
          token,
          role,
          subject: typeof subject === 'string' && subject ? subject : `api:${role}`,
          realm: typeof realm === 'string' && realm ? realm : undefined
        }];
      }
      return [];
    });
  } catch {
    return raw.split(',').map((entry) => entry.trim()).filter(Boolean).flatMap((entry) => {
      const [token, roleRaw, subjectRaw] = entry.split(':');
      if (!token || !validRole(roleRaw)) return [];
      return [{ token, role: roleRaw, subject: subjectRaw || `api:${roleRaw}` }];
    });
  }
}

function tokenEqual(a: string, b: string) {
  const left = Buffer.from(a);
  const right = Buffer.from(b);
  return left.length === right.length && timingSafeEqual(left, right);
}

function header(req: IncomingMessage, name: string) {
  const value = req.headers[name];
  return typeof value === 'string' ? value.trim() : '';
}

export class AuthPolicy {
  readonly required: boolean;
  readonly keys: KeyEntry[];
  readonly corsOrigin: string;

  constructor(
    required = process.env.XUNIA_AUTH_REQUIRED === '1',
    rawKeys = process.env.XUNIA_API_KEYS ?? '',
    corsOrigin = process.env.XUNIA_CORS_ORIGIN ?? '',
    readonly sovereign: SovereigntyPolicy = sovereignty
  ) {
    this.required = required;
    this.keys = parseKeys(rawKeys);
    this.corsOrigin = corsOrigin;
  }

  authenticate(req: IncomingMessage): Principal | null {
    const requestDecision = this.sovereign.evaluateRequest(header(req, 'x-xunia-realm') || undefined, header(req, 'x-xunia-region') || undefined);
    if (!requestDecision.allowed) return null;
    if (!this.required) return { subject: 'local-dev', role: 'admin', authenticated: false, realm: this.sovereign.realm };
    const auth = req.headers.authorization ?? '';
    const bearer = auth.startsWith('Bearer ') ? auth.slice(7).trim() : '';
    const headerKey = typeof req.headers['x-api-key'] === 'string' ? req.headers['x-api-key'].trim() : '';
    const token = bearer || headerKey;
    if (!token) return null;
    const match = this.keys.find((entry) => tokenEqual(entry.token, token));
    if (!match) return null;
    const credentialRealm = match.realm ?? this.sovereign.realm;
    if (this.sovereign.mode === 'enforced' && credentialRealm !== this.sovereign.realm) return null;
    return { subject: match.subject, role: match.role, authenticated: true, realm: credentialRealm };
  }

  permits(principal: Principal, minimum: Role) {
    const realmAllowed = this.sovereign.mode !== 'enforced' || principal.realm === this.sovereign.realm;
    return realmAllowed && ROLE_ORDER.indexOf(principal.role) >= ROLE_ORDER.indexOf(minimum);
  }

  ready() {
    const hasUsableCredential = !this.required || this.keys.some((entry) => (
      this.sovereign.mode !== 'enforced' || !entry.realm || entry.realm === this.sovereign.realm
    ));
    return hasUsableCredential && this.sovereign.ready().ok;
  }

  sanitized() {
    const usableKeys = this.keys.filter((entry) => this.sovereign.mode !== 'enforced' || !entry.realm || entry.realm === this.sovereign.realm).length;
    return {
      required: this.required,
      configuredKeys: this.keys.length,
      usableKeys,
      corsOrigin: this.corsOrigin || null,
      sovereignty: this.sovereign.sanitized()
    };
  }
}

export function securityHeaders(
  res: ServerResponse,
  requestId: string,
  corsOrigin = '',
  options: SecurityHeaderOptions = {}
) {
  res.setHeader('x-request-id', requestId);
  res.setHeader('x-xunia-realm', sovereignty.realm);
  res.setHeader('x-xunia-region', sovereignty.region);
  res.setHeader('x-content-type-options', 'nosniff');
  res.setHeader('x-frame-options', 'DENY');
  res.setHeader('referrer-policy', 'no-referrer');
  res.setHeader(
    'permissions-policy',
    options.camera ? 'camera=(self), microphone=(), geolocation=()' : 'camera=(), microphone=(), geolocation=()'
  );

  const contentSecurityPolicy = options.visionAssets
    ? "default-src 'self'; style-src 'self'; script-src 'self' 'wasm-unsafe-eval' https://cdn.jsdelivr.net; connect-src 'self' https://cdn.jsdelivr.net https://storage.googleapis.com; media-src 'self' blob:; img-src 'self' data: blob:; worker-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    : "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'";
  res.setHeader('content-security-policy', contentSecurityPolicy);

  if (corsOrigin) {
    res.setHeader('access-control-allow-origin', corsOrigin);
    res.setHeader('access-control-allow-headers', 'authorization, content-type, x-api-key, x-request-id, x-xunia-realm, x-xunia-region');
    res.setHeader('access-control-allow-methods', 'GET,POST,DELETE,OPTIONS');
    res.setHeader('vary', 'origin');
  }
}

export class RateLimiter {
  private buckets = new Map<string, { at: number; count: number }>();
  constructor(readonly perMinute = Math.max(10, Number(process.env.XUNIA_RATE_LIMIT_PER_MIN ?? 300))) {}

  allow(key: string, now = Date.now()) {
    const current = this.buckets.get(key);
    if (!current || now - current.at >= 60_000) {
      this.buckets.set(key, { at: now, count: 1 });
      return true;
    }
    current.count += 1;
    if (this.buckets.size > 10_000) {
      for (const [id, bucket] of this.buckets) if (now - bucket.at >= 60_000) this.buckets.delete(id);
    }
    return current.count <= this.perMinute;
  }
}
