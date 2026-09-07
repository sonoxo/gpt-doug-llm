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
    console.error('GrimTheBuilder could not create the first project:', error);
  }
}

if (typeof window !== 'undefined' && typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootFirstProject, { once: true });
  } else {
    bootFirstProject();
  }
}
