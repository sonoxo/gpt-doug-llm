import {test,expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';
import {TOOLS} from '../../docs/darkweb/core.mjs';
const PATH = '/darkweb/';
test.beforeEach(async({page})=>await page.addInitScript(()=>{window.open=(url)=>{window.__xuniaRequestedExternalURL=url;return null;};}));
test('21 named entries are all selectable with exactly one functioning research pane',async({page})=>{
  await page.goto(PATH);
  await expect(page.locator('.tool-card')).toHaveCount(21);
  for(const tool of TOOLS){
    await page.getByRole('button',{name:'Open '+tool.name,exact:true}).click();
    await expect(page.locator('#active-title')).toHaveText(tool.name);
    await expect(page.locator('.engine-pane[data-engine="'+tool.engine+'"]')).toBeVisible();
    await expect(page.locator('.engine-pane:not([hidden])')).toHaveCount(1);
    await expect(page.locator('.tool-card.selected')).toHaveCount(1);
  }
});
test('search and category filters update catalog',async({page})=>{
  await page.goto(PATH);
  await page.locator('#tool-search').fill('PGP');
  await expect(page.locator('.tool-card')).toHaveCount(1);
  await page.locator('#tool-search').fill('unlikely-query');
  await expect(page.locator('.tool-card')).toHaveCount(0);
  await expect(page.locator('#tool-empty')).toBeVisible();
  await page.locator('#tool-search').fill('');
  await page.getByRole('button',{name:/^Exposure/}).click();
  await expect(page.locator('.tool-card')).toHaveCount(4);
  await page.getByRole('button',{name:/^All/}).click();
  await expect(page.locator('.tool-card')).toHaveCount(21);
});
test('public-source launches preserve encoded queries',async({page})=>{
  await page.goto(PATH);
  await page.locator('#global-query').fill('defensive A & B');
  await page.getByRole('button',{name:'Search Ahmia'}).click();
  await expect.poll(()=>page.evaluate(()=>window.__xuniaRequestedExternalURL)).toBe('https://ahmia.fi/search/?q=defensive%20A%20%26%20B');
  await page.locator('#search-aleph').click();
  await expect.poll(()=>page.evaluate(()=>window.__xuniaRequestedExternalURL)).toBe('https://aleph.occrp.org/search?q=defensive%20A%20%26%20B');
});
test('local vault creates, searches, exports, clears, imports and escapes HTML',async({page})=>{
  await page.goto(PATH);
  await page.locator('input[name=title]').fill('<img src=x onerror=alert(1)>');
  await page.locator('input[name=source]').fill('Authorized local source');
  await page.locator('textarea[name=notes]').fill('Source notes');
  await page.getByRole('button',{name:'Add to local vault'}).click();
  await expect(page.locator('#evidence-total')).toHaveText('1');
  await expect(page.locator('#evidence-list .record strong')).toHaveText('<img src=x onerror=alert(1)>');
  await expect(page.locator('#evidence-list img')).toHaveCount(0);
  await page.locator('#evidence-search').fill('no match');
  await expect(page.locator('#evidence-list .record')).toHaveCount(0);
  await page.locator('#evidence-search').fill('');
  const downloadPromise=page.waitForEvent('download');
  await page.locator('#export-evidence').click();
  expect((await downloadPromise).suggestedFilename()).toBe('xunia-glass-onion-evidence.json');
  page.once('dialog',dialog=>dialog.accept());
  await page.locator('#clear-evidence').click();
  await expect(page.locator('#evidence-total')).toHaveText('0');
  await page.locator('#import-evidence').setInputFiles({name:'authorized.csv',mimeType:'text/csv',buffer:Buffer.from('title,source,notes\nImported,Authorized,Auditable\n')});
  await expect(page.locator('#evidence-total')).toHaveText('1');
  await page.reload();
  await expect(page.locator('#evidence-total')).toHaveText('1');
});
test('HIBP adapter sends only a five-character hash prefix over HTTPS',async({page})=>{
  let request;
  await page.route('https://api.pwnedpasswords.com/range/*',async route=>{
    request=route.request();
    await route.fulfill({status:200,contentType:'text/plain',body:'1E4C9B93F3F0682250B6CF8331B7EE68FD8:4242\n'});
  });
  await page.goto(PATH);
  await page.getByRole('button',{name:'Open Have I Been Pwned'}).click();
  await page.locator('#password-input').fill('password');
  await page.getByRole('button',{name:'Check exposure'}).click();
  await expect(page.locator('#password-feedback')).toContainText('4,242');
  expect(request.url()).toBe('https://api.pwnedpasswords.com/range/5BAA6');
  await expect(page.locator('#password-input')).toBeEmpty();
});
test('CISA adapter renders and filters actual-format official feed data',async({page})=>{
  await page.route('https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json',route=>route.fulfill({
    status:200,contentType:'application/json',body:JSON.stringify({vulnerabilities:[
      {cveID:'CVE-2026-0001',vendorProject:'ExampleCo',product:'Portal',vulnerabilityName:'Example issue',dateAdded:'2026-10-19'},
      {cveID:'CVE-2026-0002',vendorProject:'AnotherCo',product:'Widget',vulnerabilityName:'Another issue',dateAdded:'2026-10-18'}]})
  }));
  await page.goto(PATH);
  await page.getByRole('button',{name:'Open DeepDarkCTI'}).click();
  await page.locator('#load-kev').click();
  await expect(page.locator('.intel-item')).toHaveCount(2);
  await page.locator('#kev-query').fill('ExampleCo');
  await expect(page.locator('.intel-item')).toHaveCount(1);
  await expect(page.locator('.intel-item a')).toHaveAttribute('href','https://www.cve.org/CVERecord?id=CVE-2026-0001');
});
test('CISA adapter displays failures instead of invented data',async({page})=>{
  await page.route('https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json',route=>route.abort('failed'));
  await page.goto(PATH);
  await page.getByRole('button',{name:'Open DeepDarkCTI'}).click();
  await page.locator('#load-kev').click();
  await expect(page.locator('#kev-feedback')).toContainText('Unable to load official CISA feed');
  await expect(page.locator('.intel-item')).toHaveCount(0);
});
test('OpenPGP browser operations: keygen, encrypt, decrypt, sign, verify',async({page})=>{
  test.setTimeout(120000);
  const js=await readFile(new URL('./node_modules/openpgp/dist/openpgp.min.js',import.meta.url));
  await page.route('https://unpkg.com/openpgp@5.11.3/dist/openpgp.min.js',route=>route.fulfill({status:200,contentType:'text/javascript',body:js}));
  await page.goto(PATH);
  await page.getByRole('button',{name:'Open PGP Tool'}).click();
  await page.locator('#pgp-name').fill('XUNIA Test');
  await page.locator('#pgp-passphrase').fill('Passphrase Only For Synthetic Test 2026');
  await page.locator('#pgp-generate').click();
  await expect(page.locator('#pgp-feedback')).toContainText('Key pair generated',{timeout:45000});
  const pub=await page.locator('#pgp-public').inputValue(),secret=await page.locator('#pgp-private').inputValue();
  expect(pub).toContain('BEGIN PGP PUBLIC KEY BLOCK');
  expect(secret).toContain('BEGIN PGP PRIVATE KEY BLOCK');
  await page.locator('#pgp-input').fill('XUNIA browser roundtrip');
  await page.locator('#pgp-encrypt').click();
  await expect(page.locator('#pgp-output')).toHaveValue(/BEGIN PGP MESSAGE/);
  const armored=await page.locator('#pgp-output').inputValue();
  await page.locator('#pgp-input').fill(armored);
  await page.locator('#pgp-decrypt').click();
  await expect(page.locator('#pgp-output')).toHaveValue('XUNIA browser roundtrip');
  await page.locator('#pgp-input').fill('XUNIA signed note');
  await page.locator('#pgp-sign').click();
  await expect(page.locator('#pgp-output')).toHaveValue(/BEGIN PGP SIGNED MESSAGE/);
  const signed=await page.locator('#pgp-output').inputValue();
  await page.locator('#pgp-input').fill(signed);
  await page.locator('#pgp-verify').click();
  await expect(page.locator('#pgp-output')).toHaveValue(/Signature verified successfully/);
});
