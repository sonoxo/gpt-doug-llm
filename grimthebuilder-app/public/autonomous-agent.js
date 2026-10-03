const SUPPORTED_MODES = new Set(['build', 'fix', 'plan', 'explain']);
const MAX_REPAIRS = 3;

function abortError() {
  const error = new Error('Agent run cancelled.');
  error.name = 'AbortError';
  return error;
}

function assertActive(signal) {
  if (signal?.aborted) throw abortError();
}

function asText(value, limit = 6000) {
  if (typeof value === 'string') return value.slice(0, limit);
  try {
    return JSON.stringify(value, null, 2).slice(0, limit);
  } catch {
    return String(value).slice(0, limit);
  }
}

export class AutonomousWorkflowError extends Error {
  constructor(message, { stage = 'unknown', attempts = 0, failure = null } = {}) {
    super(message);
    this.name = 'AutonomousWorkflowError';
    this.stage = stage;
    this.attempts = attempts;
    this.failure = failure;
  }
}

export function buildRepairPrompt({ originalPrompt, failure, repairAttempt }) {
  const stage = failure?.stage || 'runtime';
  const detail = failure?.detail || failure?.error || failure?.message || 'Unknown failure';
  const logs = failure?.logs || failure?.output || failure?.runtime?.logs || '';
  return [
    `REPAIR ATTEMPT ${repairAttempt} OF ${MAX_REPAIRS}.`,
    'Fix the existing project; do not replace working features with a mockup.',
    'Return only the normal GrimTheBuilder JSON file-operation response.',
    'Make the smallest complete change that resolves the verified failure.',
    '',
    `ORIGINAL REQUEST:\n${asText(originalPrompt, 5000)}`,
    '',
    `FAILED STAGE: ${stage}`,
    `FAILURE DETAIL:\n${asText(detail, 2500)}`,
    logs ? `RUNTIME OUTPUT:\n${asText(logs, 5000)}` : '',
    '',
    'After the fix, preserve process.env.PORT or PORT support, bind servers to 0.0.0.0, and keep GET /api/health when a backend exists.',
  ].filter(Boolean).join('\n');
}

function normalizeFailure(stage, error, extra = {}) {
  const detail = error?.message || extra.detail || 'Unknown failure';
  return {
    stage,
    detail,
    error: detail,
    logs: extra.logs || error?.logs || error?.output || '',
    runtime: extra.runtime || error?.runtime || null,
  };
}

export async function runAutonomousWorkflow({
  prompt,
  mode = 'build',
  maxRepairs = MAX_REPAIRS,
  generate,
  apply,
  inspect,
  install,
  start,
  verify,
  onStage = () => {},
  signal,
}) {
  const request = String(prompt || '').trim();
  if (!request) throw new Error('Agent prompt is required.');
  if (!SUPPORTED_MODES.has(mode)) throw new Error(`Unsupported agent mode: ${mode}`);
  if (![generate, apply, inspect, install, start, verify].every(fn => typeof fn === 'function')) {
    throw new Error('Autonomous workflow dependencies are incomplete.');
  }

  const repairLimit = Math.max(0, Math.min(MAX_REPAIRS, Number(maxRepairs) || 0));
  const emit = (stage, status, detail = '', attempt = 0, data = null) => {
    onStage({ stage, status, detail, attempt, data, time: new Date().toISOString() });
  };

  assertActive(signal);
  emit('analyze', 'running', 'Reading project and preparing model context.');
  const initial = await generate({ prompt: request, mode, attempt: 0, signal, emit });
  assertActive(signal);
  emit('apply', 'running', `Applying ${initial.operations?.length || 0} file operation(s).`);
  await apply(initial.operations || [], mode, { attempt: 0, signal });
  emit('apply', 'success', 'Generated files applied.');

  if (mode === 'plan' || mode === 'explain') {
    emit('complete', 'success', `${mode.toUpperCase()} completed without runtime changes.`);
    return { ...initial, verified: false, runtime: null, repairs: 0 };
  }

  let repairs = 0;
  let latest = initial;
  let lastFailure = null;

  while (true) {
    assertActive(signal);
    let inspection;
    try {
      emit('inspect', 'running', 'Detecting project runtime and dependencies.', repairs);
      inspection = await inspect({ signal });
      emit('inspect', 'success', `${inspection.kind || 'project'} runtime detected.`, repairs, inspection);
    } catch (error) {
      lastFailure = normalizeFailure('inspect', error);
    }

    if (!lastFailure && inspection?.needsInstall) {
      try {
        emit('install', 'running', inspection.installLabel || 'Installing declared dependencies.', repairs);
        const installed = await install(inspection, { signal });
        emit('install', 'success', installed?.detail || 'Dependencies installed.', repairs, installed);
      } catch (error) {
        lastFailure = normalizeFailure('install', error);
      }
    } else if (!lastFailure) {
      emit('install', 'skipped', 'No dependency installation required.', repairs);
    }

    let runtime = null;
    if (!lastFailure) {
      try {
        emit('start', 'running', inspection?.kind === 'static' ? 'Opening static preview.' : 'Starting application runtime.', repairs);
        runtime = await start(inspection, { signal });
        emit('start', 'success', runtime?.detail || 'Runtime started.', repairs, runtime);
      } catch (error) {
        lastFailure = normalizeFailure('start', error);
      }
    }

    if (!lastFailure) {
      try {
        emit('verify', 'running', 'Checking preview and application health.', repairs);
        const verification = await verify(runtime, inspection, { signal });
        if (verification?.verified === true) {
          emit('verify', 'success', verification.detail || 'Application verified.', repairs, verification);
          emit('complete', 'success', 'Build, runtime, and preview verified.', repairs);
          return {
            ...latest,
            verified: true,
            verification,
            runtime,
            inspection,
            repairs,
          };
        }
        lastFailure = normalizeFailure('verify', null, {
          detail: verification?.detail || 'Application health verification failed.',
          logs: verification?.logs || '',
          runtime,
        });
        emit('verify', 'failed', lastFailure.detail, repairs, verification);
      } catch (error) {
        lastFailure = normalizeFailure('verify', error, { runtime });
      }
    }

    if (repairs >= repairLimit) {
      emit('failed', 'failed', lastFailure?.detail || 'Autonomous runtime failed.', repairs, lastFailure);
      throw new AutonomousWorkflowError(
        `Autonomous runtime failed after ${repairs} repair attempt(s): ${lastFailure?.detail || 'unknown failure'}`,
        { stage: lastFailure?.stage, attempts: repairs, failure: lastFailure },
      );
    }

    repairs += 1;
    assertActive(signal);
    emit('repair', 'running', `Repairing ${lastFailure.stage} failure (${repairs}/${repairLimit}).`, repairs, lastFailure);
    const repairPrompt = buildRepairPrompt({ originalPrompt: request, failure: lastFailure, repairAttempt: repairs });
    latest = await generate({ prompt: repairPrompt, mode: 'fix', attempt: repairs, signal, emit });
    assertActive(signal);
    emit('apply', 'running', `Applying repair ${repairs}: ${latest.operations?.length || 0} file operation(s).`, repairs);
    await apply(latest.operations || [], 'fix', { attempt: repairs, signal });
    emit('apply', 'success', `Repair ${repairs} applied.`, repairs);
    lastFailure = null;
  }
}
