(() => {
  const nodes = [...document.querySelectorAll('.map-node')];
  const objectName = document.getElementById('objectName');
  const objectDomain = document.getElementById('objectDomain');
  const objectState = document.getElementById('objectState');
  const objectDetail = document.getElementById('objectDetail');
  const objectIcon = document.querySelector('.object-icon');
  const incidentCount = document.getElementById('incidentCount');
  const healthScore = document.getElementById('healthScore');
  const aipCard = document.getElementById('aipCard');
  const timeline = document.getElementById('timelineTrack');
  const clock = document.getElementById('clock');
  const helpModal = document.getElementById('helpModal');

  let elapsed = 2;
  let incidentActive = false;

  const addEvent = (title, detail, type = '') => {
    elapsed += 1;
    const event = document.createElement('div');
    event.className = `timeline-event ${type}`.trim();
    const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const secs = String(elapsed % 60).padStart(2, '0');
    event.innerHTML = `<span class="time">T+${mins}:${secs}</span><i></i><div><b>${title}</b><span>${detail}</span></div>`;
    timeline.appendChild(event);
    timeline.scrollLeft = timeline.scrollWidth;
  };

  const setSelected = (node) => {
    nodes.forEach((n) => n.classList.remove('selected'));
    node.classList.add('selected');
    objectName.textContent = node.dataset.node.toUpperCase();
    objectDomain.textContent = node.dataset.domain;
    objectState.textContent = node.dataset.state;
    objectDetail.textContent = node.dataset.detail;
    objectIcon.textContent = node.dataset.domain.charAt(0);
  };

  nodes.forEach((node) => node.addEventListener('click', () => setSelected(node)));
  setSelected(nodes[0]);

  const resetNodes = () => {
    nodes.forEach((node) => {
      node.classList.remove('alert', 'degraded');
      if (node.classList.contains('ems')) {
        node.classList.add('protected');
        node.dataset.state = 'PROTECTED';
      } else {
        node.dataset.state = 'HEALTHY';
      }
    });
  };

  const scenarios = {
    power() {
      resetNodes();
      const power = document.querySelector('.map-node.power');
      const water = document.querySelector('.map-node.water');
      power.classList.add('alert');
      water.classList.add('degraded');
      power.dataset.state = 'ALERT';
      water.dataset.state = 'DEGRADED';
      incidentActive = true;
      incidentCount.textContent = '01';
      healthScore.textContent = '87.4%';
      aipCard.querySelector('p').textContent = 'Synthetic power degradation is propagating toward the water twin. Preserve EMS dependencies, stage backup-power failover, then verify recovery before restoring the primary node.';
      addEvent('POWER_SIM ALERT', 'Synthetic voltage instability injected into POWER-PRIMARY', 'alert');
      addEvent('AIP PLAN STAGED', 'Preserve life-safety → activate synthetic failover → verify water dependency', '');
      setSelected(power);
    },
    water() {
      resetNodes();
      const water = document.querySelector('.map-node.water');
      water.classList.add('alert');
      water.dataset.state = 'ALERT';
      incidentActive = true;
      incidentCount.textContent = '01';
      healthScore.textContent = '91.2%';
      aipCard.querySelector('p').textContent = 'Synthetic treatment telemetry exceeds the exercise threshold. Contain the affected digital-twin node while preserving hospital water dependency through a simulated alternate supply path.';
      addEvent('WATER_SIM STRESS', 'Synthetic treatment telemetry threshold exceeded', 'alert');
      setSelected(water);
    },
    traffic() {
      resetNodes();
      const traffic = document.querySelector('.map-node.traffic');
      traffic.classList.add('degraded');
      traffic.dataset.state = 'DEGRADED';
      incidentActive = true;
      incidentCount.textContent = '01';
      healthScore.textContent = '93.6%';
      aipCard.querySelector('p').textContent = 'Synthetic traffic corridor is degraded. Maintain the simulated EMS priority route and stage safe-state behavior for the affected intersection twins.';
      addEvent('TRAFFIC_SIM DEGRADED', 'Synthetic corridor timing anomaly introduced', 'alert');
      addEvent('EMS ROUTE PRESERVED', 'Life-safety route remains protected in simulation', 'recovery');
      setSelected(traffic);
    },
    ems() {
      resetNodes();
      const ems = document.querySelector('.map-node.ems');
      ems.classList.add('degraded');
      ems.dataset.state = 'SURGE';
      incidentActive = true;
      incidentCount.textContent = '01';
      healthScore.textContent = '89.9%';
      aipCard.querySelector('p').textContent = 'Synthetic EMS demand surge detected. Do not isolate the life-safety twin. Preserve service, activate simulated surge capacity, and verify power/water/traffic dependencies.';
      addEvent('EMS_SIM SURGE', 'Synthetic demand spike injected into EMS-HOSPITAL-A', 'alert');
      addEvent('LIFE-SAFETY POLICY', 'Direct isolation blocked; preservation workflow selected', 'recovery');
      setSelected(ems);
    },
    reset() {
      resetNodes();
      incidentActive = false;
      incidentCount.textContent = '00';
      healthScore.textContent = '99.7%';
      aipCard.querySelector('p').textContent = 'No active synthetic incident. Digital-twin graph is stable and all life-safety dependencies are protected.';
      addEvent('EXERCISE RESET', 'All synthetic objects restored to baseline state', 'recovery');
      setSelected(nodes[0]);
    }
  };

  document.querySelectorAll('[data-scenario]').forEach((button) => {
    button.addEventListener('click', () => scenarios[button.dataset.scenario]?.());
  });

  document.querySelectorAll('.rail-item[data-view]').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.rail-item[data-view]').forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      addEvent('VIEW CHANGED', `${button.dataset.view.toUpperCase()} workspace selected`);
    });
  });

  document.querySelectorAll('.tool-button').forEach((button) => {
    button.addEventListener('click', () => {
      if (button.classList.contains('icon-only')) return;
      document.querySelectorAll('.tool-button').forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
    });
  });

  document.getElementById('clearLog').addEventListener('click', () => {
    timeline.innerHTML = '';
    addEvent('AUDIT VIEW CLEARED', 'Display cleared locally; immutable backend audit concept remains unchanged');
  });

  document.getElementById('helpButton').addEventListener('click', () => {
    helpModal.hidden = false;
  });
  document.getElementById('closeHelp').addEventListener('click', () => {
    helpModal.hidden = true;
  });
  helpModal.addEventListener('click', (event) => {
    if (event.target === helpModal) helpModal.hidden = true;
  });

  const tick = () => {
    const now = new Date();
    clock.textContent = now.toISOString().slice(11, 19) + 'Z';
  };
  tick();
  setInterval(tick, 1000);

  window.ZYRAPALANTIR = {
    mode: 'SIMULATION_ONLY',
    realInfrastructureWriteAccess: false,
    outboundActuation: false,
    get incidentActive() { return incidentActive; }
  };
})();
