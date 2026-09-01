package virginia_llm.safety

default allow := false

# Illustrative OPA/Rego policy for the Safety Shield control plane.
allow if {
  input.identity.verified == true
  input.capability.scope_permits == true
  not input.context.prompt_injection_detected
  input.risk.score < 0.70
  input.action.reversible == true
}

allow if {
  input.identity.verified == true
  input.capability.scope_permits == true
  input.human_approval.valid == true
  input.audit.precommit_written == true
}

deny_reason contains "human_approval_required" if {
  input.action.high_impact == true
  not input.human_approval.valid
}

deny_reason contains "prompt_injection_detected" if {
  input.context.prompt_injection_detected
}

deny_reason contains "scope_violation" if {
  not input.capability.scope_permits
}
