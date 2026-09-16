import contract from './route-evidence.json' with { type: 'json' };

export function parseRouteEvidence(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('ROUTE_EVIDENCE_INVALID');
  for (const key of ['schemaVersion', 'type', 'controlPlane', 'kernelVersion', 'source', 'executionVerified']) {
    if (value[key] !== contract[key]) throw new Error('ROUTE_EVIDENCE_INVALID_' + key);
  }
  if (!contract.statuses.includes(value.status)) throw new Error('ROUTE_EVIDENCE_INVALID_STATUS');
  for (const key of contract.requiredStrings) {
    if (typeof value[key] !== 'string' || !value[key].trim()) throw new Error('ROUTE_EVIDENCE_MISSING_' + key);
  }
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(value.observedAt) || !Number.isFinite(Date.parse(value.observedAt))) throw new Error('ROUTE_EVIDENCE_INVALID_TIME');
  if (value.executionState === 'LOCAL_PLAN_COMPLETE' && value.status !== 'PLANNED') throw new Error('ROUTE_EVIDENCE_STATE_MISMATCH');
  if (value.executionState === 'MISSION_CONTRACT_ACCEPTED' && value.status !== 'ACCEPTED') throw new Error('ROUTE_EVIDENCE_STATE_MISMATCH');
  const fields = ['schemaVersion','type','controlPlane','kernelVersion','source','executionVerified','status',...contract.requiredStrings];
  return Object.freeze(Object.fromEntries(fields.map(key => [key, value[key]])));
}

export function extractRouteEvidence(reply) {
  const receipt = parseRouteEvidence(reply?.mission?.evidence?.at(-1));
  if (receipt.missionId !== reply.mission.missionId || receipt.target !== reply.mission.target || receipt.status !== reply.status || receipt.executionState !== (reply.mission.result?.executionState || 'NOT_EXECUTED')) throw new Error('ROUTE_EVIDENCE_ENVELOPE_MISMATCH');
  return receipt;
}
