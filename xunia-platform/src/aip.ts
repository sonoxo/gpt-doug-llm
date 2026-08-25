import { randomUUID } from 'node:crypto';
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
  status: 'approval_required' | 'executed' | 'blocked';
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
  details: Record<string, unknown>;
};

export class ToolRegistry {
  private tools = new Map<string, ToolSpec>();
  register(tool: ToolSpec) { this.tools.set(tool.name, tool); return tool; }
  get(name: string) { return this.tools.get(name) ?? null; }
  list() { return [...this.tools.values()].map(({ execute: _execute, ...tool }) => tool); }
}

export class ModelGateway {
  constructor(
    private endpoint = process.env.XUNIA_MODEL_URL ?? '',
    private token = process.env.XUNIA_MODEL_TOKEN ?? ''
  ) {}

  async complete(system: string, message: string, context: unknown[]): Promise<string> {
    if (!this.endpoint) {
      const summary = context.length ? ` Grounded on ${context.length} ontology object(s).` : '';
      return `AIP analysis: ${message.trim()}${summary}`;
    }
    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        ...(this.token ? { authorization: `Bearer ${this.token}` } : {})
      },
      body: JSON.stringify({ system, message, context })
    });
    if (!response.ok) throw new Error(`model_gateway_${response.status}`);
    const body = await response.json() as { text?: string; response?: string; output?: string };
    return body.text ?? body.response ?? body.output ?? 'Model returned no text.';
  }
}

export class AipEngine {
  readonly tools = new ToolRegistry();
  readonly agents = new Map<string, AgentSpec>();
  readonly audits: AuditRecord[] = [];
  readonly runs = new Map<string, AipRun>();

  constructor(readonly ontology: OntologyStore, readonly model = new ModelGateway()) {
    this.registerDefaultTools();
    this.registerAgent({
      id: 'xunia-analyst',
      name: 'XUNIA Analyst',
      system: 'Ground analysis in the ontology, identify evidence and uncertainty, and use registered tools only.',
      tools: ['ontology.search', 'ontology.neighbors', 'telemetry.write'],
      approvalFor: ['high']
    });
    this.registerAgent({
      id: 'xunia-operator',
      name: 'XUNIA Operator',
      system: 'Operate XUNIA services through registered tools. Prefer reversible and auditable actions.',
      tools: ['ontology.search', 'ontology.neighbors', 'telemetry.write'],
      approvalFor: ['medium', 'high']
    });
  }

  registerAgent(agent: AgentSpec) { this.agents.set(agent.id, agent); return agent; }

  private audit(runId: string, event: string, details: Record<string, unknown>) {
    const record = { id: randomUUID(), at: new Date().toISOString(), runId, event, details };
    this.audits.push(record);
    return record;
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
      name: 'telemetry.write',
      description: 'Write an aggregate AIP event to the configured SONOXO telemetry endpoint.',
      risk: 'medium',
      execute: async (input) => {
        const url = process.env.SONOXO_URL ?? 'http://127.0.0.1:3001/api/sonoxo/harvest';
        const response = await fetch(url, {
          method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ type: 'xunia.aip', payload: input })
        });
        if (!response.ok) throw new Error(`telemetry_${response.status}`);
        return response.json();
      }
    });
  }

  private proposedSteps(message: string): Omit<PlanStep, 'id' | 'status'>[] {
    const lower = message.toLowerCase();
    const steps: Omit<PlanStep, 'id' | 'status'>[] = [
      { tool: 'ontology.search', input: { query: message.slice(0, 160) }, reason: 'Ground the request in known XUNIA objects.' }
    ];
    const idMatch = message.match(/[a-z]+:[a-z0-9._-]+/i);
    if (idMatch) steps.push({ tool: 'ontology.neighbors', input: { id: idMatch[0] }, reason: 'Expand the requested object through ontology links.' });
    if (/telemetry|record|audit|harvest/.test(lower)) {
      steps.push({ tool: 'telemetry.write', input: { message }, reason: 'Record aggregate operational telemetry.' });
    }
    return steps;
  }

  async run(agentId: string, message: string, contextIds: string[] = []): Promise<AipRun> {
    const agent = this.agents.get(agentId);
    if (!agent) throw new Error('agent_not_found');
    if (!message.trim()) throw new Error('message_required');

    const id = randomUUID();
    const context = contextIds.map((objectId) => this.ontology.getObject(objectId)).filter(Boolean);
    const response = await this.model.complete(agent.system, message, context);
    const steps: PlanStep[] = [];

    for (const proposal of this.proposedSteps(message)) {
      const tool = this.tools.get(proposal.tool);
      const stepId = randomUUID();
      if (!tool || !agent.tools.includes(proposal.tool)) {
        steps.push({ ...proposal, id: stepId, status: 'blocked' });
        this.audit(id, 'tool_blocked', { tool: proposal.tool });
        continue;
      }
      if (agent.approvalFor.includes(tool.risk)) {
        steps.push({ ...proposal, id: stepId, status: 'approval_required' });
        this.audit(id, 'approval_required', { stepId, tool: tool.name, risk: tool.risk });
        continue;
      }
      try {
        const output = await tool.execute(proposal.input);
        steps.push({ ...proposal, id: stepId, status: 'executed', output });
        this.audit(id, 'tool_executed', { stepId, tool: tool.name, risk: tool.risk });
      } catch (error) {
        steps.push({ ...proposal, id: stepId, status: 'blocked', output: { error: error instanceof Error ? error.message : 'tool_failed' } });
        this.audit(id, 'tool_failed', { stepId, tool: tool.name });
      }
    }

    const run: AipRun = { id, agentId, message, createdAt: new Date().toISOString(), context, response, steps };
    this.runs.set(id, run);
    this.audit(id, 'run_completed', { agentId, steps: steps.length });
    return run;
  }

  async approve(runId: string, stepId: string) {
    const run = this.runs.get(runId);
    if (!run) throw new Error('run_not_found');
    const step = run.steps.find((candidate) => candidate.id === stepId);
    if (!step || step.status !== 'approval_required') throw new Error('step_not_approvable');
    const agent = this.agents.get(run.agentId)!;
    const tool = this.tools.get(step.tool);
    if (!tool || !agent.tools.includes(step.tool)) throw new Error('tool_not_allowed');
    try {
      step.output = await tool.execute(step.input);
      step.status = 'executed';
      this.audit(runId, 'step_approved_and_executed', { stepId, tool: tool.name });
    } catch (error) {
      step.status = 'blocked';
      step.output = { error: error instanceof Error ? error.message : 'tool_failed' };
      this.audit(runId, 'approved_step_failed', { stepId, tool: tool.name });
    }
    return run;
  }
}
