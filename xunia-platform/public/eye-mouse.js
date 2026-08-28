import { FaceLandmarker, FilesetResolver } from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/+esm";

const MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
const WASM_URL = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm";
const CALIBRATION_KEY = "xunia-eye-mouse-calibration-v1";
const CALIBRATION_POINTS = [
  [0.12, 0.12], [0.50, 0.12], [0.88, 0.12],
  [0.12, 0.50], [0.50, 0.50], [0.88, 0.50],
  [0.12, 0.88], [0.50, 0.88], [0.88, 0.88]
];

const $ = (id) => document.getElementById(id);
const camera = $("camera");
const startButton = $("startButton");
const recalibrateButton = $("recalibrateButton");
const pauseButton = $("pauseButton");
const cameraStatus = $("cameraStatus");
const trackingStatus = $("trackingStatus");
const calibrationStatus = $("calibrationStatus");
const faceStatus = $("faceStatus");
const gazeCursor = $("gazeCursor");
const gazeReadout = $("gazeReadout");
const calibrationLayer = $("calibrationLayer");
const calibrationTarget = $("calibrationTarget");
const calibrationText = $("calibrationText");
const dwellTime = $("dwellTime");
const dwellOutput = $("dwellOutput");
const smoothing = $("smoothing");
const smoothOutput = $("smoothOutput");
const showGaze = $("showGaze");
const soundCue = $("soundCue");
const modeText = $("modeText");
const demoResult = $("demoResult");

let landmarker = null;
let stream = null;
let started = false;
let calibrating = false;
let paused = false;
let currentFeatures = null;
let calibrationModel = loadCalibration();
let lastVideoTime = -1;
let smoothX = null;
let smoothY = null;
let dwellTarget = null;
let dwellStartedAt = 0;
let dwellCooldownUntil = 0;
let frameHandle = 0;

function setPill(element, text, state = "") {
  element.textContent = text;
  element.classList.remove("ok", "warn");
  if (state) element.classList.add(state);
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function averagePoint(landmarks, indexes) {
  const sum = indexes.reduce((acc, index) => {
    acc.x += landmarks[index].x;
    acc.y += landmarks[index].y;
    return acc;
  }, { x: 0, y: 0 });
  return { x: sum.x / indexes.length, y: sum.y / indexes.length };
}

function eyeOffset(iris, a, b, top, bottom) {
  const horizontal = Math.max(0.0001, Math.abs(b.x - a.x));
  const vertical = Math.max(0.0001, Math.abs(bottom.y - top.y));
  const centerX = (a.x + b.x) / 2;
  const centerY = (top.y + bottom.y) / 2;
  return [(iris.x - centerX) / horizontal, (iris.y - centerY) / vertical];
}

function extractFeatures(landmarks) {
  if (!Array.isArray(landmarks) || landmarks.length < 478) return null;

  const irisA = averagePoint(landmarks, [468, 469, 470, 471, 472]);
  const irisB = averagePoint(landmarks, [473, 474, 475, 476, 477]);
  const a = eyeOffset(irisA, landmarks[33], landmarks[133], landmarks[159], landmarks[145]);
  const b = eyeOffset(irisB, landmarks[362], landmarks[263], landmarks[386], landmarks[374]);

  const faceLeft = landmarks[234];
  const faceRight = landmarks[454];
  const faceTop = landmarks[10];
  const faceBottom = landmarks[152];
  const nose = landmarks[1];
  const faceWidth = Math.max(0.0001, Math.abs(faceRight.x - faceLeft.x));
  const faceHeight = Math.max(0.0001, Math.abs(faceBottom.y - faceTop.y));
  const faceCenterX = (faceLeft.x + faceRight.x) / 2;
  const faceCenterY = (faceTop.y + faceBottom.y) / 2;

  return [
    (a[0] + b[0]) / 2,
    (a[1] + b[1]) / 2,
    a[0] - b[0],
    (nose.x - faceCenterX) / faceWidth,
    (nose.y - faceCenterY) / faceHeight,
    faceWidth / faceHeight
  ];
}

function gaussianSolve(matrix, vector) {
  const n = vector.length;
  const a = matrix.map((row, index) => [...row, vector[index]]);

  for (let column = 0; column < n; column += 1) {
    let pivot = column;
    for (let row = column + 1; row < n; row += 1) {
      if (Math.abs(a[row][column]) > Math.abs(a[pivot][column])) pivot = row;
    }
    if (Math.abs(a[pivot][column]) < 1e-10) throw new Error("calibration_matrix_unstable");
    [a[column], a[pivot]] = [a[pivot], a[column]];

    const divisor = a[column][column];
    for (let j = column; j <= n; j += 1) a[column][j] /= divisor;

    for (let row = 0; row < n; row += 1) {
      if (row === column) continue;
      const factor = a[row][column];
      for (let j = column; j <= n; j += 1) a[row][j] -= factor * a[column][j];
    }
  }

  return a.map((row) => row[n]);
}

function fitRidge(samples, axis) {
  const dimension = samples[0].features.length + 1;
  const xtx = Array.from({ length: dimension }, () => Array(dimension).fill(0));
  const xty = Array(dimension).fill(0);

  for (const sample of samples) {
    const row = [1, ...sample.features];
    const y = axis === "x" ? sample.x : sample.y;
    for (let i = 0; i < dimension; i += 1) {
      xty[i] += row[i] * y;
      for (let j = 0; j < dimension; j += 1) xtx[i][j] += row[i] * row[j];
    }
  }

  const ridge = 0.035;
  for (let i = 1; i < dimension; i += 1) xtx[i][i] += ridge;
  return gaussianSolve(xtx, xty);
}

function dot(coefficients, features) {
  const row = [1, ...features];
  return coefficients.reduce((sum, coefficient, index) => sum + coefficient * row[index], 0);
}

function validCalibration(model) {
  return Boolean(
    model &&
    Array.isArray(model.x) && model.x.length === 7 &&
    Array.isArray(model.y) && model.y.length === 7 &&
    model.x.every(Number.isFinite) && model.y.every(Number.isFinite)
  );
}

function loadCalibration() {
  try {
    const parsed = JSON.parse(localStorage.getItem(CALIBRATION_KEY) || "null");
    return validCalibration(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function saveCalibration(model) {
  localStorage.setItem(CALIBRATION_KEY, JSON.stringify(model));
}

function gazeFromFeatures(features) {
  if (!validCalibration(calibrationModel)) return null;
  const nx = clamp(dot(calibrationModel.x, features), -0.08, 1.08);
  const ny = clamp(dot(calibrationModel.y, features), -0.08, 1.08);
  return {
    x: clamp(nx * window.innerWidth, 0, window.innerWidth - 1),
    y: clamp(ny * window.innerHeight, 0, window.innerHeight - 1)
  };
}

function resetDwell() {
  if (dwellTarget) dwellTarget.classList.remove("gaze-hover");
  dwellTarget = null;
  dwellStartedAt = 0;
  gazeCursor.style.setProperty("--dwell", "0deg");
}

function beep() {
  if (!soundCue.checked) return;
  try {
    const audio = new AudioContext();
    const oscillator = audio.createOscillator();
    const gain = audio.createGain();
    oscillator.frequency.value = 660;
    gain.gain.value = 0.04;
    oscillator.connect(gain).connect(audio.destination);
    oscillator.start();
    oscillator.stop(audio.currentTime + 0.08);
    oscillator.addEventListener("ended", () => audio.close(), { once: true });
  } catch {
    // Sound is optional; ignore unavailable audio contexts.
  }
}

function activateTarget(target) {
  const action = target.dataset.gazeAction || "";
  beep();

  if (action === "scroll-up") {
    window.scrollBy({ top: -window.innerHeight * 0.65, behavior: "smooth" });
  } else if (action === "scroll-down") {
    window.scrollBy({ top: window.innerHeight * 0.65, behavior: "smooth" });
  } else if (action === "pause") {
    paused = !paused;
    gazeCursor.classList.toggle("paused", paused);
    pauseButton.querySelector("small").textContent = paused ? "Resume" : "Pause";
    pauseButton.firstChild.textContent = paused ? "▶" : "Ⅱ";
    modeText.textContent = paused
      ? "Eye Mouse paused. Keep looking at Resume to turn dwell actions back on."
      : "Eye Mouse active. Hold your gaze on a target to activate it.";
    setPill(trackingStatus, paused ? "TRACKING PAUSED" : "TRACKING ACTIVE", paused ? "warn" : "ok");
  } else if (action === "recalibrate") {
    void calibrate();
  } else if (action === "demo") {
    demoResult.textContent = target.dataset.message || "Eye-controlled target activated.";
  } else {
    target.click();
  }
}

function updateDwell(x, y, now) {
  if (calibrating || now < dwellCooldownUntil) {
    resetDwell();
    return;
  }

  let target = document.elementFromPoint(x, y)?.closest("[data-gaze-action]") || null;
  if (paused && target !== pauseButton) target = null;

  if (!target) {
    resetDwell();
    return;
  }

  if (target !== dwellTarget) {
    resetDwell();
    dwellTarget = target;
    dwellStartedAt = now;
    target.classList.add("gaze-hover");
  }

  const duration = Number(dwellTime.value);
  const elapsed = now - dwellStartedAt;
  const progress = clamp(elapsed / duration, 0, 1);
  gazeCursor.style.setProperty("--dwell", `${progress * 360}deg`);

  if (progress >= 1) {
    const activated = dwellTarget;
    resetDwell();
    dwellCooldownUntil = now + 800;
    if (activated) activateTarget(activated);
  }
}

function renderGaze(point, now) {
  const retention = Number(smoothing.value) / 100;
  smoothX = smoothX == null ? point.x : smoothX * retention + point.x * (1 - retention);
  smoothY = smoothY == null ? point.y : smoothY * retention + point.y * (1 - retention);
  const x = clamp(smoothX, 0, window.innerWidth - 1);
  const y = clamp(smoothY, 0, window.innerHeight - 1);

  gazeCursor.style.transform = `translate3d(${x}px,${y}px,0)`;
  gazeCursor.classList.toggle("visible", showGaze.checked);
  gazeReadout.textContent = `${Math.round(x)} , ${Math.round(y)}`;
  updateDwell(x, y, now);
}

async function createLandmarker() {
  const files = await FilesetResolver.forVisionTasks(WASM_URL);
  const options = {
    baseOptions: { modelAssetPath: MODEL_URL, delegate: "GPU" },
    runningMode: "VIDEO",
    numFaces: 1,
    outputFaceBlendshapes: false,
    outputFacialTransformationMatrixes: false
  };

  try {
    return await FaceLandmarker.createFromOptions(files, options);
  } catch {
    options.baseOptions.delegate = "CPU";
    return FaceLandmarker.createFromOptions(files, options);
  }
}

async function startCamera() {
  if (stream) return;
  if (!navigator.mediaDevices?.getUserMedia) throw new Error("camera_not_supported");
  stream = await navigator.mediaDevices.getUserMedia({
    video: {
      facingMode: "user",
      width: { ideal: 1280 },
      height: { ideal: 720 },
      frameRate: { ideal: 30, max: 60 }
    },
    audio: false
  });
  camera.srcObject = stream;
  await camera.play();
  setPill(cameraStatus, "CAMERA ON", "ok");
}

function detectionLoop() {
  if (!started || !landmarker) return;
  const now = performance.now();

  if (camera.readyState >= 2 && camera.currentTime !== lastVideoTime) {
    lastVideoTime = camera.currentTime;
    const result = landmarker.detectForVideo(camera, now);
    const landmarks = result.faceLandmarks?.[0];
    currentFeatures = extractFeatures(landmarks);

    if (currentFeatures) {
      faceStatus.textContent = "FACE LOCKED";
      faceStatus.style.color = "var(--accent)";
      if (!calibrating) {
        const point = gazeFromFeatures(currentFeatures);
        if (point) renderGaze(point, now);
      }
    } else {
      faceStatus.textContent = "NO FACE";
      faceStatus.style.color = "var(--warn)";
      gazeCursor.classList.remove("visible");
      resetDwell();
    }
  }

  frameHandle = requestAnimationFrame(detectionLoop);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForFace(timeoutMs = 8000) {
  const startedAt = performance.now();
  while (!currentFeatures) {
    if (performance.now() - startedAt > timeoutMs) throw new Error("face_not_detected");
    await sleep(100);
  }
}

async function collectCalibrationPoint(nx, ny, index, samples) {
  calibrationTarget.style.left = `${nx * 100}%`;
  calibrationTarget.style.top = `${ny * 100}%`;
  calibrationText.textContent = `Point ${index + 1} of ${CALIBRATION_POINTS.length}: look at the center dot and keep your head comfortable.`;
  await waitForFace();
  await sleep(900);

  let captured = 0;
  for (let i = 0; i < 18; i += 1) {
    if (currentFeatures) {
      samples.push({ features: [...currentFeatures], x: nx, y: ny });
      captured += 1;
    }
    await sleep(42);
  }
  if (captured < 8) throw new Error("calibration_samples_insufficient");
  await sleep(180);
}

async function calibrate() {
  if (!started || calibrating) return;
  calibrating = true;
  paused = true;
  resetDwell();
  gazeCursor.classList.remove("visible");
  calibrationLayer.hidden = false;
  setPill(calibrationStatus, "CALIBRATING", "warn");
  setPill(trackingStatus, "TRACKING PAUSED", "warn");
  modeText.textContent = "Calibration in progress. Follow the glowing target with your eyes.";

  try {
    const samples = [];
    for (let index = 0; index < CALIBRATION_POINTS.length; index += 1) {
      const [x, y] = CALIBRATION_POINTS[index];
      await collectCalibrationPoint(x, y, index, samples);
    }

    calibrationModel = {
      version: 1,
      x: fitRidge(samples, "x"),
      y: fitRidge(samples, "y"),
      createdAt: new Date().toISOString(),
      viewport: { width: window.innerWidth, height: window.innerHeight },
      samples: samples.length
    };
    saveCalibration(calibrationModel);
    smoothX = null;
    smoothY = null;
    paused = false;
    setPill(calibrationStatus, "CALIBRATED", "ok");
    setPill(trackingStatus, "TRACKING ACTIVE", "ok");
    modeText.textContent = "Eye Mouse active. Hold your gaze on a target until the ring completes.";
  } catch (error) {
    const message = error instanceof Error ? error.message : "calibration_failed";
    setPill(calibrationStatus, "CALIBRATION FAILED", "warn");
    modeText.textContent = `Calibration failed: ${message.replaceAll("_", " ")}. Reposition your face and try again.`;
    paused = true;
  } finally {
    calibrating = false;
    calibrationLayer.hidden = true;
    pauseButton.querySelector("small").textContent = paused ? "Resume" : "Pause";
    pauseButton.firstChild.textContent = paused ? "▶" : "Ⅱ";
  }
}

async function start() {
  if (started) return;
  startButton.disabled = true;
  startButton.textContent = "Starting…";
  modeText.textContent = "Loading local vision model…";

  try {
    await startCamera();
    landmarker = await createLandmarker();
    started = true;
    recalibrateButton.disabled = false;
    setPill(trackingStatus, "FACE SEARCH", "warn");
    frameHandle = requestAnimationFrame(detectionLoop);
    await waitForFace();

    if (validCalibration(calibrationModel)) {
      paused = false;
      setPill(calibrationStatus, "SAVED CALIBRATION", "ok");
      setPill(trackingStatus, "TRACKING ACTIVE", "ok");
      modeText.textContent = "Saved calibration loaded. Use Recalibrate if the pointer is inaccurate.";
    } else {
      await calibrate();
    }
    startButton.textContent = "Eye Mouse Running";
  } catch (error) {
    const message = error instanceof Error ? error.message : "startup_failed";
    started = false;
    startButton.disabled = false;
    startButton.textContent = "Start Eye Mouse";
    setPill(cameraStatus, "CAMERA ERROR", "warn");
    setPill(trackingStatus, "TRACKING OFF", "warn");
    modeText.textContent = `Could not start Eye Mouse: ${message.replaceAll("_", " ")}. Check camera permission and reload.`;
    if (frameHandle) cancelAnimationFrame(frameHandle);
  }
}

startButton.addEventListener("click", () => void start());
recalibrateButton.addEventListener("click", () => void calibrate());
dwellTime.addEventListener("input", () => { dwellOutput.textContent = `${dwellTime.value} ms`; });
smoothing.addEventListener("input", () => { smoothOutput.textContent = `${smoothing.value}%`; });
showGaze.addEventListener("change", () => gazeCursor.classList.toggle("visible", showGaze.checked && started && Boolean(currentFeatures)));

document.addEventListener("keydown", (event) => {
  if (!started && !startButton.disabled && (event.key === " " || event.key === "Enter")) {
    event.preventDefault();
    void start();
  }
  if (event.key === "Escape" && started) {
    paused = true;
    resetDwell();
    gazeCursor.classList.add("paused");
    setPill(trackingStatus, "TRACKING PAUSED", "warn");
    modeText.textContent = "Eye Mouse paused with Escape. Look at Resume to continue.";
    pauseButton.querySelector("small").textContent = "Resume";
    pauseButton.firstChild.textContent = "▶";
  }
});

window.addEventListener("beforeunload", () => {
  if (frameHandle) cancelAnimationFrame(frameHandle);
  stream?.getTracks().forEach((track) => track.stop());
  landmarker?.close?.();
});

if (validCalibration(calibrationModel)) setPill(calibrationStatus, "CALIBRATION SAVED", "ok");
