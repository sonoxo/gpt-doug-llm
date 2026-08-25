export const GEO_FACTOR_KEYS = [
  'confirmedIncidentHistory',
  'credibleThreatReports',
  'criticalInfrastructureExposure',
  'largeGatheringExposure',
  'transportDisruption',
  'emergencyServiceStrain',
  'crossSourceAnomaly',
  'protectiveReadinessGap'
] as const;

export type GeoFactorKey = typeof GEO_FACTOR_KEYS[number];
export type RiskBand = 'low' | 'guarded' | 'elevated' | 'high' | 'critical';

export type GeoZoneInput = {
  id: string;
  name?: string;
  latitude: number;
  longitude: number;
  observedAt?: string;
  confidence?: number;
  factors: Partial<Record<GeoFactorKey, number>>;
};

export type GeoAssessment = {
  zoneId: string;
  name: string;
  riskScore: number;
  riskBand: RiskBand;
  confidence: number;
  topFactors: Array<{ factor: GeoFactorKey; value: number; contribution: number }>;
  recommendedActions: string[];
  reviewRequired: boolean;
  ontology: {
    nodes: Array<{ id: string; type: 'zone' | 'factor' | 'assessment'; label: string }>;
    edges: Array<{ from: string; to: string; relation: 'OBSERVED_IN' | 'CONTRIBUTES_TO' | 'REQUIRES_REVIEW' }>;
  };
};

const WEIGHTS: Record<GeoFactorKey, number> = {
  confirmedIncidentHistory: 0.16,
  credibleThreatReports: 0.22,
  criticalInfrastructureExposure: 0.14,
  largeGatheringExposure: 0.12,
  transportDisruption: 0.08,
  emergencyServiceStrain: 0.08,
  crossSourceAnomaly: 0.12,
  protectiveReadinessGap: 0.08
};

const LABELS: Record<GeoFactorKey, string> = {
  confirmedIncidentHistory: 'confirmed incident history',
  credibleThreatReports: 'credible threat reporting',
  criticalInfrastructureExposure: 'critical infrastructure exposure',
  largeGatheringExposure: 'large gathering exposure',
  transportDisruption: 'transport disruption',
  emergencyServiceStrain: 'emergency service strain',
  crossSourceAnomaly: 'cross-source anomaly',
  protectiveReadinessGap: 'protective readiness gap'
};

const clamp01 = (value: number) => Math.max(0, Math.min(1, value));
const round = (value: number, digits = 4) => Number(value.toFixed(digits));

const riskBand = (score: number): RiskBand => {
  if (score >= 0.8) return 'critical';
  if (score >= 0.6) return 'high';
  if (score >= 0.4) return 'elevated';
  if (score >= 0.2) return 'guarded';
  return 'low';
};

const ensureZone = (input: unknown): GeoZoneInput => {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('zone_must_be_object');
  const raw = input as Record<string, unknown>;
  if (typeof raw.id !== 'string' || raw.id.trim().length === 0) throw new Error('zone_id_required');
  if (typeof raw.latitude !== 'number' || raw.latitude < -90 || raw.latitude > 90) throw new Error('invalid_latitude');
  if (typeof raw.longitude !== 'number' || raw.longitude < -180 || raw.longitude > 180) throw new Error('invalid_longitude');
  if (!raw.factors || typeof raw.factors !== 'object' || Array.isArray(raw.factors)) throw new Error('factors_required');

  const factorInput = raw.factors as Record<string, unknown>;
  const factors: Partial<Record<GeoFactorKey, number>> = {};
  for (const key of Object.keys(factorInput)) {
    if (!GEO_FACTOR_KEYS.includes(key as GeoFactorKey)) throw new Error(`unsupported_factor:${key}`);
    const value = factorInput[key];
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1) throw new Error(`factor_out_of_range:${key}`);
    factors[key as GeoFactorKey] = value;
  }

  const confidence = raw.confidence === undefined ? 1 : raw.confidence;
  if (typeof confidence !== 'number' || !Number.isFinite(confidence) || confidence < 0 || confidence > 1) throw new Error('confidence_out_of_range');

  return {
    id: raw.id.trim(),
    name: typeof raw.name === 'string' && raw.name.trim() ? raw.name.trim() : raw.id.trim(),
    latitude: raw.latitude,
    longitude: raw.longitude,
    observedAt: typeof raw.observedAt === 'string' ? raw.observedAt : undefined,
    confidence,
    factors
  };
};

const actionsFor = (band: RiskBand, top: GeoAssessment['topFactors']): string[] => {
  if (band === 'low') return ['Maintain routine monitoring and data-quality checks.'];
  const actions = new Set<string>(['Require human analyst review before operational escalation.', 'Verify elevated signals with at least one independent source.']);
  const keys = new Set(top.map(item => item.factor));
  if (keys.has('credibleThreatReports') || keys.has('crossSourceAnomaly')) actions.add('Prioritize source validation and time-sensitive situational awareness.');
  if (keys.has('criticalInfrastructureExposure') || keys.has('protectiveReadinessGap')) actions.add('Review defensive posture, access controls, and continuity plans for exposed infrastructure.');
  if (keys.has('largeGatheringExposure')) actions.add('Coordinate event safety, crowd management, emergency access, and evacuation readiness.');
  if (keys.has('transportDisruption')) actions.add('Coordinate transport operators and preserve emergency routing capacity.');
  if (keys.has('emergencyServiceStrain')) actions.add('Review mutual-aid coverage and emergency-service surge capacity.');
  if (band === 'high' || band === 'critical') actions.add('Escalate the area-level assessment to authorized public-safety leadership for review.');
  return [...actions];
};

export const assessZone = (input: unknown): { zone: GeoZoneInput; assessment: GeoAssessment } => {
  const zone = ensureZone(input);
  const confidence = zone.confidence ?? 1;
  const contributions = GEO_FACTOR_KEYS.map(factor => {
    const value = clamp01(zone.factors[factor] ?? 0);
    return { factor, value: round(value), contribution: round(value * WEIGHTS[factor]) };
  }).sort((a, b) => b.contribution - a.contribution);

  const rawScore = contributions.reduce((sum, item) => sum + item.contribution, 0);
  const score = round(rawScore * (0.6 + 0.4 * confidence));
  const band = riskBand(score);
  const topFactors = contributions.filter(item => item.value > 0).slice(0, 4);
  const assessmentId = `assessment:${zone.id}`;
  const zoneId = `zone:${zone.id}`;
  const nodes: GeoAssessment['ontology']['nodes'] = [
    { id: zoneId, type: 'zone', label: zone.name ?? zone.id },
    { id: assessmentId, type: 'assessment', label: `${band} risk` }
  ];
  const edges: GeoAssessment['ontology']['edges'] = [];
  for (const item of topFactors) {
    const factorId = `factor:${zone.id}:${item.factor}`;
    nodes.push({ id: factorId, type: 'factor', label: LABELS[item.factor] });
    edges.push({ from: factorId, to: zoneId, relation: 'OBSERVED_IN' });
    edges.push({ from: factorId, to: assessmentId, relation: 'CONTRIBUTES_TO' });
  }
  const reviewRequired = band === 'elevated' || band === 'high' || band === 'critical';
  if (reviewRequired) edges.push({ from: assessmentId, to: zoneId, relation: 'REQUIRES_REVIEW' });

  return {
    zone,
    assessment: {
      zoneId: zone.id,
      name: zone.name ?? zone.id,
      riskScore: score,
      riskBand: band,
      confidence: round(confidence),
      topFactors,
      recommendedActions: actionsFor(band, topFactors),
      reviewRequired,
      ontology: { nodes, edges }
    }
  };
};

export const assessGeoCollection = (input: unknown) => {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('request_must_be_object');
  const raw = input as Record<string, unknown>;
  if (!Array.isArray(raw.zones) || raw.zones.length === 0) throw new Error('zones_required');
  if (raw.zones.length > 5000) throw new Error('too_many_zones');

  const assessed = raw.zones.map(assessZone);
  const features = assessed.map(({ zone, assessment }) => ({
    type: 'Feature' as const,
    geometry: { type: 'Point' as const, coordinates: [zone.longitude, zone.latitude] },
    properties: {
      zoneId: zone.id,
      name: assessment.name,
      observedAt: zone.observedAt ?? null,
      riskScore: assessment.riskScore,
      riskBand: assessment.riskBand,
      confidence: assessment.confidence,
      reviewRequired: assessment.reviewRequired,
      topFactors: assessment.topFactors,
      recommendedActions: assessment.recommendedActions
    }
  }));

  return {
    generatedAt: new Date().toISOString(),
    methodology: 'area-level defensive risk assessment; no individual or demographic scoring',
    factorWeights: WEIGHTS,
    geojson: { type: 'FeatureCollection' as const, features },
    assessments: assessed.map(item => item.assessment)
  };
};

export const geoFactorSchema = () => ({
  scale: '0..1',
  factors: GEO_FACTOR_KEYS.map(key => ({ key, label: LABELS[key], weight: WEIGHTS[key] })),
  constraints: [
    'Area-level analysis only.',
    'No individual identification, profiling, or protected-class factors.',
    'Elevated outputs require human review and independent source verification.',
    'The score is decision support, not a prediction that an attack will occur.'
  ]
});
