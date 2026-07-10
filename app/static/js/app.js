const API = window.location.origin;
let TOKEN = localStorage.getItem("sc_token") || null;
let USER = null;

function setToken(t) { TOKEN = t; localStorage.setItem("sc_token", t); }
function logout() { TOKEN = null; USER = null; localStorage.removeItem("sc_token"); showPage("login"); }

async function api(method, path, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (TOKEN) opts.headers["Authorization"] = "Bearer " + TOKEN;
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(API + path, opts);
  if (!r.ok) {
    let msg = "Error " + r.status;
    try { const j = await r.json(); msg = j.detail || msg; } catch {}
    throw new Error(msg);
  }
  return r.json();
}

function hashRoute() {
  const hash = location.hash.slice(1) || "/";
  if (!TOKEN) { showPage("login"); return; }
  const routes = { "/": "dashboard", "/projects": "projects", "/audits": "audits", "/profile": "profile" };
  showPage(routes[hash] || "dashboard");
}
window.addEventListener("hashchange", hashRoute);

function showPage(name) {
  document.getElementById("page-login").classList.add("d-none");
  document.getElementById("page-layout").classList.add("d-none");
  document.getElementById("loading-screen").classList.remove("d-none");
  if (name === "login") {
    document.getElementById("loading-screen").classList.add("d-none");
    document.getElementById("page-login").classList.remove("d-none");
    return;
  }
  document.getElementById("page-layout").classList.remove("d-none");
  document.querySelectorAll("#sidebar .nav-link").forEach(a => a.classList.remove("active"));
  const map = { dashboard: "/", projects: "/projects", audits: "/audits", profile: "/profile" };
  const sel = document.querySelector(`#sidebar .nav-link[href="#${map[name]}"]`);
  if (sel) sel.classList.add("active");
  loadPage(name);
}

function loadPage(name) {
  const ct = document.getElementById("page-content");
  if (name === "dashboard") renderDashboard(ct);
  else if (name === "projects") renderProjects(ct);
  else if (name === "audits") renderAudits(ct);
  else if (name === "profile") renderProfile(ct);
}

// ---------- LOGIN ----------
document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("login-btn");
  btn.disabled = true;
  document.getElementById("login-spinner").classList.remove("d-none");
  document.getElementById("login-text").textContent = "Ingresando...";
  document.getElementById("login-alert").classList.add("d-none");
  try {
    const data = await api("POST", "/auth/login", {
      username: document.getElementById("login-username").value,
      password: document.getElementById("login-password").value,
    });
    setToken(data.access_token);
    USER = await api("GET", "/auth/me");
    document.getElementById("sidebar-user").textContent = USER.username;
    location.hash = "/";
  } catch (err) {
    document.getElementById("login-alert").textContent = err.message;
    document.getElementById("login-alert").classList.remove("d-none");
  } finally {
    btn.disabled = false;
    document.getElementById("login-spinner").classList.add("d-none");
    document.getElementById("login-text").textContent = "Ingresar";
  }
});

async function seedRoles() {
  const btn = document.getElementById("seed-btn");
  btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>...';
  try {
    await api("POST", "/auth/seed");
    btn.innerHTML = '<i class="bi bi-check-circle text-success"></i> OK';
    setTimeout(() => { btn.innerHTML = '<i class="bi bi-database"></i> Seed'; btn.disabled = false; }, 2000);
  } catch (err) {
    btn.innerHTML = '<i class="bi bi-x-circle text-danger"></i> ' + err.message;
    setTimeout(() => { btn.innerHTML = '<i class="bi bi-database"></i> Seed'; btn.disabled = false; }, 2000);
  }
}

function showRegister() { new bootstrap.Modal(document.getElementById("register-modal")).show(); }
document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  document.getElementById("reg-alert").classList.add("d-none");
  try {
    await api("POST", "/auth/register", {
      username: document.getElementById("reg-username").value,
      email: document.getElementById("reg-email").value,
      password: document.getElementById("reg-password").value,
      nombre_completo: document.getElementById("reg-nombre").value,
    });
    bootstrap.Modal.getInstance(document.getElementById("register-modal")).hide();
    alert("Usuario registrado. Ahora puedes iniciar sesión.");
  } catch (err) {
    document.getElementById("reg-alert").textContent = err.message;
    document.getElementById("reg-alert").classList.remove("d-none");
  }
});

// ---------- DASHBOARD ----------
async function renderDashboard(ct) {
  ct.innerHTML = document.getElementById("tpl-dashboard").innerHTML;
  document.getElementById("dash-date").textContent = new Date().toLocaleDateString("es-CL", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });
  try {
    const dash = await api("GET", "/dashboard/kpi");
    document.getElementById("dash-cards").innerHTML = [
      { label: "Proyectos", icon: "bi-folder", value: dash.total_proyectos },
      { label: "Auditorías", icon: "bi-shield", value: dash.total_auditorias },
      { label: "Vulnerabilidades", icon: "bi-bug", value: dash.total_vulnerabilidades },
      { label: "Usuarios", icon: "bi-people", value: dash.total_usuarios },
    ].map(i => `<div class="col-md-3 col-6">
      <div class="card border-secondary text-center h-100">
        <div class="card-body p-3">
          <i class="bi ${i.icon} fs-3 text-secondary"></i>
          <h5 class="mt-1 mb-0 fw-normal">${i.value ?? "—"}</h5>
          <small class="text-secondary">${i.label}</small>
        </div>
      </div></div>`).join("");
  } catch {}
  try {
    const sev = await api("GET", "/dashboard/vulnerabilities-by-severity");
    new Chart(document.getElementById("chart-severity"), {
      type: "doughnut",
      data: { labels: Object.keys(sev), datasets: [{ data: Object.values(sev), backgroundColor: ["#2b8755", "#e8b931", "#d43f52", "#7b4fbf"] }] },
      options: { responsive: true, plugins: { legend: { position: "bottom", labels: { boxWidth: 10, padding: 8 } } } },
    });
  } catch {}
  try {
    const trend = await api("GET", "/dashboard/trends");
    new Chart(document.getElementById("chart-trend"), {
      type: "line",
      data: { labels: Object.keys(trend), datasets: [{ label: "Auditorías", data: Object.values(trend), borderColor: "#5a6d80", backgroundColor: "rgba(90,109,128,.08)", fill: true, tension: .3 }] },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: { grid: { color: "rgba(255,255,255,.04)" } }, y: { grid: { color: "rgba(255,255,255,.04)" }, beginAtZero: true } } },
    });
  } catch {}
  document.getElementById("loading-screen").classList.add("d-none");
}

// ---------- PROJECTS ----------
async function renderProjects(ct) {
  ct.innerHTML = document.getElementById("tpl-projects").innerHTML;
  try {
    window._projects = await api("GET", "/projects");
    renderProjectList();
  } catch (err) {
    document.getElementById("project-list").innerHTML = `<p class="text-danger small">${err.message}</p>`;
  }
  document.getElementById("loading-screen").classList.add("d-none");
}

function renderProjectList() {
  const list = document.getElementById("project-list");
  const q = (document.getElementById("project-search")?.value || "").toLowerCase();
  const filtered = (window._projects || []).filter(p => (p.nombre || "").toLowerCase().includes(q));
  if (!filtered.length) { list.innerHTML = ""; document.getElementById("project-empty").classList.remove("d-none"); return; }
  document.getElementById("project-empty").classList.add("d-none");
  list.innerHTML = filtered.map(p => {
    p.created_at = p.created_at ? new Date(p.created_at).toLocaleDateString("es-CL") : "";
    p.lenguaje = p.lenguaje || "—";
    p.framework = p.framework || "";
    return fillTpl(document.getElementById("tpl-project-card").innerHTML, p);
  }).join("");
}

function showNewProject() { new bootstrap.Modal(document.getElementById("project-modal")).show(); }
document.getElementById("project-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  document.getElementById("proj-alert").classList.add("d-none");
  try {
    await api("POST", "/projects", {
      nombre: document.getElementById("proj-nombre").value,
      descripcion: document.getElementById("proj-desc").value,
    });
    bootstrap.Modal.getInstance(document.getElementById("project-modal")).hide();
    document.getElementById("project-form").reset();
    window._projects = await api("GET", "/projects");
    renderProjectList();
  } catch (err) {
    document.getElementById("proj-alert").textContent = err.message;
    document.getElementById("proj-alert").classList.remove("d-none");
  }
});

async function showProjectDetail(projectId) {
  projectId = parseInt(projectId);
  const proj = (window._projects || []).find(p => p.id === projectId) || {};
  const modal = new bootstrap.Modal(document.getElementById("detail-modal"));
  document.getElementById("detail-title").textContent = proj.nombre || `Proyecto #${projectId}`;
  document.getElementById("detail-body").innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-secondary"></div> Cargando...</div>';
  modal.show();
  try {
    const stats = await api("GET", `/projects/${projectId}/stats`);
    const files = await api("GET", `/projects/${projectId}/files`);
    document.getElementById("detail-body").innerHTML = `
      <div class="row g-2 mb-3">
        <div class="col-4"><div class="card border-secondary text-center p-2"><small class="text-secondary">Archivos</small><b>${stats.total_files}</b></div></div>
        <div class="col-4"><div class="card border-secondary text-center p-2"><small class="text-secondary">Auditorías</small><b>${stats.total_audits}</b></div></div>
        <div class="col-4"><div class="card border-secondary text-center p-2"><small class="text-secondary">Lenguaje</small><b>${stats.lenguaje}</b></div></div>
      </div>
      <h6 class="small text-secondary mb-2">Archivos</h6>
      ${files.length ? `<ul class="list-group list-group-flush small">${files.map(f => `<li class="list-group-item bg-transparent border-secondary py-1 px-2">${f.ruta} <span class="text-secondary">(${f.lenguaje})</span></li>`).join("")}</ul>`
        : '<p class="text-secondary small">Sin archivos.</p>'}
      <hr>
      <div class="d-flex gap-2 align-items-end">
        <div class="flex-grow-1">
          <p class="small text-secondary mb-1">Subir ZIP</p>
          <input type="file" class="form-control form-control-sm" accept=".zip" id="upload-input">
        </div>
        <button class="btn btn-sm btn-outline-secondary" onclick="uploadProject(${projectId})"><i class="bi bi-upload me-1"></i>Subir</button>
        <button class="btn btn-sm btn-primary" onclick="startAuditAfterUpload(${projectId})"><i class="bi bi-shield me-1"></i>Auditar</button>
      </div>
    `;
  } catch (err) {
    document.getElementById("detail-body").innerHTML = `<p class="text-danger small">${err.message}</p>`;
  }
}

async function uploadProject(id) {
  const input = document.getElementById("upload-input");
  if (!input.files.length) return alert("Selecciona un archivo ZIP");
  const form = new FormData();
  form.append("file", input.files[0]);
  try {
    const r = await fetch(`${API}/projects/${id}/upload`, {
      method: "POST", headers: { "Authorization": "Bearer " + TOKEN }, body: form,
    });
    if (!r.ok) throw new Error((await r.json()).detail || "Error");
    alert("Archivos subidos correctamente");
    showProjectDetail(id);
  } catch (err) { alert(err.message); }
}

async function startAuditAfterUpload(projectId) {
  const input = document.getElementById("upload-input");
  if (input.files.length) {
    const form = new FormData();
    form.append("file", input.files[0]);
    try {
      const r = await fetch(`${API}/projects/${projectId}/upload`, {
        method: "POST", headers: { "Authorization": "Bearer " + TOKEN }, body: form,
      });
      if (!r.ok) throw new Error((await r.json()).detail || "Error");
    } catch (err) { alert("Error al subir: " + err.message); return; }
  }
  await api("POST", "/audits/", { proyecto_id: projectId });
  alert("Auditoría iniciada");
  location.hash = "/audits";
}

// ---------- AUDITS ----------
async function renderAudits(ct) {
  ct.innerHTML = document.getElementById("tpl-audits").innerHTML;
  try {
    const audits = await api("GET", "/audits/");
    const list = document.getElementById("audit-list");
    if (!audits.length) { document.getElementById("audit-empty").classList.remove("d-none"); return; }
    document.getElementById("audit-empty").classList.add("d-none");
    const colors = { pendiente: "warning", en_progreso: "info", completado: "success", fallido: "danger" };
    list.innerHTML = audits.map(a => {
      a.estado_color = colors[a.estado] || "secondary";
      a.created_at = a.created_at ? new Date(a.created_at).toLocaleDateString("es-CL") : "";
      a.proyecto_nombre = a.proyecto_nombre || "—";
      a.nombre = a.nombre || `Auditoría #${a.id}`;
      a.tipo = a.tipo || "automática";
      return fillTpl(document.getElementById("tpl-audit-row").innerHTML, a);
    }).join("");
  } catch (err) {
    document.getElementById("audit-list").innerHTML = `<p class="text-danger small">${err.message}</p>`;
  }
  document.getElementById("loading-screen").classList.add("d-none");
}

async function showNewAudit() {
  try { window._projects = await api("GET", "/projects"); } catch {}
  const sel = document.getElementById("audit-proyecto");
  sel.innerHTML = '<option value="">Seleccionar...</option>';
  (window._projects || []).forEach(p => { sel.innerHTML += `<option value="${p.id}">${p.nombre}</option>`; });
  try {
    const frameworks = await api("GET", "/audits/frameworks");
    const container = document.getElementById("framework-checks");
    const allIds = ["owasp", "nist_csf", "iso_27001", "cis", "mitre_attck"];
    container.innerHTML = (frameworks.length ? frameworks : allIds.map(id => ({ id, label: id }))).map(f => `
      <div class="form-check">
        <input class="form-check-input framework-check" type="checkbox" value="${f.id}" id="fw-${f.id}" ${allIds.includes(f.id) ? "checked" : ""}>
        <label class="form-check-label text-secondary small" for="fw-${f.id}">${f.label}</label>
      </div>
    `).join("");
  } catch { document.getElementById("framework-checks").innerHTML = ""; }
  new bootstrap.Modal(document.getElementById("audit-modal")).show();
}
document.getElementById("audit-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  document.getElementById("audit-alert").classList.add("d-none");
  const checks = document.querySelectorAll(".framework-check:checked");
  try {
    await api("POST", "/audits/", {
      proyecto_id: parseInt(document.getElementById("audit-proyecto").value),
      nombre: document.getElementById("audit-nombre").value || undefined,
      git_url: document.getElementById("audit-git").value || undefined,
      frameworks: Array.from(checks).map(c => c.value),
    });
    bootstrap.Modal.getInstance(document.getElementById("audit-modal")).hide();
    document.getElementById("audit-form").reset();
    renderAudits(document.getElementById("page-content"));
  } catch (err) {
    document.getElementById("audit-alert").textContent = err.message;
    document.getElementById("audit-alert").classList.remove("d-none");
  }
});

// ---------- PROFILE ----------
async function renderProfile(ct) {
  ct.innerHTML = document.getElementById("tpl-profile").innerHTML;
  try {
    const u = await api("GET", "/auth/me");
    document.getElementById("prof-username").textContent = u.username;
    document.getElementById("prof-email").textContent = u.email;
    document.getElementById("prof-nombre").textContent = u.nombre_completo || "—";
    document.getElementById("prof-rol").textContent = u.rol_nombre || u.rol?.nombre || "—";
  } catch {}
  document.getElementById("pw-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    document.getElementById("pw-alert").classList.add("d-none");
    try {
      await api("POST", "/auth/change-password", {
        current_password: document.getElementById("pw-old").value,
        new_password: document.getElementById("pw-new").value,
      });
      alert("Contraseña actualizada.");
      document.getElementById("pw-form").reset();
    } catch (err) {
      document.getElementById("pw-alert").textContent = err.message;
      document.getElementById("pw-alert").classList.remove("d-none");
    }
  });
  document.getElementById("loading-screen").classList.add("d-none");
}

// ---------- UTILS ----------
function fillTpl(tpl, data) {
  let h = tpl;
  Object.keys(data).forEach(k => {
    const v = data[k] == null ? "" : String(data[k]);
    h = h.replaceAll("{" + k + "}", v);
    h = h.replaceAll("{" + k + "|raw}", v);
  });
  h = h.replace(/\{[^}]+\|raw\}/g, "");
  return h;
}

// ---------- INIT ----------
(async function init() {
  if (TOKEN) {
    try {
      USER = await api("GET", "/auth/me");
      document.getElementById("sidebar-user").textContent = USER.username;
      if (location.hash) hashRoute();
      else location.hash = "/";
      return;
    } catch { setToken(null); }
  }
  showPage("login");
  document.getElementById("loading-screen").classList.add("d-none");
})();
