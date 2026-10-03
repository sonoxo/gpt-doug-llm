"""Version-bound, single-use authorization receipts for ZYRA-CTE."""

from copy import deepcopy
from dataclasses import asdict

from research_lab.approval import ApprovalGate, digest, validate_snapshot

from .engine import CounterfactualTransactionEngine
from .models import TransactionResult

RESERVED_DATA_BINDINGS = {
    "ontology_state",
    "proposed_transition",
}


def build_authorization_snapshot(
    state,
    transition,
    code_versions,
    data_versions,
    policy_versions,
):
    """Bind authorization to exact CTE state, transition, code, data and policy."""

    if transition.required_policy not in policy_versions:
        raise ValueError("required policy version is missing")

    if RESERVED_DATA_BINDINGS.intersection(data_versions):
        raise ValueError("reserved CTE data binding name")

    bound_data = deepcopy(data_versions)

    bound_data["ontology_state"] = digest(asdict(state))
    bound_data["proposed_transition"] = digest(asdict(transition))

    return {
        "mission": "zyra-cte",
        "action": transition.transition_id,
        "code": deepcopy(code_versions),
        "data": bound_data,
        "policy": deepcopy(policy_versions),
    }


def build_authorization_binding(
    state,
    transition,
    code_versions,
    data_versions,
    policy_versions,
):
    """Return the validated digest bound to an authorization snapshot."""

    snapshot = build_authorization_snapshot(
        state,
        transition,
        code_versions,
        data_versions,
        policy_versions,
    )

    return validate_snapshot(snapshot)


class ReceiptAuthorizer:
    """Consumes a valid receipt before allowing synthetic CTE execution."""

    def __init__(self, database, approvers):
        self.gate = ApprovalGate(database, approvers)
        self.engine = CounterfactualTransactionEngine()

    def close(self):
        self.gate.close()

    def begin_attempt(
        self,
        journal,
        attempt_id,
        state,
        transition,
        code_versions,
        data_versions,
        policy_versions,
        now,
    ):
        """Bind a durable attempt to the exact authorization snapshot."""

        binding = build_authorization_binding(
            state,
            transition,
            code_versions,
            data_versions,
            policy_versions,
        )

        return journal.start(
            attempt_id,
            transition.transition_id,
            state.version,
            now,
            request_binding=binding,
        )

    def issue(
        self,
        state,
        transition,
        code_versions,
        data_versions,
        policy_versions,
        authenticated_approver,
        now,
        ttl=300,
    ):
        snapshot = build_authorization_snapshot(
            state,
            transition,
            code_versions,
            data_versions,
            policy_versions,
        )

        return self.gate.issue(
            snapshot,
            authenticated_approver,
            now,
            ttl,
        )

    def execute_durable(
        self,
        journal,
        attempt_id,
        token,
        state,
        transition,
        code_versions,
        data_versions,
        policy_versions,
        now,
        observed_override=None,
    ):
        """Execute a synthetic transaction through the durable CTE lifecycle."""

        attempt = self.begin_attempt(
            journal,
            attempt_id,
            state,
            transition,
            code_versions,
            data_versions,
            policy_versions,
            now,
        )

        branch_id = f"cf-{transition.transition_id}"

        if attempt.phase in {"COMMITTED", "ROLLED_BACK"}:
            events = journal.events(attempt_id)
            payload = events[-1].payload if events else {}

            return TransactionResult(
                status=payload.get("result_status", attempt.phase),
                branch_id=branch_id,
                reason=payload.get("reason"),
            )

        if attempt.phase != "PROPOSED":
            return TransactionResult(
                status="RECOVERY_REQUIRED",
                branch_id=branch_id,
                reason=(
                    "durable attempt already persisted in "
                    f"{attempt.phase}; explicit recovery required"
                ),
            )

        snapshot = build_authorization_snapshot(
            state,
            transition,
            code_versions,
            data_versions,
            policy_versions,
        )

        binding = validate_snapshot(snapshot)

        branch = self.engine.fork(
            state,
            transition,
        )

        simulation = self.engine.simulate(
            branch,
            transition,
        )

        journal.advance(
            attempt_id,
            "SIMULATED",
            now,
            {
                "allowed": simulation.allowed,
                "reasons": simulation.reasons,
                "expected_state_digest": digest(
                    simulation.expected_state
                ),
            },
        )

        if not simulation.allowed:
            reason = "; ".join(simulation.reasons)

            journal.advance(
                attempt_id,
                "ROLLED_BACK",
                now,
                {
                    "result_status": "REJECTED",
                    "reason": reason,
                },
            )

            return TransactionResult(
                status="REJECTED",
                branch_id=branch.branch_id,
                reason=reason,
            )

        if not self.gate.consume(token, snapshot, now):
            reason = (
                "receipt missing, expired, replayed, "
                "or version binding changed"
            )

            journal.advance(
                attempt_id,
                "ROLLED_BACK",
                now,
                {
                    "result_status": "AUTHORIZATION_DENIED",
                    "reason": reason,
                },
            )

            return TransactionResult(
                status="AUTHORIZATION_DENIED",
                branch_id=branch.branch_id,
                reason=reason,
            )

        journal.advance(
            attempt_id,
            "AUTHORIZED",
            now,
            {
                "authorization_binding": binding,
            },
        )

        journal.advance(
            attempt_id,
            "EXECUTING",
            now,
            {
                "executor": "synthetic",
            },
        )

        observed = (
            deepcopy(observed_override)
            if observed_override is not None
            else self.engine.execute_synthetic(branch)
        )

        journal.advance(
            attempt_id,
            "OBSERVED",
            now,
            {
                "observed_state_digest": digest(observed),
            },
        )

        reconciliation = self.engine.reconcile(
            simulation.expected_state,
            observed,
        )

        if reconciliation.decision == "COMMIT":
            journal.advance(
                attempt_id,
                "COMMITTED",
                now,
                {
                    "decision": "COMMIT",
                    "result_status": "COMMITTED",
                },
            )

            return TransactionResult(
                status="COMMITTED",
                branch_id=branch.branch_id,
            )

        reason = repr(reconciliation.drift)

        journal.advance(
            attempt_id,
            "ROLLED_BACK",
            now,
            {
                "decision": "ROLLBACK",
                "drift_digest": digest(reconciliation.drift),
                "drift_keys": sorted(reconciliation.drift),
                "reason": reason,
                "result_status": "ROLLED_BACK",
            },
        )

        return TransactionResult(
            status="ROLLED_BACK",
            branch_id=branch.branch_id,
            reason=reason,
        )

    def execute(
        self,
        token,
        state,
        transition,
        code_versions,
        data_versions,
        policy_versions,
        now,
        observed_override=None,
    ):
        snapshot = build_authorization_snapshot(
            state,
            transition,
            code_versions,
            data_versions,
            policy_versions,
        )

        if not self.gate.consume(token, snapshot, now):
            return TransactionResult(
                status="AUTHORIZATION_DENIED",
                branch_id=f"cf-{transition.transition_id}",
                reason="receipt missing, expired, replayed, or version binding changed",
            )

        return self.engine.run(
            state,
            transition,
            human_approved=True,
            observed_override=observed_override,
        )
