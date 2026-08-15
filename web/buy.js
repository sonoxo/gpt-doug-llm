document.getElementById("buyForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("submitBtn");
  const errEl = document.getElementById("buyError");
  errEl.style.display = "none";
  const task = document.getElementById("taskInput").value.trim();
  if (!task) return;

  btn.disabled = true;
  btn.textContent = "Redirecting to payment...";
  try {
    const res = await fetch("/api/paid-tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task }),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.error || "request failed");
    window.location.href = body.checkout_url;
  } catch (err) {
    errEl.textContent = err.message;
    errEl.style.display = "block";
    btn.disabled = false;
    btn.textContent = "Pay $1 & run task";
  }
});
