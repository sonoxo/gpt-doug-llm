package virginia_llm.frontline_compliance

default allow_build := false
default allow_deploy := false

default state := "RED"

# Build is permitted only when the manifest is complete enough for the current
# mission/data/environment and no hard-deny condition is present.
allow_build if {
  input.mission.owner != ""
  input.mission.use_case != ""
  input.data.classification != "UNKNOWN"
  input.environment.authorized == true
  input.security.threat_model_complete == true
  input.security.rollback_defined == true
  input.security.audit_enabled == true
  not hard_deny
  not unresolved_review
}

# Deployment requires the stronger release evidence set.
allow_deploy if {
  allow_build
  input.release.tests_passed == true
  input.release.evals_passed == true
  input.release.owner_approved == true
  input.release.version != ""
  input.release.audit_receipt != ""
}

state := "BLACK" if {
  input.incident.controlled_data_spill == true
}

state := "RED" if {
  hard_deny
  not input.incident.controlled_data_spill
}

state := "AMBER" if {
  not hard_deny
  unresolved_review
}

state := "GREEN" if {
  allow_build
}

# Hard-deny conditions.
hard_deny if {
  input.mission.autonomous_weapon_release == true
}

hard_deny if {
  input.mission.autonomous_target_selection == true
}

hard_deny if {
  input.mission.unrestricted_offensive_cyber == true
}

hard_deny if {
  input.data.classification == "CLASSIFIED"
  input.environment.classified_accredited != true
}

hard_deny if {
  input.data.contains_secret_credentials == true
  input.model.prompt_includes_secret_credentials == true
}

hard_deny if {
  input.data.classification == "CUI"
  input.model.external_egress == true
  input.model.authorized_for_data_class != true
}

hard_deny if {
  input.data.classification == "CUI_CTI"
  input.model.external_egress == true
  input.model.authorized_for_data_class != true
}

hard_deny if {
  input.data.classification == "EXPORT_CONTROLLED"
  input.export.recipient_authorized != true
}

hard_deny if {
  input.data.classification == "EXPORT_CONTROLLED"
  input.model.external_egress == true
  input.model.authorized_for_export_controlled != true
}

# Review is required when a triggered compliance question is unresolved.
unresolved_review if {
  input.export.jurisdiction_status == "UNRESOLVED"
}

unresolved_review if {
  input.contract.cui_required == true
  input.contract.required_cmmc_status == "UNKNOWN"
}

unresolved_review if {
  input.data.classification == "CLASSIFIED"
  input.security.program_authorization_verified != true
}

unresolved_review if {
  input.mission.material_external_action == true
  input.mission.human_approval_required == true
  input.release.human_approval_record == ""
}

unresolved_review if {
  input.environment.required_impact_level != ""
  input.environment.actual_impact_level != input.environment.required_impact_level
}
