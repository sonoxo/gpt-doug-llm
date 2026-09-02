package shadow_glass.external_model_egress

# Provider-agnostic policy for sending context to any model boundary outside the
# trusted local control plane. This policy does not itself authorize handling
# classified, export-controlled, privileged, regulated, or otherwise restricted data.

default allow := false

default decision := {
  "allow": false,
  "state": "RED",
  "reasons": ["external model egress denied by default"]
}

allowed_data_classes := {"PUBLIC", "INTERNAL"}

registered_model if {
  input.provider.registered == true
  input.model.registered == true
  input.provider.approved == true
  input.model.approved == true
}

approved_contract_controls if {
  input.provider.training_on_customer_data == false
  input.provider.retention_acceptable == true
  input.provider.region_allowed == true
}

request_controls_pass if {
  input.request.purpose_allowed == true
  input.request.minimum_necessary == true
  input.request.redaction_passed == true
  input.request.secrets_present == false
  input.request.audit_enabled == true
}

tool_controls_pass if {
  input.request.tool_scope_valid == true
  input.request.action_scope_valid == true
}

human_gate_pass if {
  input.request.human_review_required == false
}

human_gate_pass if {
  input.request.human_review_required == true
  input.request.human_approval_valid == true
}

allow if {
  registered_model
  approved_contract_controls
  request_controls_pass
  tool_controls_pass
  human_gate_pass
  input.data.classification in allowed_data_classes
}

# Never put credentials or explicitly restricted material into an external-model prompt.
deny_reason contains "secret credential detected" if {
  input.request.secrets_present == true
}

deny_reason contains "provider or model is not registered and approved" if {
  not registered_model
}

deny_reason contains "provider training/retention/region controls failed" if {
  not approved_contract_controls
}

deny_reason contains "request minimization, redaction, purpose, or audit controls failed" if {
  not request_controls_pass
}

deny_reason contains "tool/action scope failed" if {
  not tool_controls_pass
}

deny_reason contains "required human approval missing" if {
  not human_gate_pass
}

deny_reason contains "data classification not eligible for external model egress" if {
  not input.data.classification in allowed_data_classes
}

state := "GREEN" if {
  allow
  input.data.classification == "PUBLIC"
}

state := "AMBER" if {
  allow
  input.data.classification == "INTERNAL"
}

state := "RED" if {
  not allow
}

result := {
  "allow": allow,
  "state": state,
  "reasons": sort([r | r := deny_reason[_]])
}
