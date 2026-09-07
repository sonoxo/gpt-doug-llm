chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "palantir-toolbox-capture",
    title: "Capture selection to Palantir Toolbox",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "palantir-toolbox-capture") return;

  const capture = {
    text: info.selectionText || "",
    url: tab?.url || "",
    title: tab?.title || "",
    capturedAt: new Date().toISOString()
  };

  await chrome.storage.session.set({ lastCapture: capture });
});
