export interface RouteEvidence {
  schemaVersion: "xunia.route-evidence/v1";
  type: "RouteEvidence";
  controlPlane: "THE_BLACK_HOUSE_V1";
  kernelVersion: "3.0.0";
  source: "RVIA";
  executionVerified: false;
  missionId: string;
  target: string;
  executionState: string;
  observedAt: string;
  status: "PLANNED" | "ACCEPTED" | "HOLD" | "REJECTED" | "DENIED" | "APPROVAL_REQUIRED" | "ADAPTER_UNAVAILABLE" | "FAILED";
}
export function parseRouteEvidence(value: unknown): Readonly<RouteEvidence>;
export function extractRouteEvidence(reply: unknown): Readonly<RouteEvidence>;
