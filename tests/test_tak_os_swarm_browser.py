"""Chromium smoke tests for the UI <-> local gateway contract without network.

Runs with HTML/CSS/JS in about:blank and a tiny in-browser mock of the
already separately HTTP-tested Python swarm endpoints.
"""
from pathlib import Path
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None

APP = Path(__file__).resolve().parents[1] / 'docs' / 'tak-os'
CSS = (APP / 'styles.css').read_text()
APP_JS = (APP / 'app.js').read_text()
SWARM_JS = (APP / 'swarm-ui.js').read_text().replace(
    "new URL('./api/v1/', window.location.href)",
    "new URL('https://synthetic-lab.invalid/api/v1/')"
)

STUB = r'''
window.__lab = {mode:'paused', integrity:'VERIFIED', proposals:[], changes:[], token:'test-only'};
window.confirm = () => true;
window.prompt = () => 'APPROVE SYNTHETIC PROPOSAL';
window.fetch = async (endpoint, options={}) => {
  const path = new URL(endpoint).pathname.split('/api/v1/')[1];
  const lab = window.__lab;
  if (path === 'session') return {ok:true, json:async()=>({mode:'synthetic-lab',csrfToken:lab.token})};
  if (path === 'swarm' && options.method !== 'POST') return {ok:true,json:async()=>({
    mode:lab.mode,kind:'deterministic-rule-based-agents', integrity:lab.integrity,
    agents:[{id:'gpt-doug-planner',role:'Planner',status:'ACTIVE'},
      {id:'gpt-chaos-critic',role:'Critic',status:'ACTIVE'},
      {id:'zyra-guardian',role:'Guardian',status:'ACTIVE'},
      {id:'ontology-verifier',role:'Ontology',status:'ACTIVE'},
      {id:'provenance-sentinel',role:'Provenance',status:'ACTIVE'},
      {id:'pulse-watchdog',role:'Watchdog',status:'ACTIVE'}],
    pending:lab.proposals.filter(x=>x.status==='pending_review').length,
    budget:{evaluationsPerMinute:30,remaining:30,maxPending:64},
    proposals:lab.proposals,pulses:2,realLLMConnected:false,realTakConnected:false
  })};
  if (path === 'swarm/audit') return {ok:true,json:async()=>({integrity:lab.integrity,events:[
    {seq:1,action:'startup',ts:'2026-10-13T15:00:00Z',hash:'a'.repeat(64),data:{mode:lab.mode}}
  ]})};
  if (options.method === 'POST' && options.headers['X-TAK-OS-Token'] === lab.token) {
    const body=JSON.parse(options.body);
    if (path === 'swarm/control') {
      if (body.action==='rearm') lab.mode='paused'; else if (body.action==='stop') lab.mode='stopped';
      else if (body.action==='start') lab.mode='running'; else lab.mode='paused';
    } else if (path === 'swarm/evaluate') {
      lab.proposals.unshift({id:lab.proposals.length+1,
        created:'2026-10-13T15:00:00Z',candidate:body.candidate,
        status:'pending_review',risk:'low',votes:[{agent:'gpt-chaos-critic',verdict:'PASS',reason:'Reviewed'}]});
    } else if (path === 'swarm/review') {
      let proposal=lab.proposals.find(x=>x.id===body.id);
      proposal.status = body.decision==='approve'?'approved':'rejected';
      lab.changes.push(body);
    } else return {ok:false,status:404,json:async()=>({error:'Unknown endpoint'})};
    return {ok:true,status:200,json:async()=>({mode:lab.mode})};
  }
  return {ok:false,status:404,json:async()=>({error:'Service unavailable'})};
};
'''

HTML = (APP / 'index.html').read_text()
HTML = HTML.replace('<link rel="stylesheet" href="./styles.css">', '<style>'+CSS+'</style>')
HTML = HTML.replace('<script defer src="./app.js"></script>', '<script>'+STUB+'\n'+APP_JS+'</script>')
HTML = HTML.replace('<script defer src="./bridge.js"></script>', '')
HTML = HTML.replace('<script defer src="./swarm-ui.js"></script>', '<script>'+SWARM_JS+'</script>')


@unittest.skipUnless(sync_playwright, 'Playwright/Chromium optional')
class SwarmBrowserChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright=sync_playwright().start()
        cls.browser=cls.playwright.chromium.launch(
            executable_path='/usr/bin/chromium',headless=True,
            args=['--no-sandbox','--disable-background-networking'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page=self.browser.new_page(viewport={'width':1340,'height':900})
        self.errors=[]
        self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.page.set_content(HTML,wait_until='domcontentloaded')
        self.page.locator('#toggle-tiles').uncheck()
        self.page.locator('[data-view="swarm"]').click()
        self.page.wait_for_function("document.querySelector('#swarm-stat-mode').textContent==='PAUSED'",timeout=5000)

    def tearDown(self):
        self.assertEqual(self.errors,[])
        self.page.close()

    def test_six_roles_and_human_gates(self):
        self.assertEqual(self.page.locator('#swarm-agents .swarm-agent').count(),6)
        self.assertTrue(self.page.locator('#swarm-evaluate').is_disabled())
        self.page.locator('#swarm-start').click()
        self.page.wait_for_function("document.querySelector('#swarm-stat-mode').textContent==='RUNNING'",timeout=4000)
        self.page.locator('#swarm-evaluate').click()
        self.page.wait_for_function("document.querySelectorAll('#swarm-proposals .swarm-proposal').length===1",timeout=4000)
        self.assertIn('pending_review',self.page.locator('#swarm-proposals').inner_text())
        self.page.locator('#swarm-proposals .btn-primary').click()
        self.page.wait_for_function("window.__lab.proposals[0].status==='approved'",timeout=4000)
        self.assertEqual(self.page.evaluate('window.__lab.changes[0].confirmation'),'APPROVE SYNTHETIC PROPOSAL')

    def test_killswitch_and_audit_export(self):
        self.page.locator('#swarm-start').click()
        self.page.wait_for_function("document.querySelector('#swarm-stat-mode').textContent==='RUNNING'")
        self.page.locator('#swarm-stop').click()
        self.page.wait_for_function("document.querySelector('#swarm-stat-mode').textContent==='STOPPED'")
        self.assertTrue(self.page.locator('#swarm-evaluate').is_disabled())
        self.page.locator('#swarm-rearm-phrase').fill('REARM LOCAL SWARM')
        self.page.locator('#swarm-rearm').click()
        self.page.wait_for_function("document.querySelector('#swarm-stat-mode').textContent==='PAUSED'")
        with self.page.expect_download() as result:
            self.page.locator('#swarm-export').click()
        self.assertEqual(result.value.suggested_filename,'gpt-chaos-local-audit.json')


if __name__ == '__main__':
    unittest.main()
