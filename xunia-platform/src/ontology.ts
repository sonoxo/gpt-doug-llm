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

export class OntologyStore {
  private objects = new Map<string, OntologyObject>();
  private links = new Map<string, OntologyLink>();

  seed() {
    this.upsertObject({ id: 'zone:virginia-local', type: 'Zone', properties: { name: 'Virginia Local', region: 'virginia-local' } });
    this.upsertObject({ id: 'service:sonoxo', type: 'Service', properties: { name: 'SONOXO', endpoint: '/api/sonoxo/harvest' } });
    this.upsertObject({ id: 'chain:xunia', type: 'Blockchain', properties: { name: 'XUNIA Chain', symbol: 'XUN' } });
    this.upsertLink({ id: 'link:zone-sonoxo', type: 'HOSTS', from: 'zone:virginia-local', to: 'service:sonoxo', properties: {} });
    this.upsertLink({ id: 'link:sonoxo-chain', type: 'OBSERVES', from: 'service:sonoxo', to: 'chain:xunia', properties: {} });
  }

  upsertObject(input: Omit<OntologyObject, 'updatedAt'> & { updatedAt?: string }): OntologyObject {
    if (!input.id || !input.type) throw new Error('object_id_and_type_required');
    const object: OntologyObject = { ...input, updatedAt: input.updatedAt ?? new Date().toISOString() };
    this.objects.set(object.id, object);
    return object;
  }

  upsertLink(link: OntologyLink): OntologyLink {
    if (!link.id || !link.type || !link.from || !link.to) throw new Error('link_fields_required');
    if (!this.objects.has(link.from) || !this.objects.has(link.to)) throw new Error('link_endpoint_missing');
    this.links.set(link.id, link);
    return link;
  }

  getObject(id: string) { return this.objects.get(id) ?? null; }

  search(query = '', type?: string) {
    const q = query.trim().toLowerCase();
    return [...this.objects.values()].filter((object) => {
      if (type && object.type !== type) return false;
      if (!q) return true;
      const haystack = JSON.stringify(object).toLowerCase();
      return haystack.includes(q);
    });
  }

  neighbors(id: string) {
    const connected = [...this.links.values()].filter((link) => link.from === id || link.to === id);
    return connected.map((link) => ({ link, object: this.objects.get(link.from === id ? link.to : link.from) ?? null }));
  }

  snapshot() {
    return { objects: [...this.objects.values()], links: [...this.links.values()] };
  }
}
