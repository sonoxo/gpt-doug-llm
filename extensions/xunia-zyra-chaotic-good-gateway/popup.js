const $ = (id) => document.getElementById(id);
const send = (message) => chrome.runtime.sendMessage(message);

function scanText(scan) {
  if (!scan) return "No scan yet.";
  const lines = [`SHIELD ${scan.state} · risk ${scan.riskScore}/100 · ${scan.findings?.length || 0} finding(s)`];
  for (const finding of (scan.findings || []).slice(0, 6)) {
    lines.push(`${finding.severity.toUpperCase()} ${finding.code}: ${finding.detail}`);
  }
  return lines.join("\n");
}

async function refresh() {
  const response = await send({ type: "GET_STATUS" });
  if (!response?.ok) {
    $("status").textContent = response?.error || "Status unavailable";
    return;
  }
  const { state, tab } = response;
  const arm = state.writeArm || { armed: false, remainingSeconds: 0 };
  $("status").textContent = tab
    ? `${state.shieldEnabled ? "SHIELD ON" : "SHIELD OFF"} · ${state.loopEnabled ? "LOOP ON" : "LOOP OFF"} · ${arm.armed ? `WRITES ARMED ${arm.remainingSeconds}s` : "WRITES DISARMED"}\n${tab.title || "Active tab"}\n${tab.url || ""}`
    : "Open an allowlisted Foundry, GitHub, or localhost tab.";
  $("scan").textContent = scanText(state.latestScan);
  $("snapshot").textContent = state.latestSnapshot
    ? JSON.stringify(state.latestSnapshot, null, 2)
    : "None yet.";
}

async function run(message) {
  const response = await send(message);
  if (!response?.ok) $("status").textContent = `ERROR: ${response?.error || "Unknown error"}`;
  await refresh();
}

$("startLoop").addEventListener("click", () => run({ type: "SET_LOOP", enabled: true, intervalMs: 2000 }));
$("stopLoop").addEventListener("click", () => run({ type: "SET_LOOP", enabled: false }));
$("snapshotNow").addEventListener("click", () => run({ type: "SNAPSHOT_NOW" }));
$("scanNow").addEventListener("click", () => run({ type: "SCAN_NOW" }));
$("shieldOn").addEventListener("click", () => run({ type: "SET_SHIELD", enabled: true }));
$("shieldOff").addEventListener("click", () => run({ type: "SET_SHIELD", enabled: false }));
$("arm").addEventListener("click", () => run({ type: "ARM_WRITES", durationMs: 300000 }));
$("disarm").addEventListener("click", () => run({ type: "DISARM_WRITES" }));
$("panic").addEventListener("click", () => run({ type: "PANIC_STOP" }));

function selector() { return $("selector").value.trim(); }
$("highlight").addEventListener("click", () => run({ type: "ACTION", action: { type: "highlight", selector: selector() } }));
$("focus").addEventListener("click", () => run({ type: "ACTION", action: { type: "focus", selector: selector() } }));
$("click").addEventListener("click", () => run({ type: "ACTION", action: { type: "click", selector: selector() } }));
$("type").addEventListener("click", () => run({ type: "ACTION", action: { type: "type", selector: selector(), text: $("text").value } }));
$("up").addEventListener("click", () => run({ type: "ACTION", action: { type: "scroll", deltaY: -650 } }));
$("down").addEventListener("click", () => run({ type: "ACTION", action: { type: "scroll", deltaY: 650 } }));

refresh().catch((error) => { $("status").textContent = String(error); });
setInterval(() => refresh().catch(() => {}), 1000);
