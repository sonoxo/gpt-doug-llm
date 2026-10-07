/* GPT-DOUG Quantum-Inspired Visual Renderer
 * Classical GPU/canvas visualization inspired by interference, phase-space,
 * superposition, and uncertainty concepts. This does NOT claim quantum-computer execution.
 */
(() => {
  if (window.GPT_QUANTUM_VIS) return;

  const state = {
    enabled: true,
    mode: "INTERFERENCE",
    intensity: 0.58,
    density: 72,
    coherence: 0.91,
    uncertainty: 0.14,
    phase: 0,
    fps: 60,
    reduced: matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches
  };

  const css = document.createElement("style");
  css.textContent = `
  :root{--q-cyan:#5ce1ff;--q-violet:#a779ff;--q-pink:#ff66c9;--q-gold:#ffd56b}
  #gpt-quantum-layer{position:fixed;inset:0;z-index:880;pointer-events:none;mix-blend-mode:screen;opacity:.54}
  #gpt-quantum-panel{position:fixed;right:10px;bottom:38px;z-index:1300;width:214px;padding:8px;border:1px solid rgba(92,225,255,.24);border-radius:7px;background:rgba(5,8,18,.82);backdrop-filter:blur(10px);box-shadow:0 12px 36px #0008;color:#dff9ff;font:8px ui-monospace,SFMono-Regular,Menlo,monospace}
  #gpt-quantum-panel .qtitle{display:flex;justify-content:space-between;color:var(--q-cyan);font-weight:800;letter-spacing:.08em}
  #gpt-quantum-panel .qrow{display:flex;justify-content:space-between;gap:8px;line-height:1.55;color:#86a6b4}
  #gpt-quantum-panel .qrow b{color:#f4fbff}
  #gpt-quantum-panel .qbar{height:3px;background:#132331;border-radius:99px;overflow:hidden;margin:3px 0 5px}
  #gpt-quantum-panel .qbar i{display:block;height:100%;background:linear-gradient(90deg,var(--q-cyan),var(--q-violet),var(--q-pink));box-shadow:0 0 10px var(--q-cyan)}
  #gpt-quantum-panel button{width:auto!important;padding:4px 6px!important;margin:3px 2px 0 0!important;font:7px ui-monospace,SFMono-Regular,Menlo,monospace!important;border:1px solid #275873!important;border-radius:4px!important;background:#07141d!important;color:#ccefff!important;cursor:pointer!important}
  .qviz-clarity{filter:contrast(1.05) saturate(1.06)}
  @media(max-width:760px){#gpt-quantum-panel{width:180px;right:6px;bottom:34px;opacity:.92}}
  `;
  document.head.appendChild(css);

  const canvas = document.createElement("canvas");
  canvas.id = "gpt-quantum-layer";
  document.body.appendChild(canvas);
  const ctx = canvas.getContext("2d", { alpha: true });
  const particles = [];
  const links = [];
  let w=0,h=0,dpr=1,last=performance.now(),frame=0;

  function resize(){
    dpr = Math.min(devicePixelRatio || 1, 2);
    w = innerWidth; h = innerHeight;
    canvas.width = Math.max(1, Math.floor(w*dpr));
    canvas.height = Math.max(1, Math.floor(h*dpr));
    canvas.style.width = w+"px"; canvas.style.height = h+"px";
    ctx.setTransform(dpr,0,0,dpr,0,0);
    seed();
  }

  function seed(){
    particles.length=0;
    const n = state.reduced ? Math.min(28,state.density) : state.density;
    for(let i=0;i<n;i++){
      particles.push({
        x:Math.random()*w,y:Math.random()*h,
        vx:(Math.random()-.5)*.18,vy:(Math.random()-.5)*.18,
        p:Math.random()*Math.PI*2,
        amp:.25+Math.random()*.75,
        band:i%4
      });
    }
  }

  function rgba(b,a){
    return [
      `rgba(92,225,255,${a})`,
      `rgba(167,121,255,${a})`,
      `rgba(255,102,201,${a})`,
      `rgba(255,213,107,${a})`
    ][b%4];
  }

  function drawField(t){
    const step = state.reduced ? 130 : 86;
    ctx.lineWidth=.55;
    for(let y=step/2;y<h;y+=step){
      const phase = t*.00045 + y*.008;
      ctx.beginPath();
      for(let x=0;x<=w;x+=8){
        const yv=y+Math.sin(x*.014+phase)*4.5*Math.sin(t*.0008+y*.002);
        x?ctx.lineTo(x,yv):ctx.moveTo(x,yv);
      }
      ctx.strokeStyle="rgba(92,225,255,.035)";
      ctx.stroke();
    }
    for(let x=step/2;x<w;x+=step){
      ctx.beginPath();
      for(let y=0;y<=h;y+=8){
        const xv=x+Math.sin(y*.014-t*.0004+x*.005)*3.5;
        y?ctx.lineTo(xv,y):ctx.moveTo(xv,y);
      }
      ctx.strokeStyle="rgba(167,121,255,.028)";
      ctx.stroke();
    }
  }

  function drawParticles(t,dt){
    const drift=state.reduced?0:1;
    for(const p of particles){
      p.x+=p.vx*dt*.06*drift; p.y+=p.vy*dt*.06*drift; p.p+=dt*.0007;
      if(p.x<-20)p.x=w+20;if(p.x>w+20)p.x=-20;if(p.y<-20)p.y=h+20;if(p.y>h+20)p.y=-20;
    }
    for(let i=0;i<particles.length;i++){
      const a=particles[i];
      const glow=(.025+.045*(.5+.5*Math.sin(a.p+t*.0018)))*state.intensity;
      ctx.fillStyle=rgba(a.band,glow*2.5);
      ctx.beginPath();ctx.arc(a.x,a.y,1.1+a.amp*1.1,0,Math.PI*2);ctx.fill();
      if(i%2===0){
        for(let j=i+1;j<Math.min(particles.length,i+9);j++){
          const b=particles[j],dx=a.x-b.x,dy=a.y-b.y,d=Math.hypot(dx,dy);
          if(d<145){
            const alpha=(1-d/145)*.045*state.intensity;
            ctx.strokeStyle=rgba((a.band+b.band)%4,alpha);
            ctx.lineWidth=.55;
            ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
          }
        }
      }
    }
  }

  function drawPhaseRing(t){
    const x=w*.5,y=h*.5,r=Math.min(w,h)*.18;
    ctx.save();
    ctx.translate(x,y);
    ctx.rotate(t*.00008);
    ctx.setLineDash([4,9]);
    for(let i=0;i<3;i++){
      ctx.beginPath();ctx.arc(0,0,r+i*18,0,Math.PI*2);
      ctx.strokeStyle=rgba(i,.035*state.intensity);
      ctx.lineWidth=.7;ctx.stroke();
    }
    ctx.restore();ctx.setLineDash([]);
  }

  function loop(t){
    const dt=Math.min(50,t-last);last=t;frame++;
    if(frame%20===0) state.fps=Math.round(1000/Math.max(1,dt));
    if(state.enabled){
      ctx.clearRect(0,0,w,h);
      state.phase=(state.phase+dt*.00016)%(Math.PI*2);
      state.coherence=.88+.07*(.5+.5*Math.sin(t*.00037));
      state.uncertainty=.09+.09*(.5+.5*Math.cos(t*.00029));
      if(state.mode==="INTERFERENCE") drawField(t);
      if(state.mode==="PHASE"||state.mode==="INTERFERENCE") drawPhaseRing(t);
      drawParticles(t,dt);
      updatePanel();
    } else ctx.clearRect(0,0,w,h);
    requestAnimationFrame(loop);
  }

  const panel=document.createElement("div");
  panel.id="gpt-quantum-panel";
  panel.innerHTML=`
    <div class="qtitle"><span>◈ QUANTUM-INSPIRED RENDER</span><span id="qstat">ON</span></div>
    <div class="qrow"><span>Mode</span><b id="qmode">INTERFERENCE</b></div>
    <div class="qrow"><span>Coherence</span><b id="qcoh">91%</b></div><div class="qbar"><i id="qcohbar" style="width:91%"></i></div>
    <div class="qrow"><span>Uncertainty</span><b id="qunc">14%</b></div><div class="qbar"><i id="quncbar" style="width:14%"></i></div>
    <div class="qrow"><span>Renderer</span><b id="qfps">GPU/CANVAS</b></div>
    <div class="qrow"><span>Compute</span><b>CLASSICAL / QUANTUM-INSPIRED</b></div>
    <button id="qtoggle">Q TOGGLE</button><button id="qmodebtn">M MODE</button><button id="qclarity">CLARITY</button>
  `;
  document.body.appendChild(panel);

  function updatePanel(){
    panel.querySelector("#qstat").textContent=state.enabled?"ON":"OFF";
    panel.querySelector("#qmode").textContent=state.mode;
    panel.querySelector("#qcoh").textContent=Math.round(state.coherence*100)+"%";
    panel.querySelector("#qcohbar").style.width=(state.coherence*100)+"%";
    panel.querySelector("#qunc").textContent=Math.round(state.uncertainty*100)+"%";
    panel.querySelector("#quncbar").style.width=(state.uncertainty*100)+"%";
    panel.querySelector("#qfps").textContent=state.fps+" FPS";
  }

  function toggle(){state.enabled=!state.enabled;canvas.style.display=state.enabled?"block":"none";updatePanel()}
  function mode(){state.mode=state.mode==="INTERFERENCE"?"PHASE":state.mode==="PHASE"?"ENTANGLEMENT":"INTERFERENCE";updatePanel()}
  function clarity(){document.documentElement.classList.toggle("qviz-clarity")}

  panel.querySelector("#qtoggle").onclick=toggle;
  panel.querySelector("#qmodebtn").onclick=mode;
  panel.querySelector("#qclarity").onclick=clarity;
  addEventListener("keydown",e=>{
    if(e.target && /input|textarea|select/i.test(e.target.tagName)) return;
    if(e.key.toLowerCase()==="q") toggle();
    if(e.key.toLowerCase()==="m") mode();
  });
  addEventListener("resize",resize);

  window.GPT_QUANTUM_VIS={
    state,
    toggle,
    mode,
    clarity,
    setIntensity(v){state.intensity=Math.max(0,Math.min(1,Number(v)||0));},
    setDensity(v){state.density=Math.max(12,Math.min(180,Number(v)||72));seed();},
    status(){return {...state,technology:"classical GPU/canvas, quantum-inspired visualization"}}
  };

  resize();requestAnimationFrame(loop);
})();
