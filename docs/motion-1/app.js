"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const local = ["127.0.0.1", "localhost"].includes(location.hostname) && location.protocol === "http:";
  const setStatus=(text,error=false)=>{$("status").textContent=text;$("status").classList.toggle("error",error);};
  const setEnabled=enabled=>{$("generate").disabled=!enabled;$("preview").disabled=!local;};
  let healthTimer = null;
  function checkAgain() {
    if(healthTimer) clearTimeout(healthTimer);
    healthTimer = setTimeout(health, 5000);
  }
  async function health(){
    if(!local){
      setStatus("PUBLIC SOURCE VIEW. Neural video runs on your Mac, not on GitHub Pages. Install the free model and open http://127.0.0.1:8792/ for working generation.");
      $("modelReady").textContent="LOCAL";
      $("modelHint").textContent="No hosted GPU or paid service";
      return;
    }
    try{
      const response=await fetch("/api/health",{cache:"no-store"});
      if(!response.ok)throw Error("Local backend not reachable");
      const data=await response.json();
      if(!data.local || !data.ok)throw Error("Invalid backend");
      $("modelReady").textContent=data.trained_checkpoint_present?"TRAINED":"SETUP";
      $("modelHint").textContent=data.trained_checkpoint_present?"Checkpoint detected":"Train original model to unlock neural generation";
      setEnabled(data.trained_checkpoint_present);
      if (!data.trained_checkpoint_present) checkAgain();
      setStatus(data.trained_checkpoint_present?
        "LOCAL MODEL ONLINE. A trained Motion-1 checkpoint is available. Select Generate from trained weights.":
        "LOCAL STUDIO ONLINE. Starter training may be running in Terminal. This page checks automatically and unlocks neural generation when the checkpoint is ready.");
    }catch(error){setStatus("Local model unavailable: "+error.message,true);setEnabled(false);}
  }
  async function create(preview){
    if(!local){setStatus("Model generation requires the local Python studio, not the public website.",true);return;}
    const prompt=$("prompt").value.trim(),seed=Number($("seed").value),fps=Number($("fps").value);
    if(!prompt||prompt.length>400||!Number.isSafeInteger(seed)||seed<0||seed>2147483647||!Number.isSafeInteger(fps)||fps<1||fps>30){
      setStatus("Enter a prompt (up to 400 characters), a valid seed and FPS 1–30.",true);return;
    }
    $("generate").disabled=true;$("preview").disabled=true;
    setStatus(preview?"Rendering original geometric preview (not neural output)…":"Running trained GPT-DOUG Motion-1 diffusion locally…");
    try{
      const response=await fetch(preview?"/api/preview":"/api/generate",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({prompt,seed,fps})
      });
      const data=await response.json();
      if(!response.ok||!data.ok)throw Error(data.error||"Render failed");
      const img=$("result");
      img.src=data.url+"?v="+Date.now();
      img.hidden=false;$("screenEmpty").hidden=true;
      $("screenTag").textContent=data.preview_not_ml?"SYNTHETIC PREVIEW / NOT NEURAL AI":"MOTION-1 / TRAINED NEURAL SAMPLE";
      $("receipt").textContent=data.receipt?.model+" · "+data.receipt?.frames+" frames · seed "+seed+" · Generated locally";
      setStatus(data.preview_not_ml?"Procedural preview complete. No trained AI model was used.":"Original Motion-1 neural model generated a GIF locally. Output stays on your Mac.");
    }catch(error){setStatus(error.message,true);}
    finally{await health();}
  }
  $("generator").addEventListener("submit",e=>{e.preventDefault();create(false);});
  $("preview").addEventListener("click",()=>create(true));
  $("copy").addEventListener("click",async()=>{
    try{await navigator.clipboard.writeText($("setupCommand").textContent);setStatus("Mac setup and training commands copied.");}
    catch{setStatus("Clipboard unavailable. Select the displayed commands and copy manually.",true);}
  });
  health();
})();
