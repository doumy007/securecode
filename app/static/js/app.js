const API = window.location.origin;
let TOKEN = localStorage.getItem("sc_token") || null;
let USER = null;
let _pollInterval = null;

function setToken(t) { TOKEN = t; localStorage.setItem("sc_token", t); }
function logout() { TOKEN = null; USER = null; localStorage.removeItem("sc_token"); stopPolling(); showPage("login"); }

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
          <input class="form-control form-control-sm" placeholder="https://github.com/usuario/repo.git" id="git-url-input">
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
  if (mode === "git") {
    gitUrl = document.getElementById("git-url-input").value.trim();
    if (!gitUrl) return alert("Ingresa una URL de Git");
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
  try {
    const data = await api("GET", `/audits/${auditId}/progress`);
    const view = document.getElementById("audit-detail-body");
    const pct = data.percentage || 0;
    const done = data.estado === "completada" || data.estado === "fallida";

    const stateLabels = { pendiente: "Pendiente", ejecutando: "Ejecutando...", completada: "Completada", fallida: "Fallida" };
    const stateColors = { pendiente: "warning", ejecutando: "info", completada: "success", fallida: "danger" };

    // Status header
    const statusHtml = `<div class="d-flex justify-content-between align-items-center">
      <h6 class="mb-0 small fw-semibold">
        <span class="badge bg-${stateColors[data.estado] || "secondary"}">${stateLabels[data.estado] || data.estado}</span>
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
    const errorBarHtml = error ? `<div class="alert alert-danger py-2 small mb-2"><i class="bi bi-exclamation-triangle me-1"></i>${error}</div>` : "";

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
      currentStep = `<div class="badge bg-info-subtle text-info px-2 py-1 small mb-2"><i class="bi bi-arrow-repeat me-1"></i>${runningStep.name || "Ejecutando..."}</div>`;
    }

    // Message
    const msgHtml = data.message ? `<small class="text-secondary">${data.message}</small>` : "";

    // Interactive log - show all steps like a chat/log
    const statusMap = { pendiente: ["circle", "text-secondary"], ejecutando: ["arrow-repeat text-info", "text-info"], completado: ["check-circle-fill text-success", "text-success"], fallido: ["x-circle-fill text-danger", "text-danger"] };
    const logHtml = steps.length ? `<div class="mb-3" style="max-height:320px;overflow-y:auto">` + steps.map((s, idx) => {
      if (!s) return "";
      const [icon, color] = statusMap[s.status] || ["circle", "text-secondary"];
      const vulns = s.vulnerabilities != null ? `<span class="badge bg-secondary-subtle text-secondary small ms-2">${s.vulnerabilities} encontradas</span>` : "";
      const err = s.error ? `<small class="text-danger d-block ms-3">${s.error}</small>` : "";
      const bg = s.status === "ejecutando" ? "style='background:rgba(13,202,240,.08);border-left:2px solid #0dcaf0'" : 
                 s.status === "fallido" ? "style='background:rgba(220,53,69,.06);border-left:2px solid #dc3545'" :
                 s.status === "completado" ? "style='background:rgba(25,135,84,.06);border-left:2px solid #198754'" : "";
      const files = s.files_count != null ? `<small class="text-secondary ms-2">${s.files_count} archivos</small>` : "";
      return `<div class="d-flex align-items-start gap-2 mb-1 py-1 px-2 rounded" ${bg}>
        <i class="bi bi-${icon} mt-1 ${color}"></i>
        <div class="flex-grow-1">
          <span class="small ${color}">${s.name || ""}</span>${vulns}${files}
          ${err}
        </div>
      </div>`;
    }).join("") + `</div>` : "";

    // Frameworks badges
    const fws = Array.isArray(data.frameworks) ? data.frameworks : [];
    const fwLabels = { owasp: "OWASP Top 10", nist_csf: "NIST CSF", nist_800_82: "NIST SP 800-82", iso_27001: "ISO 27001", cis: "CIS Controls", mitre_attck: "MITRE ATT&CK" };
    const fwHtml = fws.length ? fws.map(f => `<span class="badge bg-secondary-subtle text-secondary small">${fwLabels[f] || f}</span>`).join(" ") : "";

    // Actions
    let actionsHtml = "";
    if (data.estado === "completada") {
      actionsHtml = `<button class="btn btn-sm btn-outline-success flex-grow-1" onclick="closeAuditDetail()"><i class="bi bi-check-lg me-1"></i>Cerrar</button>`;
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
    stopPolling();
    document.getElementById("audit-detail-body").innerHTML = `<div class="alert alert-danger py-2 small mb-0"><i class="bi bi-exclamation-triangle me-1"></i>${err.message}</div>`;
  }
}

function closeAuditDetail() {
  bootstrap.Modal.getInstance(document.getElementById("audit-detail-modal"))?.hide();
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
