/* XUNIA CYBER SWARM: deterministic, offline, synthetic defensive-training processor.
   This module never scans, transmits, exploits, or calls external APIs. */
export const ROLES = Object.freeze([
  {id:'intake',name:'SCOPE GUARD',short:'01',focus:'Training boundary & source identity',color:'#73e8ff'},
  {id:'mapper',name:'ATT&CK MAPPER',short:'02',focus:'Tactic classification and provenance',color:'#a28dff'},
  {id:'sensor',name:'SIGNAL ANALYST',short:'03',focus:'Synthetic event triage',color:'#49e3c0'},
  {id:'defender',name:'DEFENSE BUILDER',short:'04',focus:'Defensive controls and response options',color:'#ffd18c'},
  {id:'critic',name:'CHAOS CRITIC',short:'05',focus:'Alternative explanations and uncertainty',color:'#ff8db7'},
  {id:'auditor',name:'EVIDENCE VERIFIER',short:'06',focus:'Provenance, limitations and completion gate',color:'#b0ed9b'}
]);
export const ALLOWED_FUNCTIONS = Object.freeze(['Govern','Identify','Protect','Detect','Respond','Recover']);
export const TACTICS = Object.freeze([
 ['TA0043','Reconnaissance'],['TA0042','Resource Development'],['TA0001','Initial Access'],
 ['TA0002','Execution'],['TA0003','Persistence'],['TA0004','Privilege Escalation'],
 ['TA0005','Stealth'],['TA0112','Defense Impairment'],['TA0006','Credential Access'],
 ['TA0007','Discovery'],['TA0008','Lateral Movement'],['TA0009','Collection'],
 ['TA0011','Command and Control'],['TA0010','Exfiltration'],['TA0040','Impact']
]);
const allowedTactics = new Map(TACTICS);
export function validateCurriculum(data){
  const errors=[];
  if(data?.schema!=='xunia.cyber.swarm.curriculum.v1') errors.push('invalid schema');
  if(data?.mode!=='synthetic-defensive-training') errors.push('invalid mode');
  if(!data?.provenance?.no_live_targets || !data?.provenance?.no_autonomous_intrusion) errors.push('unsafe execution boundary');
  const rows=Array.isArray(data?.scenarios)?data.scenarios:[];
  if(rows.length!==15) errors.push('expected one synthetic exercise per ATT&CK enterprise tactic');
  const ids=new Set(),covered=new Set(),functions=new Set();
  for(const [i,row] of rows.entries()){
    if(!/^LAB-\d\d$/.test(row?.id||'') || ids.has(row.id)) errors.push(`bad or duplicate lab id at ${i}`);
    ids.add(row.id);
    if(!allowedTactics.has(row.tactic)||allowedTactics.get(row.tactic)!==row.tactic_name||covered.has(row.tactic)) errors.push(`unknown or duplicate tactic in ${row?.id}`);
    covered.add(row.tactic);
    for(const k of ['domain','title','brief','critic','question','rationale','source'])if(!row?.[k]||typeof row[k]!=='string')errors.push(`missing ${k} in ${row?.id}`);
    for(const k of ['signals','controls','choices'])if(!Array.isArray(row?.[k])||row[k].length!==3||row[k].some(x=>!x||typeof x!=='string'))errors.push(`invalid ${k} in ${row?.id}`);
    if(!Number.isInteger(row?.answer)||row.answer<0||row.answer>2)errors.push(`invalid answer in ${row?.id}`);
    if(!Array.isArray(row?.nist)||row.nist.length===0||row.nist.some(x=>!ALLOWED_FUNCTIONS.includes(x)))errors.push(`invalid NIST mapping in ${row?.id}`);
    (row?.nist||[]).forEach(x=>functions.add(x));
    if(row?.source!==`https://attack.mitre.org/tactics/${row.tactic}/`) errors.push(`source mismatch in ${row?.id}`);
  }
  if(covered.size!==TACTICS.length)errors.push('ATT&CK tactics not fully mapped');
  if(functions.size!==ALLOWED_FUNCTIONS.length)errors.push('NIST CSF function coverage incomplete');
  for(const x of data?.provenance?.sources||[])if(!/^https:\/\//.test(x.url||''))errors.push('non-HTTPS source');
  return {ok:errors.length===0,errors,scenarios:rows.length,coverage:{tactics:covered.size,nist:functions.size,roles:ROLES.length}};
}
export function analyzeStage(row,stage){
  if(!row || !ROLES[stage]) throw new RangeError('unknown stage');
  const role=ROLES[stage];
  const findings=[
    {heading:'Scope accepted',body:`${row.id} is a fictional training exercise. No production target, credentials, network scan, or real-world action is authorized.`,evidence:'TRAINING_MODE=synthetic; NO_LIVE_TARGETS=true'},
    {heading:'Tactic mapped',body:`${row.tactic_name} (${row.tactic}) is a MITRE ATT&CK Enterprise tactic. NIST CSF coverage: ${row.nist.join(' · ')}.`,evidence:row.source},
    {heading:'Signals correlated',body:`Reviewed ${row.signals.length} fabricated signals. None individually proves malicious activity. Investigate cause and authorization.`,evidence:row.signals.join(' | ')},
    {heading:'Controls proposed',body:row.controls.join(' · '),evidence:'Original XUNIA training controls; implementation not verified'},
    {heading:'Counter-hypothesis recorded',body:row.critic,evidence:'Alternative explanation retained; attribution remains unconfirmed'},
    {heading:'Evidence gate complete',body:'Scenario and official tactic source validated. Controls remain recommendations until independently tested. Operator checkpoint required for training completion.',evidence:`${row.id}; source=${row.source}; scope=synthetic`}
  ];
  return {sequence:stage+1,role:role.name,role_id:role.id,status:'SIMULATED',...findings[stage]};
}
export function scoreChoice(row,choice){
  if(!row||!Number.isInteger(choice)||choice<0||choice>2) return {answered:false,correct:false,reason:'Choose one of the three options.'};
  return {answered:true,correct:choice===row.answer,reason:row.rationale};
}
export function buildReport(row,executed,choice){
  const quiz=scoreChoice(row,choice);
  return {
    schema:'xunia.cyber.swarm.exercise-report.v1',
    generated_at:new Date().toISOString(),
    mode:'synthetic-defensive-training',
    lab_id:row.id,tactic:row.tactic,tactic_name:row.tactic_name,nist_functions:row.nist,
    provenance:{source:row.source,scenario:'original fictional XUNIA exercise'},
    roles:ROLES.map((role,i)=>({role:role.name,executed:i<executed})),
    checkpoints:{analyst_choice:quiz.answered?choice:null,passed:quiz.correct,reason:quiz.reason},
    result:executed===ROLES.length&&quiz.correct?'TRAINING_COMPLETE':'INCOMPLETE_OR_REVIEW_REQUIRED',
    real_world_actions:0,automated_agents_spawned:0
  };
}
