export function buildMusicGeneratorOperations(prompt='Build a music generator app') {
  return [
    { op: 'write_file', path: 'index.html', content: INDEX_HTML },
    { op: 'write_file', path: 'style.css', content: STYLE_CSS },
    { op: 'write_file', path: 'script.js', content: APP_JS },
    { op: 'write_file', path: 'README.md', content: `# GrimBeat Generator\n\nBuilt inside GrimTheBuilder from this prompt:\n\n> ${String(prompt).replace(/\r?\n/g, ' ').slice(0, 500)}\n\n## Features\n- Web Audio synthesis; no external audio API required\n- Prompt-aware pattern generation\n- Trap, house, ambient and synthwave modes\n- BPM, key and bar controls\n- Kick, snare, hi-hat, bass and melody sequencing\n- Deterministic seeded generation\n- Play/stop transport\n- Browser recording to WebM when MediaRecorder is supported\n- Pattern JSON export\n- Local autosave\n` }
  ];
}

const INDEX_HTML = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="theme-color" content="#080a0f">
  <title>GrimBeat Generator</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main class="shell">
    <header class="hero">
      <div>
        <div class="eyebrow">GRIMTHEBUILDER // MUSIC LAB</div>
        <h1>GrimBeat<br>Generator</h1>
        <p class="lede">Generate original browser-synth patterns from a prompt, then play, reshape, record and export them.</p>
      </div>
      <div class="status" id="audioStatus">AUDIO READY</div>
    </header>

    <section class="panel prompt-panel">
      <label for="prompt">Describe the sound</label>
      <div class="prompt-row">
        <input id="prompt" value="dark futuristic trap, spacious melody, hard drums" autocomplete="off">
        <button id="generate" class="primary">Generate</button>
      </div>
      <div class="controls">
        <label>Style<select id="genre"><option value="trap">Trap</option><option value="house">House</option><option value="ambient">Ambient</option><option value="synthwave">Synthwave</option></select></label>
        <label>BPM<input id="bpm" type="range" min="60" max="180" value="138"><output id="bpmOut">138</output></label>
        <label>Key<select id="key"><option>C</option><option>C#</option><option>D</option><option>D#</option><option>E</option><option>F</option><option>F#</option><option>G</option><option>G#</option><option>A</option><option>A#</option><option>B</option></select></label>
        <label>Bars<select id="bars"><option>1</option><option selected>2</option><option>4</option></select></label>
        <label>Seed<input id="seed" type="number" value="2401"></label>
      </div>
    </section>

    <section class="transport panel">
      <button id="play" class="primary">▶ Play</button>
      <button id="stop">■ Stop</button>
      <button id="record">● Record</button>
      <button id="export">⇩ Pattern JSON</button>
      <span id="now">Stopped</span>
    </section>

    <section class="panel sequencer-panel">
      <div class="section-head"><h2>Sequence</h2><span>16 steps / bar</span></div>
      <div id="grid" class="grid" aria-label="Generated music sequence"></div>
    </section>

    <section class="panel meters">
      <div><span>STYLE</span><strong id="styleReadout">TRAP</strong></div>
      <div><span>KEY</span><strong id="keyReadout">C MINOR</strong></div>
      <div><span>TEMPO</span><strong id="tempoReadout">138 BPM</strong></div>
      <div><span>SEED</span><strong id="seedReadout">2401</strong></div>
    </section>

    <footer>Built by GrimTheBuilder · Web Audio API · Original procedural synthesis</footer>
  </main>
  <script src="script.js"></script>
</body>
</html>`;

const STYLE_CSS = `:root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#080a0f;color:#f5f7fa}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 85% 0%,#1d2638 0,transparent 34%),linear-gradient(180deg,#080a0f,#0b0e14 70%,#07090d)}button,input,select{font:inherit}.shell{width:min(1180px,94vw);margin:auto;padding:42px 0 52px}.hero{display:flex;justify-content:space-between;gap:30px;align-items:flex-start;margin-bottom:28px}.eyebrow{font-size:11px;letter-spacing:.22em;font-weight:800;color:#8fa0b8}.hero h1{font-size:clamp(58px,9vw,112px);line-height:.78;letter-spacing:-.07em;margin:18px 0 28px}.lede{max-width:680px;color:#9aa6b6;font-size:17px;line-height:1.65}.status{border:1px solid #283141;border-radius:999px;padding:10px 14px;font-size:11px;letter-spacing:.14em;color:#9fd3a9;background:#0c1510}.panel{background:rgba(15,18,25,.88);border:1px solid #222a38;border-radius:16px;padding:18px;box-shadow:0 20px 60px rgba(0,0,0,.2);margin-bottom:14px}.prompt-panel>label{display:block;font-size:12px;color:#8f9bab;margin-bottom:9px;text-transform:uppercase;letter-spacing:.1em}.prompt-row{display:grid;grid-template-columns:1fr auto;gap:10px}.prompt-row input{width:100%;background:#090c12;border:1px solid #2b3443;border-radius:10px;color:#fff;padding:14px}.controls{display:grid;grid-template-columns:1.2fr 2fr 1fr .8fr 1fr;gap:12px;margin-top:14px}.controls label{display:flex;flex-direction:column;gap:7px;color:#8290a2;font-size:11px;text-transform:uppercase;letter-spacing:.08em}.controls input,.controls select{background:#090c12;border:1px solid #283141;border-radius:8px;color:#eaf0f8;padding:9px}.controls input[type=range]{padding:6px 0}.controls output{font-weight:800;color:#fff}.primary{background:#eef3ff;color:#0b0d12!important;border-color:#eef3ff!important;font-weight:800}.transport{display:flex;align-items:center;gap:9px;flex-wrap:wrap}.transport button,.prompt-row button{border:1px solid #303a49;background:#121721;color:#d8e0ec;border-radius:9px;padding:11px 15px;cursor:pointer}.transport button:hover,.prompt-row button:hover{transform:translateY(-1px)}#record.recording{background:#6d1a25;border-color:#ba394d;color:#fff}.transport #now{margin-left:auto;color:#8e9bad;font-size:12px}.section-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}.section-head h2{font-size:18px;margin:0}.section-head span{color:#718096;font-size:11px}.grid{overflow-x:auto;display:grid;gap:7px}.track{display:grid;grid-template-columns:72px repeat(var(--steps),minmax(22px,1fr));gap:4px;align-items:center;min-width:760px}.track-name{font-size:10px;letter-spacing:.1em;color:#8390a2}.step{height:28px;border-radius:5px;background:#151b26;border:1px solid #202939;position:relative}.step.on{background:#dbe7ff;border-color:#f6f9ff}.step.on::after{content:"";position:absolute;inset:6px;border-radius:3px;background:#0b0e14}.step.playing{outline:2px solid #9fd3a9;outline-offset:1px}.meters{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.meters div{background:#0a0d13;border-radius:10px;padding:13px}.meters span{display:block;color:#6f7d90;font-size:9px;letter-spacing:.12em}.meters strong{display:block;margin-top:6px;font-size:15px}footer{text-align:center;color:#566274;font-size:11px;padding-top:18px}@media(max-width:780px){.hero{display:block}.status{display:inline-block}.controls{grid-template-columns:1fr 1fr}.prompt-row{grid-template-columns:1fr}.meters{grid-template-columns:1fr 1fr}.transport #now{width:100%;margin:6px 0 0}}`;

const APP_JS = `const $=s=>document.querySelector(s);
const TRACKS=['kick','snare','hat','bass','melody'];
const NOTE_NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
const SCALES={trap:[0,3,5,7,10],house:[0,2,3,5,7,9,10],ambient:[0,2,3,5,7,10],synthwave:[0,3,5,7,8,10]};
let audio=null,master=null,compressor=null,pattern=null,playing=false,timer=null,nextNoteTime=0,stepIndex=0,recordDest=null,recorder=null,chunks=[];

function hashString(str){let h=2166136261;for(let i=0;i<str.length;i++){h^=str.charCodeAt(i);h=Math.imul(h,16777619)}return h>>>0}
function rng(seed){let s=seed>>>0||1;return()=>{s+=0x6D2B79F5;let t=s;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296}}
function currentSettings(){return{prompt:$('#prompt').value.trim(),genre:$('#genre').value,bpm:Number($('#bpm').value),key:$('#key').value,bars:Number($('#bars').value),seed:Number($('#seed').value)||1}}
function applyPromptHints(s){const p=s.prompt.toLowerCase();if(p.includes('house'))s.genre='house';if(p.includes('ambient')||p.includes('chill'))s.genre='ambient';if(p.includes('synthwave')||p.includes('retro'))s.genre='synthwave';if(p.includes('trap'))s.genre='trap';if(p.includes('fast'))s.bpm=Math.max(s.bpm,150);if(p.includes('slow'))s.bpm=Math.min(s.bpm,90);if(p.includes('dark'))s.key=['C','D','F','G','A'][hashString(p)%5];$('#genre').value=s.genre;$('#bpm').value=s.bpm;$('#bpmOut').value=s.bpm;$('#key').value=s.key}
function makePattern(){const s=currentSettings();applyPromptHints(s);const seed=hashString(s.prompt+'|'+s.genre+'|'+s.key+'|'+s.seed);const r=rng(seed);const steps=s.bars*16;const scale=SCALES[s.genre];const root=NOTE_NAMES.indexOf(s.key);const out={settings:s,steps,tracks:{kick:[],snare:[],hat:[],bass:[],melody:[]}};
  for(let i=0;i<steps;i++){
    const pos=i%16;
    out.tracks.kick.push((pos===0||pos===8||((pos===6||pos===11||pos===14)&&r()>.48))?1:0);
    out.tracks.snare.push((pos===4||pos===12)?1:(s.genre==='house'&&pos%4===0&&r()>.78?1:0));
    out.tracks.hat.push((s.genre==='ambient'?r()>.78:(pos%2===0||r()>.57))?1:0);
    const bassOn=(pos%4===0||r()>.82);out.tracks.bass.push(bassOn?36+root+scale[Math.floor(r()*Math.min(scale.length,4))]:null);
    const melodyChance=s.genre==='ambient'?.46:.32;out.tracks.melody.push(r()<melodyChance?60+root+scale[Math.floor(r()*scale.length)]+(r()>.82?12:0):null);
  }
  pattern=out;save();render();return out}
function ensureAudio(){if(audio)return;audio=new (window.AudioContext||window.webkitAudioContext)();master=audio.createGain();master.gain.value=.62;compressor=audio.createDynamicsCompressor();compressor.threshold.value=-16;compressor.knee.value=20;compressor.ratio.value=5;master.connect(compressor);compressor.connect(audio.destination);$('#audioStatus').textContent='AUDIO ONLINE'}
function midiHz(m){return 440*Math.pow(2,(m-69)/12)}
function kick(t){const o=audio.createOscillator(),g=audio.createGain();o.type='sine';o.frequency.setValueAtTime(155,t);o.frequency.exponentialRampToValueAtTime(46,t+.11);g.gain.setValueAtTime(1,t);g.gain.exponentialRampToValueAtTime(.001,t+.32);o.connect(g).connect(master);o.start(t);o.stop(t+.34)}
function noiseBuffer(){const b=audio.createBuffer(1,audio.sampleRate*.25,audio.sampleRate);const d=b.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=Math.random()*2-1;return b}
function snare(t){const n=audio.createBufferSource(),f=audio.createBiquadFilter(),g=audio.createGain();n.buffer=noiseBuffer();f.type='highpass';f.frequency.value=1100;g.gain.setValueAtTime(.48,t);g.gain.exponentialRampToValueAtTime(.001,t+.16);n.connect(f).connect(g).connect(master);n.start(t);n.stop(t+.18)}
function hat(t){const n=audio.createBufferSource(),f=audio.createBiquadFilter(),g=audio.createGain();n.buffer=noiseBuffer();f.type='highpass';f.frequency.value=6500;g.gain.setValueAtTime(.16,t);g.gain.exponentialRampToValueAtTime(.001,t+.055);n.connect(f).connect(g).connect(master);n.start(t);n.stop(t+.07)}
function tone(m,t,dur,type='sawtooth',gain=.14){const o=audio.createOscillator(),f=audio.createBiquadFilter(),g=audio.createGain();o.type=type;o.frequency.value=midiHz(m);f.type='lowpass';f.frequency.setValueAtTime(type==='sine'?900:2200,t);f.frequency.exponentialRampToValueAtTime(620,t+dur);g.gain.setValueAtTime(.001,t);g.gain.exponentialRampToValueAtTime(gain,t+.018);g.gain.exponentialRampToValueAtTime(.001,t+dur);o.connect(f).connect(g).connect(master);o.start(t);o.stop(t+dur+.03)}
function scheduleStep(i,t){if(!pattern)return;if(pattern.tracks.kick[i])kick(t);if(pattern.tracks.snare[i])snare(t);if(pattern.tracks.hat[i])hat(t);if(pattern.tracks.bass[i]!=null)tone(pattern.tracks.bass[i],t,.20,'square',.12);if(pattern.tracks.melody[i]!=null)tone(pattern.tracks.melody[i],t,.32,pattern.settings.genre==='ambient'?'sine':'sawtooth',.10);setTimeout(()=>highlight(i),Math.max(0,(t-audio.currentTime)*1000))}
function scheduler(){if(!playing)return;const stepSeconds=60/Number($('#bpm').value)/4;while(nextNoteTime<audio.currentTime+.12){scheduleStep(stepIndex,nextNoteTime);nextNoteTime+=stepSeconds;stepIndex=(stepIndex+1)%pattern.steps}timer=setTimeout(scheduler,25)}
async function play(){if(!pattern)makePattern();ensureAudio();await audio.resume();if(playing)return;playing=true;stepIndex=0;nextNoteTime=audio.currentTime+.06;$('#now').textContent='Playing';scheduler()}
function stop(){playing=false;clearTimeout(timer);timer=null;stepIndex=0;$('#now').textContent='Stopped';highlight(-1)}
function highlight(i){document.querySelectorAll('.step').forEach(el=>el.classList.toggle('playing',Number(el.dataset.step)===i))}
function render(){if(!pattern)return;const g=$('#grid');g.innerHTML='';g.style.setProperty('--steps',pattern.steps);for(const name of TRACKS){const row=document.createElement('div');row.className='track';const label=document.createElement('div');label.className='track-name';label.textContent=name.toUpperCase();row.appendChild(label);pattern.tracks[name].forEach((v,i)=>{const cell=document.createElement('div');cell.className='step'+(v!=null&&v!==0?' on':'');cell.dataset.step=i;cell.title=name+' step '+(i+1)+(typeof v==='number'&&v>1?' · MIDI '+v:'');row.appendChild(cell)});g.appendChild(row)}const s=pattern.settings;$('#styleReadout').textContent=s.genre.toUpperCase();$('#keyReadout').textContent=s.key+' MINOR';$('#tempoReadout').textContent=s.bpm+' BPM';$('#seedReadout').textContent=s.seed;$('#bpmOut').value=s.bpm}
function save(){if(pattern)localStorage.setItem('grimbeat.pattern',JSON.stringify(pattern));localStorage.setItem('grimbeat.settings',JSON.stringify(currentSettings()))}
function load(){try{const saved=JSON.parse(localStorage.getItem('grimbeat.pattern'));if(saved?.tracks&&saved?.steps){pattern=saved;const s=saved.settings||{};for(const k of ['prompt','genre','bpm','key','bars','seed'])if(s[k]!=null&&$('#'+k))$('#'+k).value=s[k];render();return}}catch{}makePattern()}
function downloadPattern(){if(!pattern)return;const blob=new Blob([JSON.stringify(pattern,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='grimbeat-pattern.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
async function toggleRecord(){ensureAudio();if(!window.MediaRecorder){$('#now').textContent='Recording is unavailable in this browser';return}if(recorder?.state==='recording'){recorder.stop();$('#record').classList.remove('recording');$('#record').textContent='● Record';return}recordDest=audio.createMediaStreamDestination();compressor.connect(recordDest);chunks=[];recorder=new MediaRecorder(recordDest.stream);recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};recorder.onstop=()=>{const blob=new Blob(chunks,{type:recorder.mimeType||'audio/webm'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='grimbeat-session.webm';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);try{compressor.disconnect(recordDest)}catch{};recordDest=null};recorder.start();$('#record').classList.add('recording');$('#record').textContent='■ Save Recording';if(!playing)await play()}

$('#generate').onclick=()=>{stop();makePattern();$('#now').textContent='New pattern generated'};
$('#play').onclick=play;$('#stop').onclick=stop;$('#record').onclick=toggleRecord;$('#export').onclick=downloadPattern;
$('#bpm').oninput=()=>{$('#bpmOut').value=$('#bpm').value;if(pattern){pattern.settings.bpm=Number($('#bpm').value);render();save()}};
for(const id of ['genre','key','bars'])$('#'+id).onchange=()=>{stop();makePattern()};
window.addEventListener('beforeunload',stop);load();`;
