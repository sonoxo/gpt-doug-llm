/* SKULL-LLM 3D command center. Pure WebGL2; no CDN, cookies, tracking, or paid API. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const canvas = $('#brain-scene');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const state = {
    mode: 'fusion', autorotate: !reducedMotion, nodes: true,
    yaw: -0.18, pitch: -0.045, distance: 4.75,
    running: false, activity: 0.13, t: 0, phase: 'retrieve',
  };
  $('#autorotate').checked = state.autorotate;
  $('#orbit-value').textContent = state.autorotate ? 'ON' : 'OFF';
  const clean = (text) => String(text || '').replace(/[\u0000-\u001f\u007f]/g, ' ').slice(0, 500);

  const el = (tag, className, value) => {
    const elem = document.createElement(tag);
    if (className) elem.className = className;
    if (value !== undefined) elem.textContent = value;
    return elem;
  };
  function createMessage(role, content) {
    const empty = $('.transcript-empty');
    if (empty) empty.remove();
    const messages = $('#transcript');
    const wrap = el('div', `message ${role}`);
    const head = el('div', 'message-header');
    head.append(el('span', null, role === 'user' ? 'YOU / COMMAND' : role === 'error' ? 'SYSTEM / ERROR' : 'SKULL-LLM / RESPONSE'));
    head.append(el('small', null, new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})));
    wrap.append(head, el('div', 'bubble', content));
    messages.append(wrap);
    while (messages.children.length > 30) messages.firstElementChild.remove();
    messages.scrollTop = messages.scrollHeight;
    return wrap;
  }
  const phaseSequence = ['retrieve', 'draft', 'critique', 'revise'];
  function setPhase(phase, message) {
    state.phase = phase;
    const idx = phaseSequence.indexOf(phase);
    $$('#phase-track .phase').forEach((node, i) => {
      node.classList.toggle('done', idx >= 0 && i < idx);
      node.classList.toggle('active', idx >= 0 && i === idx);
    });
    $('#phase-detail').textContent = clean(message || phase.toUpperCase());
    $('#metric-phase').textContent = clean(message || phase.toUpperCase()).toUpperCase();
    state.activity = Math.max(state.activity, 0.9);
  }
  function $$(selector) { return [...document.querySelectorAll(selector)]; }
  function setBusy(busy) {
    state.running = busy;
    $('#send').disabled = busy;
    $('#send-text').textContent = busy ? 'PROCESSING' : 'EXECUTE';
    if (!busy) state.activity = 0.35;
  }
  async function getStatus() {
    const badge = $('#connection');
    try {
      const response = await fetch('/api/status', {cache:'no-store', credentials:'same-origin'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const snapshot = await response.json();
      const ollama = snapshot.ollama || {};
      const available = Boolean(snapshot.ready_for_inference);
      badge.lastChild.textContent = available ? ' LOCAL MODEL READY' : snapshot.stopped ? ' EMERGENCY STOP' : ' LOCAL MODEL OFFLINE';
      $('#connection-dot').classList.toggle('off', !available);
      $('#metric-ready').textContent = available ? 'READY' : snapshot.stopped ? 'STOPPED' : 'OFFLINE';
      $('#metric-model').textContent = clean(ollama.model || 'NOT SELECTED').toUpperCase();
      $('#system-intro').textContent = available
        ? 'Local neural model connected. Your prompts remain on this computer.'
        : '3D interface ready. Start Ollama and install a local model to activate chat.';
    } catch (error) {
      badge.lastChild.textContent = ' SERVICE NOT CONNECTED';
      $('#connection-dot').classList.add('off');
      $('#metric-ready').textContent = 'OFFLINE';
      $('#metric-model').textContent = 'NOT CONNECTED';
    }
  }
  getStatus();
  window.setInterval(getStatus, 30000);

  const form = $('#chat-form');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (state.running) return;
    const task = $('#prompt').value.trim();
    if (!task || task.length > 8000) return;
    createMessage('user', task);
    $('#prompt').value = '';
    setBusy(true);
    setPhase('retrieve', 'Retrieving local context');
    let gotAnswer = false;
    try {
      const response = await fetch('/api/chat', {
        method:'POST', cache:'no-store', credentials:'same-origin',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({task, depth:Number($('#depth').value), remember:$('#remember').checked}),
      });
      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        try { const data = await response.json(); errorMessage = String(data.error || errorMessage); }
        catch (_) { /* status is still available */ }
        throw new Error(errorMessage);
      }
      if (!response.body) throw new Error('Streaming response unavailable in this browser');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let pending = '';
      function receive(record) {
        if (!record || typeof record !== 'object') return;
        if (record.type === 'phase') setPhase(record.phase, record.message);
        if (record.type === 'answer') {
          gotAnswer = true;
          createMessage('assistant', String(record.answer || 'No answer returned.'));
          setPhase('complete', `${Number(record.calls || 0)} local model call(s) completed`);
        }
        if (record.type === 'error') throw new Error(String(record.error || 'Local model failed'));
      }
      for (;;) {
        const {value, done} = await reader.read();
        if (done) break;
        pending += decoder.decode(value, {stream:true});
        let split;
        while ((split = pending.indexOf('\n')) !== -1) {
          const line = pending.slice(0, split); pending = pending.slice(split + 1);
          if (!line.trim()) continue;
          receive(JSON.parse(line));
        }
      }
      pending += decoder.decode();
      if (pending.trim()) receive(JSON.parse(pending));
      if (!gotAnswer) throw new Error('Local model completed without returning an answer');
    } catch (error) {
      createMessage('error', `SKULL link failed: ${clean(error.message)}`);
      setPhase('error', 'Inference failed; verify local Ollama model and emergency stop');
    } finally { setBusy(false); getStatus(); }
  });
  $('#prompt').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault(); form.requestSubmit();
    }
  });
  $$('.mode-button').forEach((button) => button.addEventListener('click', () => {
    state.mode = button.dataset.mode;
    $$('.mode-button').forEach((b) => {
      const current = b === button;
      b.classList.toggle('active', current);
      b.setAttribute('aria-pressed', String(current));
    });
  }));
  $('#autorotate').addEventListener('change', (event) => {
    state.autorotate = event.target.checked;
    $('#orbit-value').textContent = state.autorotate ? 'ON' : 'OFF';
  });
  $('#show-nodes').addEventListener('change', (event) => {
    state.nodes = event.target.checked;
    $('#node-value').textContent = state.nodes ? 'ON' : 'OFF';
  });
  $('#reset-view').addEventListener('click', resetView);
  $('#refresh-status').addEventListener('click', getStatus);
  function resetView() { state.yaw = -0.18; state.pitch = -0.045; state.distance = 4.75; }
  canvas.addEventListener('dblclick', resetView);
  let drag = null;
  canvas.addEventListener('pointerdown', (event) => {
    drag = {id:event.pointerId,x:event.clientX,y:event.clientY};
    canvas.setPointerCapture(event.pointerId);
    canvas.classList.add('dragging');
  });
  canvas.addEventListener('pointermove', (event) => {
    if (!drag || event.pointerId !== drag.id) return;
    state.yaw += (event.clientX - drag.x) * 0.008;
    state.pitch = Math.max(-1.15, Math.min(1.15, state.pitch + (event.clientY - drag.y) * 0.006));
    drag.x = event.clientX; drag.y = event.clientY;
  });
  function endDrag(event) {
    if (drag && event.pointerId === drag.id) { drag = null; canvas.classList.remove('dragging'); }
  }
  canvas.addEventListener('pointerup', endDrag);
  canvas.addEventListener('pointercancel', endDrag);
  canvas.addEventListener('wheel', (event) => {
    event.preventDefault(); state.distance = Math.max(3.1, Math.min(9, state.distance + Math.sign(event.deltaY) * 0.22));
  }, {passive:false});

  // --- low-level WebGL2 math and procedural mesh generation ---
  const gl = canvas.getContext('webgl2', {alpha:false, antialias:true, depth:true, powerPreference:'high-performance'});
  if (!gl) { if (!window.SkullSoftware3D?.(canvas, state)) $('#webgl-error').hidden = false; return; }
  const shaders = {
    meshVertex: `#version 300 es
      precision highp float;
      layout(location=0) in vec3 aPosition;
      layout(location=1) in vec3 aNormal;
      layout(location=2) in vec3 aColor;
      uniform mat4 uMVP; uniform mat4 uModel;
      out vec3 vNormal; out vec3 vColor; out vec3 vPosition;
      void main(){
        vec4 world = uModel * vec4(aPosition,1.0);
        gl_Position = uMVP * vec4(aPosition,1.0);
        vNormal = normalize(mat3(uModel)*aNormal);
        vColor = aColor;
        vPosition = world.xyz;
      }
    `,
    meshFragment: `#version 300 es
      precision highp float;
      in vec3 vNormal; in vec3 vColor; in vec3 vPosition;
      uniform float uAlpha; uniform float uEnergy; uniform float uTime;
      uniform float uGlow; uniform int uType;
      out vec4 outputColor;
      void main(){
        vec3 normal = normalize(vNormal);
        vec3 light = normalize(vec3(-0.47,0.67,1.0));
        float diffuse = max(0.0,dot(normal,light));
        float bounce = max(0.0,dot(normal,normalize(vec3(0.5,-0.7,-0.6))));
        float rim = pow(1.0-max(0.0,dot(normal,vec3(0.0,0.0,1.0))),2.8);
        float noise = sin(vPosition.x*58.0+sin(vPosition.y*39.0))*sin(vPosition.y*44.0+vPosition.z*33.0)*0.018;
        vec3 color = vColor*(0.38+diffuse*0.73+bounce*0.19+noise);
        vec3 viewHalf = normalize(light+vec3(0.0,0.0,1.0));
        float shine = pow(max(0.0,dot(normal,viewHalf)),40.0);
        color += vec3(0.75,0.9,0.85)*shine*0.19;
        color += vec3(0.22,0.95,0.84)*rim*(0.3+uEnergy*0.48);
        if (uType == 1) color = vColor*(0.42+0.4*diffuse)+vec3(0.25,0.9,0.9)*rim*0.37;
        if (uType == 2) color = vColor*(0.3+diffuse*0.37)+vec3(0.25,0.95,0.86)*rim*(0.6+uEnergy*0.5);
        color += vColor*uGlow*(0.38+uEnergy*0.22);
        outputColor=vec4(color,uAlpha);
      }
    `,
    lineVertex: `#version 300 es
      precision highp float;
      layout(location=0) in vec3 aPosition;
      uniform mat4 uMVP;
      uniform float uSize;
      out vec3 vPosition;
      void main(){gl_Position=uMVP*vec4(aPosition,1.0); gl_PointSize=uSize; vPosition=aPosition;}
    `,
    lineFragment: `#version 300 es
      precision highp float;
      uniform vec3 uColor; uniform float uAlpha; uniform float uEnergy; uniform int uPoint;
      out vec4 outputColor;
      void main(){
        float falloff=1.0;
        if(uPoint==1){float dist=length(gl_PointCoord-vec2(0.5))*2.0; if(dist>1.0) discard; falloff=pow(1.0-dist,1.7);}
        outputColor=vec4(uColor*(1.0+uEnergy*0.8),uAlpha*falloff);
      }
    `,
  };
  const makeShader = (source,type) => {
    const shader=gl.createShader(type); gl.shaderSource(shader,source); gl.compileShader(shader);
    if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
    return shader;
  };
  function makeProgram(vertex,fragment) {
    const program=gl.createProgram();
    gl.attachShader(program,makeShader(vertex,gl.VERTEX_SHADER));
    gl.attachShader(program,makeShader(fragment,gl.FRAGMENT_SHADER));
    gl.linkProgram(program);
    if(!gl.getProgramParameter(program,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    return program;
  }
  let meshProgram,lineProgram;
  try { meshProgram=makeProgram(shaders.meshVertex,shaders.meshFragment); lineProgram=makeProgram(shaders.lineVertex,shaders.lineFragment); }
  catch (error) { $('#webgl-error').textContent='Unable to initialize the 3D GPU renderer: '+clean(error.message); $('#webgl-error').hidden=false; return; }
  const meshU={mvp:gl.getUniformLocation(meshProgram,'uMVP'),model:gl.getUniformLocation(meshProgram,'uModel'),alpha:gl.getUniformLocation(meshProgram,'uAlpha'),energy:gl.getUniformLocation(meshProgram,'uEnergy'),time:gl.getUniformLocation(meshProgram,'uTime'),glow:gl.getUniformLocation(meshProgram,'uGlow'),type:gl.getUniformLocation(meshProgram,'uType')};
  const lineU={mvp:gl.getUniformLocation(lineProgram,'uMVP'),size:gl.getUniformLocation(lineProgram,'uSize'),color:gl.getUniformLocation(lineProgram,'uColor'),alpha:gl.getUniformLocation(lineProgram,'uAlpha'),energy:gl.getUniformLocation(lineProgram,'uEnergy'),point:gl.getUniformLocation(lineProgram,'uPoint')};
  const identity = () => new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);
  function multiply(a,b) {
    const out=new Float32Array(16);
    for(let c=0;c<4;c++) for(let r=0;r<4;r++) {
      for(let k=0;k<4;k++) out[c*4+r]+=a[k*4+r]*b[c*4+k];
    }
    return out;
  }
  function rotateY(a) {const m=identity(),c=Math.cos(a),s=Math.sin(a);m[0]=c;m[8]=s;m[2]=-s;m[10]=c;return m;}
  function rotateX(a) {const m=identity(),c=Math.cos(a),s=Math.sin(a);m[5]=c;m[9]=-s;m[6]=s;m[10]=c;return m;}
  function translate(x,y,z) {const m=identity();m[12]=x;m[13]=y;m[14]=z;return m;}
  function perspective(fovy,aspect,near,far){
    const f=1/Math.tan(fovy/2),o=new Float32Array(16);o[0]=f/aspect;o[5]=f;o[10]=(far+near)/(near-far);o[11]=-1;o[14]=2*far*near/(near-far);return o;
  }
  function createBatch(){return {v:[],idx:[]};}
  function addVert(batch,pos,normal,color) {
    const i=batch.v.length/9;
    batch.v.push(...pos,...normal,...color);
    return i;
  }
  function ellipsoid(batch, center, radii, color, seg=30, rings=20, wave=0) {
    const offset=batch.v.length/9;
    for(let iy=0;iy<=rings;iy++){
      const theta=iy/rings*Math.PI, sy=Math.cos(theta), ring=Math.sin(theta);
      for(let ix=0;ix<=seg;ix++){
        const phi=ix/seg*Math.PI*2, x=ring*Math.cos(phi), z=ring*Math.sin(phi);
        const wrinkles=1+wave*Math.sin(phi*11+theta*7)*Math.sin(phi*5-theta*13);
        const normal=[x/radii[0],sy/radii[1],z/radii[2]];
        const len=Math.hypot(...normal)||1;
        const p=[center[0]+radii[0]*x*wrinkles,center[1]+radii[1]*sy*wrinkles,center[2]+radii[2]*z*wrinkles];
        addVert(batch,p,normal.map(c=>c/len),color);
      }
    }
    for(let y=0;y<rings;y++)for(let x=0;x<seg;x++){
      const a=offset+y*(seg+1)+x,b=a+seg+1;
      batch.idx.push(a,b,a+1,b,b+1,a+1);
    }
  }
  function addTube(batch,points,radius,color,sides=8){
    if(points.length<2)return;
    const start=batch.v.length/9;
    points.forEach((point,i)=>{
      const prev=points[Math.max(0,i-1)],next=points[Math.min(points.length-1,i+1)];
      const tangent=[next[0]-prev[0],next[1]-prev[1],next[2]-prev[2]];
      const len=Math.hypot(...tangent)||1; tangent.forEach((v,k)=>tangent[k]=v/len);
      const reference=(Math.abs(tangent[1])>0.93)?[1,0,0]:[0,1,0];
      let cross=[tangent[1]*reference[2]-tangent[2]*reference[1],tangent[2]*reference[0]-tangent[0]*reference[2],tangent[0]*reference[1]-tangent[1]*reference[0]];
      const crossLen=Math.hypot(...cross)||1;cross=cross.map(v=>v/crossLen);
      const second=[tangent[1]*cross[2]-tangent[2]*cross[1],tangent[2]*cross[0]-tangent[0]*cross[2],tangent[0]*cross[1]-tangent[1]*cross[0]];
      for(let j=0;j<=sides;j++){
        const angle=j/sides*2*Math.PI;const n=[0,1,2].map(k=>Math.cos(angle)*cross[k]+Math.sin(angle)*second[k]);
        addVert(batch,point.map((v,k)=>v+radius*n[k]),n,color);
      }
    });
    for(let i=0;i<points.length-1;i++)for(let j=0;j<sides;j++){
      const a=start+i*(sides+1)+j,b=a+sides+1;
      batch.idx.push(a,a+1,b,a+1,b+1,b);
    }
  }
  function pathPoints(fn,count=40){return Array.from({length:count+1},(_,i)=>fn(i/count));}
  function addOrbit(batch,side,color,radius=0.066){
    const pts=pathPoints(t=>{
      const a=t*Math.PI*2;
      return [side*0.50+0.34*Math.cos(a),0.05+0.405*Math.sin(a),0.865+0.06*Math.cos(a*2)];
    },55);
    addTube(batch,pts,radius,color,9);
  }
  // Four physical layers permit a scan-mode change without faking real medical data.
  const shell=createBatch(),face=createBatch(),dark=createBatch(),cortex=createBatch();
  const bone=[0.70,0.77,0.75],boneLight=[0.83,0.85,0.82],boneShadow=[0.52,0.64,0.65],teeth=[0.95,0.93,0.83];
  const cavity=[0.014,0.044,0.060],teal=[0.18,0.74,0.75],brain=[0.32,0.59,0.62];
  ellipsoid(shell,[0,0.52,-0.14],[1.03,1.15,0.84],bone,56,36,0.016);
  ellipsoid(shell,[0,-0.49,-0.34],[0.77,0.54,0.56],boneShadow,38,26,0.013);
  ellipsoid(face,[0,-0.72,0.45],[0.63,0.47,0.51],bone,35,24,0.012);
  ellipsoid(face,[0,-0.34,0.66],[0.21,0.54,0.23],boneLight,22,18,0.008);
  ellipsoid(face,[0,-0.77,0.91],[0.29,0.21,0.09],boneShadow,24,12);
  ellipsoid(dark,[0,-0.56,1.028],[0.19,0.31,0.07],cavity,25,16);
  ellipsoid(dark,[0,-0.985,0.97],[0.59,0.083,0.09],cavity,32,10);
  for(const side of [-1,1]){
    // Deep black orbital cavities with distinct orbital bone arches.
    ellipsoid(dark,[side*0.50,0.065,0.83],[0.346,0.404,0.14],cavity,34,22);
    addOrbit(face,side,boneLight,0.067);
    ellipsoid(face,[side*0.91,-0.47,0.49],[0.22,0.24,0.36],boneLight,21,15);
    ellipsoid(face,[side*0.61,-0.55,0.75],[0.26,0.19,0.27],boneShadow,22,16);
    // Brow ridges, temporal muscle attachment and zygomatic arch.
    addTube(face,pathPoints(t=>[side*(0.2+0.66*t),0.43+0.13*Math.sin(Math.PI*t),0.82-0.12*t],25),0.082,boneLight);
    addTube(face,pathPoints(t=>[side*(0.83+0.10*Math.sin(t*Math.PI)),0.10-0.66*t,0.55-0.07*Math.sin(t*Math.PI)],24),0.07,boneShadow);
    addTube(face,pathPoints(t=>[side*(0.63+0.28*t),-0.43-0.09*Math.sin(Math.PI*t),0.74-0.27*t],25),0.073,boneLight);
    addTube(face,pathPoints(t=>[side*(0.12+0.40*t),-0.47+0.02*Math.sin(Math.PI*t),0.94-0.03*t],20),0.049,boneLight);
    // Mandible angles, curved body and ascending ramus.
    const mandible=pathPoints(t=>{
      const angle=t*Math.PI;
      return [side*(0.76*(1-t)), -0.79-0.76*Math.sin(angle*0.5),0.57+0.35*Math.sin(angle*0.5)];
    },28);
    addTube(face,mandible,0.134,boneShadow,11);
    addTube(face,pathPoints(t=>[side*(0.79-0.075*Math.sin(Math.PI*t)),-0.58-0.54*t,0.54+0.03*t],18),0.115,boneShadow,10);
  }
  // Maxilla and mandible teeth, individually separated and irregularly shaped.
  for(let i=0;i<12;i++){
    const k=(i-5.5)/5.5,x=k*0.57;
    const z=1.005-0.20*k*k;
    const crown=0.085+(1-Math.abs(k))*0.016;
    ellipsoid(face,[x,-1.005,z],[crown*0.50,0.095,crown*0.72],teeth,12,10,0.02);
    ellipsoid(face,[x,-1.19,z-0.024],[crown*0.50,0.078,crown*0.74],teeth,12,10,0.02);
  }
  // Stylized anatomical cortical mass, intentionally non-clinical.
  ellipsoid(cortex,[-0.3,0.60,-0.17],[0.57,0.78,0.63],brain,35,30,0.07);
  ellipsoid(cortex,[0.3,0.60,-0.17],[0.57,0.78,0.63],brain,35,30,0.07);
  const amber=[0.55,0.67,0.58];
  for(const side of [-1,1])for(let i=0;i<8;i++){
    const yy=0.01+i*0.165,angle=i*1.83;
    addTube(cortex,pathPoints(t=>{
      const phi=-0.92+t*1.90;
      return [side*(0.26+0.42*Math.cos(phi+angle*0.05)),yy+0.035*Math.sin(t*17+i),0.24+0.33*Math.sin(phi+1.1)];
    },25),0.018,amber,6);
  }
  function toGpu(batch){
    if(batch.v.length/9>=65536) throw new Error('Geometry exceeds 16-bit index limit');
    const vao=gl.createVertexArray();gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER,gl.createBuffer());gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(batch.v),gl.STATIC_DRAW);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,gl.createBuffer());gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(batch.idx),gl.STATIC_DRAW);
    const stride=9*4;
    for(let i=0;i<3;i++){gl.enableVertexAttribArray(i);gl.vertexAttribPointer(i,3,gl.FLOAT,false,stride,i*12);}
    gl.bindVertexArray(null);
    return {vao,count:batch.idx.length};
  }
  const meshes={shell:toGpu(shell),face:toGpu(face),dark:toGpu(dark),cortex:toGpu(cortex)};
  // Seeded points and edges: physically present 3D synaptic lattice, not telemetry.
  let seed=2607;
  function rand(){seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;}
  const nodes=[];
  for(let i=0;i<270;i++){
    const u=rand()*2-1,a=rand()*Math.PI*2,r=Math.sqrt(1-u*u);
    const rr=1.11+rand()*0.16;
    nodes.push([rr*r*Math.cos(a),0.35+rr*u*1.05,rr*r*Math.sin(a)*0.80]);
  }
  const edges=[];
  for(let i=0;i<nodes.length;i++){
    const dists=[];
    for(let j=0;j<nodes.length;j++){
      if(i===j)continue;
      const v=nodes[i],w=nodes[j];
      const d=(v[0]-w[0])**2+(v[1]-w[1])**2+(v[2]-w[2])**2;
      dists.push([d,j]);
    }
    dists.sort((a,b)=>a[0]-b[0]);
    for(let k=0;k<2;k++)if(dists[k][1]>i)edges.push(nodes[i],nodes[dists[k][1]]);
  }
  const rings=[];
  for(let layer=0;layer<3;layer++)for(let i=0;i<140;i++){
    const t=i*Math.PI*2/140,u=(i+1)*Math.PI*2/140;
    const a=1.67+layer*0.12,y=0.33;
    if(layer===0){rings.push([a*Math.cos(t),y+a*0.82*Math.sin(t),-0.2],[a*Math.cos(u),y+a*0.82*Math.sin(u),-0.2]);}
    else if(layer===1){rings.push([a*Math.cos(t),0.35+0.25*Math.sin(t),a*Math.sin(t)],[a*Math.cos(u),0.35+0.25*Math.sin(u),a*Math.sin(u)]);}
    else{rings.push([a*Math.cos(t),0.35+a*0.72*Math.sin(t),-0.30],[a*Math.cos(u),0.35+a*0.72*Math.sin(u),-0.30]);}
  }
  function gpuLines(points){
    const vao=gl.createVertexArray();gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER,gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(points.flat()),gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,3,gl.FLOAT,false,0,0);
    gl.bindVertexArray(null);return {vao,count:points.length};
  }
  const gpuEdges=gpuLines(edges),gpuNodes=gpuLines(nodes),gpuRings=gpuLines(rings);
  function drawMesh(mesh,mvp,model,alpha,glow=0,type=0){
    gl.useProgram(meshProgram);gl.bindVertexArray(mesh.vao);
    gl.uniformMatrix4fv(meshU.mvp,false,mvp);gl.uniformMatrix4fv(meshU.model,false,model);
    gl.uniform1f(meshU.alpha,alpha);gl.uniform1f(meshU.energy,state.activity);gl.uniform1f(meshU.time,state.t);
    gl.uniform1f(meshU.glow,glow);gl.uniform1i(meshU.type,type);
    gl.drawElements(gl.TRIANGLES,mesh.count,gl.UNSIGNED_SHORT,0);gl.bindVertexArray(null);
  }
  function drawLines(gpu,mvp,color,alpha,size=1,point=false){
    gl.useProgram(lineProgram);gl.bindVertexArray(gpu.vao);
    gl.uniformMatrix4fv(lineU.mvp,false,mvp);
    gl.uniform3fv(lineU.color,color);gl.uniform1f(lineU.alpha,alpha);
    gl.uniform1f(lineU.energy,state.activity);gl.uniform1f(lineU.size,size);gl.uniform1i(lineU.point,point?1:0);
    gl.drawArrays(point?gl.POINTS:gl.LINES,0,gpu.count);gl.bindVertexArray(null);
  }
  gl.enable(gl.DEPTH_TEST);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
  let last=performance.now(),rendered=0;
  function render(now){
    const dt=Math.min((now-last)/1000,.05);last=now;
    if(state.autorotate && !drag) state.yaw+=dt*0.14;
    state.t+=dt;
    state.activity+=(state.running?0.95:0.16-state.activity)*Math.min(1,dt*2.4);
    const ratio=Math.min(window.devicePixelRatio||1,2);
    const bounds=canvas.getBoundingClientRect();
    const w=Math.max(1,Math.floor(bounds.width*ratio)),h=Math.max(1,Math.floor(bounds.height*ratio));
    if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);}
    gl.clearColor(0.037,0.064,0.096,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    const aspect=w/h;
    const projection=perspective(Math.PI/3.8,aspect,0.1,30);
    const view=translate(0,-0.05,-state.distance);
    const model=multiply(rotateY(state.yaw),rotateX(state.pitch));
    const mvp=multiply(projection,multiply(view,model));
    const isAnatomy=state.mode==='anatomy',xray=state.mode==='xray';
    if(xray){
      drawMesh(meshes.cortex,mvp,model,0.90,0.2,2);
      drawMesh(meshes.dark,mvp,model,0.8,0,1);
      gl.depthMask(false);drawMesh(meshes.shell,mvp,model,.13,0,0);gl.depthMask(true);
      drawMesh(meshes.face,mvp,model,0.42,0,0);
    } else if(isAnatomy){
      drawMesh(meshes.shell,mvp,model,1,0,0);
      drawMesh(meshes.dark,mvp,model,1,0,1);
      drawMesh(meshes.face,mvp,model,1,0,0);
    } else {
      drawMesh(meshes.cortex,mvp,model,.55,0.12,2);
      drawMesh(meshes.dark,mvp,model,1,0,1);
      gl.depthMask(false);drawMesh(meshes.shell,mvp,model,.61,0.05,0);gl.depthMask(true);
      drawMesh(meshes.face,mvp,model,.96,0.045,0);
    }
    if(state.nodes && !isAnatomy){
      gl.disable(gl.DEPTH_TEST);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);
      drawLines(gpuEdges,mvp,[0.20,0.76,0.74],0.12+state.activity*0.22);
      drawLines(gpuNodes,mvp,[0.42,0.99,0.86],0.45+state.activity*0.30,3.2*ratio+state.activity*3*ratio,true);
      gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.enable(gl.DEPTH_TEST);
    }
    if(!isAnatomy){
      gl.disable(gl.DEPTH_TEST);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);
      drawLines(gpuRings,mvp,[0.32,0.63,0.65],0.19+state.activity*0.07);
      gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.enable(gl.DEPTH_TEST);
    }
    if(rendered%10===0){
      $('#yaw-label').textContent=(state.yaw*180/Math.PI%360).toFixed(1).padStart(5,'0')+'°';
      $('#pitch-label').textContent=(state.pitch*180/Math.PI).toFixed(1).padStart(5,'0')+'°';
      $('#zoom-label').textContent=state.distance.toFixed(1);
    }
    rendered++;
    if(document.visibilityState==='visible') window.requestAnimationFrame(render);
  }
  document.addEventListener('visibilitychange',()=>{
    if(document.visibilityState==='visible'){last=performance.now();window.requestAnimationFrame(render);}
  });
  window.requestAnimationFrame(render);
})();
