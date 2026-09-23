const API = window.location.origin;
let TOKEN = localStorage.getItem("sc_token") || null;
let USER = null;
let _pollInterval = null;
let _pollInFlight = false;
let _pollErrorShown = false;

function setToken(t) { TOKEN = t; localStorage.setItem("sc_token", t); }
function logout() { TOKEN = null; USER = null; localStorage.removeItem("sc_token"); stopPolling(); showPage("login"); }

async function api(method, path, body, timeoutMs) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (TOKEN) opts.headers["Authorization"] = "Bearer " + TOKEN;
  if (body) opts.body = JSON.stringify(body);
  const controller = new AbortController();
  opts.signal = controller.signal;
  const timer = setTimeout(() => controller.abort(), timeoutMs || 30000);
  let r;
  try {
    r = await fetch(API + path, opts);
  } catch (err) {
    if (err.name === "AbortError") throw new Error("La petición tardó demasiado (timeout). Inténtalo de nuevo.");
    throw err;
  } finally {
    clearTimeout(timer);
  }
  if (!r.ok) {
    let msg = "Error " + r.status;
    try { const j = await r.json(); msg = j.detail || msg; } catch {}
    throw new Error(msg);
  }
  if (r.status === 204) return true;
  return r.json();
}

function hashRoute() {
  const hash = location.hash.slice(1) || "/";
  if (!TOKEN) { showPage("login"); return; }
  const routes = { "/": "dashboard", "/projects": "projects", "/audits": "audits", "/profile": "profile", "/admin": "admin" };
  showPage(routes[hash] || "dashboard");
}
window.addEventListener("hashchange", hashRoute);

function showPage(name) {
  stopPolling();
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
  const map = { dashboard: "/", projects: "/projects", audits: "/audits", profile: "/profile", admin: "/admin" };
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
  else if (name === "admin") renderAdmin(ct);
}

function stopPolling() {
  if (_pollInterval) { clearInterval(_pollInterval); _pollInterval = null; }
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
    if (USER.rol_nombre === "admin" || USER.rol?.nombre === "admin") {
      document.getElementById("nav-admin").classList.remove("d-none");
    }
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
  const isAdmin = USER?.rol_nombre === "admin" || USER?.rol?.nombre === "admin";
  list.innerHTML = filtered.map(p => {
    p.created_at = p.created_at ? new Date(p.created_at).toLocaleDateString("es-CL") : "";
    p.lenguaje = p.lenguaje || "—";
    p.framework = p.framework || "";
    return fillTpl(document.getElementById("tpl-project-card").innerHTML, p);
  }).join("");
  if (isAdmin) document.querySelectorAll(".admin-only").forEach(el => el.classList.remove("d-none"));
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
    let frameworks = [];
    try { frameworks = await api("GET", "/audits/frameworks"); } catch {}
    const defaultFws = [{id:"owasp",label:"OWASP Top 10"},{id:"nist_csf",label:"NIST CSF"},{id:"iso_27001",label:"ISO 27001"},{id:"cis",label:"CIS Controls"},{id:"mitre_attck",label:"MITRE ATT&CK"}];
    if (!Array.isArray(frameworks) || !frameworks.length) frameworks = defaultFws;
    let fwHtml = frameworks.map(f => {
      const id = f.id || f;
      const label = f.label || f;
      return `<div class="form-check"><input class="form-check-input fw-check" type="checkbox" value="${id}" id="fw-${id}" checked><label class="form-check-label text-secondary small" for="fw-${id}">${label}</label></div>`;
    }).join("");
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
      <div class="mb-2">
        <div class="btn-group btn-group-sm w-100 mb-2" role="group">
          <input type="radio" class="btn-check" name="upload-mode" id="mode-zip" value="zip" checked onchange="toggleUploadMode()">
          <label class="btn btn-outline-secondary" for="mode-zip"><i class="bi bi-file-zip me-1"></i>ZIP</label>
          <input type="radio" class="btn-check" name="upload-mode" id="mode-git" value="git" onchange="toggleUploadMode()">
          <label class="btn btn-outline-secondary" for="mode-git"><i class="bi bi-git me-1"></i>Git URL</label>
        </div>
        <div id="upload-zip">
          <input type="file" class="form-control form-control-sm" accept=".zip" id="upload-input">
        </div>
        <div id="upload-git" class="d-none">
          <input class="form-control form-control-sm mb-1" placeholder="https://github.com/usuario/repo.git" id="git-url-input">
          <input class="form-control form-control-sm mb-1" placeholder="Email (Git)" id="git-username-input">
          <input class="form-control form-control-sm" type="password" placeholder="Token o contraseña" id="git-token-input">
        </div>
      </div>
      <hr>
      <label class="text-secondary small d-block mb-1">Frameworks de seguridad</label>
      <div id="detail-frameworks" class="d-flex flex-wrap gap-2 mb-2">${fwHtml}</div>
      <button class="btn btn-primary btn-sm w-100" onclick="loadAndAudit(${projectId})">
        <i class="bi bi-shield me-1"></i>Auditar con frameworks seleccionados
      </button>
    `;
  } catch (err) {
    document.getElementById("detail-body").innerHTML = `<p class="text-danger small">${err.message}</p>`;
  }
}

function toggleUploadMode() {
  const mode = document.querySelector('input[name="upload-mode"]:checked').value;
  document.getElementById("upload-zip").classList.toggle("d-none", mode !== "zip");
  document.getElementById("upload-git").classList.toggle("d-none", mode !== "git");
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
    return true;
  } catch (err) { alert(err.message); return false; }
}

async function loadAndAudit(projectId) {
  const mode = document.querySelector('input[name="upload-mode"]:checked').value;
  let gitUrl = null;
  let gitUsername = null;
  let gitToken = null;
  if (mode === "git") {
    gitUrl = document.getElementById("git-url-input").value.trim();
    if (!gitUrl) return alert("Ingresa una URL de Git");
    gitUsername = document.getElementById("git-username-input").value.trim() || undefined;
    gitToken = document.getElementById("git-token-input").value || undefined;
  } else {
    const ok = await uploadProject(projectId);
    if (!ok) return;
  }
  const checks = document.querySelectorAll("#detail-frameworks .fw-check:checked");
  const frameworks = Array.from(checks).map(c => c.value);
  try {
    await api("POST", "/audits/", {
      proyecto_id: projectId,
      git_url: gitUrl,
      git_username: gitUsername,
      git_token: gitToken,
      frameworks: frameworks.length ? frameworks : undefined,
    });
    bootstrap.Modal.getInstance(document.getElementById("detail-modal")).hide();
    alert("Auditoría iniciada");
    location.hash = "/audits";
  } catch (err) { alert(err.message); }
}

// ---------- AUDITS ----------
async function renderAudits(ct) {
  ct.innerHTML = document.getElementById("tpl-audits").innerHTML;
  try {
    const audits = await api("GET", "/audits/");
    const list = document.getElementById("audit-list");
    if (!audits.length) { document.getElementById("audit-empty").classList.remove("d-none"); return; }
    document.getElementById("audit-empty").classList.add("d-none");
    const colors = { pendiente: "warning", ejecutando: "info", completada: "success", fallida: "danger" };
    const isAdmin = USER?.rol_nombre === "admin" || USER?.rol?.nombre === "admin";
    list.innerHTML = audits.map(a => {
      a.estado_color = colors[a.estado] || "secondary";
      a.created_at = a.created_at ? new Date(a.created_at).toLocaleDateString("es-CL") : "";
      a.proyecto_nombre = a.proyecto_nombre || "—";
      a.nombre = a.nombre || `Auditoría #${a.id}`;
      a.tipo = a.tipo || "automática";
      let errMsg = "";
      if (a.estado === "fallida" && a.resultado_resumen) {
        try {
          const rr = typeof a.resultado_resumen === "string" ? JSON.parse(a.resultado_resumen) : a.resultado_resumen;
          errMsg = rr?.error || rr?.progress?.message || "";
        } catch {}
      }
      a.error_msg = errMsg ? `<small class="text-danger d-block text-truncate" style="max-width:260px" title="${errMsg}"><i class="bi bi-exclamation-triangle me-1"></i>${errMsg}</small>` : "";
      return fillTpl(document.getElementById("tpl-audit-row").innerHTML, a);
    }).join("");
    if (isAdmin) document.querySelectorAll(".admin-only").forEach(el => el.classList.remove("d-none"));
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
      git_username: document.getElementById("audit-git-username").value.trim() || undefined,
      git_token: document.getElementById("audit-git-token").value || undefined,
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

// ---------- AUDIT DETAIL / PROGRESS ----------
async function showAuditDetail(auditId) {
  stopPolling();
  const modal = new bootstrap.Modal(document.getElementById("audit-detail-modal"));
  document.getElementById("audit-detail-title").textContent = `Auditoría #${auditId}`;
  document.getElementById("audit-detail-body").innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-secondary"></div> Cargando...</div>';
  modal.show();
  await refreshAuditProgress(auditId);
  _pollInterval = setInterval(() => refreshAuditProgress(auditId), 2000);
  document.getElementById("audit-detail-modal").addEventListener("hidden.bs.modal", () => stopPolling(), { once: true });
}

async function refreshAuditProgress(auditId) {
  if (_pollInFlight) return; // evita peticiones solapadas
  _pollInFlight = true;
  try {
    const data = await api("GET", `/audits/${auditId}/progress`);
    _pollErrorShown = false;
    const view = document.getElementById("audit-detail-body");
    const pct = data.percentage || 0;
    const done = data.estado === "completada" || data.estado === "fallida";

    const stateLabels = { pendiente: "Pendiente", ejecutando: "Ejecutando...", completada: "Completada", fallida: "Fallida" };
    const stateColors = { pendiente: "warning", ejecutando: "info", completada: "success", fallida: "danger" };

    // Status header
    const statusHtml = `<div class="d-flex justify-content-between align-items-center">
      <h6 class="mb-0 small fw-semibold">
        <span class="badge bg-${stateColors[data.estado] || "secondary"}">${esc(stateLabels[data.estado] || data.estado)}</span>
        <span class="text-secondary ms-2">${pct}%</span>
      </h6>
      <small class="text-secondary">Auditoría #${auditId}</small>
    </div>`;

    // Progress bar
    const barColor = data.estado === "completada" ? "bg-success" : data.estado === "fallida" ? "bg-danger" : "bg-info";
    const barAnimated = data.estado === "ejecutando" ? "progress-bar-striped progress-bar-animated" : "";
    const barHtml = `<div class="progress mb-3" style="height:10px;border-radius:6px;background:rgba(255,255,255,.06)">
      <div class="progress-bar ${barColor} ${barAnimated}" role="progressbar" style="width:${pct}%;transition:width .5s ease"></div>
    </div>`;

    // Error banner
    const error = data.estado === "fallida" ? data.message || "" : "";
    const errorBarHtml = error ? `<div class="alert alert-danger py-2 small mb-2"><i class="bi bi-exclamation-triangle me-1"></i>${esc(error)}</div>` : "";

    // Severity cards (only show if there are vulnerabilities)
    const sev = data.severity || {};
    const hasVulns = (sev.critical || 0) + (sev.high || 0) + (sev.medium || 0) + (sev.low || 0) > 0;
    const sevHtml = hasVulns ? `<div class="row g-2 mb-3">
      <div class="col-3"><div class="card border-secondary text-center p-1"><small class="text-secondary">Crítica</small><b class="text-danger small">${sev.critical || 0}</b></div></div>
      <div class="col-3"><div class="card border-secondary text-center p-1"><small class="text-secondary">Alta</small><b class="text-warning small">${sev.high || 0}</b></div></div>
      <div class="col-3"><div class="card border-secondary text-center p-1"><small class="text-secondary">Media</small><b class="text-info small">${sev.medium || 0}</b></div></div>
      <div class="col-3"><div class="card border-secondary text-center p-1"><small class="text-secondary">Baja</small><b class="text-secondary small">${sev.low || 0}</b></div></div>
    </div>` : "";

    // Current step indicator
    let currentStep = "";
    const steps = Array.isArray(data.steps) ? data.steps : [];
    const runningStep = steps.find(s => s && s.status === "ejecutando");
    if (runningStep && data.estado !== "completada" && data.estado !== "fallida") {
      currentStep = `<div class="badge bg-info-subtle text-info px-2 py-1 small mb-2"><i class="bi bi-arrow-repeat me-1"></i>${esc(runningStep.name || "Ejecutando...")}</div>`;
    }

    // Message
    const msgHtml = esc(data.message) ? `<small class="text-secondary">${esc(data.message)}</small>` : "";

    // Interactive accordion log - click steps to expand details
    const statusMap = { pendiente: ["circle", "text-secondary"], ejecutando: ["arrow-repeat text-info", "text-info"], completado: ["check-circle-fill text-success", "text-success"], fallido: ["x-circle-fill text-danger", "text-danger"] };
    const logHtml = steps.length ? `<div class="mb-3" style="max-height:360px;overflow-y:auto">` + steps.map((s, idx) => {
      if (!s) return "";
      const [icon, color] = statusMap[s.status] || ["circle", "text-secondary"];
      const vulnsBadge = s.vulnerabilities != null ? `<span class="badge bg-secondary-subtle text-secondary small ms-2">${s.vulnerabilities} encontradas</span>` : "";
      const filesBadge = s.files_count != null ? `<span class="badge bg-secondary-subtle text-secondary small ms-2">${s.files_count} archivos</span>` : "";
      const bg = s.status === "ejecutando" ? "style='background:rgba(13,202,240,.08);border-left:2px solid #0dcaf0;cursor:pointer'" : 
                 s.status === "fallido" ? "style='background:rgba(220,53,69,.06);border-left:2px solid #dc3545;cursor:pointer'" :
                 s.status === "completado" ? "style='background:rgba(25,135,84,.06);border-left:2px solid #198754;cursor:pointer'" :
                 "style='cursor:pointer'";
      const detail = s.detail || s.error || "";
      const collapsed = s.status === "ejecutando" ? "" : " d-none";
      return `<div class="step-row rounded mb-1" style="overflow:hidden">
        <div class="d-flex align-items-start gap-2 py-1 px-2 step-header" ${bg} onclick="toggleStepDetail(this)">
          <i class="bi bi-${icon} mt-1 ${color}"></i>
          <div class="flex-grow-1">
            <span class="small ${color}">${esc(s.name || "")}</span>${vulnsBadge}${filesBadge}
          </div>
          <i class="bi bi-chevron-down small text-secondary step-chevron"></i>
        </div>
        <div class="step-detail px-3 py-1 small text-secondary${collapsed}" style="border-left:2px solid rgba(255,255,255,.08)">
          ${detail ? esc(detail) : (s.status === "completado" ? "Sin detalles adicionales" : "")}
        </div>
      </div>`;
    }).join("") + `</div>` : "";

    // Frameworks badges
    const fws = Array.isArray(data.frameworks) ? data.frameworks : [];
    const fwLabels = { owasp: "OWASP Top 10", nist_csf: "NIST CSF", nist_800_82: "NIST SP 800-82", iso_27001: "ISO 27001", cis: "CIS Controls", mitre_attck: "MITRE ATT&CK" };
    const fwHtml = fws.length ? fws.map(f => `<span class="badge bg-secondary-subtle text-secondary small">${esc(fwLabels[f] || f)}</span>`).join(" ") : "";

    // Actions - framework-specific report buttons
    let actionsHtml = "";
    if (data.estado === "completada") {
      const fwLabels = { owasp: "OWASP", nist_csf: "NIST CSF", nist_800_82: "NIST SP 800-82", iso_27001: "ISO 27001", cis: "CIS Controls", mitre_attck: "MITRE ATT&CK" };
      const fwColors = { owasp: "danger", nist_csf: "primary", nist_800_82: "info", iso_27001: "success", cis: "warning", mitre_attck: "dark" };
      const fwIcons = { owasp: "bi-shield-fill", nist_csf: "bi-diagram-3", nist_800_82: "bi-cpu", iso_27001: "bi-check-shield", cis: "bi-list-check", mitre_attck: "bi-bullseye" };
      const fwBtns = fws.filter(f => fwLabels[f]).map(f =>
        `<button class="btn btn-sm btn-outline-${fwColors[f] || 'secondary'}" onclick="showFrameworkReport(${auditId}, '${esc(f)}')" title="Generar informe ${esc(fwLabels[f])}">
          <i class="${fwIcons[f] || 'bi-file-text'} me-1"></i>${esc(fwLabels[f] || f)}
        </button>`
      ).join("");
      actionsHtml = `
        <div class="d-flex flex-wrap gap-1 mb-2">${fwBtns}</div>
        <div class="d-flex gap-2">
          <button class="btn btn-sm btn-outline-primary" onclick="showAuditReport(${auditId})"><i class="bi bi-file-text me-1"></i>Ver informe general</button>
          <button class="btn btn-sm btn-outline-success flex-grow-1" onclick="closeAuditDetail()"><i class="bi bi-check-lg me-1"></i>Cerrar</button>
        </div>`;
    } else if (data.estado === "fallida") {
      actionsHtml = `<button class="btn btn-sm btn-outline-danger flex-grow-1" onclick="closeAuditDetail()"><i class="bi bi-x me-1"></i>Cerrar</button>
        <button class="btn btn-sm btn-outline-warning" onclick="showRetryAudit(${auditId})"><i class="bi bi-arrow-clockwise me-1"></i>Reintentar</button>`;
    }

    // Assemble full HTML
    view.innerHTML = `
      ${statusHtml}
      ${barHtml}
      ${errorBarHtml}
      ${sevHtml}
      ${currentStep}
      ${msgHtml ? `<div class="mb-2">${msgHtml}</div>` : ""}
      ${logHtml}
      ${fwHtml ? `<div class="mb-2"><small class="text-secondary fw-semibold d-block mb-1">Frameworks</small>${fwHtml}</div>` : ""}
      ${actionsHtml ? `<div class="d-flex gap-2 mt-3">${actionsHtml}</div>` : ""}
    `;

    if (done) stopPolling();
  } catch (err) {
    // Errores transitorios (red, timeout, 5xx): NO se detiene el polling,
    // se avisa al usuario y se reintenta con el siguiente tick.
    if (err.message && (String(err.message).includes("401") || String(err.message).toLowerCase().includes("sesión expirada"))) {
      stopPolling();
      alert("Sesión expirada. Vuelve a iniciar sesión.");
      logout();
      return;
    }
    const view = document.getElementById("audit-detail-body");
    if (view && !_pollErrorShown) {
      _pollErrorShown = true;
      const warn = document.createElement("div");
      warn.className = "alert alert-warning py-1 small mb-2";
      warn.textContent = "Error temporal consultando el progreso: " + (err.message || "error");
      view.prepend(warn);
    }
  } finally {
    _pollInFlight = false;
  }
}

function closeAuditDetail() {
  bootstrap.Modal.getInstance(document.getElementById("audit-detail-modal"))?.hide();
}

window.toggleReportGroup = function(header) {
  const body = header.nextElementSibling;
  const chevron = header.querySelector(".rp-chevron");
  if (!body) return;
  const isHidden = body.style.display === "none";
  body.style.display = isHidden ? "block" : "none";
  if (chevron) {
    chevron.classList.toggle("bi-chevron-down", !isHidden);
    chevron.classList.toggle("bi-chevron-up", isHidden);
  }
};

async function showAuditReport(auditId) {
  stopPolling();
  const view = document.getElementById("audit-detail-body");
  view.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-secondary"></div> Cargando informe...</div>';

  try {
    const [progress, vulns, audit] = await Promise.all([
      api("GET", `/audits/${auditId}/progress`),
      api("GET", `/audits/${auditId}/vulnerabilities`),
      api("GET", `/audits/${auditId}`),
    ]);

    // Summary
    const sev = progress.severity || {};
    const summaryHtml = `<div class="mb-3">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <h6 class="mb-0 small fw-semibold">Informe de Auditor\u00eda #${auditId}</h6>
        <span class="badge bg-success">Completada</span>
      </div>
      <div class="row g-2">
        <div class="col-3"><div class="card border-secondary text-center p-1"><small class="text-secondary">Cr\u00edtica</small><b class="text-danger small">${sev.critical || 0}</b></div></div>
        <div class="col-3"><div class="card border-secondary text-center p-1"><small class="text-secondary">Alta</small><b class="text-warning small">${sev.high || 0}</b></div></div>
        <div class="col-3"><div class="card border-secondary text-center p-1"><small class="text-secondary">Media</small><b class="text-info small">${sev.medium || 0}</b></div></div>
        <div class="col-3"><div class="card border-secondary text-center p-1"><small class="text-secondary">Baja</small><b class="text-secondary small">${sev.low || 0}</b></div></div>
      </div>
    </div>`;

    // Group by tipo, sort by severity
    const severityOrder = { "cr\u00edtica": 0, "alta": 1, "media": 2, "baja": 3 };
    const groups = {};
    for (const v of vulns) {
      const t = v.tipo || "Otros";
      if (!groups[t]) groups[t] = { items: [], severity: v.severidad || "media" };
      groups[t].items.push(v);
      const sIdx = severityOrder[groups[t].severity] || 99;
      const vIdx = severityOrder[v.severidad] || 99;
      if (vIdx < sIdx) groups[t].severity = v.severidad;
    }

    const typeOrder = Object.keys(groups).sort((a, b) => (severityOrder[groups[a].severity] || 99) - (severityOrder[groups[b].severity] || 99));

    const groupTpl = document.getElementById("tpl-report-group").innerHTML;
    const itemTpl = document.getElementById("tpl-report-item").innerHTML;

    let groupedHtml = "";
    for (const tipo of typeOrder) {
      const g = groups[tipo];
      const sv = g.severity;
      const severityColor = sv === "cr\u00edtica" ? "danger" : sv === "alta" ? "warning" : sv === "media" ? "info" : "secondary";
      const severityLabel = sv.charAt(0).toUpperCase() + sv.slice(1);

      let itemsHtml = "";
      for (const v of g.items) {
        const severidadBadge = v.severidad === "cr\u00edtica" ? "danger" : v.severidad === "alta" ? "warning" : v.severidad === "media" ? "info" : "secondary";
        const codigoVuln = v.codigo_vulnerable ? `<pre class="small mt-1 mb-0" style="background:rgba(220,53,69,.08);border-left:2px solid #dc3545;padding:4px 8px;border-radius:3px;overflow-x:auto;max-height:120px"><code class="text-danger">${escHtml(v.codigo_vulnerable)}</code></pre>` : "";
        const codigoFix = v.codigo_corregido ? `<pre class="small mt-1 mb-0" style="background:rgba(25,135,84,.08);border-left:2px solid #198754;padding:4px 8px;border-radius:3px;overflow-x:auto;max-height:120px"><code class="text-success">${escHtml(v.codigo_corregido)}</code></pre>` : "";
        const recoHtml = v.recomendacion ? `<small class="d-block mt-1"><i class="bi bi-info-circle text-info me-1"></i>${escHtml(v.recomendacion)}</small>` : "";
        const mapeos = Array.isArray(v.mapeos) ? v.mapeos : [];
        const mapeosHtml = mapeos.length ? `<div class="mt-1 d-flex flex-wrap gap-1">${mapeos.map(m => `<span class="badge bg-secondary-subtle text-secondary small">${escHtml(m.estandar || m.categoria || '')}</span>`).join("")}</div>` : "";

        const lineaInicio = v.linea_inicio != null ? v.linea_inicio : "?";
        const lineaFin = v.linea_fin != null ? v.linea_fin : "?";
        const lineRange = lineaInicio !== lineaFin ? lineaInicio + "-" + lineaFin : String(lineaInicio);
        let item = itemTpl
          .replace(/\{archivo_ruta\}/g, v.archivo_ruta ? escHtml(v.archivo_ruta) : "?")
          .replace(/\{line_range\}/g, lineRange)
          .replace(/\{descripcion\}/g, v.descripcion ? escHtml(v.descripcion) : "")
          .replace(/\{codigo_vulnerable_html\}/g, codigoVuln)
          .replace(/\{codigo_corregido_html\}/g, codigoFix)
          .replace(/\{recomendacion_html\}/g, recoHtml)
          .replace(/\{mapeos_html\}/g, mapeosHtml)
          .replace(/\{severidadBadge\}/g, severidadBadge)
          .replace(/\{cvss_score\}/g, v.cvss_score != null ? v.cvss_score.toFixed(1) : "N/A")
          .replace(/\{impacto\}/g, escHtml(v.impacto || "?"))
          .replace(/\{probabilidad\}/g, escHtml(v.probabilidad || "?"));
        itemsHtml += item;
      }

      let group = groupTpl
        .replace(/\{tipo\}/g, escHtml(tipo))
        .replace(/\{severityColor\}/g, severityColor)
        .replace(/\{severityLabel\}/g, severityLabel)
        .replace(/\{count\}/g, g.items.length)
        .replace(/\{items\}/g, itemsHtml);
      groupedHtml += group;
    }

    // Actions
    const actionsHtml = `<button class="btn btn-sm btn-outline-secondary" onclick="showAuditDetail(${auditId})"><i class="bi bi-arrow-left me-1"></i>Volver al progreso</button>
      <button class="btn btn-sm btn-outline-success" onclick="closeAuditDetail()"><i class="bi bi-check-lg me-1"></i>Cerrar</button>`;

    view.innerHTML = summaryHtml + groupedHtml + `<div class="d-flex gap-2 mt-2">${actionsHtml}</div>`;
    document.getElementById("audit-detail-title").textContent = "Informe - Auditor\u00eda #" + auditId;
  } catch (err) {
    view.innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle me-1"></i>Error al cargar informe: ${err.message}</div>`;
  }
}

// ---------- FRAMEWORK REPORTS ----------
const FW_LABELS = { owasp: "OWASP Top 10 + ASVS", nist_csf: "NIST CSF 2.0", nist_800_82: "NIST SP 800-82", iso_27001: "ISO 27001:2022", cis: "CIS Controls v8", mitre_attck: "MITRE ATT&CK v14" };
const FW_COLORS = { owasp: "danger", nist_csf: "primary", nist_800_82: "info", iso_27001: "success", cis: "warning", mitre_attck: "dark" };

async function showFrameworkReport(auditId, framework) {
  stopPolling();
  const view = document.getElementById("audit-detail-body");
  view.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-secondary"></div> Generando informe ' + (FW_LABELS[framework] || framework) + '...</div>';
  document.getElementById("audit-detail-title").textContent = (FW_LABELS[framework] || framework) + " - Auditor\u00eda #" + auditId;

  try {
    const report = await api("GET", `/audits/${auditId}/report/${framework}`);
    document.getElementById("audit-detail-title").textContent = "Informe " + (FW_LABELS[framework] || framework) + " - Auditor\u00eda #" + auditId;
    const html = renderFrameworkReportContent(report, auditId, framework);
    view.innerHTML = html;
  } catch (err) {
    view.innerHTML = '<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle me-1"></i>Error: ' + err.message + '</div>';
  }
}

function renderFrameworkReportContent(report, auditId, framework) {
  const meta = report.report_metadata || {};
  const exec = report.executive_summary || {};
  const controls = report.controls_evaluation || [];
  const findings = report.findings || [];
  const riskMatrix = report.risk_matrix || {};
  const implPlan = report.implementation_plan || [];
  const compliance = report.compliance_summary || {};
  const checklist = report.developer_checklist || [];

  const riskLevelBadge = exec.risk_level === "Cr\u00edtico" ? "danger" : exec.risk_level === "Alto" ? "warning" : exec.risk_level === "Medio" ? "info" : exec.risk_level === "Bajo" ? "success" : "secondary";

  // Executive Summary
  const execHtml = `<div class="card mb-3 border-${riskLevelBadge}" style="border-left:3px solid">
    <div class="card-body p-3">
      <div class="d-flex justify-content-between align-items-start mb-2">
        <h6 class="mb-0 small fw-semibold">Resumen Ejecutivo</h6>
        <span class="badge bg-${riskLevelBadge}">${exec.risk_level || "N/A"}</span>
      </div>
      <div class="d-flex align-items-center gap-3 mb-2">
        <div class="text-center">
          <div style="width:60px;height:60px;border-radius:50%;border:4px solid ${exec.compliance_score > 70 ? '#198754' : exec.compliance_score > 40 ? '#ffc107' : '#dc3545'};display:flex;align-items:center;justify-content:center;font-size:1.1rem;font-weight:700">${exec.compliance_score || 0}%</div>
          <small class="text-secondary d-block mt-1">Cumplimiento</small>
        </div>
        <div class="flex-grow-1">
          <div class="row g-1">
            <div class="col-3 text-center"><small class="text-danger d-block fw-bold">${exec.critical_findings || 0}</small><small class="text-secondary">Cr\u00edticas</small></div>
            <div class="col-3 text-center"><small class="text-warning d-block fw-bold">${exec.high_findings || 0}</small><small class="text-secondary">Altas</small></div>
            <div class="col-3 text-center"><small class="text-info d-block fw-bold">${exec.medium_findings || 0}</small><small class="text-secondary">Medias</small></div>
            <div class="col-3 text-center"><small class="text-secondary d-block fw-bold">${exec.low_findings || 0}</small><small class="text-secondary">Bajas</small></div>
          </div>
          ${exec.projected_score_post_fix != null ? `<small class="text-success d-block mt-1"><i class="bi bi-arrow-up me-1"></i>Proyecci\u00f3n post-correcci\u00f3n: ${exec.projected_score_post_fix}%</small>` : ""}
        </div>
      </div>
      <small class="d-block text-secondary" style="line-height:1.5">${exec.overview || "Sin resumen disponible."}</small>
    </div>
  </div>`;

  // Compliance score bar
  const scorePct = Math.min(Math.max(compliance.current_score != null ? compliance.current_score : exec.compliance_score || 0, 0), 100);
  const projPct = Math.min(Math.max(compliance.projected_score != null ? compliance.projected_score : exec.projected_score_post_fix || 0, 0), 100);
  const compHtml = `<div class="card mb-3">
    <div class="card-body p-3">
      <h6 class="small fw-semibold mb-2">L\u00ednea de Cumplimiento</h6>
      <div class="mb-1"><small class="text-secondary">Actual: ${scorePct}%</small>
        <div class="progress" style="height:8px"><div class="progress-bar ${scorePct > 70 ? 'bg-success' : scorePct > 40 ? 'bg-warning' : 'bg-danger'}" style="width:${scorePct}%"></div></div>
      </div>
      <div><small class="text-success">Proyectado: ${projPct}%</small>
        <div class="progress" style="height:8px"><div class="progress-bar bg-success" style="width:${projPct}%;opacity:.6"></div></div>
      </div>
      <small class="text-secondary d-block mt-1">Controles: ${compliance.verified_controls || 0} verificables de ${compliance.total_controls || 0} totales</small>
    </div>
  </div>`;

  // Controls Evaluation Table
  const controlsHtml = controls.length ? `<div class="card mb-3">
    <div class="card-header p-2 d-flex justify-content-between align-items-center">
      <small class="fw-semibold">Evaluaci\u00f3n de Controles</small>
      <small class="text-secondary">
        <span class="text-success">${controls.filter(c=>c.status==='verified').length}</span> OK ·
        <span class="text-warning">${controls.filter(c=>c.status==='partial').length}</span> parcial ·
        <span class="text-secondary">${controls.filter(c=>c.status==='non_verifiable'||c.status==='not_applicable').length}</span> N/V
      </small>
    </div>
    <div class="p-0" style="max-height:360px;overflow-y:auto">
      <table class="table table-sm small mb-0">
        <thead class="sticky-top" style="background:var(--bg-card)"><tr>
          <th class="ps-2 text-secondary fw-normal" style="width:90px">Control</th>
          <th class="text-secondary fw-normal">Nombre</th>
          <th class="text-secondary fw-normal" style="width:100px">Estado</th>
          <th class="text-secondary fw-normal">Evidencia / Hallazgo</th>
          <th class="pe-2 text-secondary fw-normal" style="width:80px">Tipo</th>
        </tr></thead>
        <tbody>${controls.map(c => {
          const stColor = c.status === "verified" ? "success" : c.status === "partial" ? "warning" : c.status === "non_verifiable" ? "secondary" : "info";
          const stIcon = c.status === "verified" ? "bi-check-circle-fill" : c.status === "partial" ? "bi-exclamation-triangle-fill" : c.status === "non_verifiable" ? "bi-question-circle" : "bi-dash-circle";
          const stLabel = c.status === "verified" ? "Correcto" : c.status === "partial" ? "Parcial" : c.status === "non_verifiable" ? "No Verificable" : c.status === "not_applicable" ? "No Aplica" : c.status || "?";
          const vtLabel = c.verification_type === "verified" ? "Verif." : c.verification_type === "non_verifiable" ? "No Verif." : "";
          const evidenceText = c.evidence || (c.status === "verified" ? "Cumple con el control, sin hallazgos" : c.status === "non_verifiable" ? "Requiere revisi\u00f3n manual de infraestructura" : c.status === "not_applicable" ? "No aplica al proyecto" : "");
          const refs = Array.isArray(c.findings_ref) && c.findings_ref.length ? c.findings_ref.join(', ') : "";
          return `<tr>
            <td class="ps-2" style="white-space:nowrap"><small class="fw-semibold">${escHtml(c.control_id || "")}</small></td>
            <td><small>${escHtml(c.control_name || "")}</small></td>
            <td><span class="badge bg-${stColor}-subtle text-${stColor}" style="font-size:.7rem"><i class="${stIcon} me-1"></i>${stLabel}</span></td>
            <td><small class="text-secondary" style="font-size:.75rem;line-height:1.3">${escHtml(evidenceText)}${refs ? ' <span class="text-info">('+escHtml(refs)+')</span>' : ''}</small></td>
            <td class="pe-2"><small class="text-secondary" style="font-size:.7rem">${vtLabel}</small></td>
          </tr>`;
        }).join("")}</tbody>
      </table>
    </div>
  </div>` : "";

  // Findings with code
  const findingsHtml = findings.length ? `<div class="card mb-3">
    <div class="card-header p-2"><small class="fw-semibold">Hallazgos Detallados (${findings.length})</small></div>
    ${findings.map(f => {
      const riskColor = f.risk === "critical" ? "danger" : f.risk === "high" ? "warning" : f.risk === "medium" ? "info" : "secondary";
      const riskLabel = f.risk === "critical" ? "Cr\u00edtico" : f.risk === "high" ? "Alto" : f.risk === "medium" ? "Medio" : "Bajo";
      const separator = '<div style="border-bottom:1px dashed var(--border);margin:8px 0"></div>';
      const vulnCode = f.vulnerable_code ? `<div class="mt-2"><small class="text-danger fw-semibold"><i class="bi bi-x-circle me-1"></i>C\u00f3digo vulnerable (evidencia):</small><pre class="small mt-1 mb-1" style="background:rgba(220,53,69,.08);border-left:3px solid #dc3545;padding:6px 10px;border-radius:4px;overflow-x:auto;max-height:150px;font-size:.75rem;line-height:1.3"><code class="text-danger">${escHtml(f.vulnerable_code)}</code></pre></div>` : "";
      const fixCode = f.fixed_code ? `<div class="mt-2"><small class="text-success fw-semibold"><i class="bi bi-check-circle me-1"></i>C\u00f3digo corregido:</small><pre class="small mt-1 mb-1" style="background:rgba(25,135,84,.08);border-left:3px solid #198754;padding:6px 10px;border-radius:4px;overflow-x:auto;max-height:150px;font-size:.75rem;line-height:1.3"><code class="text-success">${escHtml(f.fixed_code)}</code></pre></div>` : "";
      const fileInfo = f.file ? (f.line_start ? `${f.file}:${f.line_start}${f.line_end && f.line_end !== f.line_start ? '-'+f.line_end : ''}` : f.file) : "";
      const mControls = Array.isArray(f.mapped_controls) && f.mapped_controls.length ? `<div class="mt-1"><small class="text-secondary"><i class="bi bi-tags me-1"></i>Controles: ${f.mapped_controls.join(', ')}</small></div>` : "";
      return `<div class="p-3 border-bottom border-secondary-subtle">
        <div class="d-flex justify-content-between align-items-start mb-1">
          <small class="fw-semibold" style="font-size:.85rem">${escHtml(f.title || f.id || "")}</small>
          <span class="badge bg-${riskColor} flex-shrink-0">${riskLabel}${f.cvss_score != null ? ' | CVSS:'+f.cvss_score.toFixed(1) : ''}</span>
        </div>
        ${fileInfo ? `<small class="d-block text-info mb-1" style="font-size:.8rem"><i class="bi bi-file-earmark-code me-1"></i>${escHtml(fileInfo)}</small>` : ""}
        ${separator}
        <small class="d-block text-secondary" style="line-height:1.5">${escHtml(f.description || "")}</small>
        ${vulnCode}
        ${f.fix_explanation ? `<div class="mt-2"><small class="text-info fw-semibold"><i class="bi bi-info-circle me-1"></i>Soluci\u00f3n:</small><small class="d-block text-info mt-1" style="line-height:1.4">${escHtml(f.fix_explanation)}</small></div>` : ""}
        ${f.recommendation ? `<div class="mt-1"><small class="text-success"><i class="bi bi-check-circle me-1"></i>${escHtml(f.recommendation)}</small></div>` : ""}
        ${fixCode}
        ${mControls}
        ${f.compliance_impact ? `<small class="d-block text-secondary mt-1"><i class="bi bi-shield me-1"></i>${escHtml(f.compliance_impact)}</small>` : ""}
      </div>`;
    }).join("")}
  </div>` : "";

  // Risk Matrix
  const riskHtml = `<div class="card mb-3">
    <div class="card-body p-3">
      <h6 class="small fw-semibold mb-2">Matriz de Riesgo</h6>
      <div class="row g-1 text-center">
        <div class="col-3"><div class="p-1 rounded" style="background:rgba(220,53,69,.12)"><small class="text-danger d-block fw-bold">${riskMatrix.critical || 0}</small><small class="text-secondary" style="font-size:.7rem">Cr\u00edticas</small></div></div>
        <div class="col-3"><div class="p-1 rounded" style="background:rgba(255,193,7,.12)"><small class="text-warning d-block fw-bold">${riskMatrix.high || 0}</small><small class="text-secondary" style="font-size:.7rem">Altas</small></div></div>
        <div class="col-3"><div class="p-1 rounded" style="background:rgba(13,202,240,.12)"><small class="text-info d-block fw-bold">${riskMatrix.medium || 0}</small><small class="text-secondary" style="font-size:.7rem">Medias</small></div></div>
        <div class="col-3"><div class="p-1 rounded" style="background:rgba(134,142,150,.12)"><small class="text-secondary d-block fw-bold">${riskMatrix.low || 0}</small><small class="text-secondary" style="font-size:.7rem">Bajas</small></div></div>
      </div>
      ${riskMatrix.risk_score != null ? `<small class="d-block mt-2 text-secondary">Puntaje de Riesgo: <strong>${riskMatrix.risk_score}%</strong> - ${riskMatrix.risk_level || ""}</small>` : ""}
      ${Array.isArray(riskMatrix.top_risks) && riskMatrix.top_risks.length ? `<div class="mt-2"><small class="text-secondary fw-semibold d-block mb-1">Principales Riesgos:</small>${riskMatrix.top_risks.map(r => `<small class="d-block text-secondary"><i class="bi bi-dot me-1"></i>${escHtml(r)}</small>`).join("")}</div>` : ""}
    </div>
  </div>`;

  // Implementation Plan
  const planHtml = implPlan.length ? `<div class="card mb-3">
    <div class="card-header p-2"><small class="fw-semibold">Plan de Implementaci\u00f3n</small></div>
    <div class="p-2">
      ${implPlan.map(p => {
        const priColor = p.priority === "critical" ? "danger" : p.priority === "high" ? "warning" : p.priority === "medium" ? "info" : "secondary";
        const files = Array.isArray(p.files_affected) && p.files_affected.length ? `<small class="text-secondary d-block mt-1"><i class="bi bi-files me-1"></i>${p.files_affected.join(', ')}</small>` : "";
        return `<div class="d-flex gap-2 mb-2">
          <div class="flex-shrink-0" style="width:24px;height:24px;border-radius:50%;background:var(--bg-body);display:flex;align-items:center;justify-content:center"><small class="fw-bold">${p.order || "?"}</small></div>
          <div class="flex-grow-1">
            <small class="d-block fw-semibold">${escHtml(p.action || "")}</small>
            ${files}
            <div class="d-flex gap-2 mt-1">
              <span class="badge bg-${priColor} small">${p.priority || "?"}</span>
              ${p.estimated_effort ? `<small class="text-secondary"><i class="bi bi-clock me-1"></i>${escHtml(p.estimated_effort)}</small>` : ""}
            </div>
            ${p.expected_impact ? `<small class="text-success d-block mt-1"><i class="bi bi-arrow-up me-1"></i>${escHtml(p.expected_impact)}</small>` : ""}
            ${Array.isArray(p.framework_controls_addressed) && p.framework_controls_addressed.length ? `<small class="text-secondary d-block mt-1">Controles: ${p.framework_controls_addressed.join(', ')}</small>` : ""}
          </div>
        </div>`;
      }).join("")}
    </div>
  </div>` : "";

  // Developer Checklist
  const checklistHtml = checklist.length ? `<div class="card mb-3">
    <div class="card-header p-2"><small class="fw-semibold"><i class="bi bi-check2-square me-1"></i>Checklist para Desarrolladores</small></div>
    <div class="p-2">
      ${checklist.map(c => `<div class="form-check mb-1">
        <input class="form-check-input" type="checkbox" id="chk-${escHtml(c).replace(/\s+/g, '-').toLowerCase().slice(0, 30)}" style="cursor:pointer">
        <label class="form-check-label small text-secondary" for="chk-${escHtml(c).replace(/\s+/g, '-').toLowerCase().slice(0, 30)}">${escHtml(c)}</label>
      </div>`).join("")}
    </div>
  </div>` : "";

  // Actions
  const actionsHtml = `<button class="btn btn-sm btn-outline-primary" onclick="downloadFrameworkReportPdf(${auditId}, '${framework}')">
    <i class="bi bi-download me-1"></i>Descargar PDF
  </button>
  <button class="btn btn-sm btn-outline-secondary" onclick="showAuditDetail(${auditId})">
    <i class="bi bi-arrow-left me-1"></i>Volver al progreso
  </button>
  <button class="btn btn-sm btn-outline-success flex-grow-1" onclick="closeAuditDetail()">
    <i class="bi bi-check-lg me-1"></i>Cerrar
  </button>`;

  return `
    <div class="fw-report">
      <div class="d-flex justify-content-between align-items-start mb-3">
        <div>
          <h6 class="mb-1 fw-semibold">${escHtml(meta.framework || FW_LABELS[framework] || framework)}</h6>
          <small class="text-secondary">${escHtml(meta.project_name || "")} · ${escHtml(meta.generated_at ? meta.generated_at.slice(0,10) : "")} · Auditor: ${escHtml(meta.author || "SecureCode AI")}</small>
        </div>
        <span class="badge bg-${riskLevelBadge}">${exec.risk_level || "?"}</span>
      </div>
      ${execHtml}
      ${compHtml}
      ${controlsHtml}
      ${findingsHtml}
      ${riskHtml}
      ${planHtml}
      ${checklistHtml}
      <div class="d-flex gap-2 mt-3 no-print">${actionsHtml}</div>
    </div>`;
}

async function downloadFrameworkReportPdf(auditId, framework) {
  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert("El navegador bloque\u00f3 la ventana emergente. Permite popups para este sitio e intenta de nuevo.");
    return;
  }

  try {
    const report = await api("GET", `/audits/${auditId}/report/${framework}`);
    const meta = report.report_metadata || {};
    const content = renderFrameworkReportContent(report, auditId, framework);

    printWindow.document.write(`<!DOCTYPE html><html lang="es"><head>
      <meta charset="UTF-8"><title>Informe ${meta.framework || framework} - ${meta.project_name || ""}</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
      <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
      <style>
        body { background:#fff !important; color:#222; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; font-size:11pt; padding:20px; }
        .card { border:1px solid #ddd; border-radius:4px; margin-bottom:12px; page-break-inside:avoid; }
        .card-body { padding:12px; }
        .card-header { background:#f5f5f5; border-bottom:1px solid #ddd; padding:6px 12px; font-weight:600; }
        .badge { display:inline-block; padding:2px 8px; border-radius:3px; font-size:9pt; font-weight:500; }
        .progress { height:8px; background:#eee; border-radius:4px; margin:4px 0; }
        .progress-bar { border-radius:4px; height:100%; }
        pre { font-size:8pt; padding:6px; border-radius:3px; white-space:pre-wrap; word-break:break-all; max-height:200px; overflow:auto; }
        .text-secondary { color:#666 !important; }
        .fw-semibold { font-weight:600; }
        h6 { font-size:11pt; margin:0 0 4px; }
        small { font-size:9pt; }
        table { width:100%; border-collapse:collapse; font-size:9pt; }
        th { text-align:left; padding:4px 6px; border-bottom:1px solid #ddd; color:#666; font-weight:400; }
        td { padding:4px 6px; border-bottom:1px solid #eee; }
        .form-check { display:flex; align-items:center; gap:6px; margin-bottom:4px; }
        .form-check-input { width:14px; height:14px; }
        .bg-danger { background:#dc3545; color:#fff; }
        .bg-warning { background:#ffc107; color:#222; }
        .bg-info { background:#0dcaf0; color:#222; }
        .bg-success { background:#198754; color:#fff; }
        .bg-secondary { background:#6c757d; color:#fff; }
        @media print {
          body { padding:0; }
          .no-print { display:none !important; }
          .card { break-inside:avoid; }
          pre { max-height:none; overflow:visible; }
        }
      </style>
    </head><body>
      <div class="no-print mb-3">
        <button onclick="window.print()" style="padding:6px 16px;background:#0d6efd;color:#fff;border:none;border-radius:4px;cursor:pointer">
          <i class="bi bi-printer"></i> Imprimir / Guardar PDF
        </button>
        <button onclick="window.close()" style="padding:6px 16px;background:#6c757d;color:#fff;border:none;border-radius:4px;cursor:pointer;margin-left:8px">
          Cerrar
        </button>
      </div>
      ${content}
      <div style="text-align:center;margin-top:20px;font-size:8pt;color:#999;border-top:1px solid #ddd;padding-top:8px">
        Generado por SecureCode AI · ${new Date().toLocaleDateString("es-CL")}
      </div>
    </body></html>`);
    printWindow.document.close();
    printWindow.focus();
  } catch (err) {
    alert("Error generando PDF: " + err.message);
  }
}

function escHtml(s) {
  if (typeof s !== "string") return String(s || "");
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

async function showRetryAudit(auditId) {
  closeAuditDetail();
  try {
    await api("POST", `/audits/reset-stuck`);
    const audit = (await api("GET", "/audits/")).find(a => a.id === auditId);
    if (audit) {
      await api("POST", "/audits/", {
        proyecto_id: audit.proyecto_id,
        nombre: audit.nombre,
        git_url: audit.git_url,
        git_username: audit.git_username || undefined,
        frameworks: audit.frameworks,
      });
      alert("Nueva auditoría creada.");
      location.hash = "/audits";
    }
  } catch (err) { alert(err.message); }
}

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

// ---------- ADMIN ----------
async function renderAdmin(ct) {
  ct.innerHTML = document.getElementById("tpl-admin").innerHTML;
  document.getElementById("admin-tabs").addEventListener("click", (e) => {
    const tab = e.target.closest("[data-tab]");
    if (!tab) return;
    e.preventDefault();
    document.querySelectorAll("#admin-tabs .nav-link").forEach(a => a.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("admin-users").classList.toggle("d-none", tab.dataset.tab !== "users");
    document.getElementById("admin-roles").classList.toggle("d-none", tab.dataset.tab !== "roles");
    if (tab.dataset.tab === "users") renderAdminUsers();
    if (tab.dataset.tab === "roles") renderAdminRoles();
  });
  renderAdminUsers();
  renderAdminRoles();
  document.getElementById("loading-screen").classList.add("d-none");
}

async function renderAdminUsers() {
  try {
    const users = await api("GET", "/auth/users");
    document.getElementById("admin-users-list").innerHTML = users.map(u => fillTpl(document.getElementById("tpl-admin-user-row").innerHTML, u)).join("");
  } catch (err) {
    document.getElementById("admin-users-list").innerHTML = `<p class="text-danger small">${err.message}</p>`;
  }
}

async function renderAdminRoles() {
  try {
    const roles = await api("GET", "/auth/roles");
    document.getElementById("admin-roles-list").innerHTML = roles.map(r => fillTpl(document.getElementById("tpl-admin-role-row").innerHTML, r)).join("");
  } catch (err) {
    document.getElementById("admin-roles-list").innerHTML = `<p class="text-danger small">${err.message}</p>`;
  }
}

function showAdminNewUser() {
  const username = prompt("Nombre de usuario:");
  if (!username) return;
  const email = prompt("Email:");
  if (!email) return;
  const password = prompt("Contraseña (mín 8 caracteres):");
  if (!password || password.length < 8) return alert("Mínimo 8 caracteres");
  api("POST", "/auth/users", { username, email, password }).then(() => renderAdminUsers()).catch(err => alert(err.message));
}

function showAdminNewRole() {
  const nombre = prompt("Nombre del rol:");
  if (!nombre) return;
  const descripcion = prompt("Descripción:");
  const permisosStr = prompt("Permisos (separados por coma, ej: audits:read,projects:write):");
  const permisos = permisosStr ? permisosStr.split(",").map(s => s.trim()).filter(Boolean) : [];
  api("POST", "/auth/roles", { nombre, descripcion, permisos }).then(() => renderAdminRoles()).catch(err => alert(err.message));
}

async function adminDeleteUser(userId) {
  if (!confirm("¿Eliminar este usuario?")) return;
  try {
    await api("DELETE", `/auth/users/${userId}`);
    renderAdminUsers();
  } catch (err) { alert(err.message); }
}

async function adminDeleteRole(roleId) {
  if (!confirm("¿Eliminar este rol?")) return;
  try {
    await api("DELETE", `/auth/roles/${roleId}`);
    renderAdminRoles();
  } catch (err) { alert(err.message); }
}

async function adminDeleteProject(projectId) {
  if (!confirm("¿Eliminar este proyecto? Se borrará de la base de datos y el almacenamiento.")) return;
  try {
    await api("DELETE", `/projects/${projectId}`);
    window._projects = await api("GET", "/projects");
    renderProjectList();
  } catch (err) { alert(err.message); }
}

async function adminDeleteAudit(auditId) {
  if (!confirm("¿Eliminar esta auditoría?")) return;
  try {
    await api("DELETE", `/audits/${auditId}`);
    renderAudits(document.getElementById("page-content"));
  } catch (err) { alert(err.message); }
}

async function adminResetStuck() {
  if (!confirm("¿Resetear auditorías atascadas (ejecutando > 1 hora)?")) return;
  try {
    const r = await api("POST", "/audits/reset-stuck");
    alert(r.message);
  } catch (err) { alert(err.message); }
}

// ---------- UTILS ----------
function escapeHtml(s) {
  return String(s).replace(/[&<>"'`]/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;", "`": "&#96;"
  })[c]);
}
function esc(v) { return v == null ? "" : escapeHtml(v); }

function fillTpl(tpl, data) {
  let h = tpl;
  Object.keys(data).forEach(k => {
    const v = data[k] == null ? "" : String(data[k]);
    // {k} se escapa (XSS-safe); {k|raw} inserta HTML sin escapar (uso explícito)
    h = h.replaceAll("{" + k + "}", escapeHtml(v));
    h = h.replaceAll("{" + k + "|raw}", v);
  });
  h = h.replace(/\{[^}]+\|raw\}/g, "");
  return h;
}

// ---------- ACCORDION ----------
window.toggleStepDetail = function(header) {
  const row = header.closest(".step-row");
  if (!row) return;
  const detail = row.querySelector(".step-detail");
  const chevron = row.querySelector(".step-chevron");
  if (!detail) return;
  const isHidden = detail.classList.contains("d-none");
  detail.classList.toggle("d-none", !isHidden);
  if (chevron) chevron.classList.toggle("bi-chevron-down", !isHidden);
  if (chevron) chevron.classList.toggle("bi-chevron-up", isHidden);
};

// ---------- INIT ----------
(async function init() {
  if (TOKEN) {
    try {
      USER = await api("GET", "/auth/me");
      document.getElementById("sidebar-user").textContent = USER.username;
      if (USER.rol_nombre === "admin" || USER.rol?.nombre === "admin") {
        document.getElementById("nav-admin").classList.remove("d-none");
      }
      if (location.hash) hashRoute();
      else location.hash = "/";
      return;
    } catch { setToken(null); }
  }
  showPage("login");
  document.getElementById("loading-screen").classList.add("d-none");
})();
