const API = "http://127.0.0.1:8000";

// ── Toggle Forms ─────────────────────────────
function showLogin() {
  document.getElementById("login-form").style.display = "block";
  document.getElementById("register-form").style.display = "none";
  document.getElementById("btn-login").classList.add("active");
  document.getElementById("btn-register").classList.remove("active");
  clearMsg();
}

function showRegister() {
  document.getElementById("login-form").style.display = "none";
  document.getElementById("register-form").style.display = "block";
  document.getElementById("btn-register").classList.add("active");
  document.getElementById("btn-login").classList.remove("active");
  clearMsg();
}

function showMsg(text, type) {
  const el = document.getElementById("msg");
  if (!el) return;
  el.textContent = text;
  el.className = `msg ${type}`;
}

function clearMsg() {
  const el = document.getElementById("msg");
  if (el) { el.textContent = ""; el.className = "msg"; }
}

// ── Register ──────────────────────────────────
document.getElementById("register-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.target.querySelector("button");
  btn.textContent = "Creating account...";

  const res = await fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: document.getElementById("reg-name").value,
      email: document.getElementById("reg-email").value,
      password: document.getElementById("reg-pass").value
    })
  });

  const data = await res.json();
  btn.textContent = "Create Account →";

  if (res.ok) {
    showMsg("✅ Account created! Please login.", "success");
    setTimeout(showLogin, 1500);
  } else {
    showMsg(data.detail || "Registration failed", "error");
  }
});

// ── Login ─────────────────────────────────────
document.getElementById("login-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.target.querySelector("button");
  btn.textContent = "Logging in...";

  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-pass").value
    })
  });

  const data = await res.json();
  btn.textContent = "Login →";

  if (res.ok && data.access_token) {
    localStorage.setItem("token", data.access_token);
    showMsg("✅ Login successful! Redirecting...", "success");
    setTimeout(() => window.location.href = "/dashboard", 1000);
  } else {
    showMsg(data.detail || "Login failed", "error");
  }
});