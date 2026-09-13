"""Version-bound, single-use authorization receipts for ZYRA-CTE."""

from copy import deepcopy
from dataclasses import asdict

from research_lab.approval import ApprovalGate, digest

from .engine import CounterfactualTransactionEngine
from .models import ProposedTransition, StateSnapshot, TransactionResult


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


class ReceiptAuthorizer:
    """Consumes a valid receipt before allowing synthetic CTE execution."""

    def __init__(self, database, approvers):
        self.gate = ApprovalGate(database, approvers)
        self.engine = CounterfactualTransactionEngine()

    def close(self):
        self.gate.close()

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
