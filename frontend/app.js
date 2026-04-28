const API_BASE = "/api";

function getToken() {
  return localStorage.getItem("token");
}

function setToken(token) {
  localStorage.setItem("token", token);
}

function logout() {
  localStorage.removeItem("token");
  window.location.href = "/index.html";
}

async function apiRequest(path, options = {}) {
  const token = getToken();
  const headers = options.headers || {};
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(path.startsWith("http") ? path : `${API_BASE}${path}`, {
    ...options,
    headers,
    body: options.body ? (options.body instanceof FormData ? options.body : JSON.stringify(options.body)) : undefined,
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || "Request failed");
  }
  return res.status === 204 ? null : res.json();
}

async function ensureAuthenticated() {
  const token = getToken();
  if (!token) {
    window.location.href = "/index.html";
    return null;
  }
  try {
    return await apiRequest("/auth/me");
  } catch (e) {
    logout();
    return null;
  }
}

function setUserBadge(user) {
  const badge = document.getElementById("user-badge");
  if (badge && user) {
    badge.textContent = `${user.full_name} · ${user.role}`;
  }
}

function showMessage(text, tone = "info") {
  const el = document.getElementById("message");
  if (!el) return;
  el.textContent = text;
  el.className = `muted ${tone}`;
}

function statusPill(status, passed) {
  if (passed === true) return `<span class="pill success">зачет</span>`;
  if (passed === false) return `<span class="pill danger">незачет</span>`;
  if (status === "completed") return `<span class="pill success">завершен</span>`;
  if (status === "not_started") return `<span class="pill info">не начат</span>`;
  return `<span class="pill info">${status}</span>`;
}
