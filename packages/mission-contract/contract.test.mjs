import test from 'node:test';
import assert from 'node:assert/strict';
import { parseRouteEvidence, extractRouteEvidence } from './index.mjs';
const receipt = {schemaVersion:'xunia.route-evidence/v1',type:'RouteEvidence',controlPlane:'THE_BLACK_HOUSE_V1',kernelVersion:'3.0.0',source:'RVIA',executionVerified:false,status:'ACCEPTED',missionId:'fixture-1',target:'ZYRA',executionState:'MISSION_CONTRACT_ACCEPTED',observedAt:'2026-09-09T12:00:00Z'};
test('receipt preserves dispatch state without claiming execution', () => assert.equal(parseRouteEvidence(receipt).executionVerified,false));
test('completion and forged verification fail closed', () => {
  for (const patch of [{status:'COMPLETED'},{executionVerified:true},{observedAt:'invalid'},{source:'unknown'},{missionId:''},{status:'PLANNED'}]) assert.throws(() => parseRouteEvidence({...receipt,...patch}));
});
test('envelope and receipt identity must agree', () => {
  const reply = {status:'ACCEPTED',mission:{missionId:'fixture-1',target:'ZYRA',result:{executionState:'MISSION_CONTRACT_ACCEPTED'},evidence:[receipt]}};
  assert.equal(extractRouteEvidence(reply).missionId,'fixture-1');
  assert.throws(() => extractRouteEvidence({...reply,status:'PLANNED'}));
});
