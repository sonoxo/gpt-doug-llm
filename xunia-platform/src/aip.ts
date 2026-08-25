import { createHash, randomUUID } from 'node:crypto';
import { JsonState } from './persistence.js';
import { OntologyStore } from './ontology.js';

export type ToolRisk = 'low' | 'medium' | 'high';
export type ToolSpec = {
  name: string;
  description: string;
  risk: ToolRisk;
  execute: (input: Record<string, unknown>) => Promise<unknown>;
};

export type AgentSpec = {
  id: string;
  name: string;
  system: string;
  tools: string[];
  approvalFor: ToolRisk[];
};

export type PlanStep = {
  id: string;
  tool: string;
  input: Record<string, unknown>;
  reason: string;
  status: 'approval_required' | 'executing' | 'executed' | 'blocked';
  output?: unknown;
};

export type AipRun = {
  id: string;
  agentId: string;
  message: string;
  createdAt: string;
  context: unknown[];
  response: string;
  steps: PlanStep[];
};

export type AuditRecord = {
  id: string;
  at: string;
  runId: string;
  event: string;
  actor: string;
  details: Record<string, unknown>;
  prevHash: string;
  hash: string;
};

type AipState = { audits: AuditRecord[]; runs: AipRun[]; agents: AgentSpec[] };

type ProposedStep = Omit<PlanStep, 'id' | 'status'>;

export class ToolRegistry {
  private tools = new Map<string, ToolSpec>();
  register(tool: ToolSpec) { this.tools.set(tool.name, tool); return tool; }
  get(name: string) { return this.tools.get(name) ?? null; }
  list() { return [...this.tools.values()].map(({ execute: _execute, ...tool }) => tool); }
}

export class ModelGateway {
  constructor(
    private endpoint = process.env.XUNIA_MODEL_URL ?? '',
    private token = process.env.XUNIA_MODEL_TOKEN ?? '',
    private timeoutMs = Math.max(1_000, Number(process.env.XUNIA_MODEL_TIMEOUT_MS ?? 30_000))
  ) {}

  async complete(system: string, message: string, context: unknown[]): Promise<string> {
    if (!this.endpoint) {
      const summary = context.length ? ` Grounded on ${context.length} ontology object(s).` : '';
      return `AIP analysis: ${message.trim()}${summary}`;
    }
    const response = await fetch(this.endpoint, {
      method: 'POST',
      signal: AbortSignal.timeout(this.timeoutMs),
      headers: {
        'content-type': 'application/json',
        ...(this.token ? { authorization: `Bearer ${this.token}` } : {})
      },
      body: JSON.stringify({ system, message, context })
    });
    if (!response.ok) throw new Error(`model_gateway_${response.status}`);
    const payload = await response.json() as { text?: string; response?: string; output?: string };
    return payload.text ?? payload.response ?? payload.output ?? 'Model returned no text.';
  }

  status() { return this.endpoint ? 'configured' : 'local-fallback'; }
}

export class AipEngine {
  readonly tools = new ToolRegistry();
  readonly agents = new Map<string, AgentSpec>();
  readonly audits: AuditRecord[] = [];
  readonly runs = new Map<string, AipRun>();
  private state: JsonState<AipState>;

  constructor(readonly ontology: OntologyStore, readonly model = new ModelGateway(), stateFile?: string) {
    this.state = new JsonState(stateFile);
    this.registerDefaultTools();
    this.registerBuiltins();
    const stored = this.state.read({ audits: [], runs: [], agents: [] });
    this.audits.push(...stored.audits.slice(-5_000));
    for (const run of stored.runs.slice(-1_000)) this.runs.set(run.id, run);
    for (const agent of stored.agents) this.registerAgent(agent, false);
  }

  private registerBuiltins() {
    this.registerAgent({
      id: 'xunia-analyst',
      name: 'XUNIA Analyst',
      system: 'Ground analysis in the ontology, identify evidence and uncertainty, and use registered tools only.',
      tools: ['ontology.search', 'ontology.neighbors', 'chain.health', 'telemetry.write'],
      approvalFor: ['medium', 'high']
    }, false);
    this.registerAgent({
      id: 'xunia-operator',
      name: 'XUNIA Operator',
      system: 'Operate XUNIA services through registered tools. Prefer reversible and auditable actions.',
      tools: ['ontology.search', 'ontology.neighbors', 'chain.health', 'telemetry.write'],
      approvalFor: ['medium', 'high']
    }, false);
  }

  registerAgent(agent: AgentSpec, persist = true) {
    if (!agent.id || !agent.name || !agent.system) throw new Error('agent_fields_required');
    if (agent.tools.some((name) => !this.tools.get(name))) throw new Error('agent_tool_unknown');
    if (agent.approvalFor.some((risk) => !['low', 'medium', 'high'].includes(risk))) throw new Error('agent_risk_invalid');
    this.agents.set(agent.id, agent);
    if (persist) this.persist();
    return agent;
  }

  private persist() {
    this.state.write({
      audits: this.audits.slice(-5_000),
      runs: [...this.runs.values()].slice(-1_000),
      agents: [...this.agents.values()]
    });
  }

  private audit(runId: string, event: string, details: Record<string, unknown>, actor = 'system') {
    const prevHash = this.audits.at(-1)?.hash ?? '';
    const base = { id: randomUUID(), at: new Date().toISOString(), runId, event, actor, details, prevHash };
    const hash = createHash('sha256').update(JSON.stringify(base)).digest('hex');
    const record: AuditRecord = { ...base, hash };
    this.audits.push(record);
    if (this.audits.length > 5_000) this.audits.splice(0, this.audits.length - 5_000);
    this.persist();
    return record;
  }

  verifyAuditChain() {
    let prevHash = '';
    for (const record of this.audits) {
      const base = { id: record.id, at: record.at, runId: record.runId, event: record.event, actor: record.actor, details: record.details, prevHash: record.prevHash };
      const hash = createHash('sha256').update(JSON.stringify(base)).digest('hex');
      if (record.prevHash !== prevHash || record.hash !== hash) return { ok: false, recordId: record.id };
      prevHash = record.hash;
    }
    return { ok: true, records: this.audits.length, head: prevHash };
  }

  private registerDefaultTools() {
    this.tools.register({
      name: 'ontology.search',
      description: 'Search XUNIA ontology objects.',
      risk: 'low',
      execute: async (input) => this.ontology.search(String(input.query ?? ''), input.type ? String(input.type) : undefined)
    });
    this.tools.register({
      name: 'ontology.neighbors',
      description: 'Read linked ontology objects for one object id.',
      risk: 'low',
      execute: async (input) => this.ontology.neighbors(String(input.id ?? ''))
    });
    this.tools.register({
      name: 'chain.health',
      description: 'Read XUNIA Chain health from the configured node endpoint.',
      risk: 'low',
      execute: async () => {
        const url = `${(process.env.XUNIA_CHAIN_URL ?? 'http://127.0.0.1:4317').replace(/\/$/, '')}/health`;
        const response = await fetch(url, { signal: AbortSignal.timeout(5_000) });
        if (!response.ok) throw new Error(`chain_health_${response.status}`);
        return response.json();
      }
    });
    this.tools.register({
      name: 'telemetry.write',
      description: 'Write an aggregate AIP event to the configured SONOXO telemetry endpoint.',
      risk: 'medium',
      execute: async (input) => {
        const url = process.env.SONOXO_URL ?? 'http://127.0.0.1:3001/api/sonoxo/harvest';
        const response = await fetch(url, {
          method: 'POST', signal: AbortSignal.timeout(5_000), headers: { 'content-type': 'application/json' }, body: JSON.stringify({ type: 'xunia.aip', payload: input })
        });
        if (!response.ok) throw new Error(`telemetry_${response.status}`);
        return response.json();
      }
    });
  }

  private proposedSteps(message: string): ProposedStep[] {
    const lower = message.toLowerCase();
    const steps: ProposedStep[] = [
      { tool: 'ontology.search', input: { query: message.slice(0, 160) }, reason: 'Ground the request in known XUNIA objects.' }
    ];
    const idMatch = message.match(/[a-z]+:[a-z0-9._-]+/i);
    if (idMatch) steps.push({ tool: 'ontology.neighbors', input: { id: idMatch[0] }, reason: 'Expand the requested object through ontology links.' });
    if (/chain health|node health|xunia chain/.test(lower)) {
      steps.push({ tool: 'chain.health', input: {}, reason: 'Read current XUNIA Chain node health.' });
    }
    if (/telemetry|record|audit|harvest/.test(lower)) {
      steps.push({ tool: 'telemetry.write', input: { message }, reason: 'Record aggregate operational telemetry.' });
    }
    return steps;
  }

  private isGroundingTool(name: string) {
    return name === 'ontology.search' || name === 'ontology.neighbors';
  }

  async run(agentId: string, message: string, contextIds: string[] = [], actor = 'system'): Promise<AipRun> {
    const agent = this.agents.get(agentId);
    if (!agent) throw new Error('agent_not_found');
    if (!message.trim()) throw new Error('message_required');
    if (message.length > 20_000) throw new Error('message_too_large');

    const id = randomUUID();
    const explicitContext = contextIds.slice(0, 100).map((objectId) => this.ontology.getObject(objectId)).filter(Boolean);
    const context: unknown[] = [...explicitContext];
    const steps: PlanStep[] = [];
    const proposals = this.proposedSteps(message);
    const grounding = new Set<ProposedStep>();

    // Ground the model before completion. Browser-console calls may provide no contextIds,
    // so ontology search/neighborhood results must be available to the model itself.
    for (const proposal of proposals) {
      if (!this.isGroundingTool(proposal.tool)) continue;
      grounding.add(proposal);
      const tool = this.tools.get(proposal.tool);
      const stepId = randomUUID();
      if (!tool || !agent.tools.includes(proposal.tool)) {
        steps.push({ ...proposal, id: stepId, status: 'blocked' });
        this.audit(id, 'tool_blocked', { tool: proposal.tool }, actor);
        continue;
      }
      try {
        const output = await tool.execute(proposal.input);
        steps.push({ ...proposal, id: stepId, status: 'executed', output });
        context.push({ source: proposal.tool, input: proposal.input, output });
        this.audit(id, 'tool_executed', { stepId, tool: tool.name, risk: tool.risk, phase: 'grounding' }, actor);
      } catch (error) {
        steps.push({ ...proposal, id: stepId, status: 'blocked', output: { error: error instanceof Error ? error.message : 'tool_failed' } });
        this.audit(id, 'tool_failed', { stepId, tool: tool.name, phase: 'grounding' }, actor);
      }
    }

    const response = await this.model.complete(agent.system, message, context);

    for (const proposal of proposals) {
      if (grounding.has(proposal)) continue;
      const tool = this.tools.get(proposal.tool);
      const stepId = randomUUID();
      if (!tool || !agent.tools.includes(proposal.tool)) {
        steps.push({ ...proposal, id: stepId, status: 'blocked' });
        this.audit(id, 'tool_blocked', { tool: proposal.tool }, actor);
        continue;
      }
      if (agent.approvalFor.includes(tool.risk)) {
        steps.push({ ...proposal, id: stepId, status: 'approval_required' });
        this.audit(id, 'approval_required', { stepId, tool: tool.name, risk: tool.risk }, actor);
        continue;
      }
      try {
        const output = await tool.execute(proposal.input);
        steps.push({ ...proposal, id: stepId, status: 'executed', output });
        this.audit(id, 'tool_executed', { stepId, tool: tool.name, risk: tool.risk }, actor);
      } catch (error) {
        steps.push({ ...proposal, id: stepId, status: 'blocked', output: { error: error instanceof Error ? error.message : 'tool_failed' } });
        this.audit(id, 'tool_failed', { stepId, tool: tool.name }, actor);
      }
    }

    const run: AipRun = { id, agentId, message, createdAt: new Date().toISOString(), context, response, steps };
    this.runs.set(id, run);
    this.audit(id, 'run_completed', { agentId, steps: steps.length }, actor);
    return run;
  }

  getRun(id: string) { return this.runs.get(id) ?? null; }
  listRuns(limit = 100) { return [...this.runs.values()].slice(-Math.max(1, Math.min(limit, 500))).reverse(); }

  async approve(runId: string, stepId: string, actor = 'system') {
    const run = this.runs.get(runId);
    if (!run) throw new Error('run_not_found');
    const step = run.steps.find((candidate) => candidate.id === stepId);
    if (!step || step.status !== 'approval_required') throw new Error('step_not_approvable');
    const agent = this.agents.get(run.agentId)!;
    const tool = this.tools.get(step.tool);
    if (!tool || !agent.tools.includes(step.tool)) throw new Error('tool_not_allowed');

    // Claim the step synchronously before the first await. A concurrent approval now sees
    // `executing` and fails closed instead of invoking the side effect twice.
    step.status = 'executing';
    this.persist();
    this.audit(runId, 'step_approval_claimed', { stepId, tool: tool.name }, actor);

    try {
      step.output = await tool.execute(step.input);
      step.status = 'executed';
      this.audit(runId, 'step_approved_and_executed', { stepId, tool: tool.name }, actor);
    } catch (error) {
      step.status = 'blocked';
      step.output = { error: error instanceof Error ? error.message : 'tool_failed' };
      this.audit(runId, 'approved_step_failed', { stepId, tool: tool.name }, actor);
    }
    this.persist();
    return run;
  }

  persistenceStatus() { return this.state.status(); }
}
