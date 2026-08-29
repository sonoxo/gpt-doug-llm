type SimStatus = "READY" | "RUNNING" | "PAUSED" | "COMPLETE";
type Vec2 = { x: number; y: number };
type Equipment = { id: string; label: string; x: number; y: number; w: number; h: number };
type Step = { action: string; instruction: string; target: string };
type SimEvent = { t: number; type: string; message: string };

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const canvas = $("simCanvas") as HTMLCanvasElement;
const ctx = canvas.getContext("2d")!;

const statusEl = $("simStatus");
const timerEl = $("simTimer");
const scoreEl = $("simScore");
const errorsEl = $("simErrors");
const messageEl = $("simMessage");
const stepTitleEl = $("stepTitle");
const stepInstructionEl = $("stepInstruction");
const stepTargetEl = $("stepTarget");
const procedureListEl = $("procedureList");
const eventLogEl = $("eventLog");
const faultStateEl = $("faultState");

const buttons = {
  start: $("startBtn") as HTMLButtonElement,
  pause: $("pauseBtn") as HTMLButtonElement,
  confirm: $("confirmBtn") as HTMLButtonElement,
  error: $("errorBtn") as HTMLButtonElement,
  fault: $("faultBtn") as HTMLButtonElement,
  clearFault: $("clearFaultBtn") as HTMLButtonElement,
  reset: $("resetBtn") as HTMLButtonElement,
  export: $("exportBtn") as HTMLButtonElement,
};

const equipment: Equipment[] = [
  { id: "pump-01", label: "HX-100 Pump", x: 270, y: 220, w: 150, h: 95 },
  { id: "valve-iso", label: "Isolation Valve", x: 610, y: 200, w: 105, h: 105 },
  { id: "panel-main", label: "Main Access Panel", x: 880, y: 360, w: 180, h: 85 },
  { id: "sensor-bank", label: "Telemetry Sensor Bank", x: 440, y: 465, w: 160, h: 80 },
];

const steps: Step[] = [
  { action: "INSPECT", instruction: "Approach the HX-100 pump and inspect the housing.", target: "pump-01" },
  { action: "ISOLATE", instruction: "Move to the isolation valve and interact to secure the training line.", target: "valve-iso" },
  { action: "ACCESS", instruction: "Open the main access panel for the simulated inspection.", target: "panel-main" },
  { action: "VERIFY", instruction: "Verify the telemetry sensor bank and complete the maintenance sequence.", target: "sensor-bank" },
];

let status: SimStatus = "READY";
let player: Vec2 = { x: 130, y: 590 };
let heading = 0;
let stepIndex = 0;
let errors = 0;
let score = 100;
let elapsed = 0;
let lastFrame = performance.now();
let faultTarget: string | null = null;
let events: SimEvent[] = [];
const keys = new Set<string>();

const clamp = (n: number, min: number, max: number) => Math.max(min, Math.min(max, n));
const distance = (a: Vec2, b: Vec2) => Math.hypot(a.x - b.x, a.y - b.y);
const formatTime = (seconds: number) => `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;

function event(type: string, message: string) {
  events.push({ t: elapsed, type, message });
  renderLog();
}

function nearestEquipment() {
  return equipment
    .map((item) => ({ item, d: distance(player, { x: item.x + item.w / 2, y: item.y + item.h / 2 }) }))
    .sort((a, b) => a.d - b.d)[0];
}

function interact() {
  if (status !== "RUNNING") return;
  const near = nearestEquipment();
  if (!near || near.d > 125) {
    messageEl.textContent = "Move closer to the highlighted equipment.";
    return;
  }
  const step = steps[stepIndex];
  if (near.item.id !== step.target) {
    errors += 1;
    score = Math.max(0, score - 10);
    event("ERROR", `Wrong interaction: ${near.item.label}. Expected ${step.target}.`);
    messageEl.textContent = `Wrong component. Target is ${step.target}.`;
    updateHud();
    return;
  }
  event("INTERACTION", `${near.item.label} interaction accepted.`);
  messageEl.textContent = `${near.item.label}: interaction accepted. Confirm the step from Mission Control.`;
}

function confirmStep() {
  if (status !== "RUNNING") return;
  event("STEP", `Step ${stepIndex + 1} confirmed: ${steps[stepIndex].action}.`);
  if (stepIndex === steps.length - 1) {
    status = "COMPLETE";
    messageEl.textContent = "Simulation complete. Export the AAR.";
    event("SESSION", "Scenario complete.");
  } else {
    stepIndex += 1;
    messageEl.textContent = `Advance to step ${stepIndex + 1}.`;
  }
  updateHud();
  renderProcedure();
}

function injectFault() {
  if (status !== "RUNNING") return;
  faultTarget = steps[stepIndex].target;
  score = Math.max(0, score - 5);
  faultStateEl.textContent = `RED_HIGH // ${faultTarget} // TEMP 96 C`;
  event("FAULT", `Injected RED_HIGH representative temperature fault on ${faultTarget}.`);
  updateHud();
}

function clearFault() {
  if (!faultTarget) return;
  event("FAULT", `Cleared injected fault on ${faultTarget}.`);
  faultTarget = null;
  faultStateEl.textContent = "NONE";
}

function reset() {
  status = "READY";
  player = { x: 130, y: 590 };
  heading = 0;
  stepIndex = 0;
  errors = 0;
  score = 100;
  elapsed = 0;
  faultTarget = null;
  events = [];
  faultStateEl.textContent = "NONE";
  messageEl.textContent = "Press START, then use WASD to move and E to interact.";
  updateHud();
  renderProcedure();
  renderLog();
}

function exportAar() {
  const payload = {
    schema: "XUNIA_HOLO_AAR_V1",
    generatedAt: new Date().toISOString(),
    runtime: "GitHub Pages static TypeScript simulator",
    mission: "HX-100 representative maintenance training",
    session: { status, elapsedSeconds: Math.round(elapsed * 100) / 100, score, errors, completedSteps: status === "COMPLETE" ? steps.length : stepIndex, activeFault: faultTarget },
    events,
    truthBoundary: "Representative training simulation only; no engineering fidelity, operational authority, or government validation claimed.",
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `xunia-holo-aar-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function updateHud() {
  statusEl.textContent = status;
  timerEl.textContent = formatTime(elapsed);
  scoreEl.textContent = `SCORE ${score}`;
  errorsEl.textContent = `ERRORS ${errors}`;
  const step = steps[Math.min(stepIndex, steps.length - 1)];
  stepTitleEl.textContent = status === "COMPLETE" ? "MISSION COMPLETE" : `STEP ${stepIndex + 1} / ${steps.length}`;
  stepInstructionEl.textContent = status === "COMPLETE" ? "Procedure complete. Export the AAR or reset for another run." : step.instruction;
  stepTargetEl.textContent = status === "COMPLETE" ? "COMPLETE" : step.target;
  buttons.start.disabled = status === "RUNNING" || status === "COMPLETE";
  buttons.pause.disabled = status !== "RUNNING";
  buttons.confirm.disabled = status !== "RUNNING";
  buttons.error.disabled = status !== "RUNNING";
  buttons.fault.disabled = status !== "RUNNING";
  buttons.clearFault.disabled = !faultTarget;
}

function renderProcedure() {
  procedureListEl.innerHTML = steps.map((step, index) => {
    const done = status === "COMPLETE" || index < stepIndex;
    const active = status !== "COMPLETE" && index === stepIndex;
    return `<div class="step-row${done ? " done" : active ? " active" : ""}"><strong>${index + 1}. ${step.action}</strong><br>${step.instruction}<br><small>${done ? "CONFIRMED" : active ? "ACTIVE" : "PENDING"}</small></div>`;
  }).join("");
}

function renderLog() {
  eventLogEl.innerHTML = events.length ? [...events].reverse().map((e) => `<div class="event-row"><small>${e.type} // ${formatTime(e.t)}</small>${e.message}</div>`).join("") : `<div class="event-row">No events yet.</div>`;
}

function drawGrid() {
  ctx.strokeStyle = "rgba(70,243,255,.08)";
  ctx.lineWidth = 1;
  for (let x = 0; x < canvas.width; x += 64) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke(); }
  for (let y = 0; y < canvas.height; y += 64) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke(); }
}

function drawEquipment(item: Equipment) {
  const active = status !== "COMPLETE" && steps[stepIndex].target === item.id;
  const fault = faultTarget === item.id;
  ctx.save();
  ctx.shadowBlur = active || fault ? 25 : 8;
  ctx.shadowColor = fault ? "#ff315f" : active ? "#46f3ff" : "#173846";
  ctx.fillStyle = fault ? "#3a0b18" : active ? "#0a2d39" : "#09151d";
  ctx.strokeStyle = fault ? "#ff315f" : active ? "#46f3ff" : "#28505f";
  ctx.lineWidth = active || fault ? 3 : 1.5;
  ctx.fillRect(item.x, item.y, item.w, item.h);
  ctx.strokeRect(item.x, item.y, item.w, item.h);
  ctx.fillStyle = "#d9f8ff";
  ctx.font = "700 17px system-ui";
  ctx.fillText(item.label, item.x + 12, item.y + 28);
  ctx.fillStyle = active ? "#46f3ff" : fault ? "#ff789e" : "#6e909d";
  ctx.font = "12px ui-monospace,monospace";
  ctx.fillText(fault ? "RED_HIGH FAULT" : active ? "ACTIVE TARGET" : item.id, item.x + 12, item.y + 50);
  ctx.restore();
}

function drawPlayer() {
  ctx.save();
  ctx.translate(player.x, player.y);
  ctx.rotate(heading);
  ctx.shadowBlur = 18;
  ctx.shadowColor = "#9d5cff";
  ctx.fillStyle = "#9d5cff";
  ctx.beginPath(); ctx.moveTo(18, 0); ctx.lineTo(-12, -10); ctx.lineTo(-7, 0); ctx.lineTo(-12, 10); ctx.closePath(); ctx.fill();
  ctx.restore();
}

function render(now: number) {
  const dt = Math.min(.05, (now - lastFrame) / 1000);
  lastFrame = now;
  if (status === "RUNNING") {
    elapsed += dt;
    let dx = 0, dy = 0;
    if (keys.has("KeyW") || keys.has("ArrowUp")) dy -= 1;
    if (keys.has("KeyS") || keys.has("ArrowDown")) dy += 1;
    if (keys.has("KeyA") || keys.has("ArrowLeft")) dx -= 1;
    if (keys.has("KeyD") || keys.has("ArrowRight")) dx += 1;
    const mag = Math.hypot(dx, dy);
    if (mag) {
      const speed = keys.has("ShiftLeft") || keys.has("ShiftRight") ? 300 : 185;
      dx /= mag; dy /= mag;
      player.x = clamp(player.x + dx * speed * dt, 30, canvas.width - 30);
      player.y = clamp(player.y + dy * speed * dt, 30, canvas.height - 30);
      heading = Math.atan2(dy, dx);
    }
  }
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, "#07131c"); gradient.addColorStop(1, "#02060a");
  ctx.fillStyle = gradient; ctx.fillRect(0, 0, canvas.width, canvas.height);
  drawGrid(); equipment.forEach(drawEquipment); drawPlayer();
  const near = nearestEquipment();
  if (near && near.d <= 125 && status === "RUNNING") {
    ctx.fillStyle = "rgba(0,0,0,.72)"; ctx.fillRect(20, 20, 330, 48);
    ctx.fillStyle = "#46f3ff"; ctx.font = "700 15px system-ui"; ctx.fillText(`E // INTERACT ${near.item.label}`, 34, 50);
  }
  updateHud();
  requestAnimationFrame(render);
}

buttons.start.addEventListener("click", () => {
  if (status === "READY" || status === "PAUSED") {
    const wasPaused = status === "PAUSED";
    status = "RUNNING";
    event("SESSION", wasPaused ? "Simulation resumed." : "Simulation started.");
    messageEl.textContent = "WASD move · E interact · Shift sprint.";
    updateHud();
  }
});
buttons.pause.addEventListener("click", () => { if (status === "RUNNING") { status = "PAUSED"; event("SESSION", "Simulation paused."); updateHud(); } });
buttons.confirm.addEventListener("click", confirmStep);
buttons.error.addEventListener("click", () => { if (status === "RUNNING") { errors += 1; score = Math.max(0, score - 12); event("ERROR", `Instructor-recorded error on step ${stepIndex + 1}.`); updateHud(); } });
buttons.fault.addEventListener("click", injectFault);
buttons.clearFault.addEventListener("click", clearFault);
buttons.reset.addEventListener("click", reset);
buttons.export.addEventListener("click", exportAar);
window.addEventListener("keydown", (e) => { keys.add(e.code); if (e.code === "KeyE" && !e.repeat) interact(); if (["ArrowUp","ArrowDown","ArrowLeft","ArrowRight"].includes(e.code)) e.preventDefault(); });
window.addEventListener("keyup", (e) => keys.delete(e.code));

reset();
requestAnimationFrame((now) => { lastFrame = now; render(now); });
