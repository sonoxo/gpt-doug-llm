import { JsonState } from './persistence.js';

export type OntologyObject = {
  id: string;
  type: string;
  properties: Record<string, unknown>;
  updatedAt: string;
};

export type OntologyLink = {
  id: string;
  type: string;
  from: string;
  to: string;
  properties: Record<string, unknown>;
};

export type OntologySnapshot = { objects: OntologyObject[]; links: OntologyLink[] };

export class OntologyStore {
  private objects = new Map<string, OntologyObject>();
  private links = new Map<string, OntologyLink>();
  private state: JsonState<OntologySnapshot>;

  constructor(file?: string) {
    this.state = new JsonState(file);
    const stored = this.state.read({ objects: [], links: [] });
    for (const object of stored.objects) this.objects.set(object.id, object);
    for (const link of stored.links) this.links.set(link.id, link);
  }

  seed() {
    if (this.objects.size) return;
    this.upsertObject({ id: 'zone:virginia-local', type: 'Zone', properties: { name: 'Virginia Local', region: 'virginia-local' } });
    this.upsertObject({ id: 'service:sonoxo', type: 'Service', properties: { name: 'SONOXO', endpoint: '/api/sonoxo/harvest' } });
    this.upsertObject({ id: 'chain:xunia', type: 'Blockchain', properties: { name: 'XUNIA Chain', symbol: 'XUN' } });
    this.upsertLink({ id: 'link:zone-sonoxo', type: 'HOSTS', from: 'zone:virginia-local', to: 'service:sonoxo', properties: {} });
    this.upsertLink({ id: 'link:sonoxo-chain', type: 'OBSERVES', from: 'service:sonoxo', to: 'chain:xunia', properties: {} });
  }

  private persist() { this.state.write(this.snapshot()); }

  upsertObject(input: Omit<OntologyObject, 'updatedAt'> & { updatedAt?: string }): OntologyObject {
    if (!input.id || !input.type) throw new Error('object_id_and_type_required');
    if (input.id.length > 200 || input.type.length > 100) throw new Error('object_identifier_too_long');
    const object: OntologyObject = { ...input, updatedAt: input.updatedAt ?? new Date().toISOString() };
    this.objects.set(object.id, object);
    this.persist();
    return object;
  }

  upsertLink(link: OntologyLink): OntologyLink {
    if (!link.id || !link.type || !link.from || !link.to) throw new Error('link_fields_required');
    if (!this.objects.has(link.from) || !this.objects.has(link.to)) throw new Error('link_endpoint_missing');
    this.links.set(link.id, link);
    this.persist();
    return link;
  }

  deleteLink(id: string) {
    const deleted = this.links.delete(id);
    if (deleted) this.persist();
    return deleted;
  }

  deleteObject(id: string, cascade = false) {
    const connected = [...this.links.values()].filter((link) => link.from === id || link.to === id);
    if (connected.length && !cascade) throw new Error('object_has_links');
    if (cascade) for (const link of connected) this.links.delete(link.id);
    const deleted = this.objects.delete(id);
    if (deleted) this.persist();
    return deleted;
  }

  getObject(id: string) { return this.objects.get(id) ?? null; }
  getLink(id: string) { return this.links.get(id) ?? null; }

  search(query = '', type?: string) {
    const q = query.trim().toLowerCase();
    return [...this.objects.values()].filter((object) => {
      if (type && object.type !== type) return false;
      if (!q) return true;
      return JSON.stringify(object).toLowerCase().includes(q);
    });
  }

  neighbors(id: string) {
    const connected = [...this.links.values()].filter((link) => link.from === id || link.to === id);
    return connected.map((link) => ({ link, object: this.objects.get(link.from === id ? link.to : link.from) ?? null }));
  }

  types() {
    const counts = new Map<string, number>();
    for (const object of this.objects.values()) counts.set(object.type, (counts.get(object.type) ?? 0) + 1);
    return [...counts.entries()].map(([type, count]) => ({ type, count })).sort((a, b) => a.type.localeCompare(b.type));
  }

  snapshot(): OntologySnapshot {
    return { objects: [...this.objects.values()], links: [...this.links.values()] };
  }

  persistenceStatus() { return this.state.status(); }
}
