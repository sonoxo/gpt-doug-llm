import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const zyra = resolve(process.env.ZYRA_REPO_PATH || resolve(root, '../zyra'));
const xunia = resolve(process.env.XUNIA_REPO_PATH || resolve(root, '../gods-eye-viewXUNIA'));
const contract = 'packages/mission-contract';
for (const file of readdirSync(resolve(root, contract))) {
  for (const repo of [zyra, xunia]) {
    assert.equal(readFileSync(resolve(repo, contract, file), 'utf8'), readFileSync(resolve(root, contract, file), 'utf8'), `Contract drift: ${repo}/${file}`);
  }
}
const producer = spawnSync(process.env.PYTHON || 'python3', ['-c', `
import json, tempfile
from pathlib import Path
from va3lm.rvia import MissionEnvelope, RVIARouter
from va3lm.mission_ledger import MissionLedger
with tempfile.TemporaryDirectory() as directory:
    ledger = MissionLedger(Path(directory) / 'integration.db')
    router = RVIARouter(ledger)
    replies = []
    for target in ('ZYRA', 'XUNIA', 'NXYZ', 'ZYRA_CLOUD', 'SAFEHOUSE_EVERYDAYSPY_TRAINING_V1'):
        reply = router.route(MissionEnvelope(requestedBy='integration-test', intent='Inspect integration state', target=target, classification='public'))
        persisted = MissionLedger(ledger.path).get(reply['mission']['missionId'])
        assert persisted['envelope']['evidence'] == reply['mission']['evidence']
        replies.append(reply)
    print(json.dumps(replies))
`], { cwd: root, encoding: 'utf8', env: { ...process.env, PYTHONPATH: resolve(root, 'va3lm/src') } });
assert.equal(producer.status, 0, producer.stderr);
const { extractRouteEvidence } = await import(pathToFileURL(resolve(zyra, contract, 'index.mjs')));
const { createVirginiaOntology } = await import(pathToFileURL(resolve(xunia, 'src/ontology/virginia.js')));
const ontology = createVirginiaOntology();
const replies = JSON.parse(producer.stdout);
for (const reply of replies) {
  const receipt = extractRouteEvidence(reply);
  const object = ontology.importMissionResult(reply);
  assert.equal(object.missionId, receipt.missionId);
  assert.equal(object.status, receipt.status);
  assert.equal(object.executionVerified, false);
}
assert.equal(ontology.listObjects('RouteEvidence').length, 5);
console.log(JSON.stringify({ status:'PASS', scope:'local producer, durable ledger, Zyra contract validator, XUNIA ontology consumer', routes:replies.map(r => ({ target:r.mission.target,status:r.status })), liveDeploymentVerified:false }, null, 2));
