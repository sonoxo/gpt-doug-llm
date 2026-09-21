from copy import deepcopy
from typing import Any, Dict, Optional

from .models import (
    CounterfactualBranch,
    ProposedTransition,
    ReconciliationResult,
    SimulationResult,
    StateSnapshot,
    TransactionResult,
)


class CounterfactualTransactionEngine:
    """Synthetic-only ZYRA counterfactual transaction engine."""

    def fork(
        self,
        state: StateSnapshot,
        transition: ProposedTransition,
    ) -> CounterfactualBranch:
        candidate = deepcopy(state.objects)

        for key, value in transition.changes.items():
            if value is None:
                candidate.pop(key, None)
            else:
                candidate[key] = deepcopy(value)

        return CounterfactualBranch(
            branch_id=f"cf-{transition.transition_id}",
            base_version=state.version,
            objects=candidate,
        )

    def simulate(
        self,
        branch: CounterfactualBranch,
        transition: ProposedTransition,
    ) -> SimulationResult:
        reasons = []

        if not transition.actor.strip():
            reasons.append("missing actor")

        if not transition.required_policy.strip():
            reasons.append("missing policy binding")

        if not transition.changes:
            reasons.append("transition contains no changes")

        return SimulationResult(
            allowed=not reasons,
            reasons=reasons,
            expected_state=deepcopy(branch.objects),
        )

    def execute_synthetic(
        self,
        branch: CounterfactualBranch,
    ) -> Dict[str, Any]:
        # No external side effects in v1.
        return deepcopy(branch.objects)

    def reconcile(
        self,
        expected: Dict[str, Any],
        observed: Dict[str, Any],
    ) -> ReconciliationResult:
        drift = {}

        for key in sorted(set(expected) | set(observed)):
            if expected.get(key) != observed.get(key):
                drift[key] = {
                    "expected": expected.get(key),
                    "observed": observed.get(key),
                }

        return ReconciliationResult(
            decision="COMMIT" if not drift else "ROLLBACK",
            drift=drift,
        )

    def run(
        self,
        state: StateSnapshot,
        transition: ProposedTransition,
        human_approved: bool = False,
        observed_override: Optional[Dict[str, Any]] = None,
    ) -> TransactionResult:
        branch = self.fork(state, transition)
        simulation = self.simulate(branch, transition)

        if not simulation.allowed:
            return TransactionResult(
                status="REJECTED",
                branch_id=branch.branch_id,
                reason="; ".join(simulation.reasons),
            )

        if transition.requires_human_approval and not human_approved:
            return TransactionResult(
                status="PENDING_HUMAN_REVIEW",
                branch_id=branch.branch_id,
                reason="human authorization required",
            )

        observed = (
            deepcopy(observed_override)
            if observed_override is not None
            else self.execute_synthetic(branch)
        )

        reconciliation = self.reconcile(
            simulation.expected_state,
            observed,
        )

        return TransactionResult(
            status=(
                "COMMITTED"
                if reconciliation.decision == "COMMIT"
                else "ROLLED_BACK"
            ),
            branch_id=branch.branch_id,
            reason=None if not reconciliation.drift else repr(reconciliation.drift),
        )
