const params = new URLSearchParams(window.location.search);
const taskId = params.get("id");

function escapeHtml(s) {
  return (s || "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

async function poll() {
  if (!taskId) {
    document.getElementById("taskText").textContent = "No task id in URL.";
    return;
  }
  const res = await fetch(`/api/paid-tasks/${taskId}`);
  if (!res.ok) {
    document.getElementById("taskText").textContent = "Task not found.";
    return;
  }
  const task = await res.json();
  document.getElementById("taskText").textContent = task.task;
  const pill = document.getElementById("statusPill");
  pill.className = `status-pill ${task.status}`;
  pill.textContent = task.status;

  if (task.status === "done") {
    document.getElementById("resultBox").innerHTML = escapeHtml(task.result);
  } else if (task.status === "failed") {
    document.getElementById("resultBox").textContent = `Something went wrong: ${task.result || "unknown error"}`;
  } else {
    document.getElementById("resultBox").textContent = "Working on it — this can take a few minutes on local hardware. This page auto-refreshes.";
    setTimeout(poll, 8000);
  }
}
poll();
