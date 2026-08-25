import test from 'node:test';
import assert from 'node:assert/strict';
import { assessGeoCollection, assessZone, geoFactorSchema } from '../src/geospatial.js';

test('assesses an area and emits explainable ontology links', () => {
  const { assessment } = assessZone({
    id: 'zone-a',
    name: 'Transit district',
    latitude: 38.9,
    longitude: -77.03,
    confidence: 0.9,
    factors: {
      credibleThreatReports: 0.9,
      largeGatheringExposure: 0.8,
      criticalInfrastructureExposure: 0.7,
      crossSourceAnomaly: 0.6
    }
  });

  assert.ok(assessment.riskScore > 0.3);
  assert.ok(assessment.topFactors.length > 0);
  assert.ok(assessment.ontology.nodes.some(node => node.type === 'assessment'));
  assert.ok(assessment.ontology.edges.some(edge => edge.relation === 'CONTRIBUTES_TO'));
  assert.ok(assessment.recommendedActions.some(action => action.includes('human analyst review')));
});

test('emits GeoJSON for map rendering', () => {
  const output = assessGeoCollection({
    zones: [
      {
        id: 'zone-1', latitude: 38.8, longitude: -77.1,
        factors: { confirmedIncidentHistory: 0.4, protectiveReadinessGap: 0.3 }
      },
      {
        id: 'zone-2', latitude: 38.85, longitude: -77.05,
        factors: { largeGatheringExposure: 0.7, emergencyServiceStrain: 0.5 }
      }
    ]
  });

  assert.equal(output.geojson.type, 'FeatureCollection');
  assert.equal(output.geojson.features.length, 2);
  assert.deepEqual(output.geojson.features[0].geometry.coordinates, [-77.1, 38.8]);
  assert.match(output.methodology, /no individual or demographic scoring/);
});

test('rejects unsupported or demographic proxy fields', () => {
  assert.throws(() => assessZone({
    id: 'bad-zone', latitude: 0, longitude: 0,
    factors: { race: 1 }
  }), /unsupported_factor:race/);
});

test('rejects invalid coordinates and out-of-range factors', () => {
  assert.throws(() => assessZone({ id: 'bad-lat', latitude: 91, longitude: 0, factors: {} }), /invalid_latitude/);
  assert.throws(() => assessZone({ id: 'bad-factor', latitude: 0, longitude: 0, factors: { credibleThreatReports: 1.2 } }), /factor_out_of_range/);
});

test('publishes an explicit factor schema and constraints', () => {
  const schema = geoFactorSchema();
  assert.equal(schema.scale, '0..1');
  assert.ok(schema.factors.length >= 8);
  assert.ok(schema.constraints.some(item => item.includes('No individual identification')));
});
