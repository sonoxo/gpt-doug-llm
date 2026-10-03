const HOST = "com.zyrazap.helper";
const $ = (id) => document.getElementById(id);

function send(msg) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendNativeMessage(HOST, msg, (response) => {
      const err = chrome.runtime.lastError;
      if (err) return reject(new Error(err.message));
      if (!response) return reject(new Error("No response from zyraZap helper"));
      if (response.ok === false) return reject(new Error(response.error || "zyraZap helper error"));
      resolve(response);
    });
  });
}

function fmt(n) {
  if (n == null) return "—";
  const u = ["B","KB","MB","GB","TB"];
  let i=0, x=Number(n);
  while (x>=1024 && i<u.length-1) { x/=1024; i++; }
  return `${x.toFixed(x>=10 || i===0 ? 0 : 1)} ${u[i]}`;
}

function setStatus(ok) {
  $("statusDot").className = "dot " + (ok ? "ok" : "bad");
}

async function scan() {
  $("result").textContent = "Scanning…";
  try {
    const r = await send({action:"scan", backup_root:$("backupRoot").value});
    setStatus(true);
    $("diskInfo").textContent =
      `Mac free: ${fmt(r.disk?.free)} / ${fmt(r.disk?.total)}\n` +
      `Backup writable: ${r.backup?.writable ? "yes" : "no"}`;
    const box = $("targets");
    box.innerHTML = "";
    for (const t of r.targets || []) {
      const row = document.createElement("div");
      row.className = "target";
      row.innerHTML = `
        <input type="checkbox" class="targetCheck" value="${t.id}">
        <div><div class="name">${t.label}</div><div class="meta">${t.policy}</div></div>
        <div class="size">${fmt(t.bytes)}</div>`;
      box.appendChild(row);
    }
    $("result").textContent = "Scan complete.";
  } catch (e) {
    setStatus(false);
    $("result").textContent = "Helper unavailable:\n" + e.message;
  }
}

$("scanBtn").addEventListener("click", scan);
$("refreshBtn").addEventListener("click", scan);

$("selectAllBtn").addEventListener("click", () => {
  document.querySelectorAll(".targetCheck").forEach(x => x.checked = true);
});

$("cleanBtn").addEventListener("click", async () => {
  const ids = [...document.querySelectorAll(".targetCheck:checked")].map(x => x.value);
  if (!ids.length) {
    $("result").textContent = "Select at least one cleanup target.";
    return;
  }
  const dry = $("dryRun").checked;
  if (!dry && !confirm("zyraZap will back up required items, verify them, then remove only allowlisted data. Continue?")) return;

  $("result").textContent = dry ? "Running dry run…" : "Backing up + cleaning…";
  try {
    const r = await send({
      action:"clean",
      target_ids:ids,
      backup_root:$("backupRoot").value,
      dry_run:dry
    });
    setStatus(true);
    $("result").textContent = (r.events || []).join("\n");
    await scan();
  } catch (e) {
    setStatus(false);
    $("result").textContent = "Error:\n" + e.message;
  }
});

scan();
