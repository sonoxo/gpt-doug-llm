type SimStatus = "READY" | "RUNNING" | "PAUSED" | "COMPLETE";
type Vec3 = [number, number, number];
type Mat4 = Float32Array;
type SimEvent = { t: number; type: string; message: string };
type Equipment = { id: string; label: string; position: Vec3; scale: Vec3; color: Vec3 };
type SceneNode = { position: Vec3; scale: Vec3; color: Vec3; emissive?: Vec3; equipmentId?: string };
type Step = { action: string; instruction: string; target: string };
type Camera = { position: Vec3; yaw: number; pitch: number };

const $ = <T extends HTMLElement>(id: string) => {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Missing required element #${id}`);
  return node as T;
};

const canvas = $("simCanvas") as HTMLCanvasElement;
const context = canvas.getContext("webgl2", { antialias: true, alpha: false, powerPreference: "high-performance" });
const runtimeStateEl = $("runtimeState");
if (!context) {
  runtimeStateEl.textContent = "WEBGL2 NOT AVAILABLE";
  throw new Error("HOLO requires a WebGL2-capable browser/GPU.");
}
const gl: WebGL2RenderingContext = context;

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
const fpsStateEl = $("fpsState");
const lookHintEl = $("lookHint");

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

const VERTEX_SHADER = `#version 300 es
layout(location=0) in vec3 aPosition;
layout(location=1) in vec3 aNormal;
uniform mat4 uModel;
uniform mat4 uViewProj;
out vec3 vWorldPos;
out vec3 vNormal;
void main(){
  vec4 world = uModel * vec4(aPosition,1.0);
  vWorldPos = world.xyz;
  vNormal = normalize(mat3(uModel) * aNormal);
  gl_Position = uViewProj * world;
}`;

const FRAGMENT_SHADER = `#version 300 es
precision highp float;
in vec3 vWorldPos;
in vec3 vNormal;
uniform vec3 uBaseColor;
uniform vec3 uEmissive;
uniform vec3 uCameraPos;
uniform float uFaultPulse;
uniform float uTime;
out vec4 outColor;
void main(){
  vec3 N = normalize(vNormal);
  vec3 L = normalize(vec3(-0.35,0.92,0.22));
  vec3 V = normalize(uCameraPos-vWorldPos);
  vec3 H = normalize(L+V);
  float ndl = max(dot(N,L),0.0);
  float spec = pow(max(dot(N,H),0.0),38.0)*0.34;
  float rim = pow(1.0-max(dot(N,V),0.0),3.0)*0.16;
  vec3 base = uBaseColor*(0.13+ndl*0.86)+vec3(spec)+rim*uBaseColor;
  vec3 pulse = uEmissive*(0.68+0.32*sin(uTime*5.5))*uFaultPulse;
  vec3 color = base+pulse;
  float fog = smoothstep(13.0,28.0,distance(uCameraPos,vWorldPos));
  color = mix(color,vec3(0.006,0.014,0.022),fog);
  color = color/(color+vec3(1.0));
  color = pow(color,vec3(0.88));
  outColor = vec4(color,1.0);
}`;

function compileShader(type: number, source: string) {
  const shader = gl.createShader(type);
  if (!shader) throw new Error("Unable to allocate WebGL shader.");
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const message = gl.getShaderInfoLog(shader) ?? "Shader compile failure";
    gl.deleteShader(shader);
    throw new Error(message);
  }
  return shader;
}

function createProgram() {
  const program = gl.createProgram();
  if (!program) throw new Error("Unable to allocate WebGL program.");
  const vertex = compileShader(gl.VERTEX_SHADER, VERTEX_SHADER);
  const fragment = compileShader(gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  gl.deleteShader(vertex);
  gl.deleteShader(fragment);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program) ?? "Program link failure");
  return program;
}

function cubeVertices() {
  const p = 0.5;
  const faces: Array<{ n: Vec3; c: Vec3[] }> = [
    { n:[0,0,1], c:[[-p,-p,p],[p,-p,p],[p,p,p],[-p,p,p]] },
    { n:[0,0,-1], c:[[p,-p,-p],[-p,-p,-p],[-p,p,-p],[p,p,-p]] },
    { n:[1,0,0], c:[[p,-p,p],[p,-p,-p],[p,p,-p],[p,p,p]] },
    { n:[-1,0,0], c:[[-p,-p,-p],[-p,-p,p],[-p,p,p],[-p,p,-p]] },
    { n:[0,1,0], c:[[-p,p,p],[p,p,p],[p,p,-p],[-p,p,-p]] },
    { n:[0,-1,0], c:[[-p,-p,-p],[p,-p,-p],[p,-p,p],[-p,-p,p]] },
  ];
  const out:number[]=[];
  for(const face of faces){
    for(const i of [0,1,2,0,2,3]){
      const v=face.c[i]!;
      out.push(v[0],v[1],v[2],face.n[0],face.n[1],face.n[2]);
    }
  }
  return out;
}

function createCubeMesh() {
  const vao = gl.createVertexArray();
  const buffer = gl.createBuffer();
  if (!vao || !buffer) throw new Error("Unable to allocate WebGL geometry.");
  const vertices = new Float32Array(cubeVertices());
  gl.bindVertexArray(vao);
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
  const stride = 6 * Float32Array.BYTES_PER_ELEMENT;
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0,3,gl.FLOAT,false,stride,0);
  gl.enableVertexAttribArray(1);
  gl.vertexAttribPointer(1,3,gl.FLOAT,false,stride,3*Float32Array.BYTES_PER_ELEMENT);
  gl.bindVertexArray(null);
  return { vao, count: vertices.length/6 };
}

function identity(): Mat4 {
  return new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);
}
function multiply(a:Mat4,b:Mat4):Mat4{
  const out=new Float32Array(16);
  for(let r=0;r<4;r++) for(let c=0;c<4;c++){
    let sum=0;
    for(let k=0;k<4;k++) sum+=a[k*4+r]!*b[c*4+k]!;
    out[c*4+r]=sum;
  }
  return out;
}
function translation([x,y,z]:Vec3):Mat4{
  const out=identity(); out[12]=x; out[13]=y; out[14]=z; return out;
}
function scaling([x,y,z]:Vec3):Mat4{
  const out=identity(); out[0]=x; out[5]=y; out[10]=z; return out;
}
function perspective(fov:number,aspect:number,near:number,far:number):Mat4{
  const f=1/Math.tan(fov/2), nf=1/(near-far);
  return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+near)*nf,-1,0,0,2*far*near*nf,0]);
}
function normalize3([x,y,z]:Vec3):Vec3{
  const len=Math.hypot(x,y,z)||1; return [x/len,y/len,z/len];
}
function cross(a:Vec3,b:Vec3):Vec3{
  return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
}
function dot(a:Vec3,b:Vec3){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
function lookAt(eye:Vec3,center:Vec3,up:Vec3):Mat4{
  const z=normalize3([eye[0]-center[0],eye[1]-center[1],eye[2]-center[2]]);
  const x=normalize3(cross(up,z));
  const y=cross(z,x);
  return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);
}
function modelMatrix(node:SceneNode,time:number,activeId:string|null):Mat4{
  let p:Vec3=[...node.position];
  let s:Vec3=[...node.scale];
  if(node.equipmentId===activeId){
    const pulse=1+Math.sin(time*3.4)*0.025;
    s=[s[0]*pulse,s[1]*pulse,s[2]*pulse];
  }
  return multiply(translation(p),scaling(s));
}
function cameraForward(camera:Camera):Vec3{
  const cp=Math.cos(camera.pitch);
  return normalize3([Math.sin(camera.yaw)*cp,Math.sin(camera.pitch),-Math.cos(camera.yaw)*cp]);
}
function distance3(a:Vec3,b:Vec3){return Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2]);}
function clamp(n:number,min:number,max:number){return Math.max(min,Math.min(max,n));}
function formatTime(seconds:number){return `${String(Math.floor(seconds/60)).padStart(2,"0")}:${String(Math.floor(seconds%60)).padStart(2,"0")}`;}

const equipment:Equipment[]=[
  { id:"pump-01", label:"HX-100 Pump", position:[-4.2,1.0,-3.5], scale:[2.1,2.0,2.1], color:[0.12,0.34,0.42] },
  { id:"valve-iso", label:"Isolation Valve", position:[0.0,1.1,-5.7], scale:[1.25,2.2,1.25], color:[0.22,0.28,0.34] },
  { id:"panel-main", label:"Main Access Panel", position:[4.7,1.25,-3.4], scale:[2.8,2.5,0.65], color:[0.20,0.24,0.31] },
  { id:"sensor-bank", label:"Telemetry Sensor Bank", position:[4.0,1.25,2.0], scale:[2.5,2.5,0.8], color:[0.12,0.30,0.29] },
];

const steps:Step[]=[
  { action:"INSPECT", instruction:"Approach the HX-100 pump, face it, and press E to inspect the housing.", target:"pump-01" },
  { action:"ISOLATE", instruction:"Move to the isolation valve and press E to secure the representative training line.", target:"valve-iso" },
  { action:"ACCESS", instruction:"Move to the main access panel and press E to open the simulated inspection point.", target:"panel-main" },
  { action:"VERIFY", instruction:"Move to the telemetry sensor bank and press E to verify the representative readings.", target:"sensor-bank" },
];

const environment:SceneNode[]=[
  { position:[0,-0.15,0], scale:[16,0.3,16], color:[0.045,0.075,0.095] },
  { position:[0,4.2,0], scale:[16,0.25,16], color:[0.035,0.055,0.075] },
  { position:[0,2.0,-8], scale:[16,4.0,0.25], color:[0.06,0.10,0.13] },
  { position:[0,2.0,8], scale:[16,4.0,0.25], color:[0.04,0.07,0.10] },
  { position:[-8,2.0,0], scale:[0.25,4.0,16], color:[0.05,0.08,0.11] },
  { position:[8,2.0,0], scale:[0.25,4.0,16], color:[0.05,0.08,0.11] },
  { position:[-1.6,0.25,-1.1], scale:[4.0,0.5,1.2], color:[0.10,0.13,0.15] },
  { position:[-1.6,1.15,-1.1], scale:[0.35,1.8,5.5], color:[0.16,0.18,0.21] },
  { position:[2.0,3.25,-0.7], scale:[0.35,0.35,12], color:[0.10,0.18,0.21] },
  { position:[-3.2,3.25,1.0], scale:[0.35,0.35,10], color:[0.12,0.15,0.18] },
];
const equipmentNodes:SceneNode[]=equipment.map(item=>({ position:item.position, scale:item.scale, color:item.color, equipmentId:item.id }));
const accentNodes:SceneNode[]=[
  { position:[-4.2,2.25,-3.5], scale:[1.1,0.18,1.1], color:[0.08,0.12,0.14], emissive:[0.08,0.42,0.60], equipmentId:"pump-01" },
  { position:[0,2.45,-5.7], scale:[0.5,0.18,0.5], color:[0.10,0.12,0.14], emissive:[0.08,0.42,0.60], equipmentId:"valve-iso" },
  { position:[4.7,1.25,-3.0], scale:[2.0,1.5,0.12], color:[0.05,0.10,0.13], emissive:[0.04,0.30,0.55], equipmentId:"panel-main" },
  { position:[4.0,1.25,1.55], scale:[1.7,1.6,0.12], color:[0.04,0.12,0.12], emissive:[0.03,0.45,0.32], equipmentId:"sensor-bank" },
];
const sceneNodes=[...environment,...equipmentNodes,...accentNodes];

const program=createProgram();
const mesh=createCubeMesh();
gl.useProgram(program);
const uniforms={
  model: gl.getUniformLocation(program,"uModel"),
  viewProj: gl.getUniformLocation(program,"uViewProj"),
  baseColor: gl.getUniformLocation(program,"uBaseColor"),
  emissive: gl.getUniformLocation(program,"uEmissive"),
  cameraPos: gl.getUniformLocation(program,"uCameraPos"),
  faultPulse: gl.getUniformLocation(program,"uFaultPulse"),
  time: gl.getUniformLocation(program,"uTime"),
};
if(Object.values(uniforms).some(value=>value===null)) throw new Error("Required WebGL uniform not found.");

gl.enable(gl.DEPTH_TEST);
gl.enable(gl.CULL_FACE);
gl.cullFace(gl.BACK);
gl.clearColor(0.004,0.009,0.016,1);
runtimeStateEl.textContent="WEBGL2 ONLINE // GPU RENDERING ACTIVE";

let simStatus:SimStatus="READY";
let camera:Camera={ position:[0,1.65,6.0], yaw:0, pitch:-0.04 };
let stepIndex=0;
let stepInteracted=false;
let errors=0;
let score=100;
let elapsed=0;
let faultTarget:string|null=null;
let events:SimEvent[]=[];
let pointerLocked=false;
let lastFrame=performance.now();
let fpsAccumulator=0;
let fpsFrames=0;
let fpsValue=0;
const keys=new Set<string>();

function logEvent(type:string,message:string){
  events.push({t:elapsed,type,message});
  renderLog();
}
function nearestEquipment(){
  return equipment.map(item=>({item,d:distance3(camera.position,item.position)})).sort((a,b)=>a.d-b.d)[0];
}
function facingScore(target:Vec3){
  const f=cameraForward(camera);
  const to=normalize3([target[0]-camera.position[0],target[1]-camera.position[1],target[2]-camera.position[2]]);
  return dot(f,to);
}
function interact(){
  if(simStatus!=="RUNNING") return;
  const near=nearestEquipment();
  if(!near || near.d>3.0){ messageEl.textContent="Move closer to the highlighted equipment."; return; }
  if(facingScore(near.item.position)<0.18){ messageEl.textContent=`Face ${near.item.label} and press E again.`; return; }
  const step=steps[stepIndex]!;
  if(near.item.id!==step.target){
    errors++; score=Math.max(0,score-10);
    logEvent("ERROR",`Wrong interaction: ${near.item.label}. Expected ${step.target}.`);
    messageEl.textContent=`Wrong component. Active target: ${step.target}.`;
    updateHud(); return;
  }
  stepInteracted=true;
  logEvent("INTERACTION",`${near.item.label} interaction accepted in first-person runtime.`);
  messageEl.textContent=`${near.item.label}: interaction accepted. Confirm the step in Mission Control.`;
  updateHud();
}
function confirmStep(){
  if(simStatus!=="RUNNING") return;
  if(!stepInteracted){ messageEl.textContent="Interact with the active 3D target first (E), then confirm the step."; return; }
  logEvent("STEP",`Step ${stepIndex+1} confirmed: ${steps[stepIndex]!.action}.`);
  if(stepIndex===steps.length-1){
    simStatus="COMPLETE";
    messageEl.textContent="Simulation complete. Export the AAR or reset for another run.";
    logEvent("SESSION","Scenario complete.");
  }else{
    stepIndex++; stepInteracted=false;
    messageEl.textContent=`Advance to step ${stepIndex+1}: ${steps[stepIndex]!.action}.`;
  }
  updateHud(); renderProcedure();
}
function injectFault(){
  if(simStatus!=="RUNNING") return;
  faultTarget=steps[stepIndex]!.target;
  score=Math.max(0,score-5);
  faultStateEl.textContent=`RED_HIGH // ${faultTarget} // TEMP 96 C`;
  logEvent("FAULT",`Injected RED_HIGH representative fault on ${faultTarget}.`);
  updateHud();
}
function clearFault(){
  if(!faultTarget) return;
  logEvent("FAULT",`Cleared injected fault on ${faultTarget}.`);
  faultTarget=null; faultStateEl.textContent="NONE"; updateHud();
}
function resetSimulation(){
  simStatus="READY";
  camera={position:[0,1.65,6.0],yaw:0,pitch:-0.04};
  stepIndex=0; stepInteracted=false; errors=0; score=100; elapsed=0; faultTarget=null; events=[];
  faultStateEl.textContent="NONE";
  messageEl.textContent="Press START, click the viewport, then use WASD + mouse. E interacts with the highlighted component.";
  updateHud(); renderProcedure(); renderLog();
}
function exportAar(){
  const payload={
    schema:"XUNIA_HOLO_AAR_V1",
    generatedAt:new Date().toISOString(),
    runtime:"GitHub Pages static TypeScript simulator // WebGL2 first-person renderer",
    renderer:{api:"WebGL2",input:"Pointer Lock + WASD + Shift + E",hosting:"GitHub Pages"},
    mission:"HX-100 representative maintenance training",
    session:{status:simStatus,elapsedSeconds:Math.round(elapsed*100)/100,score,errors,completedSteps:simStatus==="COMPLETE"?steps.length:stepIndex,activeFault:faultTarget},
    events,
    truthBoundary:"Representative training simulation only; no engineering fidelity, operational authority, named-device certification, or government validation claimed."
  };
  const blob=new Blob([JSON.stringify(payload,null,2)],{type:"application/json"});
  const url=URL.createObjectURL(blob); const a=document.createElement("a");
  a.href=url; a.download=`xunia-holo-aar-${Date.now()}.json`; a.click(); URL.revokeObjectURL(url);
}
function updateHud(){
  statusEl.textContent=simStatus;
  timerEl.textContent=formatTime(elapsed);
  scoreEl.textContent=`SCORE ${score}`;
  errorsEl.textContent=`ERRORS ${errors}`;
  fpsStateEl.textContent=`FPS ${fpsValue || "--"}`;
  const step=steps[Math.min(stepIndex,steps.length-1)]!;
  stepTitleEl.textContent=simStatus==="COMPLETE"?"MISSION COMPLETE":`STEP ${stepIndex+1} / ${steps.length}`;
  stepInstructionEl.textContent=simStatus==="COMPLETE"?"Procedure complete. Export the AAR or reset for another run.":step.instruction;
  stepTargetEl.textContent=simStatus==="COMPLETE"?"COMPLETE":`${step.target}${stepInteracted?" // INTERACTED":""}`;
  buttons.start.disabled=simStatus==="RUNNING"||simStatus==="COMPLETE";
  buttons.pause.disabled=simStatus!=="RUNNING";
  buttons.confirm.disabled=simStatus!=="RUNNING";
  buttons.error.disabled=simStatus!=="RUNNING";
  buttons.fault.disabled=simStatus!=="RUNNING";
  buttons.clearFault.disabled=!faultTarget;
}
function renderProcedure(){
  procedureListEl.innerHTML=steps.map((step,index)=>{
    const done=simStatus==="COMPLETE"||index<stepIndex;
    const active=simStatus!=="COMPLETE"&&index===stepIndex;
    const state=done?"CONFIRMED":active?(stepInteracted?"INTERACTION COMPLETE // CONFIRM":"ACTIVE 3D TARGET"):"PENDING";
    return `<div class="step-row${done?" done":active?" active":""}"><strong>${index+1}. ${step.action}</strong><br>${step.instruction}<br><small>${state}</small></div>`;
  }).join("");
}
function renderLog(){
  eventLogEl.innerHTML=events.length?[...events].reverse().map(e=>`<div class="event-row"><small>${e.type} // ${formatTime(e.t)}</small>${e.message}</div>`).join(""):`<div class="event-row">No events yet.</div>`;
}
function resizeCanvas(){
  const dpr=Math.min(2,window.devicePixelRatio||1);
  const width=Math.max(1,Math.round(canvas.clientWidth*dpr));
  const height=Math.max(1,Math.round(canvas.clientHeight*dpr));
  if(canvas.width!==width||canvas.height!==height){ canvas.width=width; canvas.height=height; }
  gl.viewport(0,0,canvas.width,canvas.height);
}
function renderScene(time:number){
  resizeCanvas();
  gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  gl.useProgram(program);
  const forward=cameraForward(camera);
  const center:Vec3=[camera.position[0]+forward[0],camera.position[1]+forward[1],camera.position[2]+forward[2]];
  const view=lookAt(camera.position,center,[0,1,0]);
  const proj=perspective(Math.PI/3,canvas.width/canvas.height,0.08,70);
  const viewProj=multiply(proj,view);
  gl.uniformMatrix4fv(uniforms.viewProj,false,viewProj);
  gl.uniform3fv(uniforms.cameraPos,camera.position);
  gl.uniform1f(uniforms.time,time);
  gl.bindVertexArray(mesh.vao);
  const activeId=simStatus==="COMPLETE"?null:steps[stepIndex]!.target;
  for(const node of sceneNodes){
    const active=node.equipmentId===activeId;
    const fault=node.equipmentId===faultTarget;
    const emissive:Vec3=fault?[0.95,0.02,0.10]:active?[0.02,0.58,0.82]:(node.emissive??[0,0,0]);
    gl.uniformMatrix4fv(uniforms.model,false,modelMatrix(node,time,activeId));
    gl.uniform3fv(uniforms.baseColor,node.color);
    gl.uniform3fv(uniforms.emissive,emissive);
    gl.uniform1f(uniforms.faultPulse,fault?2.2:active?1.35:1.0);
    gl.drawArrays(gl.TRIANGLES,0,mesh.count);
  }
  gl.bindVertexArray(null);
}
function updateMovement(dt:number){
  if(simStatus!=="RUNNING") return;
  const forward:Vec3=[Math.sin(camera.yaw),0,-Math.cos(camera.yaw)];
  const right:Vec3=[Math.cos(camera.yaw),0,Math.sin(camera.yaw)];
  let mx=0,mz=0;
  if(keys.has("KeyW")||keys.has("ArrowUp")){mx+=forward[0];mz+=forward[2];}
  if(keys.has("KeyS")||keys.has("ArrowDown")){mx-=forward[0];mz-=forward[2];}
  if(keys.has("KeyD")||keys.has("ArrowRight")){mx+=right[0];mz+=right[2];}
  if(keys.has("KeyA")||keys.has("ArrowLeft")){mx-=right[0];mz-=right[2];}
  const mag=Math.hypot(mx,mz);
  if(mag>0){
    const sprint=keys.has("ShiftLeft")||keys.has("ShiftRight");
    const speed=sprint?5.4:3.2;
    mx/=mag; mz/=mag;
    camera.position[0]=clamp(camera.position[0]+mx*speed*dt,-7.2,7.2);
    camera.position[2]=clamp(camera.position[2]+mz*speed*dt,-7.2,7.2);
  }
}
function frame(now:number){
  const dt=Math.min(0.05,(now-lastFrame)/1000); lastFrame=now;
  if(simStatus==="RUNNING") elapsed+=dt;
  updateMovement(dt);
  fpsAccumulator+=dt; fpsFrames++;
  if(fpsAccumulator>=0.5){ fpsValue=Math.round(fpsFrames/fpsAccumulator); fpsAccumulator=0; fpsFrames=0; }
  renderScene(now/1000);
  const near=nearestEquipment();
  if(simStatus==="RUNNING"&&near&&near.d<3.0&&facingScore(near.item.position)>0.18){
    messageEl.textContent=near.item.id===steps[stepIndex]!.target?`E // INTERACT ${near.item.label}`:`${near.item.label} nearby // active target is ${steps[stepIndex]!.target}`;
  }
  updateHud();
  requestAnimationFrame(frame);
}

buttons.start.addEventListener("click",()=>{
  if(simStatus!=="READY"&&simStatus!=="PAUSED") return;
  const wasPaused=simStatus==="PAUSED"; simStatus="RUNNING";
  logEvent("SESSION",wasPaused?"Simulation resumed.":"WebGL2 first-person simulation started.");
  messageEl.textContent="Click the viewport for mouse-look. WASD move · Shift sprint · E interact · R reset.";
  updateHud();
});
buttons.pause.addEventListener("click",()=>{ if(simStatus==="RUNNING"){simStatus="PAUSED";logEvent("SESSION","Simulation paused.");updateHud();} });
buttons.confirm.addEventListener("click",confirmStep);
buttons.error.addEventListener("click",()=>{ if(simStatus==="RUNNING"){errors++;score=Math.max(0,score-12);logEvent("ERROR",`Instructor-recorded error on step ${stepIndex+1}.`);updateHud();} });
buttons.fault.addEventListener("click",injectFault);
buttons.clearFault.addEventListener("click",clearFault);
buttons.reset.addEventListener("click",resetSimulation);
buttons.export.addEventListener("click",exportAar);

canvas.addEventListener("click",()=>{ if(document.pointerLockElement!==canvas) void canvas.requestPointerLock(); });
document.addEventListener("pointerlockchange",()=>{
  pointerLocked=document.pointerLockElement===canvas;
  lookHintEl.textContent=pointerLocked?"MOUSE CAPTURED // ESC TO RELEASE":"CLICK VIEWPORT TO CAPTURE MOUSE";
  lookHintEl.classList.toggle("locked",pointerLocked);
});
document.addEventListener("mousemove",event=>{
  if(!pointerLocked||simStatus!=="RUNNING") return;
  camera.yaw-=event.movementX*0.0022;
  camera.pitch=clamp(camera.pitch-event.movementY*0.0020,-1.35,1.35);
});
window.addEventListener("keydown",event=>{
  keys.add(event.code);
  if(event.code==="KeyE"&&!event.repeat) interact();
  if(event.code==="KeyR"&&!event.repeat) resetSimulation();
  if(["ArrowUp","ArrowDown","ArrowLeft","ArrowRight","Space"].includes(event.code)) event.preventDefault();
});
window.addEventListener("keyup",event=>keys.delete(event.code));
window.addEventListener("blur",()=>keys.clear());

resetSimulation();
requestAnimationFrame(now=>{lastFrame=now;requestAnimationFrame(frame);});
