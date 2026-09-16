"""Validate this portable ontology using only the Python standard library."""
import json, hashlib, copy
from pathlib import Path
BASE=Path(__file__).resolve().parent
def load(n): return json.loads((BASE/n).read_text())
def validate(model,objects,links):
 ids=[o['id'] for o in objects]; assert len(ids)==len(set(ids)), 'Duplicate object IDs'
 index={o['id']:o for o in objects}; evidence={o['id'] for o in objects if o['type']=='Evidence'}
 for o in objects:
  assert o['type'] in model['object_types'], 'Unknown object type'
  assert set(model['object_types'][o['type']]['required_properties']) <= set(o['properties']), 'Missing property'
  assert set(o['source_ids']) <= evidence, 'Missing provenance'
  assert o['type']=='Evidence' or o['source_ids'], 'Unattributed object'
  p=o['properties']
  for key in ['verification_status','maturity','readiness','registration_status']:
   if key in p: assert p[key] in model['enums'][key], 'Invalid enum'
  status_enum={'Membership':'membership_status','Submission':'submission_status','Agreement':'agreement_status','Task':'task_status'}.get(o['type'])
  if status_enum: assert p['status'] in model['enums'][status_enum], 'Invalid status'
  if o['type']=='Membership' and p['status']=='confirmed':
   assert p['verification_status'] in ['document_supported','independently_verified'], 'Unverified membership promotion'
   ref=p.get('official_confirmation_reference');assert ref in evidence, 'Missing membership confirmation'
   assert index[ref]['properties']['source_kind'] in ['membership_confirmation','executed_agreement'], 'Wrong membership evidence kind'
  if o['type']=='Event' and p['registration_status'] in ['registered','attended']:
   assert p.get('registration_evidence_id') in evidence, 'Missing registration evidence'
  if o['type']=='Submission' and p['status']=='submitted':
   assert p['submitted_at'] and p.get('receipt_evidence_id') in evidence, 'Missing submission receipt'
  if o['type']=='Agreement' and p['status'] in ['signed','awarded']:
   assert p.get('executed_document_evidence_id') in evidence, 'Missing executed agreement'
   if p['status']=='awarded':assert p['award_number'], 'Missing award identifier'
  if o['type']=='Capability' and p['readiness'] in ['tested','operational']:
   assert p.get('test_evidence') in evidence, 'Missing test evidence'
 link_ids=[l['id'] for l in links];assert len(link_ids)==len(set(link_ids)), 'Duplicate link IDs'
 for l in links:
  assert l['type'] in model['link_types'], 'Unknown link type'
  assert l['source_id'] in index and l['target_id'] in index, 'Dangling link'
  spec=model['link_types'][l['type']]
  assert index[l['source_id']]['type']==spec['source_type'], 'Wrong source type'
  assert index[l['target_id']]['type']==spec['target_type'], 'Wrong target type'
  assert l['evidence_ids'] and set(l['evidence_ids'])<=evidence, 'Missing link evidence'
  assert l['relationship_status'] in model['enums']['relationship_status'], 'Invalid relationship status'
 return True
if __name__=='__main__':
 m,o,l=load('ontology.json'),load('objects.json'),load('links.json')
 validate(m,o,l)
 e=next(x for x in o if x['id']=='evidence.portal')
 assert hashlib.sha256((BASE/'source_portal_export.md').read_bytes()).hexdigest()==e['properties']['sha256'], 'Source changed'
 tests=[]
 def rejected(name,objects,links):
  try:validate(m,objects,links)
  except AssertionError:tests.append({'test':name,'result':'pass'});return
  raise AssertionError('Invalid fixture accepted: '+name)
 x=copy.deepcopy(o);next(z for z in x if z['type']=='Membership')['properties']['status']='confirmed';rejected('Block unsupported membership confirmation',x,l)
 x=copy.deepcopy(l);x[0]['target_id']='missing';rejected('Reject dangling relationship',o,x)
 x=copy.deepcopy(l);x[0]['target_id']='person.douglas';rejected('Reject incorrect endpoint type',o,x)
 x=copy.deepcopy(o);next(z for z in x if z['type']=='Event')['properties']['registration_status']='registered';rejected('Require registration evidence',x,l)
 x=copy.deepcopy(o);next(z for z in x if z['type']=='Submission')['properties']['status']='submitted';rejected('Require submission receipt',x,l)
 x=copy.deepcopy(o);next(z for z in x if z['type']=='Capability')['properties']['readiness']='tested';rejected('Require capability test evidence',x,l)
 report={'status':'passed','objects':len(o),'links':len(l),'object_types':len(m['object_types']),'link_types':len(m['link_types']),'source_hash':'verified','negative_tests':tests,'limits':'Structural checks do not authenticate documents, establish membership or replace live authorization.'}
 (BASE/'validation_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
