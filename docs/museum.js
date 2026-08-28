(() => {
  const OWNER = 'sonoxo';
  const API = `https://api.github.com/users/${OWNER}/repos?per_page=100&type=owner&sort=updated`;
  const STATIC_REPOS = [
    'xuniadao','SuperAGI','0-hello-world-svelte','mindsdb','zyra','hounddogZyra','osirisanon','hermes-agent','gpt-doug-llm','GDK','Smash-Bros-Ultimate-Random-Character-Selector','AlmightySonoxo','blueprint','tslint','python-language-server','openai-apps-sdk-examples','WUPify','uShop','cody-public-snapshot','vibesdk','cline','myNetwork','llama.cpp','vllm','langchain','open-webui','ml-agents','awesome-ai-tools-for-game-dev','anything-llm','DeepLearning-YouTube','witchcraft-go-tasks','pymss-studio','eyeris','awesome-machine-learning','soundcloudopen','ZYRAxAlgorithm','distroprep','FreeToken','aip-community-registry-zyra','flow-ai-tools','soundnode-app-xunia','ghidraGPTDougLLMXYRA','plandevXUNIA-','AIT-CoreXUNIA','MMGISxunia-','BSLxunia','DCSxunia','VICARxunia','plandev-uiXUNIA','NASA-3D-ResourcesXUNIA-','api-docsXUNIA','instructionsXUNIA-','earthaccessXUNIA-','fprimeXUNIA-','SpaceX-APIxunia','xrpl-dev-portalXUNIA','XRPL-StandardsXUNIA-','rippledXUNIA','xrpl.jsXUNIA','xrpl4jXUNIA','openai-pythonXUNIA','nsacyber.github.ioZYRA'
  ];

  const CATEGORY_ORDER = [
    'XUNIA Core & Products',
    'AI Runtime & Developer Tools',
    'Security, Governance & Evidence',
    'Space, Geospatial & Mission Systems',
    'Ledger & XRPL',
    'Media, Creator & Experience',
    'Learning, Research & Experiments'
  ];

  const SETS = {
    'XUNIA Core & Products': new Set(['xuniadao','gpt-doug-llm','zyra','eyeris','myNetwork','distroprep','FreeToken','flow-ai-tools','WUPify','uShop']),
    'Security, Governance & Evidence': new Set(['hounddogZyra','ghidraGPTDougLLMXYRA','aip-community-registry-zyra','nsacyber.github.ioZYRA','ZYRAxAlgorithm']),
    'Space, Geospatial & Mission Systems': new Set(['pymss-studio','plandevXUNIA-','AIT-CoreXUNIA','MMGISxunia-','BSLxunia','DCSxunia','VICARxunia','plandev-uiXUNIA','NASA-3D-ResourcesXUNIA-','api-docsXUNIA','instructionsXUNIA-','earthaccessXUNIA-','fprimeXUNIA-','SpaceX-APIxunia']),
    'Ledger & XRPL': new Set(['xrpl-dev-portalXUNIA','XRPL-StandardsXUNIA-','rippledXUNIA','xrpl.jsXUNIA','xrpl4jXUNIA']),
    'Media, Creator & Experience': new Set(['AlmightySonoxo','soundcloudopen','soundnode-app-xunia','DeepLearning-YouTube','Smash-Bros-Ultimate-Random-Character-Selector','GDK']),
    'Learning, Research & Experiments': new Set(['0-hello-world-svelte','osirisanon','awesome-ai-tools-for-game-dev','awesome-machine-learning','witchcraft-go-tasks']),
    'AI Runtime & Developer Tools': new Set(['SuperAGI','mindsdb','hermes-agent','blueprint','tslint','python-language-server','openai-apps-sdk-examples','cody-public-snapshot','vibesdk','cline','llama.cpp','vllm','langchain','open-webui','ml-agents','anything-llm','openai-pythonXUNIA'])
  };

  const DETAILS = {
    xuniadao: ['Root ontology + governance registry', 'Acts as the XUNIAverse front door: it defines the ecosystem registry, governance/compliance contracts, identity boundaries, and the high-level route into VA3LM, Zyra, and GPT-Doug.'],
    'gpt-doug-llm': ['Agentic reasoning + execution core', 'Turns a goal into a bounded engineering loop: policy check → plan → repository edits/tools → tests → verification → keep or roll back. It also hosts the public HQ/Pages site.'],
    zyra: ['Workflow, routing + approval layer', 'Provides the Zyra-facing application and control surfaces around the ecosystem, routing work through bounded execution and visible evidence rather than giving a model unrestricted action.'],
    eyeris: ['Authorized geovision pipeline', 'Normalizes authorized camera/image inputs into non-identifying object/scene detections, enriches them with WGS84 geospatial context, and exposes Foundry-ready model/ontology contracts.'],
    hounddogZyra: ['Privacy code-scanning reference', 'Scans source code for sensitive-data elements and traces where data is stored or shared, producing evidence that can support privacy review. This repository preserves upstream HoundDog attribution.'],
    ZYRAxAlgorithm: ['Feed-ranking transparency reference', 'Preserves and explains the X For You feed source: retrieve candidates → predict viewer actions → filter eligibility → rank/assemble the feed. It is an upstream-derived reference, not an X affiliation claim.'],
    AlmightySonoxo: ['Creative identity + media layer', 'Represents the public creative/artist layer connected to the wider Sonoxo ecosystem and serves as a bridge between technical infrastructure and media-facing work.'],
    FreeToken: ['Token/credit experiment', 'Holds a Sonoxo experiment around tokenized or credit-like application mechanics. It is catalogued as a product experiment; the repository source remains the authority for exact behavior.'],
    distroprep: ['Environment preparation utility', 'Collects setup/bootstrap logic used to prepare development environments before higher-level XUNIA or agent workloads run.'],
    myNetwork: ['Network experiment / service layer', 'Provides a network-oriented project surface connected to XUNIA; it is treated as an experimental service/network component unless a stronger runtime contract is documented in-source.'],
    'flow-ai-tools': ['AI workflow tool collection', 'Groups AI workflow utilities that can be used as building blocks around planning, routing, transformation, or automation tasks.'],
    soundcloudopen: ['Music platform integration experiment', 'Holds a SoundCloud-oriented integration/experiment used in the creator side of the ecosystem; exact API behavior is governed by the repository implementation and upstream service rules.'],
    'soundnode-app-xunia': ['Desktop music client reference', 'Connects a Soundnode-style music application codebase into the XUNIA creator collection as a reference/adaptation for desktop music experiences.'],
    'aip-community-registry-zyra': ['Palantir AIP registry contribution workspace', 'Tracks the XUNIA/Zyra contribution work against the AIP Community Registry. Presence here does not itself prove Palantir approval, partnership, certification, or marketplace acceptance.'],
    ghidraGPTDougLLMXYRA: ['Reverse-engineering research reference', 'Connects a Ghidra-derived code-analysis workbench to the research/security collection for authorized inspection and software understanding. Upstream ownership and licensing remain intact.'],
    'nsacyber.github.ioZYRA': ['Public cyber-reference mirror/adaptation', 'Connects public cybersecurity reference material into the defensive research collection. It does not imply NSA affiliation, endorsement, access, or certification.'],
    GDK: ['Large developer/game toolkit source', 'A large developer-kit repository connected as a tooling/experience reference. The museum links to the source rather than claiming undocumented integration.'],
    WUPify: ['Product experiment', 'A compact application experiment connected to the product layer; its repository is the source of truth for current behavior.'],
    uShop: ['Commerce experiment', 'A compact shopping/commerce application experiment in the product layer; it is catalogued without implying a production payment deployment.'],
    'pymss-studio': ['Screen/visual capture tooling', 'A Python screen-capture/studio-oriented repository that can support visual-input, recording, or computer-vision experiments.'],
    'api-docsXUNIA': ['API documentation reference', 'A documentation repository in the XUNIA mission/science collection. It provides reference material rather than acting as a runtime by itself.'],
    'instructionsXUNIA-': ['Instruction/reference corpus', 'Stores instruction-oriented reference material used for learning or integration work; source provenance and upstream licensing remain separate from XUNIA.'],
    'NASA-3D-ResourcesXUNIA-': ['3D/space asset reference', 'Connects NASA 3D resource material into the visual/space research collection for lawful reference and prototyping. XUNIA does not imply NASA endorsement or affiliation.'],
    'earthaccessXUNIA-': ['Earth science data-access reference', 'Provides an Earth-data access code/reference surface used in the geospatial collection; upstream data policies still govern actual data access.'],
    'fprimeXUNIA-': ['Flight-software framework reference', 'Connects an F Prime-derived flight-software framework into the mission-systems collection for architecture study and prototyping.'],
    'SpaceX-APIxunia': ['Spaceflight data API reference', 'Provides a SpaceX-API-oriented source/reference for spaceflight data experiments. It does not imply SpaceX affiliation or operational access.'],
    'MMGISxunia-': ['Geospatial mission UI reference', 'Connects a mission-oriented geospatial visualization codebase into the XUNIA map/operations collection.'],
    VICARxunia: ['Scientific image-processing reference', 'Connects VICAR-style scientific image-processing source into the mission/vision collection for image-processing research and tooling.'],
    'plandevXUNIA-': ['Mission/planning source reference', 'Provides a planning-oriented source repository in the mission-systems collection; it is catalogued as a connected reference unless a direct runtime binding is documented.'],
    'plandev-uiXUNIA': ['Planning UI reference', 'Provides the user-interface side of the planning collection and complements planning/backend reference code.'],
    'AIT-CoreXUNIA': ['Mission engineering reference', 'A mission/engineering source repository connected to the XUNIA space-systems collection; exact upstream semantics remain defined by its source.'],
    BSLxunia: ['Mission engineering reference', 'A connected mission/engineering repository used as a source/reference surface; no undocumented operational integration is implied.'],
    DCSxunia: ['Mission engineering reference', 'A connected mission/engineering repository used as a source/reference surface; no undocumented operational integration is implied.']
  };

  const KNOWN_AI = {
    SuperAGI: ['Autonomous-agent framework reference','Provides an upstream agent framework for studying/pluggable agent orchestration, tools, and autonomous task loops.'],
    mindsdb: ['AI/data integration reference','Provides an upstream AI/data platform reference for connecting models with databases and structured data workflows.'],
    'hermes-agent': ['Agent framework reference','Provides an agent-runtime codebase used as a comparative/reference implementation for tool use and autonomous workflows.'],
    'llama.cpp': ['Local model inference engine','Runs GGUF-family language models efficiently on local CPUs/GPUs and serves as a reference for free/local inference paths.'],
    vllm: ['High-throughput model serving engine','Provides optimized LLM serving and batching for GPU-backed inference endpoints.'],
    langchain: ['LLM orchestration framework','Provides chains, tools, retrieval, agents, and integration abstractions for composing model-driven applications.'],
    'open-webui': ['Model web interface','Provides a browser UI for interacting with local or remote model backends.'],
    'anything-llm': ['RAG/workspace reference','Provides document ingestion, retrieval, workspace, and model-chat patterns for knowledge-assisted AI applications.'],
    cline: ['IDE coding-agent reference','Provides an editor-integrated coding agent pattern for reading, changing, and testing project code with tool calls.'],
    'cody-public-snapshot': ['Coding-assistant reference','Provides a public coding-assistant snapshot/reference used for comparing developer-agent interaction patterns.'],
    vibesdk: ['App-building SDK reference','Provides app-building/agentic SDK patterns useful to the XUNIA developer-experience layer.'],
    'openai-apps-sdk-examples': ['App SDK examples','Provides example applications and integration patterns; presence in the museum does not imply OpenAI endorsement or partnership.'],
    'openai-pythonXUNIA': ['OpenAI Python SDK reference','Provides a Python API-client reference/adaptation for model API interoperability. It does not imply OpenAI affiliation.'],
    'python-language-server': ['Python editor tooling','Provides language-server capabilities such as code intelligence, symbols, diagnostics, and editor integration.'],
    tslint: ['TypeScript linting reference','Provides static TypeScript linting/reference tooling used for code-quality study and developer tooling.'],
    'ml-agents': ['Reinforcement-learning toolkit reference','Provides Unity ML-Agents-style reinforcement-learning environments and training workflows.'],
    blueprint: ['Developer framework/reference','A connected developer-framework source used as a reference surface; exact behavior and upstream provenance remain defined in the repository.']
  };

  const XRPL = {
    'xrpl-dev-portalXUNIA': ['XRPL developer documentation','Provides XRPL developer documentation/reference material for ledger application work.'],
    'XRPL-StandardsXUNIA-': ['XRPL standards reference','Collects XRPL standards/proposals used to understand protocol and application conventions.'],
    rippledXUNIA: ['XRPL server reference','Provides the rippled server codebase/reference for understanding ledger-node behavior.'],
    'xrpl.jsXUNIA': ['XRPL JavaScript client','Provides JavaScript client patterns for interacting with XRPL services.'],
    xrpl4jXUNIA: ['XRPL Java client','Provides Java client patterns for interacting with XRPL services.']
  };

  const LEARNING = {
    '0-hello-world-svelte': ['Svelte starter/learning project','A small Svelte application used as a frontend learning or starter reference.'],
    osirisanon: ['Research/experiment repository','A connected research experiment; the source repository remains the authority for exact scope.'],
    'awesome-ai-tools-for-game-dev': ['Game-AI resource index','A curated reference collection of AI tools relevant to game development.'],
    'awesome-machine-learning': ['Machine-learning resource index','A curated machine-learning reference collection used for research and discovery.'],
    'witchcraft-go-tasks': ['Go task/reference repository','A Go-oriented task/reference codebase connected for engineering study.'],
    'DeepLearning-YouTube': ['Deep-learning learning/reference source','A large learning/reference repository centered on deep-learning material and examples.'],
    'Smash-Bros-Ultimate-Random-Character-Selector': ['Interactive game utility','A focused application for selecting a random Super Smash Bros. Ultimate character.']
  };

  function category(name) {
    for (const c of CATEGORY_ORDER) if (SETS[c] && SETS[c].has(name)) return c;
    return 'Learning, Research & Experiments';
  }

  function detail(name) {
    return DETAILS[name] || KNOWN_AI[name] || XRPL[name] || LEARNING[name] || [
      `${category(name)} repository`,
      `This repository is connected to the ${category(name)} department of the XUNIAverse. The museum treats the repository itself as the source of truth and does not infer an undocumented runtime integration.`
    ];
  }

  function escapeHtml(value='') {
    return String(value).replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  }

  function formatDate(value) {
    if (!value) return 'metadata fallback';
    try { return new Intl.DateTimeFormat(undefined, {year:'numeric',month:'short',day:'numeric'}).format(new Date(value)); }
    catch { return value; }
  }

  function staticEntry(name) {
    return { name, html_url:`https://github.com/${OWNER}/${name}`, default_branch:'—', language:null, description:null, fork:null, pushed_at:null };
  }

  function provenance(repo) {
    if (repo.fork === true) return 'UPSTREAM-DERIVED / FORK';
    if (repo.fork === false) return 'ACCOUNT REPOSITORY';
    return 'CONNECTED SOURCE';
  }

  let repos = STATIC_REPOS.map(staticEntry);
  let activeCategory = 'ALL';
  let query = '';

  const grid = document.getElementById('repoGrid');
  const count = document.getElementById('repoCount');
  const sync = document.getElementById('repoSync');
  const categoryRow = document.getElementById('museumCategories');
  const search = document.getElementById('museumSearch');
  const deptGrid = document.getElementById('departmentGrid');

  function countsFor(list) {
    const map = Object.fromEntries(CATEGORY_ORDER.map(c => [c, 0]));
    list.forEach(r => { map[category(r.name)] = (map[category(r.name)] || 0) + 1; });
    return map;
  }

  function renderDepartments() {
    if (!deptGrid) return;
    const c = countsFor(repos);
    deptGrid.innerHTML = CATEGORY_ORDER.map((name, i) => `
      <button class="department-node" data-category="${escapeHtml(name)}" style="--i:${i}" aria-label="Show ${escapeHtml(name)} repositories">
        <strong>${c[name] || 0}</strong><span>${escapeHtml(name)}</span>
      </button>`).join('');
    deptGrid.querySelectorAll('button').forEach(btn => btn.addEventListener('click', () => {
      activeCategory = btn.dataset.category;
      renderFilters(); render();
      document.getElementById('museum')?.scrollIntoView({behavior:'smooth', block:'start'});
    }));
  }

  function renderFilters() {
    if (!categoryRow) return;
    const c = countsFor(repos);
    const buttons = [['ALL', repos.length], ...CATEGORY_ORDER.map(name => [name, c[name] || 0])];
    categoryRow.innerHTML = buttons.map(([name, n]) => `<button data-category="${escapeHtml(name)}" class="museum-chip${activeCategory === name ? ' active' : ''}">${escapeHtml(name)} <span>${n}</span></button>`).join('');
    categoryRow.querySelectorAll('button').forEach(btn => btn.addEventListener('click', () => {
      activeCategory = btn.dataset.category; renderFilters(); render();
    }));
  }

  function render() {
    const q = query.trim().toLowerCase();
    const filtered = repos.filter(repo => {
      const [role, how] = detail(repo.name);
      const matchesCategory = activeCategory === 'ALL' || category(repo.name) === activeCategory;
      const haystack = `${repo.name} ${repo.description || ''} ${role} ${how} ${repo.language || ''}`.toLowerCase();
      return matchesCategory && (!q || haystack.includes(q));
    }).sort((a,b) => category(a.name).localeCompare(category(b.name)) || a.name.localeCompare(b.name));

    count.textContent = `${filtered.length} / ${repos.length} public exhibits`;
    grid.innerHTML = filtered.map(repo => {
      const [role, how] = detail(repo.name);
      const c = category(repo.name);
      return `
      <article class="repo-exhibit" data-category="${escapeHtml(c)}">
        <div class="repo-topline"><span class="repo-category">${escapeHtml(c)}</span><span class="repo-provenance">${provenance(repo)}</span></div>
        <h3>${escapeHtml(repo.name)}</h3>
        <p class="repo-role">${escapeHtml(role)}</p>
        <p class="repo-description">${escapeHtml(repo.description || how)}</p>
        <details>
          <summary>How it works in the museum</summary>
          <p>${escapeHtml(how)}</p>
          <p class="repo-boundary">Connection means the repository is part of the Sonoxo/XUNIA GitHub collection. It does not by itself prove live runtime integration, vendor affiliation, certification, or endorsement.</p>
        </details>
        <div class="repo-meta">
          <span>${escapeHtml(repo.language || 'mixed / unknown')}</span>
          <span>branch: ${escapeHtml(repo.default_branch || '—')}</span>
          <span>updated: ${escapeHtml(formatDate(repo.pushed_at))}</span>
        </div>
        <a class="repo-link" href="${escapeHtml(repo.html_url || `https://github.com/${OWNER}/${repo.name}`)}" target="_blank" rel="noopener">OPEN SOURCE EXHIBIT ↗</a>
      </article>`;
    }).join('') || '<p class="museum-empty">No repository exhibits match this filter.</p>';
  }

  search?.addEventListener('input', e => { query = e.target.value; render(); });

  renderDepartments();
  renderFilters();
  render();

  fetch(API, {headers:{Accept:'application/vnd.github+json'}})
    .then(r => r.ok ? r.json() : Promise.reject(new Error(`GitHub API ${r.status}`)))
    .then(live => {
      const publicOwned = live.filter(r => r.owner?.login === OWNER && !r.private);
      const byName = new Map(publicOwned.map(r => [r.name, r]));
      STATIC_REPOS.forEach(name => { if (!byName.has(name)) byName.set(name, staticEntry(name)); });
      repos = [...byName.values()];
      sync.textContent = `LIVE GITHUB INVENTORY · ${repos.length} PUBLIC REPOSITORIES · refreshed ${new Date().toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})}`;
      renderDepartments(); renderFilters(); render();
    })
    .catch(err => {
      sync.textContent = `STATIC FALLBACK · ${repos.length} PUBLIC REPOSITORIES · live GitHub metadata unavailable`;
      console.warn('XUNIA museum live repository refresh failed:', err);
    });
})();