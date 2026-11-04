"use strict";
(() => {
  const $ = id => document.getElementById(id);
  let active = null;
  let state = null;
  let timer = null;
  let selectedImage = null;
  let working = false;
  const setInfo = (message, error=false) => {
    $("status").textContent = message;
    $("status").classList.toggle("error", error);
  };
  async function api(url, opts={}) {
    const response = await fetch(url, {cache:"no-store", ...opts});
    let data;
    try {data = await response.json();} catch {throw Error(`Engine HTTP ${response.status}`);}
    if (!response.ok) throw Error(data.error || `Engine HTTP ${response.status}`);
    return data;
  }
  const isReady = () => state?.renderer?.ffmpeg === true;
  function updateMode() {
    const mode = document.querySelector('input[name="mode"]:checked')?.value || "motion";
    $("refBlock").hidden = mode === "motion";
    $("storyboard").disabled = mode === "wan";
    $("engineBadge").textContent = mode === "wan" ? "MLX / WAN2.2" : mode === "image" ? "FFMPEG / IMAGE" : "FFMPEG / MOTION";
    if (mode === "wan" && !state?.renderer?.ai_ready) {
      setInfo("WAN AI requires an optional ~17 GiB model download and significant Apple Silicon memory. Motion Lab and Image → Video already generate genuine MP4s. Nothing will be downloaded without your action.");
    } else if (mode === "image") {
      setInfo("IMAGE → VIDEO: Upload a PNG/JPEG and animate it into an MP4 with pan/zoom. This is a film editor, not neural video synthesis.");
    } else if (mode === "motion") {
      setInfo("MOTION LAB: Ready for original animated video and storyboard exports using free FFmpeg. Choose Generate MP4.");
    } else {
      setInfo("WAN2.2 AI: Pretrained local neural generation selected. Large weights and hardware are required.");
    }
  }
  async function health() {
    try {
      const data = await api("/api/health");
      state = data;
      $("connection").textContent = "LOCAL ENGINE ONLINE";
      $("ffmpegStatus").textContent = data.renderer.ffmpeg ? "READY" : "MISSING / BREW INSTALL FFMPEG";
      $("mlxStatus").textContent = data.renderer.mlxgen ? "INSTALLED" : "OPTIONAL / NOT INSTALLED";
      $("modelStatus").textContent = data.renderer.wan_model_cached ? "CACHE DETECTED" : "MODEL NOT DOWNLOADED";
      $("generate").disabled = working || !isReady();
      if (!working) updateMode();
    } catch(err) {
      state = null;
      $("connection").textContent = "OFFLINE";
      $("generate").disabled = true;
      setInfo("Cannot reach the local Cinema Studio server. Keep the Terminal launcher running. " + err.message, true);
    }
  }
  function previewJob(job) {
    if (!job) return;
    active = job.id;
    $("jobId").textContent = "JOB " + job.id.slice(0, 8).toUpperCase();
    $("jobState").textContent = job.status.toUpperCase();
    $("jobStage").textContent = job.stage || job.status;
    $("progressBar").style.width = job.status === "completed" ? "100%" : job.status === "running" ? "64%" : job.status === "queued" ? "15%" : "0%";
    $("jobError").hidden = job.status !== "failed";
    $("jobError").textContent = job.error || "";
    $("downloadVideo").hidden = !job.video;
    $("downloadManifest").hidden = !job.manifest;
    if (job.video) {
      $("video").src = job.video;
      $("video").hidden = false;
      $("empty").hidden = true;
      $("downloadVideo").href = job.video;
      $("downloadVideo").download = `gpt-doug-cinema-${job.id}.mp4`;
      $("downloadManifest").href = job.manifest;
      $("downloadManifest").download = `gpt-doug-cinema-${job.id}.json`;
    } else {
      $("video").hidden = true;
      $("video").removeAttribute("src");
      $("video").load();
      $("empty").hidden = false;
    }
    if (job.status === "completed") {
      working = false;
      $("generate").disabled = !isReady();
      setInfo("MP4 rendered successfully and saved locally. Preview it or select DOWNLOAD MP4.");
    } else if (job.status === "failed") {
      working = false;
      $("generate").disabled = !isReady();
      setInfo("Render stopped: " + (job.error || "Unknown engine error"), true);
    }
  }
  async function poll(id) {
    if (timer) {clearTimeout(timer);timer = null;}
    try {
      const data = await api("/api/jobs/" + id);
      if (id !== active) return;
      previewJob(data.job);
      if (["running","queued"].includes(data.job.status)) timer = setTimeout(() => poll(id), 1100);
      else gallery();
    } catch(err) {setInfo("Could not retrieve render status: " + err.message, true);}
  }
  async function gallery() {
    try {
      const data = await api("/api/jobs");
      const root = $("gallery");root.replaceChildren();
      if (!data.jobs.length) {
        const p = document.createElement("p");p.className="small";p.textContent="No projects yet. Generate your first clip above.";root.append(p);return;
      }
      for(const j of data.jobs.slice(0, 24)) {
        const card = document.createElement("button");card.type="button";card.className="project" + (j.status === "failed" ? " failed":"");
        const tag = document.createElement("span");tag.className="state";tag.textContent = `${j.status.toUpperCase()} / ${j.mode.toUpperCase()}`;
        const subject=document.createElement("p");subject.textContent=j.prompt;
        const info=document.createElement("small");info.textContent=j.created.slice(0,19).replace("T", " ") + " UTC";
        card.append(tag,subject,info);
        card.addEventListener("click",()=>{active=j.id;poll(j.id);window.scrollTo({top:0,behavior:"smooth"});});
        root.append(card);
      }
    } catch(err) {setInfo("Gallery unavailable: " + err.message, true);}
  }
  const readImage = file => new Promise((resolve,reject) => {
    if (!file) return resolve(null);
    if (file.size > 8*1024*1024) return reject(Error("Image must be under 8 MB"));
    if (!["image/png","image/jpeg"].includes(file.type))return reject(Error("Upload PNG or JPEG only"));
    const reader = new FileReader();reader.onerror=()=>reject(Error("Could not read image"));
    reader.onload=()=>resolve(String(reader.result));reader.readAsDataURL(file);
  });
  async function submit(event) {
    event.preventDefault();if (working)return;
    const mode = document.querySelector('input[name="mode"]:checked').value;
    working=true;$("generate").disabled=true;
    setInfo("Validating request and submitting to the local renderer…");
    try {
      const payload={mode,prompt:$("prompt").value,storyboard:$("storyboard").value,
        camera:$("camera").value,palette:$("palette").value,quality:$("quality").value,
        seconds:Number($("seconds").value),fps:Number($("fps").value),seed:Number($("seed").value),
        sound:$("sound").checked};
      if(mode!=="motion")payload.image=await readImage($("image").files[0]);
      const result=await api("/api/jobs",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      active=result.job.id;
      previewJob(result.job);
      setInfo("Job queued. Running the actual local renderer; this may take time for pretrained AI.");
      poll(active);gallery();
    }catch(err){
      working=false;$("generate").disabled=!isReady();setInfo("Generation not started: "+err.message,true);
    }
  }
  document.querySelectorAll('input[name="mode"]').forEach(x=>x.addEventListener("change",updateMode));
  document.querySelectorAll(".preset").forEach(button=>button.addEventListener("click",()=>{$("prompt").value=button.dataset.prompt;}));
  $("image").addEventListener("change",()=>{$("refName").textContent=$("image").files[0] ? "Selected: " + $("image").files[0].name : "No image selected";});
  $("studioForm").addEventListener("submit",submit);
  $("refresh").addEventListener("click",health);
  $("refreshGallery").addEventListener("click",gallery);
  $("copyInstall").addEventListener("click",async()=>{
    try{await navigator.clipboard.writeText("bash cinema_studio/install_ai_mac.sh");setInfo("Optional AI installation command copied. Run it from the GPT-DOUG repository root only if your Mac has adequate storage and unified memory.");}
    catch{setInfo("Clipboard is unavailable; manually copy the displayed command.");}
  });
  health().then(gallery);
  setInterval(async()=>{if(!working)await health();},15000);
})();
