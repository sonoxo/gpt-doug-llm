"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const local = ["127.0.0.1", "localhost"].includes(location.hostname) && location.protocol === "http:";
  const setStatus = (message, error=false) => {
    $("status").textContent = message;
    $("status").classList.toggle("error", error);
  };
  const canvas = $("demoCanvas");
  const ctx = canvas.getContext("2d");
  let healthTimer = null;
  let animation = null;
  let busy = false;

  function scheduleHealth() {
    if (!local) return;
    if (healthTimer) clearTimeout(healthTimer);
    healthTimer = setTimeout(health, 4000);
  }
  function reportStage(data) {
    const ready = Boolean(data.trained_checkpoint_present);
    const pipeline = data.pipeline || {};
    const stage = ready ? "ready" : pipeline.stage || "not-started";
    const names = {
      ready: "TRAINED CHECKPOINT DETECTED",
      installing: "INSTALLING FREE MODEL DEPENDENCIES",
      training: "TRAINING STARTER MODEL LOCALLY",
      failed: "LOCAL SETUP FAILED — READ TERMINAL LOG",
      "not-started": "NO MODEL CHECKPOINT YET"
    };
    $("healthLamp").dataset.stage = stage;
    $("stageText").textContent = names[stage] || "LOCAL ENGINE CONNECTED";
    $("modelReady").textContent = ready ? "READY" : stage === "training" ? "LEARNING" : "SETUP";
    $("modelHint").textContent = ready ? "Local checkpoint available" :
      stage === "installing" ? "PyTorch and Pillow install runs on your Mac" :
      stage === "training" ? "Synthetic starter training uses only your machine" :
      stage === "failed" ? "See install.log or training.log in the local Motion-1 directory" :
      "Training begins after free setup";
    const done = pipeline.completed_steps, total = pipeline.total_steps;
    const progress = $("trainProgress");
    progress.hidden = stage !== "training" || !Number.isInteger(done) || !Number.isInteger(total) || total <= 0;
    if (!progress.hidden) progress.value = Math.min(100, Math.round(done / total * 100));
    $("generate").disabled = !ready || busy;
    $("preview").disabled = busy;
    if (!busy) {
      setStatus(ready ? "LOCAL ENGINE ONLINE. Create a neural GIF from trained weights." :
        stage === "failed" ? "Setup failed. Open Terminal and inspect the local install/training log. Browser demo remains available." :
        stage === "installing" ? "Local studio is live. Free model libraries are installing; try the instant browser demo." :
        stage === "training" ? "Local studio is live while Motion-1 trains. Neural generation unlocks when the checkpoint is saved." :
        "Local studio is live. Try the browser demo or start local training.");
    }
  }
  async function health() {
    if (!local) {
      $("healthLamp").dataset.stage = "public";
      $("stageText").textContent = "PUBLIC EXHIBIT / LOCAL MODEL NOT CONNECTED";
      $("modelReady").textContent = "LOCAL";
      $("modelHint").textContent = "Hosted page has no GPU backend";
      $("generate").disabled = true;
      $("preview").disabled = true;
      setStatus("This is the public XUNIA model exhibit. The browser demo works here; run the one-command Mac installer for neural generation.");
      return;
    }
    try {
      const response = await fetch("/api/health", {cache:"no-store"});
      if (!response.ok) throw Error("HTTP " + response.status);
      const data = await response.json();
      if (!data.ok || !data.local) throw Error("Unrecognized server");
      reportStage(data);
    } catch(error) {
      $("healthLamp").dataset.stage = "failed";
      $("stageText").textContent = "LOCAL SERVER UNAVAILABLE";
      $("generate").disabled = true;
      $("preview").disabled = true;
      if (!busy) setStatus("Local backend unavailable. Re-run the Mac launch command; you can still use the browser demo.", true);
    } finally {
      scheduleHealth();
    }
  }
  function stopAnimation() {
    if (animation !== null) {
      cancelAnimationFrame(animation);
      animation = null;
    }
  }
  function browserDemo() {
    stopAnimation();
    $("result").hidden = true;
    canvas.hidden = false;
    $("screenEmpty").hidden = true;
    $("download").hidden = true;
    $("screenTag").textContent = "LIVE PROCEDURAL CANVAS / NOT AI VIDEO";
    const caption = $("prompt").value.toLowerCase();
    const square = caption.includes("square") || caption.includes("box");
    const direction = caption.includes("left") ? -1 : 1;
    const vertical = caption.includes("up") || caption.includes("down");
    const color = caption.includes("red") ? "#fb6c7c" :
      caption.includes("blue") ? "#70b8ff" :
      caption.includes("green") ? "#64f0b5" :
      caption.includes("yellow") ? "#ffe18a" : "#5affea";
    const start = performance.now();
    const draw = timestamp => {
      const w = canvas.width, h = canvas.height;
      ctx.clearRect(0,0,w,h);
      const bg = ctx.createLinearGradient(0,0,w,h);
      bg.addColorStop(0,"#071321");bg.addColorStop(.6,"#152a44");bg.addColorStop(1,"#0a1124");
      ctx.fillStyle = bg;ctx.fillRect(0,0,w,h);
      ctx.strokeStyle = "rgba(84,242,217,.13)";
      ctx.lineWidth = 1;
      for (let x=0;x<w;x+=32){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}
      for (let y=0;y<h;y+=32){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
      const phase = ((timestamp-start)/2600)%1;
      const x = vertical ? w/2 : w*.16 + (direction<0?1-phase:phase)*w*.68;
      const y = vertical ? h*.12 + (caption.includes("up")?1-phase:phase)*h*.76 : h/2 + Math.sin(phase*6.28)*22;
      for(let i=5;i>=1;i--){
        ctx.globalAlpha = .06 + (6-i)*.014;
        ctx.fillStyle = color;
        const xx = vertical?x:x-direction*i*17;
        const yy = vertical?y-(caption.includes("up")?-1:1)*i*17:y;
        ctx.beginPath();
        if(square)ctx.rect(xx-34,yy-34,68,68);
        else ctx.arc(xx,yy,34,0,Math.PI*2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      ctx.shadowBlur = 40;ctx.shadowColor = color;ctx.fillStyle = color;
      ctx.beginPath();
      if(square)ctx.roundRect(x-32,y-32,64,64,8);
      else ctx.arc(x,y,32,0,Math.PI*2);
      ctx.fill();ctx.shadowBlur = 0;
      ctx.font = "13px ui-monospace,monospace";
      ctx.fillStyle = "rgba(230,251,255,.76)";
      ctx.fillText("GPT-DOUG // MOTION FIELD TEST",22,30);
      ctx.fillText("PROCEDURAL • NO NEURAL MODEL",22,h-20);
      animation = requestAnimationFrame(draw);
    };
    animation = requestAnimationFrame(draw);
    $("receipt").textContent = "Animated in your browser, no installation and no model weights. This is NOT generated neural video.";
    setStatus("Browser motion demo running. For a genuine neural GIF, launch Motion-1 locally and train starter weights.");
  }
  async function generate(preview) {
    if (!local) {
      setStatus("Neural rendering requires the local Mac studio. The instant browser demo is available here.",true);
      return;
    }
    if (busy) return;
    const prompt = $("prompt").value.trim();
    const seed = Number($("seed").value);
    const fps = Number($("fps").value);
    if(!prompt || prompt.length > 400 || !Number.isSafeInteger(seed) || seed<0 || seed>2147483647 ||
       !Number.isSafeInteger(fps) || fps<1 || fps>30){
      setStatus("Enter a prompt up to 400 characters, seed 0–2147483647 and FPS 1–30.",true);
      return;
    }
    busy = true;
    $("generate").disabled=true;$("preview").disabled=true;
    setStatus(preview?"Creating local moving-shape GIF (not neural AI)…":"Generating a neural GIF using your own trained checkpoint…");
    try {
      const response = await fetch(preview?"/api/preview":"/api/generate",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({prompt,seed,fps})
      });
      const data = await response.json();
      if(!response.ok || !data.ok)throw Error(data.error||"Render failed");
      stopAnimation();canvas.hidden=true;$("screenEmpty").hidden=true;
      const img=$("result");img.src=data.url+"?v="+Date.now();img.hidden=false;
      $("screenTag").textContent=data.preview_not_ml?"LOCAL GEOMETRIC GIF / NOT NEURAL":"MOTION-1 / TRAINED NEURAL GIF";
      const link=$("download");link.href=data.url;link.download=data.url.split("/").pop();link.hidden=false;
      $("receipt").textContent=(data.receipt?.model||"Local model")+" · "+(data.receipt?.frames||"")+" frames · seed "+seed;
      setStatus("Local GIF complete. Use the Download link beneath the viewer.");
    }catch(error) {
      if(preview && /dependenc|install/i.test(error.message)){
        browserDemo();
        setStatus("PyTorch is still installing. Showing a clearly labeled browser demo instead.");
      } else setStatus(error.message,true);
    }finally{
      busy=false;
      await health();
    }
  }
  $("generator").addEventListener("submit",event=>{event.preventDefault();generate(false);});
  $("preview").addEventListener("click",()=>generate(true));
  $("demo").addEventListener("click",browserDemo);
  $("check").addEventListener("click",health);
  $("copy").addEventListener("click",async()=>{
    try{await navigator.clipboard.writeText($("setupCommand").textContent);setStatus("One-command Mac installer copied. Paste into Terminal.");}
    catch{setStatus("Clipboard unavailable. Manually select and copy the displayed Terminal command.",true);}
  });
  health();
})();
