export type GuardianFinding = {
  id: string;
  eyeId: number;
  title: string;
  category: string;
  severity: number;
  confidence: number;
  horizonSeconds: number;
  evidenceCount: number;
  provenanceQuality: number;
  summary: string;
  recommendation: {
    action: string;
    rationale: string;
    reversible: boolean;
    humanApprovalRequired: boolean;
    escalation: string;
  };
};

export const guardianEyes = Array.from({ length: 100 }, (_, i) => ({
  id: i + 1,
  name: `GUARDIAN-EYE-${String(i + 1).padStart(3, "0")}`,
  family: [
    "ENVIRONMENT",
    "MOBILITY",
    "ROBOTICS",
    "INFRASTRUCTURE",
    "CYBER",
    "DATA-INTEGRITY",
    "OPERATIONS",
    "SAFETY",
    "PROVENANCE",
    "SIMULATION",
  ][i % 10],
  status: "ONLINE" as const,
}));

export const guardianActionPolicy = {
  allowed: [
    "WARN",
    "ISOLATE",
    "PAUSE",
    "FAILOVER",
    "INSPECT",
    "PATCH",
    "RETRY",
    "REDUCE_LOAD",
    "DISCONNECT_INTEGRATION",
    "REQUEST_HUMAN_REVIEW",
  ],
  blocked: [
    "WEAPON_USE",
    "TARGET_ENGAGEMENT",
    "COVERT_PERSON_TRACKING",
    "ACCESS_CONTROL_BYPASS",
    "DESTRUCTIVE_CYBER_ACTION",
  ],
};
