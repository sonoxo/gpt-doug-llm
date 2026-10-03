(() => {
  "use strict";
  const bay=document.getElementById("cameraBay");
  const video=document.getElementById("mavenCamera");
  const status=document.getElementById("cameraStatus");
  const viewToggle=document.getElementById("cameraViewToggle");
  const simPanel=bay.closest(".sim");
  const startBtn=document.getElementById("cameraStart");
  const stopBtn=document.getElementById("cameraStop");
  const flipBtn=document.getElementById("cameraFlip");
  const filterBtn=document.getElementById("cameraFilter");
  const overlayBtn=document.getElementById("cameraOverlayToggle");
  const head=bay.querySelector(".camera-bay-head");
  const closeBtn=document.createElement("button");
  closeBtn.id="cameraBayClose";closeBtn.type="button";closeBtn.textContent="CLOSE";closeBtn.className="camera-bay-close";
  head?.appendChild(closeBtn);
  if(!bay||!video||!viewToggle) return;

  let stream=null;
  let facing="environment";
  let filterIndex=0;
  const filters=["","filter-night","filter-mono","filter-cinema"];
  const filterNames=["CLEAN","NIGHT TINT","MONO","CINEMA"];

  function setStatus(label,live=false){
    status.textContent=label;
    status.classList.toggle("live",live);
  }

  function setOpen(open){
    if(open) document.dispatchEvent(new CustomEvent("maven:camera-open"));
    bay.hidden=!open;
    simPanel?.classList.toggle("camera-open",open);
    viewToggle.classList.toggle("active",open);
    viewToggle.textContent=open?"CAMERA VIEW ON":"CAMERA VIEW";
  }

  async function stopCamera(){
    if(stream){
      stream.getTracks().forEach(track=>track.stop());
      stream=null;
    }
    video.srcObject=null;
    setStatus("CAMERA OFF",false);
    stopBtn.disabled=true;
    flipBtn.disabled=true;
  }

  async function startCamera(){
    if(!navigator.mediaDevices?.getUserMedia){
      setStatus("CAMERA UNSUPPORTED",false);
      return;
    }
    await stopCamera();
    setStatus("REQUESTING PERMISSION",false);
    try{
      stream=await navigator.mediaDevices.getUserMedia({
        audio:false,
        video:{
          facingMode:{ideal:facing},
          width:{ideal:1920},
          height:{ideal:1080}
        }
      });
      video.srcObject=stream;
      video.classList.toggle("mirror",facing==="user");
      await video.play();
      setStatus(facing==="user"?"FRONT CAMERA LIVE":"REAR CAMERA LIVE",true);
      stopBtn.disabled=false;
      flipBtn.disabled=false;
      setOpen(true);
    }catch(err){
      const name=String(err?.name||"ERROR").replace("Error","");
      setStatus("CAMERA "+name.toUpperCase(),false);
    }
  }

  async function flipCamera(){
    facing=facing==="environment"?"user":"environment";
    await startCamera();
  }

  function cycleFilter(){
    video.classList.remove(...filters.filter(Boolean));
    filterIndex=(filterIndex+1)%filters.length;
    if(filters[filterIndex]) video.classList.add(filters[filterIndex]);
    filterBtn.textContent="LOOK: "+filterNames[filterIndex];
  }

  function toggleOverlay(){
    const overlay=bay.querySelector(".camera-overlay");
    const on=overlay.hidden;
    overlay.hidden=!on;
    overlayBtn.classList.toggle("active",on);
    overlayBtn.textContent=on?"HUD ON":"HUD OFF";
  }

  viewToggle.addEventListener("click",()=>setOpen(bay.hidden));
  closeBtn.addEventListener("click",()=>setOpen(false));
  document.addEventListener("maven:drone-open",()=>setOpen(false));
  startBtn.addEventListener("click",startCamera);
  stopBtn.addEventListener("click",stopCamera);
  flipBtn.addEventListener("click",flipCamera);
  filterBtn.addEventListener("click",cycleFilter);
  overlayBtn.addEventListener("click",toggleOverlay);

  document.addEventListener("visibilitychange",()=>{
    if(document.hidden&&stream) stream.getVideoTracks().forEach(t=>t.enabled=false);
    else if(stream) stream.getVideoTracks().forEach(t=>t.enabled=true);
  });

  addEventListener("pagehide",stopCamera,{once:true});
})();
