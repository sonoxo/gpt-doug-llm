async function activeTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

async function send(type, command = '') {
  const tab = await activeTab();
  if (!tab?.id) return;
  try {
    await chrome.tabs.sendMessage(tab.id, { type, command });
  } catch (error) {
    console.error('NXYZ Mouse Mic:', error);
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
