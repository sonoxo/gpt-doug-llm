document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errEl = document.getElementById("loginError");
  errEl.style.display = "none";
  const password = document.getElementById("password").value;
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.error || "login failed");
    window.location.href = "/";
  } catch (err) {
    errEl.textContent = err.message;
    errEl.style.display = "block";
  }
});
