const STORAGE_KEY = 'grimthebuilder.workspace.v1';

const starter = {
  'index.html': `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>My Grim Build</title>
</head>
<body>
  <main class="hero">
    <span class="eyebrow">GRIMTHEBUILDER // XUNIA</span>
    <h1>Build it. Run it. Ship it.</h1>
    <p>Edit HTML, CSS, and JavaScript on the left. Your preview runs on the right.</p>
    <button id="action">Test interaction</button>
  </main>
</body>
</html>`,
  'style.css': `:root {
  font-family: Inter, system-ui, sans-serif;
  color: #ecf5ff;
  background: #090d14;
}
* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: radial-gradient(circle at top, #14243a, #090d14 55%); }
.hero { width: min(760px, 88vw); padding: 64px 0; }
.eyebrow { color: #58e7ff; font-size: 12px; letter-spacing: .18em; font-weight: 800; }
h1 { margin: 18px 0 14px; font-size: clamp(44px, 8vw, 88px); line-height: .92; letter-spacing: -.055em; }
p { max-width: 600px; color: #9aa9bb; font-size: 18px; line-height: 1.65; }
button { margin-top: 18px; border: 1px solid #58e7ff55; border-radius: 9px; padding: 13px 18px; background: #58e7ff18; color: #dffbff; cursor: pointer; }`,
  'script.js': `const action = document.querySelector('#action');
action?.addEventListener('click', () => {
  action.textContent = 'Grim runtime works ✓';
  console.log('Interaction executed successfully.');
});
console.log('Project loaded inside GrimTheBuilder.');`
};

let workspace = loadWorkspace();
let activeFile = 'index.html';
let saveTimer = null;

const editor = document.querySelector('#editor');
const fileList = document.querySelector('#file-list');
const activeTab = document.querySelector('#active-tab');
const lineGutter = document.querySelector('#line-gutter');
const saveState = document.querySelector('#save-state');
const preview = document.querySelector('#preview');
const previewStage = document.querySelector('#preview-stage');
const consoleOutput = document.querySelector('#console-output');
const importFile = document.querySelector('#import-file');

function loadWorkspace() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (saved && saved.files && typeof saved.files === 'object') {
      return { files: { ...starter, ...saved.files }, updatedAt: saved.updatedAt || Date.now() };
    }
  } catch (error) {
    console.warn('Could not restore Grim workspace:', error);
  }
  return { files: { ...starter }, updatedAt: Date.now() };
}

function persistWorkspace() {
  workspace.updatedAt = Date.now();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(workspace));
  saveState.textContent = 'SAVED';
}

function scheduleSave() {
  saveState.textContent = 'SAVING…';
  clearTimeout(saveTimer);
  saveTimer = setTimeout(persistWorkspace, 220);
}

function setActiveFile(file) {
  workspace.files[activeFile] = editor.value;
  activeFile = file;
  editor.value = workspace.files[file] ?? '';
  activeTab.textContent = file;
  document.querySelectorAll('.file').forEach((button) => {
    button.classList.toggle('active', button.dataset.file === file);
  });
  updateLineNumbers();
  editor.focus();
}

function updateLineNumbers() {
  const count = Math.max(1, editor.value.split('\n').length);
  lineGutter.textContent = Array.from({ length: count }, (_, index) => index + 1).join('\n');
  lineGutter.scrollTop = editor.scrollTop;
}

function escapeScript(code) {
  return code.replace(/<\/script/gi, '<\\/script');
}

function buildDocument() {
  workspace.files[activeFile] = editor.value;
  const html = workspace.files['index.html'] || '';
  const css = workspace.files['style.css'] || '';
  const js = workspace.files['script.js'] || '';
  const bridge = `<script>
(function () {
  const send = (kind, values) => parent.postMessage({ source: 'grim-preview', kind, values }, '*');
  ['log','warn','error','info'].forEach((kind) => {
    const original = console[kind];
    console[kind] = (...args) => {
      send(kind, args.map((value) => {
        try { return typeof value === 'string' ? value : JSON.stringify(value); }
        catch { return String(value); }
      }));
      original.apply(console, args);
    };
  });
  window.addEventListener('error', (event) => send('error', [event.message + ' @ ' + event.lineno + ':' + event.colno]));
  window.addEventListener('unhandledrejection', (event) => send('error', ['Unhandled promise rejection: ' + String(event.reason)]));
})();
<\/script>`;

  const styleTag = `<style>${css}</style>`;
  const scriptTag = `<script>${escapeScript(js)}<\/script>`;
  let output = html;

  if (/<\/head>/i.test(output)) output = output.replace(/<\/head>/i, `${styleTag}</head>`);
  else output = styleTag + output;

  if (/<\/body>/i.test(output)) output = output.replace(/<\/body>/i, `${bridge}${scriptTag}</body>`);
  else output += bridge + scriptTag;

  return output;
}

function clearConsole(message = 'Preview started.') {
  consoleOutput.innerHTML = '';
  appendConsole('log', [message]);
}

function appendConsole(kind, values) {
  const line = document.createElement('div');
  line.className = kind === 'error' ? 'console-error' : kind === 'log' ? 'console-log' : '';
  line.textContent = `[${kind}] ${values.join(' ')}`;
  consoleOutput.appendChild(line);
  consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

function runPreview() {
  persistWorkspace();
  clearConsole('Grim preview executing…');
  preview.srcdoc = buildDocument();
}

function exportWorkspace() {
  workspace.files[activeFile] = editor.value;
  persistWorkspace();
  const payload = JSON.stringify({
    schema: 'grimthebuilder.workspace.v1',
    exportedAt: new Date().toISOString(),
    files: workspace.files
  }, null, 2);
  downloadBlob(payload, `grim-project-${dateStamp()}.json`, 'application/json');
  appendConsole('log', ['Workspace exported.']);
}

function downloadBlob(content, filename, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 500);
}

function dateStamp() {
  return new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
}

function importWorkspace(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const data = JSON.parse(String(reader.result));
      if (!data.files || typeof data.files !== 'object') throw new Error('Missing files object');
      workspace = { files: { ...starter, ...data.files }, updatedAt: Date.now() };
      persistWorkspace();
      setActiveFile('index.html');
      runPreview();
      appendConsole('log', ['Workspace imported successfully.']);
    } catch (error) {
      appendConsole('error', [`Import failed: ${error.message}`]);
    }
  };
  reader.readAsText(file);
}

function openPreviewInTab() {
  const url = URL.createObjectURL(new Blob([buildDocument()], { type: 'text/html' }));
  window.open(url, '_blank', 'noopener');
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

fileList.addEventListener('click', (event) => {
  const button = event.target.closest('.file');
  if (button) setActiveFile(button.dataset.file);
});

editor.addEventListener('input', () => {
  workspace.files[activeFile] = editor.value;
  updateLineNumbers();
  scheduleSave();
});

editor.addEventListener('scroll', () => {
  lineGutter.scrollTop = editor.scrollTop;
});

editor.addEventListener('keydown', (event) => {
  if (event.key === 'Tab') {
    event.preventDefault();
    const start = editor.selectionStart;
    const end = editor.selectionEnd;
    editor.setRangeText('  ', start, end, 'end');
    workspace.files[activeFile] = editor.value;
    updateLineNumbers();
    scheduleSave();
  }
});

document.querySelector('#run-preview').addEventListener('click', runPreview);
document.querySelector('#refresh-preview').addEventListener('click', runPreview);
document.querySelector('#export-project').addEventListener('click', exportWorkspace);
document.querySelector('#import-project').addEventListener('click', () => importFile.click());
document.querySelector('#open-preview').addEventListener('click', openPreviewInTab);
document.querySelector('#clear-console').addEventListener('click', () => clearConsole('Console cleared.'));

document.querySelector('#new-project').addEventListener('click', () => {
  const proceed = window.confirm('Create a new Grim project? Your current workspace will be replaced in this browser.');
  if (!proceed) return;
  workspace = { files: { ...starter }, updatedAt: Date.now() };
  persistWorkspace();
  setActiveFile('index.html');
  runPreview();
});

importFile.addEventListener('change', () => {
  const file = importFile.files?.[0];
  if (file) importWorkspace(file);
  importFile.value = '';
});

document.querySelector('#desktop-view').addEventListener('click', () => {
  previewStage.classList.remove('mobile');
  document.querySelector('#desktop-view').classList.add('active');
  document.querySelector('#mobile-view').classList.remove('active');
});

document.querySelector('#mobile-view').addEventListener('click', () => {
  previewStage.classList.add('mobile');
  document.querySelector('#mobile-view').classList.add('active');
  document.querySelector('#desktop-view').classList.remove('active');
});

window.addEventListener('message', (event) => {
  if (event.data?.source !== 'grim-preview') return;
  appendConsole(event.data.kind || 'log', Array.isArray(event.data.values) ? event.data.values : [String(event.data.values)]);
});

window.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
    event.preventDefault();
    runPreview();
  }
});

setActiveFile(activeFile);
runPreview();
console.log('GrimTheBuilder v1.0 // XUNIA local browser runtime online.');
