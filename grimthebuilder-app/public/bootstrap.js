const DEFAULT_PROJECT = Object.freeze({
  name: 'GPT Doug Build',
  template: 'static',
});

async function readFailure(response) {
  try {
    const payload = await response.json();
    return payload.error || `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

function showStartupFailure(error) {
  const message = error instanceof Error ? error.message : String(error);
  const status = document.querySelector('#status');
  const feed = document.querySelector('#agentFeed');
  const runButton = document.querySelector('#agentRun');

  if (status) status.textContent = 'PROJECT INIT ERROR';
  if (feed) {
    const row = document.createElement('div');
    row.className = 'msg grim';
    row.innerHTML = '<b>GRIM</b><div></div>';
    row.querySelector('div').textContent = `Could not create or load a project: ${message}`;
    feed.appendChild(row);
  }
  if (runButton) {
    runButton.disabled = false;
    runButton.textContent = 'RETRY PROJECT SETUP';
  }
  console.error('GrimTheBuilder could not create the first project:', error);
}

export async function ensureInitialProject({
  fetchImpl = fetch,
  reload = () => location.reload(),
} = {}) {
  const listResponse = await fetchImpl('/api/projects', {
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });
  if (!listResponse.ok) throw new Error(await readFailure(listResponse));

  const payload = await listResponse.json();
  const projects = Array.isArray(payload.projects) ? payload.projects : [];
  if (projects.length) return { created: false, project: projects[0] };

  const createResponse = await fetchImpl('/api/projects', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(DEFAULT_PROJECT),
  });
  if (!createResponse.ok) throw new Error(await readFailure(createResponse));

  const created = await createResponse.json();
  reload();
  return { created: true, project: created.project };
}

async function bootFirstProject() {
  try {
    await ensureInitialProject();
  } catch (error) {
    showStartupFailure(error);
  }
}

async function recoverMissingProject(event) {
  const button = event.target.closest?.('#agentRun');
  if (!button || document.querySelector('#projectList .item')) return;

  event.preventDefault();
  event.stopImmediatePropagation();
  button.disabled = true;
  button.textContent = 'CREATING PROJECT…';

  try {
    const result = await ensureInitialProject();
    if (!result.created) location.reload();
  } catch (error) {
    showStartupFailure(error);
  }
}

if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  document.addEventListener('click', recoverMissingProject, true);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootFirstProject, { once: true });
  } else {
    bootFirstProject();
  }
}
