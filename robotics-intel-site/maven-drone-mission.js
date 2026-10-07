(() => {
  "use strict";

  const bay = document.getElementById("droneBay");
  const stage = document.querySelector("#droneBay .drone-stage");
  if (!bay || !stage) return;

  const missionEl = document.getElementById("droneMission");
  const analyticsEl = document.getElementById("droneAnalyticsState");
  const videoEl = document.getElementById("droneVideoState");
  const eventCountEl = document.getElementById("droneEventCount");
  const segEl = document.getElementById("droneSeg");
  const classEl = document.getElementById("droneClass");
  const trackEl = document.getElementById("droneTrack");
  const eventEl = document.getElementById("droneEvent");
  const modeEl = document.getElementById("droneMode");

  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let mission = "SURVEY";
  let eventCount = 0;
  let tick = 0;
  let pipelinePhase = 0;

  const roiLayer = document.createElement("div");
  roiLayer.className = "drone-roi-layer";
  roiLayer.innerHTML = [
    '<div class="drone-roi r1" data-label="SYNTHETIC ROI // INFRA"></div>',
    '<div class="drone-roi r2" data-label="SYNTHETIC ROI // TERRAIN"></div>',
    '<div class="drone-roi r3" data-label="SYNTHETIC ROI // OBSTACLE"></div>'
  ].join("");
  stage.appendChild(roiLayer);

  const profiles = {
    SURVEY: {
      pipeline: ["SEGMENT","CLASSIFY","TRACK","EVENT","HUMAN REVIEW"],
      video: "ROI HIGH / BG SAVE",
      scan: true
    },
    GRID_SCAN: {
      pipeline: ["SEGMENT","CLASSIFY","TRACK","EVENT","HUMAN REVIEW"],
      video: "GRID ROI / BG SAVE",
      scan: true
    },
    INFRA_INSPECT: {
      pipeline: ["SEGMENT","CLASSIFY","TRACK","EVENT","HUMAN REVIEW"],
      video: "INFRA ROI HIGH",
      scan: true
    },
    ENVIRONMENT_SCAN: {
      pipeline: ["SEGMENT","CLASSIFY","TRACK","EVENT","HUMAN REVIEW"],
      video: "ENV ROI / BG SAVE",
      scan: true
    },
    RTB: {
      pipeline: ["STANDBY","STANDBY","STANDBY","CLEAR","HUMAN REVIEW"],
      video: "BACKGROUND SAVE",
      scan: false
    }
  };

  function airborne() {
    const mode = String(modeEl?.textContent || "GROUND").trim().toUpperCase();
    return !["GROUND","LAND"].includes(mode);
  }

  function setMission(next) {
    if (!profiles[next]) return;
    mission = next;
    if (missionEl) missionEl.textContent = next;
    document.querySelectorAll("[data-drone-mission]").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.droneMission === next);
    });

    if (next === "RTB") {
      document.querySelector('[data-drone-mode="HOME"]')?.click();
    }
    updateVisualState();
    document.dispatchEvent(new CustomEvent("maven:drone-mission", {
      detail: { mission: next, mode: "SYNTHETIC_FLIGHT_AUTHORIZED_OBSERVATION" }
    }));
  }

  function updateVisualState() {
    const p = profiles[mission];
    const active = p.scan && airborne();
    stage.classList.toggle("maven-scan-active", active && !reduce);
    roiLayer.style.display = active ? "" : "none";

    if (analyticsEl) analyticsEl.textContent = active ? p.pipeline[pipelinePhase % 4] : "STANDBY";
    if (videoEl) videoEl.textContent = active ? p.video : "BACKGROUND SAVE";

    if (segEl) segEl.textContent = active && pipelinePhase >= 0 ? "ACTIVE" : "READY";
    if (classEl) classEl.textContent = active && pipelinePhase >= 1 ? "ACTIVE" : "READY";
    if (trackEl) trackEl.textContent = active && pipelinePhase >= 2 ? "ACTIVE" : "READY";
    if (eventEl) eventEl.textContent = String(eventCount);
    if (eventCountEl) eventCountEl.textContent = String(eventCount);
  }

  function maybeSyntheticEvent() {
    if (!airborne() || mission === "RTB") return;
    // Deterministic synthetic cadence: every 8th cycle after TRACK is active.
    tick++;
    if (tick % 8 !== 0) return;
    eventCount++;
    document.dispatchEvent(new CustomEvent("maven:drone-synthetic-event", {
      detail: {
        id: "SIM-EVT-" + String(eventCount).padStart(3, "0"),
        mission,
        class: mission === "INFRA_INSPECT" ? "infrastructure" :
               mission === "ENVIRONMENT_SCAN" ? "environmental_region" : "synthetic_contact",
        review: "HUMAN_REQUIRED",
        actionable: false
      }
    }));
  }

  document.querySelectorAll("[data-drone-mission]").forEach(btn => {
    btn.addEventListener("click", () => setMission(btn.dataset.droneMission));
  });

  if (modeEl && "MutationObserver" in window) {
    new MutationObserver(updateVisualState).observe(modeEl, { childList:true, characterData:true, subtree:true });
  }

  setInterval(() => {
    pipelinePhase = (pipelinePhase + 1) % 5;
    maybeSyntheticEvent();
    updateVisualState();
  }, reduce ? 2200 : 1100);

  const params = new URLSearchParams(location.search);
  if (params.get("drone") === "1") {
    setTimeout(() => {
      document.dispatchEvent(new CustomEvent("maven:drone-request-open"));
      if (String(modeEl?.textContent || "GROUND").trim().toUpperCase() === "GROUND") {
        document.querySelector('[data-drone-mode="TAKEOFF"]')?.click();
      }
    }, 500);
  }

  setMission("SURVEY");
})();
