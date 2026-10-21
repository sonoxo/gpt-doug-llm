// Harmless synthetic REA analysis fixture owned by Sonoxo.
// Static imports and functions only; never execute as a background service.
export function normalizeEvidence(value) {
  const normalized = String(value).trim().toLowerCase();
  return { provenance: 'synthetic-fixture', value: normalized };
}
export const VERSION = 'REA-KRAKEN-MOCK-1';
