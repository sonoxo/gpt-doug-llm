async function activeTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

function setStatus(message, ok = false) {
  let status = document.getElementById('nxyz-popup-status');
  if (!status) {
    status = document.createElement('div');
    status.id = 'nxyz-popup-status';
    status.style.marginTop = '10px';
    status.style.padding = '8px 10px';
    status.style.borderRadius = '8px';
    status.style.fontSize = '11px';
    status.style.lineHeight = '1.35';
    document.body.appendChild(status);
  }
  status.style.background = ok ? '#18351f' : '#3a2020';
  status.style.color = '#fff';
  status.textContent = message;
}

function isSupported(url = '') {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' && parsed.hostname.endsWith('.palantirfoundry.com');
  } catch (_) {
    return false;
  }
}

async function send(type, command = '') {
  const tab = await activeTab();
  if (!tab?.id) {
    setStatus('No active browser tab found.');
    return;
  }

  if (!isSupported(tab.url || '')) {
    setStatus('Open your Palantir Foundry tab first. Mouse Mic cannot run on chrome://extensions or other Chrome internal pages.');
    return;
  }

  try {
    const response = await chrome.tabs.sendMessage(tab.id, { type, command });
    if (response?.ok) setStatus('Command sent to Foundry.', true);
  } catch (error) {
    console.error('NXYZ Mouse Mic:', error);
    setStatus('Foundry page is not connected yet. Refresh the Palantir tab once, then try again.');
  }
}

document.getElementById('send').addEventListener('click', () => {
  const input = document.getElementById('command');
  const command = input.value.trim();
  if (command) send('NXYZ_MOUSE_MIC_COMMAND', command);
});

document.getElementById('listen').addEventListener('click', () => {
  send('NXYZ_MOUSE_MIC_LISTEN');
});

document.getElementById('command').addEventListener('keydown', (event) => {
  if (event.key === 'Enter') document.getElementById('send').click();
});

activeTab().then((tab) => {
  if (isSupported(tab?.url || '')) {
    setStatus('Ready on Palantir Foundry.', true);
  } else {
    setStatus('Open your Palantir Foundry tab to use Mouse Mic.');
  }
});
