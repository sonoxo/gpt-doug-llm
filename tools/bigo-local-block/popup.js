"use strict";
const RULESET_ID="bigo";
const statusEl=document.getElementById("state");
const light=document.getElementById("light");
const toggle=document.getElementById("toggle");
const message=document.getElementById("message");
let isEnabled=null;
function render(enabled){
 isEnabled=enabled;
 statusEl.textContent=enabled?"BLOCKING BIGO":"BLOCK PAUSED";
 light.className=enabled?"on":"off";
 toggle.textContent=enabled?"Disable local block":"Enable local block";
 toggle.disabled=false;
}
async function readStatus(){
 try{
  const enabled=await chrome.declarativeNetRequest.getEnabledRulesets();
  render(enabled.includes(RULESET_ID));
 }catch(e){
  toggle.disabled=true;
  statusEl.textContent="Status unavailable";
  message.textContent="Chrome could not read the blocker state.";
 }
}
async function onToggle(){
 if(typeof isEnabled!=="boolean")return;
 toggle.disabled=true;
 message.textContent="";
 const next=!isEnabled;
 try{
  await chrome.declarativeNetRequest.updateEnabledRulesets(next
   ?{enableRulesetIds:[RULESET_ID]}
   :{disableRulesetIds:[RULESET_ID]});
  const enabled=await chrome.declarativeNetRequest.getEnabledRulesets();
  render(enabled.includes(RULESET_ID));
  message.textContent=next?"Local block enabled. Reload open BIGO tabs to apply.":"Local block disabled.";
 }catch(e){
  message.textContent="Could not change local blocking state.";
  await readStatus();
 }
}
toggle.addEventListener("click",onToggle);
readStatus();
