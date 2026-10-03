export const archiveYears = Array.from({ length: 36 }, (_, i) => 2025 - i);

export function validateYear(value) {
  const year = Number(value);
  return Number.isInteger(year) && year >= 1990 && year <= 2025 ? year : null;
}

export function parseRoute(pathname = '/') {
  const path = pathname.replace(/\/+$/, '') || '/';
  if (path === '/') return { view: 'home' };
  if (path === '/search') return { view: 'search' };
  if (path === '/years') return { view: 'years' };
  const yearMatch = path.match(/^\/years\/(\d{4})$/);
  if (yearMatch) return { view: 'year', year: Number(yearMatch[1]) };
  if (path === '/countries') return { view: 'countries' };
  const profileMatch = path.match(/^\/countries\/([^/]+)(?:\/(\d{4}))?$/);
  if (profileMatch) return { view: 'profile', slug: profileMatch[1], year: profileMatch[2] ? Number(profileMatch[2]) : 2025 };
  if (path === '/compare') return { view: 'compare' };
  if (path === '/rankings') return { view: 'rankings' };
  if (path === '/trends') return { view: 'trends' };
  if (path === '/diff') return { view: 'diff' };
  if (path === '/atlas') return { view: 'atlas' };
  if (path.startsWith('/dossier/')) return { view: 'dossier', slug: path.split('/')[2] };
  if (path === '/resources') return { view: 'resources' };
  return { view: 'not-found' };
}

export function flattenArchive(archive) {
  const rows = [];
  for (const entity of archive.entities || []) {
    const profiles = entity.profiles || {};
    const years = Object.keys(profiles);
    if (!years.length) {
      rows.push({ slug: entity.slug, entity: entity.name, year: null, category: 'Entity', field: 'Entity', content: `${entity.name} — ${entity.region}`, source: null });
      continue;
    }
    for (const year of years) {
      const profile = profiles[year];
      for (const category of profile.categories || []) {
        for (const field of category.fields || []) {
          rows.push({ slug: entity.slug, entity: entity.name, year: Number(year), category: category.title, field: field.name, content: field.content, source: profile.source });
        }
      }
    }
  }
  return rows;
}

function matchesQuery(row, rawQuery) {
  const q = (rawQuery || '').trim().toLowerCase();
  if (!q) return true;
  const hay = `${row.entity} ${row.category} ${row.field} ${row.content}`.toLowerCase();
  const quoted = [...q.matchAll(/"([^"]+)"/g)].map((m) => m[1]);
  if (quoted.length && !quoted.every((phrase) => hay.includes(phrase))) return false;
  const clean = q.replace(/"[^"]+"/g, '').trim();
  if (!clean) return true;
  if (/\s+or\s+/i.test(clean)) return clean.split(/\s+or\s+/i).some((part) => hay.includes(part.trim()));
  const terms = clean.split(/\s+and\s+|\s+/i).filter(Boolean);
  return terms.every((term) => hay.includes(term));
}

export function searchArchive(archive, query = '', filters = {}) {
  return flattenArchive(archive).filter((row) => {
    if (filters.year && row.year && Number(filters.year) !== row.year) return false;
    if (filters.entity && filters.entity !== row.slug) return false;
    if (filters.category && filters.category !== row.category) return false;
    if (filters.field && !row.field.toLowerCase().includes(String(filters.field).toLowerCase())) return false;
    return matchesQuery(row, query);
  });
}

export function getEntity(archive, slug) {
  return (archive.entities || []).find((entity) => entity.slug === slug) || null;
}

export function getProfile(archive, slug, year = 2025) {
  const entity = getEntity(archive, slug);
  if (!entity) return null;
  return { entity, year, profile: entity.profiles?.[String(year)] || null };
}

export function metricRows(archive, metric, year) {
  const rows = [];
  for (const entity of archive.entities || []) {
    const profile = entity.profiles?.[String(year)];
    if (!profile) continue;
    for (const category of profile.categories || []) {
      for (const field of category.fields || []) {
        if (field.metric === metric && Number.isFinite(Number(field.numeric))) {
          rows.push({ slug: entity.slug, entity: entity.name, field: field.name, value: Number(field.numeric), unit: field.unit || '', content: field.content });
        }
      }
    }
  }
  return rows;
}

export function rankEntities(archive, metric, year) {
  return metricRows(archive, metric, year).sort((a, b) => b.value - a.value);
}

export function diffFields(before = [], after = []) {
  const a = new Map(before.map((field) => [field.name, field.content]));
  const b = new Map(after.map((field) => [field.name, field.content]));
  const names = [...new Set([...a.keys(), ...b.keys()])].sort();
  return names.map((name) => {
    const beforeValue = a.get(name);
    const afterValue = b.get(name);
    let status = 'unchanged';
    if (beforeValue == null) status = 'added';
    else if (afterValue == null) status = 'removed';
    else if (beforeValue !== afterValue) status = 'changed';
    return { name, before: beforeValue ?? null, after: afterValue ?? null, status };
  });
}

function csvEscape(value) {
  const str = value == null ? '' : String(value);
  return /[",\n]/.test(str) ? `"${str.replaceAll('"', '""')}"` : str;
}

export function toCsv(rows = []) {
  if (!rows.length) return '';
  const keys = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  return [keys.join(','), ...rows.map((row) => keys.map((key) => csvEscape(row[key])).join(','))].join('\n');
}
