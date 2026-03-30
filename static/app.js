(() => {
  const el = (id) => document.getElementById(id);
 
  const usernameInput = el("usernameInput");
  const passwordInput = el("passwordInput");
  const pinInput = el("pinInput");
  const pinStepWrap = el("pinStepWrap");
  const loginBtn = el("loginBtn");
  const pinBtn = el("pinBtn");
  const logoutBtn = el("logoutBtn");
  const loginStatus = el("loginStatus");
  const activeModeChip = el("activeModeChip");
  const headerCalendarBtn = el("headerCalendarBtn");
 
  const loginToggle = el("loginToggle");
  const loginBody = el("loginBody");
  const loginChev = el("loginChev");
 
  const formsToggle = el("formsToggle");
  const formsBody = el("formsBody");
  const formsChev = el("formsChev");
 
  const navFormsTimeCard = el("navFormsTimeCard");
  let navFormsTimeOff = el("navFormsTimeOff");
  const navTakeoffs = el("navTakeoffs");
  let navFormsSignOff = el("navFormsSignOff");
 
  const navJobFlow = el("navJobFlow");
  const navEstimatePage = el("navEstimatePage");
  const navInvoicePage = el("navInvoicePage");
  const navEstimateInvoice = el("navEstimateInvoice");
  const navCustomers = el("navCustomers");
  const navContacts = el("navContacts");
  let navAllJobs = el("navAllJobs");
  let navPartsList = el("navPartsList");
 
  const navDataCenter = el("navDataCenter");
  const navPayroll = el("navPayroll");
  const navEmployees = el("navEmployees");
  const navDataUpload = el("navDataUpload");
  let navSaddleback = el("navSaddleback");
 
  const navNotifications = el("navNotifications");
  const navAtlas = el("navAtlas");
  const navMoses = el("navMoses");
 
  const badgeNotifications = el("badgeNotifications");
  const badgeJobFlow = el("badgeJobFlow");
 
  const primaryEstimateNav = navEstimateInvoice || navEstimatePage;
  if (!navFormsTimeOff) {
    const formsNavCol = document.querySelector("#formsBody .navcol");
    if (formsNavCol) {
      const btn = document.createElement("button");
      btn.className = "navbtn";
      btn.id = "navFormsTimeOff";
      btn.innerHTML = `<span>Time Off Request</span><small>Submit / Approve</small>`;
      if (navTakeoffs) formsNavCol.insertBefore(btn, navTakeoffs);
      else formsNavCol.appendChild(btn);
      navFormsTimeOff = btn;
    }
  }
 
  if (!navAllJobs) {
    const jobsNavCol = navJobFlow && navJobFlow.parentElement;
    if (jobsNavCol) {
      const btn = document.createElement("button");
      btn.className = "navbtn";
      btn.id = "navAllJobs";
      btn.innerHTML = `<span>All Jobs</span><small>Current + Legacy</small>`;
      if (navCustomers) jobsNavCol.insertBefore(btn, navCustomers);
      else jobsNavCol.appendChild(btn);
      navAllJobs = btn;
    }
  }
 
  if (!navFormsSignOff) {
    const formsNavCol = document.querySelector("#formsBody .navcol");
    if (formsNavCol) {
      const btn = document.createElement("button");
      btn.className = "navbtn";
      btn.id = "navFormsSignOff";
      btn.innerHTML = `<span>Sign Off</span><small>PDF + Signature</small>`;
      if (navFormsTimeCard) formsNavCol.insertBefore(btn, navFormsTimeCard);
      else if (navTakeoffs) formsNavCol.insertBefore(btn, navTakeoffs);
      else formsNavCol.appendChild(btn);
      navFormsSignOff = btn;
    }
  }

  if (!navPartsList) {
    const jobsNavCol = navJobFlow && navJobFlow.parentElement;
    if (jobsNavCol) {
      const btn = document.createElement("button");
      btn.className = "navbtn";
      btn.id = "navPartsList";
      btn.innerHTML = `<span>Parts List</span><small>Catalog + Pricing</small>`;
      if (navCustomers) jobsNavCol.insertBefore(btn, navCustomers);
      else jobsNavCol.appendChild(btn);
      navPartsList = btn;
    }
  }

  if (navCustomers) {
    const bits = navCustomers.querySelectorAll("span, small");
    if (bits[0]) bits[0].textContent = "Customers";
    if (bits[1]) bits[1].textContent = "Database";
  }
  if (navContacts) navContacts.style.display = "none";
  if (navFormsTimeOff && !navFormsTimeOff.querySelector('.badge')) {
    const badge = document.createElement('span');
    badge.className = 'badge';
    badge.id = 'badgeTimeOff';
    badge.style.display = 'none';
    badge.textContent = '0';
    navFormsTimeOff.appendChild(badge);
  }
 
  if (navEstimateInvoice) {
    if (navEstimatePage) navEstimatePage.style.display = "none";
    if (navInvoicePage) navInvoicePage.style.display = "none";
  } else if (navEstimatePage) {
    const pieces = navEstimatePage.querySelectorAll("span, small");
    if (pieces[0]) pieces[0].textContent = "Estimate/Invoice";
    if (pieces[1]) pieces[1].textContent = "Builder";
    if (navInvoicePage) navInvoicePage.style.display = "none";
    if (navCustomers && navCustomers.parentElement) {
      navCustomers.parentElement.insertBefore(navEstimatePage, navCustomers.nextSibling);
    }
  }
 
  const workspaceTitle = el("workspaceTitle");
  const workspaceActions = el("workspaceActions");
  const workspaceBody = el("workspaceBody");
  const loginPanel = loginToggle ? loginToggle.closest(".panel") : null;
  const formsPanel = formsToggle ? formsToggle.closest(".panel") : null;
  const jobFlowPanel = navJobFlow ? navJobFlow.closest(".panel") : null;
  const officeFlowPanel = navDataCenter ? navDataCenter.closest(".panel") : null;
  const chatPanel = navAtlas ? navAtlas.closest(".panel") : null;
  const notificationsPanel = navNotifications ? navNotifications.closest(".panel") : null;

  if (!navSaddleback && officeFlowPanel) {
    const navcol = officeFlowPanel.querySelector(".navcol");
    if (navcol) {
      const btn = document.createElement("button");
      btn.className = "navbtn";
      btn.id = "navSaddleback";
      btn.style.display = "none";
      btn.innerHTML = `<span>Saddleback Design Co.</span><small>Orders / Taxes</small>`;
      navcol.appendChild(btn);
      navSaddleback = btn;
    }
  }

  let apiKey = "";
  let currentUser = null;
  let pendingPinUser = null;
 
  const STATUSES = ["Sales Lead", "Dispatch", "Quote", "Quote Sent", "Parts on Order", "Complete/Quote", "Complete", "Done"];
  const JOB_STATUS_OPTIONS = ["Dispatch", "Quote", "Parts on Order", "Complete/Quote", "Complete"];
  const STATUS_META = {
    "Sales Lead": { cls: "s-blue", dot: "#2563eb" },
    "Dispatch": { cls: "s-purple", dot: "#7c3aed" },
    "Quote": { cls: "s-red", dot: "#ef4444" },
    "Quote Sent": { cls: "s-pink", dot: "#ec4899" },
    "Parts on Order": { cls: "s-brown", dot: "#8b5e3c" },
    "Complete/Quote": { cls: "s-yellow", dot: "#f59e0b" },
    "Complete": { cls: "s-green", dot: "#22c55e" },
    "Done": { cls: "s-gray", dot: "#9ca3af" },
  };
 
  const DOOR_TYPES = [
    "Automatic Door", "Man Door", "Storefront Door", "Herculite Door",
    "Roll Up", "Glass", "Roll/Swing Gate", "Other"
  ];
 
  const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  let currentView = null;
 
  function setActiveChip(label) { activeModeChip.textContent = label; }
  function setWorkspace(title) { workspaceTitle.textContent = title; }
  function clearWorkspaceActions() { workspaceActions.innerHTML = ""; }
 
  function setNavActive(btn) {
    [
      navFormsTimeCard, navFormsTimeOff, navTakeoffs, navFormsSignOff,
      navJobFlow, navAllJobs, navPartsList, navEstimatePage, navInvoicePage, navEstimateInvoice, navCustomers, navContacts,
      navDataCenter, navPayroll, navEmployees, navDataUpload, navSaddleback,
      navNotifications, navAtlas, navMoses
    ].filter(Boolean).forEach(b => b.classList.toggle("navbtn-active", b === btn));
  }
 
  async function fetchJSON(url, opts = {}) {
    const headers = opts.headers || {};
    opts.headers = headers;
    opts.credentials = "same-origin";
 
    const res = await fetch(url, opts);
    const txt = await res.text();
    let data = null;
    try { data = JSON.parse(txt); } catch {}
 
    if (!res.ok) {
      const msg = (data && (data.detail || data.error)) ? (data.detail || data.error) : (txt || `HTTP ${res.status}`);
      if (res.status === 401) {
        currentUser = null;
        applyRoleAccess(null);
        updateLoginUi();
        showLoggedOutSplash("Session expired. Please log in again.");
      }
      throw new Error(msg);
    }
    return data;
  }
 
  function togglePanel(bodyEl, chevEl) {
    const isHidden = bodyEl.style.display === "none";
    bodyEl.style.display = isHidden ? "block" : "none";
    chevEl.innerHTML = isHidden ? "&#9662;" : "&#9656;";
  }
 
  if (loginToggle) loginToggle.addEventListener("click", () => togglePanel(loginBody, loginChev));
  if (formsToggle) formsToggle.addEventListener("click", () => togglePanel(formsBody, formsChev));
 
  function yyyyMmDd(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }
 
  function mmDdYy(yyyy_mm_dd) {
    const [y, m, d] = (yyyy_mm_dd || "").split("-");
    if (!y || !m || !d) return yyyy_mm_dd;
    return `${m}-${d}-${y}`;
  }

  function formatDisplayDate(value) {
    if (!value) return "";
    const s = String(value).trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return mmDdYy(s);
    if (/^\d{4}-\d{2}$/.test(s)) {
      const [y, m] = s.split("-");
      return `${m}-${y}`;
    }
    return s;
  }

  function formatTime12(value) {
    const s = String(value || "").trim();
    if (!s) return "";
    const m = s.match(/^(\d{1,2}):(\d{2})(?::\d{2})?$/);
    if (!m) return s;
    let h = Number(m[1]);
    const min = m[2];
    const ampm = h >= 12 ? "PM" : "AM";
    h = h % 12;
    if (h === 0) h = 12;
    return `${h}:${min} ${ampm}`;
  }

  function formatTimeRange12(start, end) {
    const a = formatTime12(start);
    const b = formatTime12(end);
    if (a && b) return `${a} - ${b}`;
    return a || b || "";
  }

  function lunchSummary(item) {
    if (!item || !item.lunch_taken) return "Lunch: No";
    const range = formatTimeRange12(item.lunch_start, item.lunch_end);
    return range ? `Lunch: Yes (${range})` : "Lunch: Yes";
  }
 
  function monthLabel(d) {
    return d.toLocaleString(undefined, { month: "long", year: "numeric" });
  }


  const SALES_TAX_OPTIONS = [
    { city: "San Diego", rate: 7.75 },
    { city: "Chula Vista", rate: 8.75 },
    { city: "Del Mar", rate: 8.75 },
    { city: "El Cajon", rate: 8.25 },
    { city: "Escondido", rate: 8.75 },
    { city: "Imperial Beach", rate: 8.75 },
    { city: "La Mesa", rate: 8.50 },
    { city: "Lemon Grove", rate: 8.75 },
    { city: "National City", rate: 8.75 },
    { city: "Oceanside", rate: 8.25 },
    { city: "San Marcos", rate: 8.75 },
    { city: "Solana Beach", rate: 8.75 },
    { city: "Vista", rate: 8.25 },
    { city: "Riverside", rate: 7.75 },
    { city: "Blythe", rate: 8.75 },
    { city: "Cathedral City", rate: 9.25 },
    { city: "Coachella", rate: 8.75 },
    { city: "Corona", rate: 8.75 },
    { city: "Desert Hot Springs", rate: 8.75 },
    { city: "Hemet", rate: 8.75 },
    { city: "Indio", rate: 8.75 },
    { city: "La Quinta", rate: 8.75 },
    { city: "Lake Elsinore", rate: 8.75 },
    { city: "Menifee", rate: 8.75 },
    { city: "Moreno Valley", rate: 8.75 },
    { city: "Murrieta", rate: 8.75 },
    { city: "Norco", rate: 8.75 },
    { city: "Palm Desert", rate: 8.75 },
    { city: "Palm Springs", rate: 9.25 },
    { city: "Riverside (Alt)", rate: 8.75 },
    { city: "San Jacinto", rate: 8.75 },
    { city: "Temecula", rate: 8.75 },
    { city: "Wildomar", rate: 8.75 },
  ];

  function inferTaxCityFromAddress(address) {
    const text = String(address || "").toLowerCase();
    return SALES_TAX_OPTIONS.find(opt => text.includes(String(opt.city).toLowerCase().replace(/ \(alt\)$/i, ""))) || null;
  }
 
  function statusPill(status) {
    const meta = STATUS_META[status] || STATUS_META["Dispatch"];
    const pill = document.createElement("span");
    pill.className = `pill ${meta.cls || ""}`;
    pill.textContent = status || "Dispatch";
    const styles = {
      "Sales Lead": ["rgba(37,99,235,.10)", "rgba(37,99,235,.28)", "#1d4ed8"],
      "Dispatch": ["rgba(124,58,237,.10)", "rgba(124,58,237,.28)", "#6d28d9"],
      "Quote": ["rgba(239,68,68,.10)", "rgba(239,68,68,.25)", "#b91c1c"],
      "Quote Sent": ["rgba(236,72,153,.18)", "rgba(236,72,153,.34)", "#be185d"],
      "Parts on Order": ["rgba(139,94,60,.14)", "rgba(139,94,60,.34)", "#7c4a21"],
      "Complete/Quote": ["rgba(245,158,11,.12)", "rgba(245,158,11,.30)", "#b45309"],
      "Complete": ["rgba(34,197,94,.12)", "rgba(34,197,94,.30)", "#166534"],
      "Done": ["rgba(17,24,39,.04)", "rgba(17,24,39,.14)", "#4b5563"],
      "Approved": ["rgba(34,197,94,.12)", "rgba(34,197,94,.30)", "#166534"],
      "Denied": ["rgba(239,68,68,.10)", "rgba(239,68,68,.25)", "#b91c1c"],
      "Pending": ["rgba(245,158,11,.12)", "rgba(245,158,11,.30)", "#b45309"],
    };
    const [bg, border, color] = styles[status] || styles["Dispatch"];
    pill.style.background = bg;
    pill.style.border = `1px solid ${border}`;
    pill.style.color = color;
    return pill;
  }
 
  function dotEl(status) {
    const meta = STATUS_META[status] || STATUS_META["Dispatch"];
    const d = document.createElement("span");
    d.className = "dot";
    d.style.background = meta.dot || "#111827";
    return d;
  }
 
  function styleActionButton(btn, tone = "default", compact = false) {
    btn.className = "btn";
    btn.style.fontWeight = "1000";
    btn.style.borderRadius = compact ? "10px" : "12px";
    btn.style.padding = compact ? "7px 10px" : "10px 13px";
    btn.style.fontSize = compact ? "12px" : "14px";
    btn.style.lineHeight = "1.1";
    btn.style.whiteSpace = "nowrap";
    btn.style.borderWidth = "1px";
    btn.style.borderStyle = "solid";
    if (tone === "green") {
      btn.style.background = "rgba(34,197,94,.12)";
      btn.style.borderColor = "rgba(34,197,94,.35)";
      btn.style.color = "#166534";
    } else if (tone === "blue") {
      btn.style.background = "rgba(37,99,235,.10)";
      btn.style.borderColor = "rgba(37,99,235,.28)";
      btn.style.color = "#1d4ed8";
    } else if (tone === "ghost") {
      btn.style.background = "rgba(17,24,39,.04)";
      btn.style.borderColor = "rgba(17,24,39,.12)";
      btn.style.color = "#374151";
    } else if (tone === "danger") {
      btn.style.background = "rgba(239,68,68,.08)";
      btn.style.borderColor = "rgba(239,68,68,.24)";
      btn.style.color = "#b91c1c";
    } else {
      btn.style.background = "#fff";
      btn.style.borderColor = "var(--line)";
      btn.style.color = "var(--text)";
    }
    return btn;
  }
 
  function makeUploadLabel(text, tone = "ghost", compact = false) {
    const label = document.createElement("label");
    label.style.display = "inline-flex";
    label.style.alignItems = "center";
    label.style.justifyContent = "center";
    label.style.cursor = "pointer";
    styleActionButton(label, tone, compact);
    label.textContent = text;
    return label;
  }
 
  function openDrawer(titleText, renderFn) {
    document.querySelectorAll(".overlay").forEach(o => o.remove());
 
    const overlay = document.createElement("div");
    overlay.className = "overlay";
 
    const drawer = document.createElement("div");
    drawer.className = "drawer";
 
    const hd = document.createElement("div");
    hd.className = "drawer-hd";
 
    const title = document.createElement("div");
    title.className = "drawer-title";
    title.textContent = titleText;
 
    const close = document.createElement("button");
    close.className = "drawer-close";
    close.innerHTML = "&times;";
 
    hd.appendChild(title);
    hd.appendChild(close);
 
    const bd = document.createElement("div");
    bd.className = "drawer-bd";
 
    drawer.appendChild(hd);
    drawer.appendChild(bd);
    overlay.appendChild(drawer);
    document.body.appendChild(overlay);
 
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) overlay.remove();
    });
    close.addEventListener("click", () => overlay.remove());
 
    renderFn(bd, overlay);
    return overlay;
  }
 
  async function apiListJobs(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/calendar/jobs?${qs.toString()}`);
    return data.jobs || [];
  }
 
  async function apiListAllJobs(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/data/all-jobs?${qs.toString()}`);
    if (Array.isArray(data)) return data;
    return Array.isArray(data.jobs) ? data.jobs : [];
  }
 
  async function apiGetJob(jobId) {
    const data = await fetchJSON(`/calendar/jobs/${jobId}`);
    return data.job;
  }
 
  async function apiCreateJob(payload) {
    const data = await fetchJSON("/calendar/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.job;
  }
 
  async function apiUpdateJob(jobId, payload) {
    const data = await fetchJSON(`/calendar/jobs/${jobId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.job;
  }
 
  async function apiDeleteJob(jobId) {
    await fetchJSON(`/calendar/jobs/${jobId}`, { method: "DELETE" });
  }
 
  async function apiAddCompletion(jobId, payload) {
    const data = await fetchJSON(`/calendar/jobs/${jobId}/completion`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.form;
  }
 
  async function apiReplaceCompletionForms(jobId, completionForms) {
    const data = await fetchJSON(`/calendar/jobs/${jobId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ completion_forms: completionForms }),
    });
    return data.job;
  }
 
  async function apiUploadJobAttachments(jobId, files) {
    const formData = new FormData();
    Array.from(files || []).forEach(f => formData.append("files", f));
    const res = await fetch(`/calendar/jobs/${jobId}/attachments`, {
      method: "POST",
      credentials: "same-origin",
      body: formData,
    });
    const txt = await res.text();
    let data = null;
    try { data = JSON.parse(txt); } catch {}
    if (!res.ok) {
      const msg = (data && (data.detail || data.error)) ? (data.detail || data.error) : (txt || `HTTP ${res.status}`);
      if (res.status === 401) {
        currentUser = null;
        applyRoleAccess(null);
        updateLoginUi();
        showLoggedOutSplash("Session expired. Please log in again.");
      }
      throw new Error(msg);
    }
    return data.files || [];
  }
 
  async function apiUploadCompletionAttachments(jobId, formId, files) {
    const formData = new FormData();
    Array.from(files || []).forEach(f => formData.append("files", f));
    const res = await fetch(`/calendar/jobs/${jobId}/completion/${formId}/attachments`, {
      method: "POST",
      credentials: "same-origin",
      body: formData,
    });
    const txt = await res.text();
    let data = null;
    try { data = JSON.parse(txt); } catch {}
    if (!res.ok) {
      const msg = (data && (data.detail || data.error)) ? (data.detail || data.error) : (txt || `HTTP ${res.status}`);
      if (res.status === 401) {
        currentUser = null;
        applyRoleAccess(null);
        updateLoginUi();
        showLoggedOutSplash("Session expired. Please log in again.");
      }
      throw new Error(msg);
    }
    return data.files || [];
  }
 
  async function apiListEmployees() {
    const data = await fetchJSON("/employees");
    return data.items || [];
  }
 
  async function apiCreateEmployee(payload) {
    const data = await fetchJSON("/employees", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }
 
  async function apiDeleteEmployee(id) {
    await fetchJSON(`/employees/${id}`, { method: "DELETE" });
  }

  async function apiListAuthUsers() {
    const data = await fetchJSON("/auth/users");
    return data.items || [];
  }

  async function apiCreateAuthUser(payload) {
    const data = await fetchJSON("/auth/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }

  async function apiUpdateAuthUser(userId, payload) {
    const data = await fetchJSON(`/auth/users/${userId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }

  async function apiSetAuthUserPassword(userId, password) {
    const data = await fetchJSON(`/auth/users/${userId}/password`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    return data.item;
  }

  async function apiSetAuthUserPin(userId, pin) {
    const data = await fetchJSON(`/auth/users/${userId}/pin`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin }),
    });
    return data.item;
  }

  async function apiSetAuthUserActive(userId, active) {
    const data = await fetchJSON(`/auth/users/${userId}/active`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active }),
    });
    return data.item;
  }

  async function apiDeleteAuthUser(userId) {
    await fetchJSON(`/auth/users/${userId}`, { method: "DELETE" });
  }
 
  async function apiListCustomers() {
    const data = await fetchJSON("/crm/customers");
    return data.items || [];
  }
 
  async function apiCreateCustomer(payload) {
    const data = await fetchJSON("/crm/customers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }
 
  async function apiListContacts(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/crm/contacts?${qs.toString()}`);
    return data.items || [];
  }
 
  async function apiListParts(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/data/parts?${qs.toString()}`);
    return data.items || [];
  }

  async function apiSavePart(payload) {
    const body = {
      id: payload.id || "",
      manufacturer: payload.manufacturer || payload.Manufacturer || "",
      part_number: payload.part_number || payload.item || payload.Item || "",
      description: payload.description || payload.Description || "",
      price: payload.price ?? payload.Price ?? "",
    };
    const url = body.id ? `/data/parts/${encodeURIComponent(body.id)}` : "/data/parts";
    const method = body.id ? "PUT" : "POST";
    const data = await fetchJSON(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return data.item || data;
  }

  async function apiDeletePart(id) {
    await fetchJSON(`/data/parts/${encodeURIComponent(id)}`, { method: "DELETE" });
  }

  async function apiCreateSignoff(payload) {
    const data = await fetchJSON("/documents/signoff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data;
  }
 
  async function apiCreateContact(payload) {
    const data = await fetchJSON("/crm/contacts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }
 
  async function apiCreateEstimate(payload) {
    const data = await fetchJSON("/documents/estimate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data;
  }
 
  async function apiCreateInvoice(payload) {
    const data = await fetchJSON("/documents/invoice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data;
  }
 
  async function apiListDocuments(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/documents?${qs.toString()}`);
    return data.items || [];
  }
 
  async function apiUpdateDocument(filename, payload) {
    const data = await fetchJSON(`/documents/${encodeURIComponent(filename)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.doc || data;
  }
 
  async function apiDeleteDocument(filename) {
    await fetchJSON(`/documents/${encodeURIComponent(filename)}`, { method: "DELETE" });
  }
 
  async function apiListTimeOff(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/timeoff?${qs.toString()}`);
    return data.items || [];
  }
 
  async function apiCreateTimeOff(payload) {
    const data = await fetchJSON("/timeoff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item || data;
  }
 
  async function apiUpdateTimeOff(id, payload) {
    const data = await fetchJSON(`/timeoff/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item || data;
  }
 
  async function apiDeleteTimeOff(id) {
    await fetchJSON(`/timeoff/${id}`, { method: "DELETE" });
  }
 
  async function apiListTimecards(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/timecards?${qs.toString()}`);
    return data.items || [];
  }
 
  async function apiCreateTimecard(payload) {
    const data = await fetchJSON("/timecards", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item || data;
  }
 
  async function apiDeleteTimecard(itemId) {
    await fetchJSON(`/timecards/${itemId}`, { method: "DELETE" });
  }

  async function uploadAdminDataFile(file) {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/admin/upload-data-file", {
      method: "POST",
      credentials: "same-origin",
      body: form,
    });
    const text = await res.text();
    let data = {};
    try { data = JSON.parse(text); } catch {}
    if (!res.ok) {
      throw new Error(data.detail || text || "Upload failed");
    }
    return data;
  }


  const PTO_BANK_KEY = "doorks_pto_bank_v1";

  function getPtoBankMap() {
    try {
      const raw = localStorage.getItem(PTO_BANK_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }

  function setPtoBankHours(employee, hours) {
    const name = String(employee || "").trim();
    if (!name) return;
    const map = getPtoBankMap();
    map[name] = Number(hours || 0);
    localStorage.setItem(PTO_BANK_KEY, JSON.stringify(map));
  }

  function getPtoBankHours(employee) {
    const map = getPtoBankMap();
    return Number(map[String(employee || "").trim()] || 0);
  }

  const OT_BANK_KEY = "doorks_ot_bank_v1";

  function getOtBankMap() {
    try {
      const raw = localStorage.getItem(OT_BANK_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }

  function setOtBankHours(employee, hours) {
    const name = String(employee || "").trim();
    if (!name) return;
    const map = getOtBankMap();
    map[name] = Number(hours || 0);
    localStorage.setItem(OT_BANK_KEY, JSON.stringify(map));
  }

  function getOtBankHours(employee) {
    const map = getOtBankMap();
    return Number(map[String(employee || "").trim()] || 0);
  }

  const ROLLUP_PROFILE_KEY = "doorks_rollup_profile_v2";

  function getRollupProfileMap() {
    try {
      const raw = localStorage.getItem(ROLLUP_PROFILE_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }

  function normalizeRollupProfileRow(row) {
    const base = row && typeof row === "object" ? row : {};
    const history = base.history && typeof base.history === "object" ? base.history : {};
    return {
      wage: Number(base.wage || 0),
      multiplier: Number(base.multiplier || 0),
      history,
    };
  }

  function rollupMonthOf(dateValue) {
    const s = String(dateValue || "").trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s.slice(0, 7);
    if (/^\d{4}-\d{2}$/.test(s)) return s;
    if (/^\d{2}-\d{2}-\d{4}$/.test(s)) {
      const [m, d, y] = s.split("-");
      return `${y}-${m}`;
    }
    return monthKey(new Date());
  }

  function getRollupProfile(employee, effectiveMonth = monthKey(new Date())) {
    const map = getRollupProfileMap();
    const raw = normalizeRollupProfileRow(map[String(employee || "").trim()] || {});
    const months = Object.keys(raw.history || {}).sort();
    let applied = { wage: Number(raw.wage || 0), multiplier: Number(raw.multiplier || 0) };
    months.forEach(m => {
      if (m <= effectiveMonth) {
        const h = raw.history[m] || {};
        applied = {
          wage: Number(h.wage ?? applied.wage ?? 0),
          multiplier: Number(h.multiplier ?? applied.multiplier ?? 0),
        };
      }
    });
    return applied;
  }

  function setRollupProfile(employee, wage, multiplier, effectiveMonth = monthKey(new Date())) {
    const name = String(employee || "").trim();
    if (!name) return;
    const map = getRollupProfileMap();
    const row = normalizeRollupProfileRow(map[name] || {});
    row.wage = Number(wage || 0);
    row.multiplier = Number(multiplier || 0);
    row.history[effectiveMonth] = {
      wage: Number(wage || 0),
      multiplier: Number(multiplier || 0),
    };
    map[name] = row;
    localStorage.setItem(ROLLUP_PROFILE_KEY, JSON.stringify(map));
  }

  function getRollupProfileForDate(employee, dateValue) {
    return getRollupProfile(employee, rollupMonthOf(dateValue));
  }

  function ptoHoursFromItem(item) {
    const explicit = Number(item.pto_hours || 0);
    if (!Number.isNaN(explicit) && explicit > 0) return explicit;
    const hrs = Number(item.hours || 0);
    if (!Number.isNaN(hrs) && hrs > 0) return hrs;
    return 8;
  }

  function employeeNameOfItem(item) {
    return String(item.employee || item.employee_name || item.technician_name || "").trim();
  }

  function itemDateOf(item) {
    return item.date || item.start_date || item.created_at || "";
  }
 
  async function apiListForms() {
    const data = await fetchJSON("/forms");
    return data.forms || [];
  }
 
  async function downloadFile(url, filename) {
    const r = await fetch(url, { credentials: "same-origin" });
    if (!r.ok) throw new Error(`Download failed (${r.status})`);
    const blob = await r.blob();
    const u = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = u;
    a.download = filename || "document.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(u);
  }
 
  async function apiAuthMe() {
    const res = await fetch("/auth/me", { credentials: "same-origin" });
    const txt = await res.text();
    try { return JSON.parse(txt); } catch { return { logged_in: false, user: null }; }
  }

  async function apiLogin(username, password) {
    return fetchJSON("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
  }

  async function apiLoginPin(pin) {
    return fetchJSON("/auth/login-pin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin }),
    });
  }

  async function apiLogout() {
    return fetchJSON("/auth/logout", { method: "POST" });
  }

  async function apiListNotifications(params = {}) {
    const qs = new URLSearchParams(params);
    const data = await fetchJSON(`/notifications?${qs.toString()}`);
    return data.items || [];
  }

  async function apiCreateNotification(payload) {
    const data = await fetchJSON("/notifications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return data.item;
  }

  async function apiMarkNotificationRead(id, read = true) {
    const data = await fetchJSON(`/notifications/${id}/read`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ read }),
    });
    return data.item;
  }

  async function apiDeleteNotification(id) {
    await fetchJSON(`/notifications/${id}`, { method: "DELETE" });
  }

  async function apiNotificationRecipients() {
    const data = await fetchJSON("/notifications/recipients");
    return data.items || [];
  }

  function setVisible(node, show) {
    if (!node) return;
    node.style.display = show ? "" : "none";
  }

  function accessForRole(role) {
    const all = { calendar: true, forms: true, jobFlow: true, office: true, chat: true, notifications: true, atlas: true, moses: true, payroll: true, employees: true, dataCenter: true, customers: true, estimates: true, parts: true, saddleback: true, dataUpload: true };
    if (role === "office_admin") return all;
    if (role === "office") return { ...all, chat: false, atlas: false, moses: false, dataUpload: false };
    if (role === "lead") return { calendar: true, forms: true, jobFlow: true, office: true, chat: false, notifications: true, atlas: false, moses: false, payroll: false, employees: false, dataCenter: true, customers: true, estimates: true, parts: true, saddleback: false, dataUpload: false };
    if (role === "tech") return { calendar: true, forms: true, jobFlow: true, office: false, chat: false, notifications: true, atlas: false, moses: false, payroll: false, employees: false, dataCenter: false, customers: false, estimates: false, parts: false, saddleback: false, dataUpload: false };
    return { calendar: false, forms: false, jobFlow: false, office: false, chat: false, notifications: false, atlas: false, moses: false, payroll: false, employees: false, dataCenter: false, customers: false, estimates: false, parts: false, saddleback: false, dataUpload: false };
  }

  function applyRoleAccess(role) {
    const perms = accessForRole(role);
    setVisible(formsPanel, !!role && perms.forms);
    setVisible(jobFlowPanel, !!role && perms.jobFlow);
    setVisible(officeFlowPanel, !!role && perms.office);
    setVisible(chatPanel, !!role && perms.chat);
    setVisible(notificationsPanel, !!role && perms.notifications);
    if (headerCalendarBtn) headerCalendarBtn.style.display = role && perms.calendar ? "inline-flex" : "none";
    setVisible(navDataCenter, !!role && perms.dataCenter);
    setVisible(navPayroll, !!role && perms.payroll);
    setVisible(navEmployees, !!role && perms.employees);
    setVisible(navDataUpload, role === "office_admin" && !!perms.dataUpload);
    setVisible(navSaddleback, role === "office_admin" && !!perms.saddleback);
    setVisible(navAtlas, !!role && perms.atlas);
    setVisible(navMoses, !!role && perms.moses);
    setVisible(navCustomers, !!role && perms.customers);
    setVisible(navEstimateInvoice, !!role && perms.estimates);
    setVisible(navPartsList, !!role && perms.parts);
  }

  function updateLoginUi(message = "") {
    const loggedIn = !!currentUser;
    const awaitingPin = !loggedIn && !!pendingPinUser;
    if (usernameInput) usernameInput.disabled = loggedIn || awaitingPin;
    if (passwordInput) passwordInput.disabled = loggedIn || awaitingPin;
    if (pinInput) pinInput.disabled = loggedIn || !awaitingPin;
    if (pinStepWrap) pinStepWrap.style.display = awaitingPin ? "grid" : "none";
    if (loginBtn) {
      loginBtn.style.display = loggedIn || awaitingPin ? "none" : "inline-flex";
      loginBtn.textContent = "Next";
    }
    if (pinBtn) pinBtn.style.display = awaitingPin ? "inline-flex" : "none";
    if (logoutBtn) logoutBtn.style.display = loggedIn ? "inline-flex" : "none";
    if (loginStatus) {
      if (loggedIn) {
        loginStatus.textContent = `${currentUser.name || currentUser.username} • ${String(currentUser.role || "").replace(/_/g, " ")}`;
      } else if (awaitingPin) {
        loginStatus.textContent = message || "Enter your 4-digit PIN to continue.";
      } else {
        loginStatus.textContent = message || "Log in to access Doorks.";
      }
    }
  }

  function showLoggedOutSplash(message = "Log in to access Doorks.") {
    setActiveChip("Login");
    setWorkspace("Login");
    clearWorkspaceActions();
    workspaceBody.innerHTML = `<div class="card"><h3>Doorks Login</h3><div class="hint">${escapeHtml(message)}</div><div class="hint" style="margin-top:8px;">Use your seeded admin login to continue.</div></div>`;
    currentView = { refresh: async () => {} };
    if (loginBody) loginBody.style.display = "block";
  }

  async function handleLogin() {
    const username = usernameInput ? usernameInput.value.trim() : "";
    const password = passwordInput ? passwordInput.value : "";
    if (!username || !password) {
      updateLoginUi("Enter username and password.");
      return;
    }
    try {
      const data = await apiLogin(username, password);
      if (passwordInput) passwordInput.value = "";
      if (data && data.requires_pin) {
        pendingPinUser = data.user || { username };
        updateLoginUi("Username and password accepted. Enter your 4-digit PIN.");
        if (pinInput) {
          pinInput.value = "";
          pinInput.focus();
        }
        return;
      }
      pendingPinUser = null;
      currentUser = data.user || null;
      applyRoleAccess(currentUser ? currentUser.role : null);
      updateLoginUi();
      renderCalendarView();
      refreshBadges();
    } catch (e) {
      pendingPinUser = null;
      updateLoginUi(e.message || "Login failed.");
    }
  }

  async function handlePinLogin() {
    const pin = pinInput ? pinInput.value.trim() : "";
    if (!pin || pin.length !== 4) {
      updateLoginUi("Enter your 4-digit PIN.");
      return;
    }
    try {
      const data = await apiLoginPin(pin);
      pendingPinUser = null;
      currentUser = data.user || null;
      if (pinInput) pinInput.value = "";
      applyRoleAccess(currentUser ? currentUser.role : null);
      updateLoginUi();
      renderCalendarView();
      refreshBadges();
    } catch (e) {
      updateLoginUi(e.message || "PIN verification failed.");
    }
  }

  async function handleLogout() {
    try { await apiLogout(); } catch {}
    currentUser = null;
    pendingPinUser = null;
    if (pinInput) pinInput.value = "";
    applyRoleAccess(null);
    updateLoginUi("Logged out.");
    showLoggedOutSplash("Logged out.");
  }

  async function refreshBadges() {
    try {
      const items = await fetchJSON("/notifications").then(d => d.items || []);
      const unread = items.filter(x => !x.read && !x.is_mine).length;
      badgeNotifications.style.display = unread ? "inline-flex" : "none";
      badgeNotifications.textContent = String(unread);
 
      const statuses = ["Sales Lead", "Dispatch", "Quote", "Quote Sent", "Parts on Order", "Complete/Quote", "Complete"];
      let total = 0;
      for (const s of statuses) total += (await apiListJobs({ status: s, limit: 5000 })).length;
      badgeJobFlow.style.display = total ? "inline-flex" : "none";
      badgeJobFlow.textContent = String(total);
    } catch {}
  }
 
  function formsOf(job) {
    return Array.isArray(job.completion_forms) ? job.completion_forms : [];
  }
 
  function hasLeadRecommendation(job) {
    return formsOf(job).some(f => String(f.recommendations || "").trim().length > 0 || f.ready_to_quote === true);
  }
 
  function hasJobCompletion(job) {
    return formsOf(job).some(f =>
      String(f.tech_notes || "").trim().length > 0 ||
      String(f.parts_used || "").trim().length > 0 ||
      String(f.additional_recommendations || "").trim().length > 0 ||
      typeof f.time_onsite_hours === "number"
    );
  }
 
  function shouldShowEstimate(job) {
    if (job.kind === "sales_lead") return true;
    if (job.kind === "dispatch") {
      return ["Dispatch", "Quote", "Quote Sent", "Complete/Quote"].includes(String(job.status || ""));
    }
    return false;
  }
 
  function shouldShowInvoice(job) {
    if (job.kind !== "dispatch") return false;
    return ["Complete/Quote", "Complete", "Done"].includes(String(job.status || ""));
  }

  function cleanDocRef(value) {
    const s = String(value == null ? "" : value).replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
    if (!s) return "";
    const fixed = fixMojibake(s).replace(/[\u200B-\u200D\uFEFF]/g, "").trim();
    if (!fixed) return "";
    const normalized = fixed
      .replace(/\u00a0/g, " ")
      .replace(/[–—]/g, "-")
      .replace(/â€”|â€“/g, "-")
      .trim();
    if (!normalized) return "";
    if (/^(?:-|—|–|â€”|â€“|n\/a|na|none|null|undefined)*$/i.test(normalized)) return "";
    return normalized;
  }

  function formatDocRefDisplay(value) {
    return escapeHtml(cleanDocRef(value));
  }

  
function isApprovedEstimateJob(job, monthPrefix = "") {
    const estimateNumber = String(job?.estimate_number || "").trim();
    if (!estimateNumber) return false;
    const approvedStatuses = new Set(["Dispatch", "Parts on Order", "Complete/Quote", "Complete", "Done"]);
    const approvedAt = String(job?.approved_at || "");
    if (job?.approved === true) {
      if (!monthPrefix) return true;
      return approvedAt.startsWith(monthPrefix)
        || String(job?.updated_at || "").startsWith(monthPrefix)
        || String(job?.date || "").startsWith(monthPrefix);
    }
    if (!approvedStatuses.has(String(job?.status || ""))) return false;
    if (!monthPrefix) return true;
    return approvedAt.startsWith(monthPrefix)
      || String(job?.updated_at || "").startsWith(monthPrefix)
      || String(job?.date || "").startsWith(monthPrefix);
  }
 
  async function promptDispatchStatus() {
    return new Promise((resolve) => {
      openDrawer("Select New Job Status", (bd, overlay) => {
        const card = document.createElement("div");
        card.className = "card";
 
        const label = document.createElement("div");
        label.className = "label";
        label.textContent = "Select the updated job status before opening the completion form";
        card.appendChild(label);
 
        const wrap = document.createElement("div");
        wrap.className = "navcol";
        wrap.style.marginTop = "10px";
 
        JOB_STATUS_OPTIONS.forEach(status => {
          const b = document.createElement("button");
          b.className = "navbtn";
          b.innerHTML = `<span>${status}</span>`;
          b.addEventListener("click", () => {
            overlay.remove();
            resolve(status);
          });
          wrap.appendChild(b);
        });
 
        const cancel = document.createElement("button");
        cancel.className = "btn";
        cancel.style.marginTop = "12px";
        cancel.textContent = "Cancel";
        cancel.addEventListener("click", () => {
          overlay.remove();
          resolve(null);
        });
 
        card.appendChild(wrap);
        card.appendChild(cancel);
        bd.appendChild(card);
      });
    });
  }
 
  function buildCustomerDatalist(id, customers) {
    const dl = document.createElement("datalist");
    dl.id = id;
    customers.forEach(c => {
      const o = document.createElement("option");
      o.value = c.company_name || "";
      dl.appendChild(o);
    });
    return dl;
  }
 
  function buildContactDatalist(id, contacts) {
    const dl = document.createElement("datalist");
    dl.id = id;
    contacts.forEach(c => {
      const o = document.createElement("option");
      o.value = c.name || "";
      dl.appendChild(o);
    });
    return dl;
  }
 
  function normalizeText(v) {
    return String(v || "").trim().toLowerCase();
  }
 
  function pickContactPhone(contact) {
    return contact?.phone_number || contact?.cell_phone || "";
  }
 
  function companyMatches(contactCompany, selectedCompany) {
    const a = normalizeText(contactCompany);
    const b = normalizeText(selectedCompany);
    if (!a || !b) return false;
    return a === b || a.includes(b) || b.includes(a);
  }
 
  function findMatchingContact(contacts, name, companyName = "") {
    const n = normalizeText(name);
    if (!n) return null;
    const company = normalizeText(companyName);
    const byName = contacts.filter(c => {
      const cn = normalizeText(c.name);
      return cn === n || cn.includes(n) || n.includes(cn);
    });
    if (!byName.length) return null;
    return byName.find(c => company && companyMatches(c.company_name, company)) || byName[0] || null;
  }
 
  function wireContactAutofill({ contacts, contactInput, phoneInput, emailInput, customerInput, contactListId }) {
    if (!contactInput) return;
    const source = Array.isArray(contacts) ? contacts : [];
    const dl = contactListId ? document.getElementById(contactListId) : null;
 
    const filteredContacts = () => {
      const company = normalizeText(customerInput ? customerInput.value : "");
      return company ? source.filter(c => companyMatches(c.company_name, company)) : source;
    };
 
    const renderOptions = () => {
      if (!dl) return;
      dl.innerHTML = "";
      filteredContacts().forEach(c => {
        const o = document.createElement("option");
        o.value = c.name || "";
        o.label = c.company_name ? `${c.name || ""}  -  ${c.company_name}` : (c.name || "");
        dl.appendChild(o);
      });
    };
 
    const applyFromContact = (force = false) => {
      const match = findMatchingContact(filteredContacts(), contactInput.value, customerInput ? customerInput.value : "");
      if (!match) return;
      if (phoneInput && (force || !String(phoneInput.value || "").trim())) phoneInput.value = pickContactPhone(match) || "";
      if (emailInput && (force || !String(emailInput.value || "").trim())) emailInput.value = match.email || "";
      if (customerInput && !customerInput.value.trim() && match.company_name) customerInput.value = match.company_name;
    };
 
    const onCustomerChange = () => {
      renderOptions();
      const match = findMatchingContact(filteredContacts(), contactInput.value, customerInput ? customerInput.value : "");
      if (!match) {
        contactInput.value = "";
        if (phoneInput) phoneInput.value = "";
        if (emailInput) emailInput.value = "";
      } else {
        applyFromContact(true);
      }
    };
 
    renderOptions();
    ["change", "blur"].forEach(evt => contactInput.addEventListener(evt, () => applyFromContact(true)));
    if (customerInput) ["change", "blur", "input"].forEach(evt => customerInput.addEventListener(evt, onCustomerChange));
  }
 
  function uid(prefix = "id") {
    return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
  }
 
  function buildAddressDatalist(id, addresses) {
    const dl = document.createElement("datalist");
    dl.id = id;
    Array.from(new Set((addresses || []).map(v => String(v || "").trim()).filter(Boolean))).slice(0, 500).forEach(addr => {
      const o = document.createElement("option");
      o.value = addr;
      dl.appendChild(o);
    });
    return dl;
  }
 
  function wireGoogleAddressAutocomplete(input) {
    return false;
  }
 
  function wireAddressSuggestions(input, addresses = []) {
    if (!input) return;
    if (wireGoogleAddressAutocomplete(input)) return;
 
    const listId = uid("addrlist");
    input.setAttribute("list", listId);
    const dl = buildAddressDatalist(listId, addresses);
    if (input.parentElement) input.parentElement.appendChild(dl);
 
    const retryBind = () => {
      if (wireGoogleAddressAutocomplete(input)) {
        input.removeEventListener("focus", retryBind);
        input.removeEventListener("click", retryBind);
        window.removeEventListener("doorks:google-ready", retryBind);
      }
    };
 
    input.addEventListener("focus", retryBind);
    input.addEventListener("click", retryBind);
    window.addEventListener("doorks:google-ready", retryBind);
    setTimeout(retryBind, 1200);
    setTimeout(retryBind, 2500);
    setTimeout(retryBind, 5000);
  }
 
  function collectJobTechSummary(job) {
    const forms = formsOf(job);
    const rollupForms = forms.filter(f => String(f.door_type || "").toLowerCase() === "roll up");
    const source = rollupForms.length ? rollupForms : forms;
    const out = [];
    if (!source.length) return out;
    const techNames = Array.from(new Set(source.map(f => String(f.technician_name || "").trim()).filter(Boolean)));
    const totalHours = source.reduce((sum, f) => sum + Number(f.time_onsite_hours || 0), 0);
    if (rollupForms.length) out.push("Roll Up");
    if (techNames.length) out.push(`Tech: ${techNames.join(", ")}`);
    if (totalHours > 0) out.push(`${Number(totalHours).toFixed(2)} hrs`);
    return out;
  }
 
  function getTaxableSubtotal(items) {
    return (items || []).reduce((sum, item) => {
      if (item.taxable === false) return sum;
      return sum + (Number(item.qty || 0) * Number(item.rate || 0));
    }, 0);
  }
 
  function formatDocNumber(prefix, num) {
    return `${prefix}${String(Math.max(1, Number(num || 1))).padStart(5, "0")}`;
  }
 
  function nextDocNumberFromStorage(kind) {
    const key = kind === "estimate" ? "doorks_estimate_next" : "doorks_invoice_next";
    const prefix = kind === "estimate" ? "RE" : "JS";
    const cur = Number(localStorage.getItem(key) || "1");
    localStorage.setItem(key, String(cur + 1));
    return formatDocNumber(prefix, cur);
  }
 
  function formatBytes(bytes) {
    const n = Number(bytes || 0);
    if (!Number.isFinite(n) || n <= 0) return "0 B";
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  }
 
  function formatStamp(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  }
 
  function fixMojibake(v) {
    return String(v || "")
      .replace(/Ã¢â‚¬â€/g, "â€”")
      .replace(/Ã¢â‚¬â€œ/g, "â€“")
      .replace(/Ã¢â‚¬Ëœ/g, "â€˜")
      .replace(/Ã¢â‚¬â„¢/g, "â€™")
      .replace(/Ã¢â‚¬Å“/g, "â€œ")
      .replace(/Ã¢â‚¬Â/g, "â€")
      .replace(/Ã‚/g, "")
      .replace(/Â /g, " ");
  }
 
  function escapeHtml(v) {
    return fixMojibake(v).replace(/[&<>"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[ch] || ch));
  }
 
  function isImageFilename(name) {
    return /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(String(name || ""));
  }
 
  function buildJobAttachmentUrl(jobId, filename) {
    return `/calendar/jobs/${encodeURIComponent(jobId)}/attachments/${encodeURIComponent(filename || "")}`;
  }
 
  function buildCompletionAttachmentUrl(jobId, formId, filename) {
    return `/calendar/jobs/${encodeURIComponent(jobId)}/completion/${encodeURIComponent(formId)}/attachments/${encodeURIComponent(filename || "")}`;
  }
 
  function openImagePreview(title, url) {
    openDrawer(title || "Preview", async (drawerBody) => {
      const img = document.createElement("img");
      img.src = url;
      img.alt = title || "Preview";
      img.style.maxWidth = "100%";
      img.style.borderRadius = "12px";
      drawerBody.appendChild(img);
    });
  }
 
  function renderAttachmentSection(titleText, items, options = {}) {
    const wrap = document.createElement("div");
    wrap.style.marginTop = "10px";
 
    const title = document.createElement("div");
    title.className = "label";
    title.textContent = titleText;
    wrap.appendChild(title);
 
    const list = Array.isArray(items) ? items : [];
    if (!list.length) {
      const empty = document.createElement("div");
      empty.className = "hint";
      empty.textContent = "No attachments uploaded yet.";
      empty.style.marginTop = "6px";
      wrap.appendChild(empty);
      return wrap;
    }
 
    const box = document.createElement("div");
    box.style.display = "grid";
    box.style.gap = "8px";
    box.style.marginTop = "8px";
 
    list.forEach(file => {
      const filename = file.filename || "Attachment";
      const url = typeof options.urlBuilder === "function" ? options.urlBuilder(file) : "";
      const row = document.createElement("div");
      row.className = "jobrow";
 
      const top = document.createElement("div");
      top.className = "jobrow-top";
      const name = document.createElement("div");
      name.className = "jobrow-name";
      name.textContent = filename;
      const meta = document.createElement("div");
      meta.className = "hint";
      meta.textContent = formatBytes(file.bytes || 0);
      top.appendChild(name);
      top.appendChild(meta);
 
      const stamp = document.createElement("div");
      stamp.className = "jobrow-addr";
      stamp.textContent = formatStamp(file.created_at) || "Saved";
 
      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";
      actions.style.marginTop = "8px";
      actions.style.flexWrap = "wrap";
 
      if (url) {
        if (isImageFilename(filename)) {
          const viewBtn = document.createElement("button");
          styleActionButton(viewBtn, "blue", true);
          viewBtn.textContent = "Open";
          viewBtn.addEventListener("click", () => openImagePreview(filename, `${url}${url.includes("?") ? "&" : "?"}inline=1`));
          actions.appendChild(viewBtn);
        } else {
          const openLink = document.createElement("a");
          openLink.href = `${url}${url.includes("?") ? "&" : "?"}inline=1`;
          openLink.target = "_blank";
          openLink.rel = "noopener noreferrer";
          openLink.textContent = "Open";
          openLink.className = "btn";
          styleActionButton(openLink, "blue", true);
          actions.appendChild(openLink);
        }
      }
 
      row.appendChild(top);
      row.appendChild(stamp);
      if (actions.childNodes.length) row.appendChild(actions);
      box.appendChild(row);
    });
 
    wrap.appendChild(box);
    return wrap;
  }
 
  function openEditSavedForm(job, formIndex, container, ctx) {
    const f = formsOf(job)[formIndex];
    if (!f) return;
 
    const isSalesLead = job.kind === "sales_lead";
    let employeesPromise = apiListEmployees().catch(() => []);
 
    openDrawer(`Edit ${isSalesLead ? "Recommendation" : "Completion"} Form`, async (drawerBody, overlay) => {
      const employees = await employeesPromise;
 
      const card = document.createElement("div");
      card.className = "card";
 
      let stSel = null;
      if (!isSalesLead) {
        const statusWrap = document.createElement("div");
        statusWrap.innerHTML = `<div class="label">Status</div>`;
        stSel = document.createElement("select");
        stSel.className = "input";
        JOB_STATUS_OPTIONS.forEach(s => {
          const opt = document.createElement("option");
          opt.value = s;
          opt.textContent = s;
          stSel.appendChild(opt);
        });
        stSel.value = f.status_update || "Dispatch";
        statusWrap.appendChild(stSel);
        card.appendChild(statusWrap);
      }
 
      const techRow = document.createElement("div");
      techRow.className = "grid2";
      techRow.style.marginTop = "10px";
      techRow.innerHTML = `
        <div><div class="label">Technician Name</div><select class="input" id="ef_tech"></select></div>
        <div><div class="label">Door Type</div><select class="input" id="ef_door_type"></select></div>
      `;
 
      const techSel = techRow.querySelector("#ef_tech");
      const empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "-- Select Technician --";
      techSel.appendChild(empty);
      employees.forEach(e => {
        const opt = document.createElement("option");
        opt.value = e.name;
        opt.textContent = e.name;
        techSel.appendChild(opt);
      });
      techSel.value = f.technician_name || "";
 
      const doorSel = techRow.querySelector("#ef_door_type");
      const doorBlank = document.createElement("option");
      doorBlank.value = "";
      doorBlank.textContent = "-- Select Door Type --";
      doorSel.appendChild(doorBlank);
      DOOR_TYPES.forEach(t => {
        const opt = document.createElement("option");
        opt.value = t;
        opt.textContent = t;
        doorSel.appendChild(opt);
      });
      doorSel.value = f.door_type || "";
 
      const locRow = document.createElement("div");
      locRow.style.marginTop = "10px";
      locRow.innerHTML = `
        <div class="label">Door Location</div>
        <input class="input" id="ef_door_loc" />
      `;
      locRow.querySelector("#ef_door_loc").value = f.door_location || "";
 
      card.appendChild(techRow);
      card.appendChild(locRow);
 
      let techNotes = null;
      let partsUsed = null;
      let addRecs = null;
      let timeInput = null;
      let recs = null;
      let partsReq = null;
      let timeReq = null;
      let ready = null;
 
      if (isSalesLead) {
        const block = document.createElement("div");
        block.style.marginTop = "10px";
        block.innerHTML = `
          <div class="label">Recommendations</div>
          <textarea id="ef_recs"></textarea>
          <div class="grid2" style="margin-top:10px;">
            <div><div class="label">Parts Required</div><textarea id="ef_parts_req"></textarea></div>
            <div><div class="label">Time Required</div><input class="input" id="ef_time_req" /></div>
          </div>
          <label style="display:flex; align-items:center; gap:8px; margin-top:12px; font-weight:1000;">
            <input type="checkbox" id="ef_ready" /> Ready to Quote
          </label>
        `;
        recs = block.querySelector("#ef_recs");
        partsReq = block.querySelector("#ef_parts_req");
        timeReq = block.querySelector("#ef_time_req");
        ready = block.querySelector("#ef_ready");
 
        recs.value = f.recommendations || "";
        partsReq.value = f.parts_required || "";
        timeReq.value = f.time_required || "";
        ready.checked = !!f.ready_to_quote;
 
        card.appendChild(block);
      } else {
        const block = document.createElement("div");
        block.style.marginTop = "10px";
        block.innerHTML = `
          <div><div class="label">Time Onsite (hours)</div><input class="input" id="ef_time" type="number" step="0.5" min="0" /></div>
          <div style="margin-top:10px;"><div class="label">Tech Notes</div><textarea id="ef_tech_notes"></textarea></div>
          <div class="grid2" style="margin-top:10px;">
            <div><div class="label">Parts Used</div><textarea id="ef_parts"></textarea></div>
            <div><div class="label">Additional Recommendations</div><textarea id="ef_add_recs"></textarea></div>
          </div>
        `;
        timeInput = block.querySelector("#ef_time");
        techNotes = block.querySelector("#ef_tech_notes");
        partsUsed = block.querySelector("#ef_parts");
        addRecs = block.querySelector("#ef_add_recs");
 
        timeInput.value = typeof f.time_onsite_hours === "number" ? String(f.time_onsite_hours) : "";
        techNotes.value = f.tech_notes || "";
        partsUsed.value = f.parts_used || "";
        addRecs.value = f.additional_recommendations || "";
 
        card.appendChild(block);
      }
 
      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";
      actions.style.marginTop = "12px";
 
      const save = document.createElement("button");
      save.className = "btn btn-orange";
      save.textContent = "Save Changes";
 
      const cancel = document.createElement("button");
      cancel.className = "btn";
      cancel.textContent = "Cancel";
 
      const del = document.createElement("button");
      del.className = "btn";
      del.textContent = "Delete Form";
      del.style.borderColor = "#fecaca";
      del.style.color = "#b91c1c";
 
      actions.appendChild(save);
      actions.appendChild(cancel);
      actions.appendChild(del);
      card.appendChild(actions);
 
      drawerBody.appendChild(card);
 
      cancel.addEventListener("click", () => overlay.remove());
 
      del.addEventListener("click", async () => {
        if (!confirm("Delete this saved form?")) return;
        try {
          const updatedForms = [...formsOf(job)];
          updatedForms.splice(formIndex, 1);
          const updatedJob = await apiReplaceCompletionForms(job.id, updatedForms);
          overlay.remove();
          if (ctx && ctx.afterSave) await ctx.afterSave();
          renderJobDetails(container, updatedJob, ctx);
          refreshBadges();
        } catch (e) {
          alert(e.message || String(e));
        }
      });
 
      save.addEventListener("click", async () => {
        try {
          const updatedForms = [...formsOf(job)];
          const next = { ...updatedForms[formIndex] };
 
          next.technician_name = techSel.value;
          if (!doorSel.value.trim()) { alert("Door type is required"); return; }
          next.door_type = doorSel.value;
          next.door_location = locRow.querySelector("#ef_door_loc").value.trim();
 
          if (!doorSel.value) throw new Error("Door type is required.");

          if (stSel && stSel.value === "Parts on Order") {
            const supplier = prompt("Supplier:", job.parts_order?.supplier || "") || "";
            const poNumber = prompt("PO #:", job.parts_order?.po_number || job.po_number || "") || "";
            const orderDate = prompt("Order Date (YYYY-MM-DD):", job.parts_order?.order_date || "") || "";
            const etaDate = prompt("Expected Arrival Date (YYYY-MM-DD):", job.parts_order?.expected_arrival_date || "") || "";
            const notesVal = prompt("Notes:", job.parts_order?.notes || "") || "";
            payload.parts_order = { supplier, po_number: poNumber, order_date: orderDate, expected_arrival_date: etaDate, notes: notesVal };
          }

          if (isSalesLead) {
            next.recommendations = recs.value.trim();
            next.parts_required = partsReq.value.trim();
            next.time_required = timeReq.value.trim();
            next.ready_to_quote = !!ready.checked;
          } else {
            next.status_update = stSel ? stSel.value : next.status_update;
            next.time_onsite_hours = timeInput.value.trim() === "" ? null : Number(timeInput.value.trim());
            next.tech_notes = techNotes.value.trim();
            next.parts_used = partsUsed.value.trim();
            next.additional_recommendations = addRecs.value.trim();
          }
 
          updatedForms[formIndex] = next;
          const updatedJob = await apiReplaceCompletionForms(job.id, updatedForms);
 
          overlay.remove();
          if (ctx && ctx.afterSave) await ctx.afterSave();
          renderJobDetails(container, updatedJob, ctx);
        } catch (e) {
          alert(e.message || String(e));
        }
      });
    });
  }
 
  function renderDocumentsSection(job) {
    const wrap = document.createElement("div");
    wrap.style.marginTop = "10px";
 
    const title = document.createElement("div");
    title.className = "label";
    title.textContent = "Saved Estimate / Invoice Documents";
    wrap.appendChild(title);
 
    const loading = document.createElement("div");
    loading.className = "hint";
    loading.style.marginTop = "6px";
    loading.textContent = "Loading documents...";
    wrap.appendChild(loading);
 
    apiListDocuments({ job_id: job.id }).then(items => {
      wrap.innerHTML = "";
      wrap.appendChild(title);
      if (!items.length) {
        const empty = document.createElement("div");
        empty.className = "hint";
        empty.style.marginTop = "6px";
        empty.textContent = "No saved estimate/invoice documents yet.";
        wrap.appendChild(empty);
        return;
      }
      const box = document.createElement("div");
      box.style.display = "grid";
      box.style.gap = "8px";
      box.style.marginTop = "8px";
      items.forEach(doc => {
        const row = document.createElement("div");
        row.className = "jobrow";
        const top = document.createElement("div");
        top.className = "jobrow-top";
        const name = document.createElement("div");
        name.className = "jobrow-name";
        name.textContent = `${doc.type === "invoice" ? "Invoice" : "Estimate"} ${doc.number || ""}`.trim();
        top.appendChild(name);
        if (doc.type) top.appendChild(statusPill(doc.type === "invoice" ? "Done" : "Quote Sent"));
        const sub = document.createElement("div");
        sub.className = "jobrow-addr";
        sub.textContent = [doc.customer || "", formatStamp(doc.created_at || "")].filter(Boolean).join(" - ");
        const actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "8px";
        actions.style.marginTop = "8px";
        const openLink = document.createElement("a");
        openLink.href = doc.download_url || "#";
        openLink.target = "_blank";
        openLink.rel = "noopener noreferrer";
        openLink.textContent = "Open PDF";
        styleActionButton(openLink, "blue", true);
        actions.appendChild(openLink);
        row.appendChild(top);
        row.appendChild(sub);
        row.appendChild(actions);
        box.appendChild(row);
      });
      wrap.appendChild(box);
    }).catch(() => {
      loading.textContent = "Unable to load saved documents.";
    });
 
    return wrap;
  }
 
  function renderSavedForms(job, container, ctx) {
    const wrap = document.createElement("div");
    wrap.className = "form-summary";
 
    const title = document.createElement("div");
    title.className = "label";
    title.textContent = "Saved Forms";
    wrap.appendChild(title);
 
    const forms = formsOf(job);
    if (!forms.length) {
      const empty = document.createElement("div");
      empty.className = "hint";
      empty.textContent = "No saved completion/recommendation forms yet.";
      wrap.appendChild(empty);
      return wrap;
    }
 
    forms.forEach((f, idx) => {
      const item = document.createElement("div");
      item.className = "form-summary-item";
 
      const top = document.createElement("div");
      top.className = "jobrow-top";
 
      const left = document.createElement("div");
      left.className = "jobrow-name";
      left.textContent = `${job.kind === "sales_lead" ? "Recommendation" : "Completion"} Form #${idx + 1}`;
 
      top.appendChild(left);
      if (f.status_update) top.appendChild(statusPill(f.status_update));
 
      const body = document.createElement("div");
      body.className = "jobrow-addr";
      body.style.whiteSpace = "pre-wrap";
 
      const lines = [];
      if (f.technician_name) lines.push(`Tech: ${f.technician_name}`);
      if (f.door_type) lines.push(`Door Type: ${f.door_type}`);
      if (f.door_location) lines.push(`Door Location: ${f.door_location}`);
      if (typeof f.time_onsite_hours === "number") lines.push(`Time: ${f.time_onsite_hours} hrs`);
      if (f.tech_notes) lines.push(`Tech Notes: ${f.tech_notes}`);
      if (f.recommendations) lines.push(`Recommendations: ${f.recommendations}`);
      if (f.parts_used) lines.push(`Parts Used: ${f.parts_used}`);
      if (f.parts_required) lines.push(`Parts Required: ${f.parts_required}`);
      if (f.additional_recommendations) lines.push(`Additional Recommendations: ${f.additional_recommendations}`);
      if (f.time_required) lines.push(`Time Required: ${f.time_required}`);
      if (f.ready_to_quote) lines.push(`Ready to Quote: Yes`);
      body.textContent = lines.join("\n");
 
      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";
      actions.style.marginTop = "8px";
      actions.style.flexWrap = "wrap";
 
      const editBtn = document.createElement("button");
      editBtn.className = "btn";
      editBtn.textContent = "Edit Form";
      editBtn.addEventListener("click", () => openEditSavedForm(job, idx, container, ctx));
 
      const uploadLabel = makeUploadLabel("Upload", "ghost", false);
      const uploadInput = document.createElement("input");
      uploadInput.type = "file";
      uploadInput.multiple = true;
      uploadInput.style.display = "none";
      uploadLabel.appendChild(uploadInput);
      uploadInput.addEventListener("change", async () => {
        try {
          if (!uploadInput.files || !uploadInput.files.length) return;
          await apiUploadCompletionAttachments(job.id, f.id, uploadInput.files);
          const updatedJob = await apiGetJob(job.id);
          if (ctx && ctx.afterSave) await ctx.afterSave();
          renderJobDetails(container, updatedJob, ctx);
          refreshBadges();
        } catch (e) {
          alert(e.message || String(e));
        } finally {
          uploadInput.value = "";
        }
      });
 
      actions.appendChild(editBtn);
      actions.appendChild(uploadLabel);
 
      item.appendChild(top);
      item.appendChild(body);
      item.appendChild(actions);
      item.appendChild(renderAttachmentSection("Form Attachments", f.attachments || [], {
        urlBuilder: (file) => buildCompletionAttachmentUrl(job.id, f.id, file.filename),
      }));
      wrap.appendChild(item);
    });
 
    return wrap;
  }
 
  function renderJobDetails(container, job, ctx) {
    container.innerHTML = "";
 
    const card = document.createElement("div");
    card.className = "card";
 
    const header = document.createElement("div");
    header.style.display = "flex";
    header.style.justifyContent = "space-between";
    header.style.alignItems = "center";
    header.style.gap = "10px";
 
    const left = document.createElement("div");
    const idLabel = job.kind === "sales_lead" ? "Sales Lead #" : "Job #";
    left.innerHTML = `
      <h3 style="margin:0;">${job.customer || `${idLabel}${job.job_number || ""}`}</h3>
      <div class="hint" style="margin-top:4px;"><b>${idLabel}${job.job_number || ""}</b> - ${mmDdYy(job.date)}</div>
    `;
 
    const right = document.createElement("div");
    right.appendChild(statusPill(job.status));
 
    header.appendChild(left);
    header.appendChild(right);
 
    const fields = document.createElement("div");
    fields.className = "grid2";
    fields.style.marginTop = "10px";
    fields.innerHTML = `
      <div><div class="label">${job.kind === "sales_lead" ? "Sales Lead #" : "Job #"}</div><div class="field">${job.job_number || ""}</div></div>
      <div><div class="label">Address</div><div class="field">${job.address || ""}</div></div>
      <div><div class="label">Contact</div><div class="field">${job.contact || ""}</div></div>
      <div><div class="label">Phone</div><div class="field">${job.phone || ""}</div></div>
      <div><div class="label">Email</div><div class="field">${job.email || ""}</div></div>
      <div><div class="label">PO #</div><div class="field">${job.po_number || ""}</div></div>
      <div><div class="label">Estimate #</div><div class="field">${job.estimate_number || ""}</div></div>
      <div><div class="label">Invoice #</div><div class="field">${job.invoice_number || ""}</div></div>
    `;
 
    const officeNotes = document.createElement("div");
    officeNotes.style.marginTop = "10px";
    officeNotes.innerHTML = `<div class="label">Office Notes</div><div class="field" style="white-space:pre-wrap;">${job.office_notes || ""}</div>`;
 
    const notes = document.createElement("div");
    notes.style.marginTop = "10px";
    notes.innerHTML = `<div class="label">Job Notes</div><div class="field" style="white-space:pre-wrap;">${job.job_notes || ""}</div>`;
 
    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.flexDirection = "column";
    actions.style.alignItems = "flex-start";
    actions.style.gap = "8px";
    actions.style.marginTop = "12px";
 
    const primaryActions = document.createElement("div");
    primaryActions.style.display = "flex";
    primaryActions.style.gap = "8px";
    primaryActions.style.flexWrap = "wrap";
 
    const secondaryActions = document.createElement("div");
    secondaryActions.style.display = "flex";
    secondaryActions.style.gap = "8px";
    secondaryActions.style.flexWrap = "wrap";
 
    const btnEdit = document.createElement("button");
    btnEdit.className = "btn btn-orange";
    btnEdit.textContent = "Edit";
    primaryActions.appendChild(btnEdit);
 
    const btnForm = document.createElement("button");
    styleActionButton(btnForm, "green", false);
    btnForm.textContent = (job.kind === "sales_lead") ? "Recommendation Form" : "Completion Form";
    primaryActions.appendChild(btnForm);
 
    const jobUploadLabel = makeUploadLabel("Upload", "blue", true);
    const jobUploadInput = document.createElement("input");
    jobUploadInput.type = "file";
    jobUploadInput.multiple = true;
    jobUploadInput.style.display = "none";
    jobUploadLabel.appendChild(jobUploadInput);
    jobUploadInput.addEventListener("change", async () => {
      try {
        if (!jobUploadInput.files || !jobUploadInput.files.length) return;
        await apiUploadJobAttachments(job.id, jobUploadInput.files);
        const updatedJob = await apiGetJob(job.id);
        if (ctx && ctx.afterSave) await ctx.afterSave();
        renderJobDetails(container, updatedJob, ctx);
        refreshBadges();
      } catch (e) {
        alert(e.message || String(e));
      } finally {
        jobUploadInput.value = "";
      }
    });
    secondaryActions.appendChild(jobUploadLabel);
 
    if (job.kind === "sales_lead") {
      const btnTurnToJob = document.createElement("button");
      btnTurnToJob.className = "btn";
      btnTurnToJob.textContent = "Turn to Job";
      btnTurnToJob.addEventListener("click", async () => {
        try {
          const updated = await apiUpdateJob(job.id, {
            kind: "dispatch",
            status: "Dispatch"
          });
          renderJobDetails(container, updated, ctx);
          if (ctx && ctx.afterSave) await ctx.afterSave();
          refreshBadges();
        } catch (e) {
          alert(e.message || String(e));
        }
      });
      primaryActions.appendChild(btnTurnToJob);

      if (String(job.status || "") === "Quote Sent") {
        const btnPartsOnOrder = document.createElement("button");
        btnPartsOnOrder.className = "btn";
        btnPartsOnOrder.textContent = "Parts on Order";
        btnPartsOnOrder.addEventListener("click", async () => {
          try {
            const updated = await apiUpdateJob(job.id, {
              kind: "dispatch",
              status: "Parts on Order"
            });
            renderJobDetails(container, updated, ctx);
            if (ctx && ctx.afterSave) await ctx.afterSave();
            refreshBadges();
          } catch (e) {
            alert(e.message || String(e));
          }
        });
        primaryActions.appendChild(btnPartsOnOrder);
      }
    }
 
    if (shouldShowEstimate(job)) {
      const b = document.createElement("button");
      styleActionButton(b, "blue", true);
      b.textContent = "Estimate";
      b.addEventListener("click", () => openEstimateDrawer(job, container, ctx));
      secondaryActions.appendChild(b);
    }
 
    if (shouldShowInvoice(job)) {
      const b = document.createElement("button");
      styleActionButton(b, "blue", true);
      b.textContent = "Invoice";
      b.addEventListener("click", () => openInvoiceDrawer(job, container, ctx));
      secondaryActions.appendChild(b);
    }
 
    actions.appendChild(primaryActions);
    if (secondaryActions.childNodes.length) actions.appendChild(secondaryActions);
 
    card.appendChild(header);
    card.appendChild(fields);
    card.appendChild(officeNotes);
    if (job.parts_order && Object.values(job.parts_order).some(v => String(v || "").trim())) {
      const poCard = document.createElement("div");
      poCard.style.marginTop = "10px";
      poCard.innerHTML = `<div class="label">Parts on Order</div><div class="field" style="white-space:pre-wrap;">Supplier: ${job.parts_order.supplier || ""}
PO #: ${job.parts_order.po_number || ""}
Order Date: ${job.parts_order.order_date || ""}
Expected Arrival: ${job.parts_order.expected_arrival_date || ""}
Notes: ${job.parts_order.notes || ""}</div>`;
      card.appendChild(poCard);
    }
    card.appendChild(notes);
    card.appendChild(actions);
    card.appendChild(renderAttachmentSection(job.kind === "sales_lead" ? "Lead Attachments" : "Job Attachments", job.attachments || [], {
      urlBuilder: (file) => buildJobAttachmentUrl(job.id, file.filename),
    }));
    card.appendChild(renderDocumentsSection(job));
    card.appendChild(renderSavedForms(job, container, ctx));
 
    container.appendChild(card);
 
    btnEdit.addEventListener("click", () => openEditJob(job, container, ctx));
    btnForm.addEventListener("click", async () => {
      if (job.kind === "dispatch") {
        const nextStatus = await promptDispatchStatus();
        if (!nextStatus) return;
        const updated = await apiUpdateJob(job.id, { status: nextStatus });
        renderJobDetails(container, updated, ctx);
        await openCompletionOrRecommendation(updated, container, ctx);
      } else {
        await openCompletionOrRecommendation(job, container, ctx);
      }
    });
  }
 
  function openEditJob(job, container, ctx) {
    openDrawer("Edit Job", async (drawerBody, overlay) => {
      const customers = await apiListCustomers().catch(() => []);
      const contacts = await apiListContacts().catch(() => []);
 
      const customerListId = `cust-${Math.random().toString(36).slice(2)}`;
      const contactListId = `cont-${Math.random().toString(36).slice(2)}`;
 
      drawerBody.innerHTML = "";
      const card = document.createElement("div");
      card.className = "card";
 
      const row0 = document.createElement("div");
      row0.className = "grid2";
      row0.innerHTML = `
        <div><div class="label">Status</div><select class="input" id="ej_status"></select></div>
        <div><div class="label">Date</div><input class="input" id="ej_date" type="date" /></div>
      `;
 
      const stSel = row0.querySelector("#ej_status");
      STATUSES.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s;
        opt.textContent = s;
        stSel.appendChild(opt);
      });
      stSel.value = job.status || (job.kind === "sales_lead" ? "Sales Lead" : "Dispatch");
      row0.querySelector("#ej_date").value = job.date;
 
      const rowJob = document.createElement("div");
      rowJob.className = "grid2";
      rowJob.innerHTML = `
        <div><div class="label">${job.kind === "sales_lead" ? "Sales Lead #" : "Job #"}</div><input class="input" id="ej_job_number" /></div>
        <div><div class="label">Customer</div><input class="input" id="ej_customer" list="${customerListId}" /></div>
      `;
      rowJob.querySelector("#ej_job_number").value = job.job_number || "";
      rowJob.querySelector("#ej_customer").value = job.customer || "";
 
      const row1 = document.createElement("div");
      row1.className = "grid2";
      row1.innerHTML = `
        <div><div class="label">Address</div><input class="input" id="ej_address" /></div>
        <div><div class="label">Contact</div><input class="input" id="ej_contact" list="${contactListId}" /></div>
      `;
      row1.querySelector("#ej_address").value = job.address || "";
      row1.querySelector("#ej_contact").value = job.contact || "";
 
      const row2 = document.createElement("div");
      row2.className = "grid2";
      row2.innerHTML = `
        <div><div class="label">Phone</div><input class="input" id="ej_phone" /></div>
        <div><div class="label">Email</div><input class="input" id="ej_email" /></div>
      `;
      row2.querySelector("#ej_phone").value = job.phone || "";
      row2.querySelector("#ej_email").value = job.email || "";
 
      const row3 = document.createElement("div");
      row3.className = "grid2";
      row3.innerHTML = `
        <div><div class="label">PO #</div><input class="input" id="ej_po" /></div>
        <div><div class="label">Estimate #</div><input class="input" id="ej_est" /></div>
      `;
      row3.querySelector("#ej_po").value = job.po_number || "";
      row3.querySelector("#ej_est").value = job.estimate_number || "";
 
      const row4 = document.createElement("div");
      row4.className = "grid2";
      row4.innerHTML = `
        <div><div class="label">Invoice #</div><input class="input" id="ej_inv" /></div>
        <div><div class="label">Office Notes</div><input class="input" id="ej_office_notes" /></div>
      `;
      row4.querySelector("#ej_inv").value = job.invoice_number || "";
      row4.querySelector("#ej_office_notes").value = job.office_notes || "";
 
      const notes = document.createElement("div");
      notes.innerHTML = `<div class="label">Job Notes</div>`;
      const ta = document.createElement("textarea");
      ta.value = job.job_notes || "";
      notes.appendChild(ta);
 
      const addWrap = document.createElement("div");
      addWrap.className = "grid2";
      addWrap.style.marginTop = "12px";
      addWrap.innerHTML = `
        <div><button class="btn" id="ej_add_customer">Add Customer</button></div>
        <div><button class="btn" id="ej_add_contact">Add Contact</button></div>
      `;
 
      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";
      actions.style.marginTop = "10px";
      actions.style.flexWrap = "wrap";
 
      const btnSave = document.createElement("button");
      btnSave.className = "btn btn-orange";
      btnSave.textContent = "Save";
 
      const btnCancel = document.createElement("button");
      btnCancel.className = "btn";
      btnCancel.textContent = "Cancel";
 
      const btnDelete = document.createElement("button");
      btnDelete.className = "btn";
      btnDelete.textContent = "Delete";
      btnDelete.style.borderColor = "#fecaca";
      btnDelete.style.color = "#b91c1c";
 
      actions.appendChild(btnSave);
      actions.appendChild(btnCancel);
      actions.appendChild(btnDelete);
 
      card.appendChild(buildCustomerDatalist(customerListId, customers));
      card.appendChild(buildContactDatalist(contactListId, contacts));
      const editCustomerInput = rowJob.querySelector("#ej_customer");
      const editContactInput = row1.querySelector("#ej_contact");
      const editPhoneInput = row2.querySelector("#ej_phone");
      const editEmailInput = row2.querySelector("#ej_email");
      const editContactList = card.querySelector(`#${contactListId}`);
      let editLiveContacts = Array.isArray(contacts) ? [...contacts] : [];
      const renderEditContacts = () => {
        if (!editContactList) return;
        editContactList.innerHTML = editLiveContacts.map(c => `<option value="${escapeHtml(c.name || "")}" label="${escapeHtml(c.company_name ? `${c.name || ""}  -  ${c.company_name}` : (c.name || ""))}"></option>`).join("");
      };
      const refreshEditContacts = async (forceClear = false) => {
        const company = editCustomerInput.value.trim();
        const loaded = await apiListContacts(company ? { company_name: company } : {}).catch(() => contacts);
        editLiveContacts = Array.isArray(loaded) ? loaded : [];
        renderEditContacts();
        const exact = editLiveContacts.find(c => normalizeText(c.name) === normalizeText(editContactInput.value));
        if (!exact && (forceClear || company)) {
          editContactInput.value = "";
          editPhoneInput.value = "";
          editEmailInput.value = "";
        }
      };
      wireContactAutofill({
        contacts: editLiveContacts,
        customerInput: editCustomerInput,
        contactInput: editContactInput,
        phoneInput: editPhoneInput,
        emailInput: editEmailInput,
        contactListId,
      });
      ["change", "blur"].forEach(evt => editCustomerInput.addEventListener(evt, () => refreshEditContacts(true)));
      let editContactTimer = null;
      editCustomerInput.addEventListener("input", () => {
        clearTimeout(editContactTimer);
        editContactTimer = setTimeout(() => refreshEditContacts(false), 150);
      });
      refreshEditContacts(false);
      card.appendChild(row0);
      card.appendChild(rowJob);
      card.appendChild(row1);
      card.appendChild(row2);
      card.appendChild(row3);
      card.appendChild(row4);
      card.appendChild(notes);
      card.appendChild(addWrap);
      card.appendChild(actions);
      drawerBody.appendChild(card);
 
      addWrap.querySelector("#ej_add_customer").addEventListener("click", async () => {
        const name = prompt("New customer company name:");
        if (!name) return;
        try {
          await apiCreateCustomer({ company_name: name.trim() });
          alert("Customer added.");
        } catch (e) {
          alert(e.message || String(e));
        }
      });
 
      addWrap.querySelector("#ej_add_contact").addEventListener("click", async () => {
        const name = prompt("Contact name:");
        if (!name) return;
        try {
          await apiCreateContact({
            name: name.trim(),
            company_name: rowJob.querySelector("#ej_customer").value.trim(),
            phone_number: row2.querySelector("#ej_phone").value.trim(),
            email: row2.querySelector("#ej_email").value.trim(),
          });
          alert("Contact added.");
        } catch (e) {
          alert(e.message || String(e));
        }
      });
 
      btnCancel.addEventListener("click", () => overlay.remove());
 
      btnSave.addEventListener("click", async () => {
        try {
          const payload = {
            status: stSel.value,
            date: row0.querySelector("#ej_date").value,
            job_number: rowJob.querySelector("#ej_job_number").value.trim(),
            customer: rowJob.querySelector("#ej_customer").value.trim(),
            address: row1.querySelector("#ej_address").value.trim(),
            contact: row1.querySelector("#ej_contact").value.trim(),
            phone: row2.querySelector("#ej_phone").value.trim(),
            email: row2.querySelector("#ej_email").value.trim(),
            po_number: row3.querySelector("#ej_po").value.trim(),
            estimate_number: row3.querySelector("#ej_est").value.trim(),
            invoice_number: row4.querySelector("#ej_inv").value.trim(),
            office_notes: row4.querySelector("#ej_office_notes").value.trim(),
            job_notes: ta.value.trim(),
          };
          const updated = await apiUpdateJob(job.id, payload);
          overlay.remove();
          if (ctx && ctx.afterSave) await ctx.afterSave();
          renderJobDetails(container, updated, ctx);
          refreshBadges();
        } catch (e) {
          alert(e.message || String(e));
        }
      });
 
      btnDelete.addEventListener("click", async () => {
        if (!confirm("Delete this job?")) return;
        try {
          await apiDeleteJob(job.id);
          overlay.remove();
          if (ctx && ctx.afterDelete) await ctx.afterDelete();
          container.innerHTML = `<div class="hint">Job deleted.</div>`;
          refreshBadges();
        } catch (e) {
          alert(e.message || String(e));
        }
      });
    });
  }
 
  async function openCompletionOrRecommendation(job, container, ctx) {
    const isSalesLead = job.kind === "sales_lead";
    let employees = [];
    try { employees = await apiListEmployees(); } catch { employees = []; }
 
    openDrawer(isSalesLead ? "Recommendation Form" : "Completion Form", async (drawerBody, overlay) => {
      drawerBody.innerHTML = "";
      const card = document.createElement("div");
      card.className = "card";
 
      let stSel = null;
      if (!isSalesLead) {
        const statusWrap = document.createElement("div");
        statusWrap.innerHTML = `<div class="label">Status</div>`;
        stSel = document.createElement("select");
        stSel.className = "input";
        JOB_STATUS_OPTIONS.forEach(s => {
          const opt = document.createElement("option");
          opt.value = s;
          opt.textContent = s;
          stSel.appendChild(opt);
        });
        stSel.value = job.status || "Dispatch";
        statusWrap.appendChild(stSel);
        card.appendChild(statusWrap);
      }
 
      const techRow = document.createElement("div");
      techRow.className = "grid2";
      techRow.style.marginTop = "10px";
      techRow.innerHTML = `
        <div><div class="label">Technician Name</div><select class="input" id="cf_tech"></select></div>
        <div><div class="label">Door Type</div><select class="input" id="cf_door_type"></select></div>
      `;
 
      const techSel = techRow.querySelector("#cf_tech");
      const opt0 = document.createElement("option");
      opt0.value = "";
      opt0.textContent = "-- Select Technician --";
      techSel.appendChild(opt0);
      employees.forEach(e => {
        const opt = document.createElement("option");
        opt.value = e.name;
        opt.textContent = e.name;
        techSel.appendChild(opt);
      });
 
      const doorSel = techRow.querySelector("#cf_door_type");
      const doorBlank = document.createElement("option");
      doorBlank.value = "";
      doorBlank.textContent = "-- Select Door Type --";
      doorSel.appendChild(doorBlank);
      DOOR_TYPES.forEach(t => {
        const opt = document.createElement("option");
        opt.value = t;
        opt.textContent = t;
        doorSel.appendChild(opt);
      });
      doorSel.value = "";
 
      const locRow = document.createElement("div");
      locRow.style.marginTop = "10px";
      locRow.innerHTML = `
        <div class="label">Door Location</div>
        <input class="input" id="cf_door_loc" placeholder="e.g., Front Entry / Back Roll-Up" />
      `;
 
      card.appendChild(techRow);
      card.appendChild(locRow);
 
      if (isSalesLead) {
        const leadBlock = document.createElement("div");
        leadBlock.style.marginTop = "10px";
        leadBlock.innerHTML = `
          <div class="label">Recommendations</div>
          <textarea id="cf_lead_recs" placeholder="Recommendations"></textarea>
          <div class="grid2" style="margin-top:10px;">
            <div><div class="label">Parts Required</div><textarea id="cf_lead_parts" placeholder="Parts required"></textarea></div>
            <div><div class="label">Time Required</div><input class="input" id="cf_lead_time" placeholder="e.g., 2 hours, 1 trip, etc." /></div>
          </div>
          <label style="display:flex; align-items:center; gap:8px; margin-top:12px; font-weight:1000;">
            <input type="checkbox" id="cf_ready" /> Ready to Quote
          </label>
        `;
        card.appendChild(leadBlock);
      } else {
        const timeRow = document.createElement("div");
        timeRow.style.marginTop = "10px";
        timeRow.innerHTML = `
          <div class="label">Time Onsite (hours)</div>
          <input class="input" id="cf_time" type="number" step="0.5" min="0" placeholder="e.g., 1.5" />
          <div class="hint">Enter hours billed in 0.5 increments.</div>
        `;
 
        const techNotes = document.createElement("div");
        techNotes.style.marginTop = "10px";
        techNotes.innerHTML = `<div class="label">Tech Notes</div><textarea id="cf_tech_notes"></textarea>`;
 
        const partsRecs = document.createElement("div");
        partsRecs.className = "grid2";
        partsRecs.style.marginTop = "10px";
        partsRecs.innerHTML = `
          <div><div class="label">Parts Used</div><textarea id="cf_parts" placeholder="Parts used"></textarea></div>
          <div><div class="label">Additional Recommendations</div><textarea id="cf_add_recs" placeholder="Additional recommendations"></textarea></div>
        `;
 
        card.appendChild(timeRow);
        card.appendChild(techNotes);
        card.appendChild(partsRecs);
      }
 
      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";
      actions.style.marginTop = "10px";
 
      const btnSave = document.createElement("button");
      btnSave.className = "btn btn-orange";
      btnSave.textContent = "Save Form";
 
      const btnClose = document.createElement("button");
      btnClose.className = "btn";
      btnClose.textContent = "Close";
 
      actions.appendChild(btnSave);
      actions.appendChild(btnClose);
      card.appendChild(actions);
 
      drawerBody.appendChild(card);
 
      btnClose.addEventListener("click", () => overlay.remove());
 
      btnSave.addEventListener("click", async () => {
        try {
          if (!doorSel.value.trim()) { alert("Door type is required"); return; }
          const payload = {
            technician_name: techSel.value,
            door_type: doorSel.value,
            door_location: locRow.querySelector("#cf_door_loc").value.trim(),
          };
 
          if (isSalesLead) {
            payload.recommendations = card.querySelector("#cf_lead_recs").value.trim();
            payload.parts_required = card.querySelector("#cf_lead_parts").value.trim();
            payload.time_required = card.querySelector("#cf_lead_time").value.trim();
            payload.ready_to_quote = !!card.querySelector("#cf_ready").checked;
          } else {
            payload.status_update = stSel ? stSel.value : job.status;
            const v = card.querySelector("#cf_time").value.trim();
            if (v !== "") payload.time_onsite_hours = Number(v);
            payload.tech_notes = card.querySelector("#cf_tech_notes").value.trim();
            payload.parts_used = card.querySelector("#cf_parts").value.trim();
            payload.additional_recommendations = card.querySelector("#cf_add_recs").value.trim();
          }
 
          await apiAddCompletion(job.id, payload);
 
          overlay.remove();
          const updatedJob = await apiGetJob(job.id);
          if (ctx && ctx.afterSave) await ctx.afterSave();
          renderJobDetails(container, updatedJob, ctx);
          refreshBadges();
        } catch (e) {
          alert(e.message || String(e));
        }
      });
    });
  }
 
  function calcTimeHours(startTime, endTime, lunchTaken, lunchStart, lunchEnd) {
    if (!startTime || !endTime) return 0;
    const toMin = (t) => {
      const [h, m] = String(t).split(":").map(Number);
      return h * 60 + m;
    };
    let total = toMin(endTime) - toMin(startTime);
    if (total < 0) total = 0;
 
    if (lunchTaken && lunchStart && lunchEnd) {
      const lunch = toMin(lunchEnd) - toMin(lunchStart);
      if (lunch > 0) total -= lunch;
    }
    if (total < 0) total = 0;
    return +(total / 60).toFixed(2);
  }
 
  function renderCalendarView() {
    setNavActive(null);
    setActiveChip("Calendar");
    setWorkspace("Calendar");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const top = document.createElement("div");
    top.className = "calendar-top";
 
    const left = document.createElement("div");
    left.className = "cal-left";
 
    const btnPrev = document.createElement("button");
    btnPrev.className = "iconbtn";
    btnPrev.innerHTML = "&larr;";
 
    const btnNext = document.createElement("button");
    btnNext.className = "iconbtn";
    btnNext.innerHTML = "&rarr;";
 
    const label = document.createElement("div");
    label.className = "cal-month";
    left.style.display = "flex";
    left.style.alignItems = "center";
    left.style.gap = "14px";
    left.style.flex = "1";
    left.style.justifyContent = "center";
    label.style.flex = "0 0 auto";
    label.style.minWidth = "220px";
    label.style.textAlign = "center";
 
    left.appendChild(btnPrev);
    left.appendChild(label);
    left.appendChild(btnNext);
 
    const btnNew = document.createElement("button");
    btnNew.className = "btn btn-orange";
    btnNew.textContent = "New Dispatch";
 
    top.appendChild(left);
    top.appendChild(btnNew);
 
    const grid = document.createElement("div");
    grid.className = "cal-grid";
 
    root.appendChild(top);
    root.appendChild(grid);
 
    let cur = new Date();
    cur.setDate(1);
 
    async function refresh() {
      label.textContent = monthLabel(cur);
      grid.innerHTML = "";
 
      for (const d of DAYS) {
        const h = document.createElement("div");
        h.className = "cal-dow";
        h.textContent = d;
        grid.appendChild(h);
      }
 
      const start = new Date(cur);
      start.setDate(start.getDate() - start.getDay());
 
      const end = new Date(cur);
      end.setMonth(end.getMonth() + 1);
      end.setDate(0);
      end.setDate(end.getDate() + (6 - end.getDay()));
 
      const jobs = await apiListJobs({ limit: 5000 });
      const byDate = {};
      for (const j of jobs) {
        const dt = j.date;
        if (!byDate[dt]) byDate[dt] = [];
        byDate[dt].push(j);
      }
 
      const day = new Date(start);
      while (day <= end) {
        const cell = document.createElement("div");
        cell.className = "cal-cell";
 
        const inMonth = day.getMonth() === cur.getMonth();
        if (!inMonth) cell.classList.add("cal-cell-muted");
 
        const dayNum = document.createElement("div");
        dayNum.className = "cal-daynum";
        dayNum.textContent = String(day.getDate());
 
        const items = document.createElement("div");
        items.className = "cal-items";
 
        const dt = yyyyMmDd(day);
        const dayJobs = (byDate[dt] || []).slice();
 
        dayJobs.slice(0, 5).forEach(j => {
          const it = document.createElement("div");
          it.className = "cal-item";
          it.appendChild(dotEl(j.status));
 
          const txt = document.createElement("span");
          txt.textContent = j.customer || (j.kind === "sales_lead" ? `Sales Lead ${j.job_number}` : j.job_number);
          it.appendChild(txt);
 
          items.appendChild(it);
        });
 
        cell.appendChild(dayNum);
        cell.appendChild(items);
 
        cell.addEventListener("click", () => openDailySchedule(dt, dayJobs));
        grid.appendChild(cell);
        day.setDate(day.getDate() + 1);
      }
 
      refreshBadges();
    }
 
    function openDailySchedule(dateStr, preloadedJobs = null) {
      openDrawer(`Daily Schedule (${mmDdYy(dateStr)})`, async (container) => {
        let jobs = preloadedJobs;
        if (!jobs) jobs = await apiListJobs({ date: dateStr, limit: 2000 });
 
        if (!jobs.length) {
          container.innerHTML = `<div class="hint">No jobs scheduled for this day.</div>`;
          return;
        }
 
        container.innerHTML = "";
        jobs.forEach(j => {
          const row = document.createElement("div");
          row.className = "jobrow";
 
          const top = document.createElement("div");
          top.className = "jobrow-top";
 
          const name = document.createElement("div");
          name.className = "jobrow-name";
          name.textContent = j.customer || (j.kind === "sales_lead" ? `Sales Lead ${j.job_number}` : j.job_number);
 
          top.appendChild(name);
          top.appendChild(statusPill(j.status));
 
          const addr = document.createElement("div");
          addr.className = "jobrow-addr";
          addr.textContent = j.address || "";
 
          row.appendChild(top);
          row.appendChild(addr);
 
          row.addEventListener("click", async () => {
            const full = await apiGetJob(j.id);
            renderJobDetails(container, full, { afterSave: refresh, afterDelete: refresh });
          });
 
          container.appendChild(row);
        });
      });
    }
 
    async function openNewDispatch(defaultDate) {
      const customers = await apiListCustomers().catch(() => []);
      const contacts = await apiListContacts().catch(() => []);
 
      openDrawer("New Dispatch", (container, overlay) => {
        const customerListId = `cust-${Math.random().toString(36).slice(2)}`;
        const contactListId = `cont-${Math.random().toString(36).slice(2)}`;
 
        container.innerHTML = "";
        const card = document.createElement("div");
        card.className = "card";
 
        const row0 = document.createElement("div");
        row0.className = "grid2";
        row0.innerHTML = `
          <div><div class="label">Status</div><select class="input" id="nj_status"></select></div>
          <div><div class="label">Date</div><input class="input" id="nj_date" type="date" /></div>
        `;
 
        const stSel = row0.querySelector("#nj_status");
        ["Dispatch", "Sales Lead"].forEach(s => {
          const opt = document.createElement("option");
          opt.value = s;
          opt.textContent = s;
          stSel.appendChild(opt);
        });
        stSel.value = "Dispatch";
 
        const row1 = document.createElement("div");
        row1.className = "grid2";
        row1.innerHTML = `
          <div><div class="label">Customer</div><input class="input" id="nj_customer" list="${customerListId}" placeholder="Customer name" /></div>
          <div><div class="label">Street Address</div><input class="input" id="nj_address" name="dispatch_street_address" placeholder="Start typing address" autocomplete="off" autocapitalize="off" spellcheck="false" data-lpignore="true" data-1p-ignore="true" /></div>
        `;
 
        const row1b = document.createElement("div");
        row1b.style.display = "grid";
        row1b.style.gridTemplateColumns = "1.4fr .6fr .7fr";
        row1b.style.gap = "10px";
        row1b.innerHTML = `
          <div><div class="label">City</div><input class="input" id="nj_city" name="dispatch_city" placeholder="City" autocomplete="off" autocapitalize="words" spellcheck="false" data-lpignore="true" data-1p-ignore="true" /></div>
          <div><div class="label">State</div><input class="input" id="nj_state" name="dispatch_state" placeholder="State" maxlength="2" autocomplete="off" autocapitalize="characters" spellcheck="false" data-lpignore="true" data-1p-ignore="true" /></div>
          <div><div class="label">ZIP</div><input class="input" id="nj_zip" name="dispatch_zip" placeholder="ZIP" autocomplete="off" inputmode="numeric" spellcheck="false" data-lpignore="true" data-1p-ignore="true" /></div>
        `;
 
        const row2 = document.createElement("div");
        row2.className = "grid2";
        row2.innerHTML = `
          <div><div class="label">Contact</div><input class="input" id="nj_contact" list="${contactListId}" placeholder="Contact name" /></div>
          <div><div class="label">Phone</div><input class="input" id="nj_phone" placeholder="Phone" /></div>
        `;
 
        const row3 = document.createElement("div");
        row3.className = "grid2";
        row3.innerHTML = `
          <div><div class="label">Email</div><input class="input" id="nj_email" placeholder="Email" /></div>
          <div><div class="label">Office Notes</div><input class="input" id="nj_office_notes" placeholder="Office notes" /></div>
        `;
 
        const row4 = document.createElement("div");
        row4.className = "grid2";
        row4.innerHTML = `
          <div><div class="label">Job / Lead #</div><input class="input" id="nj_job_number" placeholder="Leave blank for next number" /></div>
          <div><div class="label">PO #</div><input class="input" id="nj_po" placeholder="PO #" /></div>
          <div><div class="label">Estimate #</div><input class="input" id="nj_est" placeholder="Estimate #" /></div>
          <div><div class="label">Invoice #</div><input class="input" id="nj_inv" placeholder="Invoice #" /></div>
          <div><div class="label">Upload</div><input class="input" id="nj_files" type="file" multiple /></div>
        `;
 
        const notes = document.createElement("div");
        notes.innerHTML = `<div class="label">Job Notes</div>`;
        const ta = document.createElement("textarea");
        notes.appendChild(ta);
 
        const addWrap = document.createElement("div");
        addWrap.className = "hint";
        addWrap.style.marginTop = "12px";
        addWrap.textContent = "Add customers and contacts in the Customers and Contacts sections.";
 
        const actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "8px";
        actions.style.marginTop = "10px";
 
        const btnSave = document.createElement("button");
        btnSave.className = "btn btn-orange";
        btnSave.textContent = "Save";
 
        const btnCancel = document.createElement("button");
        btnCancel.className = "btn";
        btnCancel.textContent = "Cancel";
 
        actions.appendChild(btnSave);
        actions.appendChild(btnCancel);
 
        card.appendChild(buildCustomerDatalist(customerListId, customers));
        card.appendChild(buildContactDatalist(contactListId, contacts));
        const newJobCustomerInput = row1.querySelector("#nj_customer");
        const newJobContactInput = row2.querySelector("#nj_contact");
        const newJobPhoneInput = row2.querySelector("#nj_phone");
        const newJobEmailInput = row3.querySelector("#nj_email");
        const newJobContactList = card.querySelector(`#${contactListId}`);
        const findSelectedCustomer = () => {
          const selected = normalizeText(newJobCustomerInput.value);
          return customers.find(c => normalizeText(c.company_name) === selected) || null;
        };
        let liveContacts = Array.isArray(contacts) ? [...contacts] : [];
        const renderNewJobContacts = () => {
          if (!newJobContactList) return;
          newJobContactList.innerHTML = liveContacts.map(c => `<option value="${escapeHtml(c.name || "")}" label="${escapeHtml(c.company_name ? `${c.name || ""}  -  ${c.company_name}` : (c.name || ""))}"></option>`).join("");
        };
        const refreshNewJobContacts = async (forceClear = false) => {
          const selectedCustomer = findSelectedCustomer();
          const company = newJobCustomerInput.value.trim();
          const params = selectedCustomer && selectedCustomer.id ? { customer_id: selectedCustomer.id } : (company ? { company_name: company } : {});
          const loaded = await apiListContacts(params).catch(() => contacts);
          liveContacts.splice(0, liveContacts.length, ...(Array.isArray(loaded) ? loaded : []));
          renderNewJobContacts();
          const exact = liveContacts.find(c => normalizeText(c.name) === normalizeText(newJobContactInput.value));
          if (!exact && (forceClear || company)) {
            newJobContactInput.value = "";
            newJobPhoneInput.value = "";
            newJobEmailInput.value = "";
          }
        };
        wireContactAutofill({
          contacts: liveContacts,
          customerInput: newJobCustomerInput,
          contactInput: newJobContactInput,
          phoneInput: newJobPhoneInput,
          emailInput: newJobEmailInput,
          contactListId,
        });
        ["change", "blur"].forEach(evt => newJobCustomerInput.addEventListener(evt, () => refreshNewJobContacts(true)));
        let newJobContactTimer = null;
        newJobCustomerInput.addEventListener("input", () => {
          clearTimeout(newJobContactTimer);
          newJobContactTimer = setTimeout(() => refreshNewJobContacts(false), 150);
        });
        refreshNewJobContacts(false);
        const existingAddresses = customers.map(c => c.address || c.site_address || c.job_address || "").filter(Boolean);
        const addressInput = row1.querySelector("#nj_address");
        const cityInput = row1b.querySelector("#nj_city");
        const stateInput = row1b.querySelector("#nj_state");
        const zipInput = row1b.querySelector("#nj_zip");
        wireAddressSuggestions(addressInput, existingAddresses);
        addressInput.addEventListener("doorks:address-selected", (ev) => {
          const d = (ev && ev.detail) || {};
          if (d.formatted_address) addressInput.value = d.formatted_address;
          if (cityInput) cityInput.value = d.city || cityInput.value || "";
          if (stateInput) stateInput.value = d.state || stateInput.value || "";
          if (zipInput) zipInput.value = d.zip || zipInput.value || "";
        });
        card.appendChild(row0);
        card.appendChild(row1);
        card.appendChild(row1b);
        card.appendChild(row2);
        card.appendChild(row3);
        card.appendChild(row4);
        card.appendChild(notes);
        card.appendChild(addWrap);
        card.appendChild(actions);
 
        container.appendChild(card);
 
        row0.querySelector("#nj_date").value = defaultDate;
 
        btnCancel.addEventListener("click", () => overlay.remove());
 
        btnSave.addEventListener("click", async () => {
          try {
            const status = stSel.value;
            const payload = {
              kind: status === "Sales Lead" ? "sales_lead" : "dispatch",
              date: row0.querySelector("#nj_date").value,
              status,
              customer: row1.querySelector("#nj_customer").value.trim(),
              address: [
                row1.querySelector("#nj_address").value.trim(),
                row1b.querySelector("#nj_city").value.trim(),
                row1b.querySelector("#nj_state").value.trim(),
                row1b.querySelector("#nj_zip").value.trim(),
              ].filter(Boolean).join(", "),
              city: row1b.querySelector("#nj_city").value.trim(),
              state: row1b.querySelector("#nj_state").value.trim(),
              zip: row1b.querySelector("#nj_zip").value.trim(),
              contact: row2.querySelector("#nj_contact").value.trim(),
              phone: row2.querySelector("#nj_phone").value.trim(),
              email: row3.querySelector("#nj_email").value.trim(),
              office_notes: row3.querySelector("#nj_office_notes").value.trim(),
              job_number: row4.querySelector("#nj_job_number").value.trim(),
              po_number: row4.querySelector("#nj_po").value.trim(),
              estimate_number: row4.querySelector("#nj_est").value.trim(),
              invoice_number: row4.querySelector("#nj_inv").value.trim(),
              job_notes: ta.value.trim(),
            };
            const created = await apiCreateJob(payload);
            const files = row4.querySelector("#nj_files").files;
            if (created && created.id && files && files.length) {
              await apiUploadJobAttachments(created.id, files);
            }
            overlay.remove();
            await refresh();
          } catch (e) {
            alert(e.message || String(e));
          }
        });
      });
    }
 
    btnPrev.addEventListener("click", async () => {
      cur.setMonth(cur.getMonth() - 1);
      await refresh();
    });
 
    btnNext.addEventListener("click", async () => {
      cur.setMonth(cur.getMonth() + 1);
      await refresh();
    });
 
    btnNew.addEventListener("click", () => openNewDispatch(yyyyMmDd(new Date())));
 
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    currentView = { refresh };
    refresh();
  }
 
  function renderJobFlowView(initialStatus = "Dispatch", standalone = false) {
    setNavActive(initialStatus === "__ALL__" ? navAllJobs : navJobFlow);
    setActiveChip("Work Flow");
    setWorkspace(initialStatus === "__ALL__" ? "All Jobs" : "Job Flow");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const tabsRow = document.createElement("div");
    tabsRow.style.display = "flex";
    tabsRow.style.gap = "8px";
    tabsRow.style.flexWrap = "wrap";
    tabsRow.style.marginBottom = "10px";
 
    const tabDefs = [
      { name: "Sales Lead", status: "Sales Lead" },
      { name: "Dispatch", status: "Dispatch" },
      { name: "Quote", status: "Quote" },
      { name: "Quote Sent", status: "Quote Sent" },
      { name: "Parts on Order", status: "Parts on Order" },
      { name: "Complete/Quote", status: "Complete/Quote" },
      { name: "Complete", status: "Complete" },
    ];
 
    let active = initialStatus;
    let allJobsQuery = "";
    const list = document.createElement("div");
    const searchWrap = document.createElement("div");
    searchWrap.style.display = "none";
    searchWrap.style.gap = "8px";
    searchWrap.style.marginBottom = "10px";
    searchWrap.style.alignItems = "center";
    searchWrap.innerHTML = `<input class="input" id="all_jobs_search" placeholder="Search by customer, contact, address, job #, estimate #, invoice #, or PO #" /><button class="btn" id="all_jobs_refresh">Search</button>`;
 
    function openAnyJobCard(job) {
      if (!job) return;
      const sourceLabel = String(job.source || "").toUpperCase();
      if ((sourceLabel && sourceLabel !== "CURRENT") || !job.id) {
        openDrawer(`Legacy Job ${job.job_number || "Details"}`, async (drawerBody) => {
          const card = document.createElement("div");
          card.className = "card";
          card.innerHTML = `
            <h3 style="margin:0;">${escapeHtml(job.customer || job.customer_name || "Legacy Job")}</h3>
            <div class="hint" style="margin-top:6px;">${escapeHtml(job.job_number || "")}${job.date ? ` - ${escapeHtml(job.date)}` : ""}${job.source ? ` - ${escapeHtml(String(job.source).toUpperCase())}` : ""}</div>
            <div id="legacy_action_mount" style="margin-top:12px;"></div>
            <div class="grid2" style="margin-top:12px;">
              <div><div class="label">Customer</div><div class="field">${escapeHtml(job.customer || job.customer_name || "")}</div></div>
              <div><div class="label">Job #</div><div class="field">${escapeHtml(job.job_number || "")}</div></div>
              <div><div class="label">Estimate #</div><div class="field">${formatDocRefDisplay(job.estimate_number || job.estimate_no || "")}</div></div>
              <div><div class="label">Invoice #</div><div class="field">${formatDocRefDisplay(job.invoice_number || job.invoice_no || "")}</div></div>
              <div><div class="label">PO #</div><div class="field">${formatDocRefDisplay(job.po_number || job.po_no || "")}</div></div>
              <div><div class="label">Address</div><div class="field">${escapeHtml(job.address || "")}</div></div>
              <div><div class="label">Date</div><div class="field">${escapeHtml(job.date || "")}</div></div>
              <div><div class="label">Status</div><div class="field">${escapeHtml(job.status || "")}</div></div>
              <div><div class="label">Contact</div><div class="field">${escapeHtml(job.contact || job.contact_name || "")}</div></div>
            </div>
            <div style="margin-top:10px;"><div class="label">Job Notes</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.job_notes || job.tech_notes || job.description || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Work Performed</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.work_performed || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Additional Recommendations</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.additional_recommendations || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Parts Used</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.parts_used || "")}</div></div>
          `;
          const actions = document.createElement("div");
          actions.style.display = "flex";
          actions.style.gap = "8px";
          actions.style.marginTop = "12px";
          actions.style.marginBottom = "12px";
          actions.style.justifyContent = "flex-end";

          const promoteBtn = document.createElement("button");
          promoteBtn.className = "btn btn-orange";
          promoteBtn.textContent = "Add to Calendar";
          promoteBtn.addEventListener("click", async () => {
            try {
              const defaultDate = new Date().toISOString().slice(0, 10);
              const chosen = prompt("Dispatch date (YYYY-MM-DD):", defaultDate) || defaultDate;
              const created = await apiPromoteLegacyJob(job.id, chosen);
              alert(`Dispatch ${created.job_number || ""} created.`);
              drawerBody.innerHTML = "";
              const local = document.createElement("div");
              drawerBody.appendChild(local);
              renderJobDetails(local, created, { afterSave: refresh, afterDelete: refresh });
              await refresh();
            } catch (e) {
              alert(e.message || String(e));
            }
          });

          const leadBtn = document.createElement("button");
          leadBtn.className = "btn";
          leadBtn.textContent = "Create Sales Lead";
          leadBtn.addEventListener("click", async () => {
            try {
              const defaultDate = new Date().toISOString().slice(0, 10);
              const chosen = prompt("Sales Lead date (YYYY-MM-DD):", defaultDate) || defaultDate;
              const created = await apiCreateSalesLeadFromLegacy(job.id, chosen);
              alert(`Sales Lead ${created.job_number || ""} created.`);
              drawerBody.innerHTML = "";
              const local = document.createElement("div");
              drawerBody.appendChild(local);
              renderJobDetails(local, created, { afterSave: refresh, afterDelete: refresh });
              await refresh();
            } catch (e) {
              alert(e.message || String(e));
            }
          });

          actions.appendChild(leadBtn);
          actions.appendChild(promoteBtn);
          const mount = card.querySelector("#legacy_action_mount");
          if (mount) mount.appendChild(actions);

          drawerBody.appendChild(card);
        });
        return;
      }
      apiGetJob(job.id).then(full => {
        openDrawer("Job Details", (drawerBody) => {
          const local = document.createElement("div");
          drawerBody.appendChild(local);
          renderJobDetails(local, full, { afterSave: refresh, afterDelete: refresh });
        });
      }).catch(e => alert(e.message || String(e)));
    }
 
    function makeTab(def) {
      const b = document.createElement("button");
      b.className = "navbtn";
      b.style.width = "auto";
      b.style.minWidth = "150px";
      b.style.display = "inline-flex";
      b.style.alignItems = "center";
      b.style.gap = "10px";
      b.style.justifyContent = "space-between";
 
      const left = document.createElement("div");
      left.innerHTML = `<span>${def.name}</span>`;
      const pill = def.status === "__ALL__" ? statusPill("Dispatch") : statusPill(def.status);
      if (def.status === "__ALL__") pill.textContent = "All";
 
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.style.display = (def.status === "Done") ? "none" : "inline-flex";
      badge.textContent = "0";
 
      b.appendChild(left);
      b.appendChild(pill);
      b.appendChild(badge);
 
      b.addEventListener("click", async () => {
        active = def.status;
        await refresh();
      });
 
      return { btn: b, badge, def };
    }
 
    const tabEls = tabDefs.map(makeTab);
    tabEls.forEach(x => tabsRow.appendChild(x.btn));
 
    function renderAllJobsRows(jobs) {
      list.innerHTML = "";
      if (!jobs.length) {
        list.innerHTML = `<div class="hint">No jobs found.</div>`;
        refreshBadges();
        return;
      }
      jobs.forEach(j => {
        const row = document.createElement("div");
        row.className = "jobrow";
        row.style.cursor = "pointer";
        const customer = j.customer || j.customer_name || "Job";
        const estimate = cleanDocRef(j.estimate_number || j.estimate_no || "");
        const invoice = cleanDocRef(j.invoice_number || j.invoice_no || "");
        const poNumber = cleanDocRef(j.po_number || j.po_no || "");
        const sourceLabel = j.source ? String(j.source).toUpperCase() : "CURRENT";
        row.innerHTML = `
          <div class="jobrow-top">
            <div class="jobrow-name">${escapeHtml(customer)} (${escapeHtml(j.job_number || "")})</div>
            <div style="display:flex; gap:8px; align-items:center;">${statusPill(j.status || "Dispatch").outerHTML}<span class="badge">${escapeHtml(sourceLabel)}</span></div>
          </div>
          <div class="jobrow-addr">${escapeHtml(j.date || j.date_display || "")} - ${escapeHtml(j.address || "")}</div>
          <div class="hint" style="margin-top:6px; font-weight:900;">Estimate: ${formatDocRefDisplay(estimate)} | Invoice: ${formatDocRefDisplay(invoice)} | PO: ${formatDocRefDisplay(poNumber)}</div>
        `;
        if (sourceLabel !== "CURRENT") {
          const actionRow = document.createElement("div");
          actionRow.style.display = "flex";
          actionRow.style.gap = "8px";
          actionRow.style.marginTop = "8px";

          const importBtn = document.createElement("button");
          importBtn.className = "btn btn-orange";
          importBtn.textContent = "Import Dispatch";
          importBtn.addEventListener("click", async (ev) => {
            ev.stopPropagation();
            try {
              const defaultDate = new Date().toISOString().slice(0, 10);
              const chosen = prompt("Dispatch date (YYYY-MM-DD):", defaultDate) || defaultDate;
              const created = await apiPromoteLegacyJob(j.id, chosen);
              alert(`Dispatch ${created.job_number || ""} created.`);
              await refresh();
            } catch (e) {
              alert(e.message || String(e));
            }
          });

          const leadBtn = document.createElement("button");
          leadBtn.className = "btn";
          leadBtn.textContent = "Import Sales Lead";
          leadBtn.addEventListener("click", async (ev) => {
            ev.stopPropagation();
            try {
              const defaultDate = new Date().toISOString().slice(0, 10);
              const chosen = prompt("Sales Lead date (YYYY-MM-DD):", defaultDate) || defaultDate;
              const created = await apiCreateSalesLeadFromLegacy(j.id, chosen);
              alert(`Sales Lead ${created.job_number || ""} created.`);
              await refresh();
            } catch (e) {
              alert(e.message || String(e));
            }
          });

          actionRow.appendChild(importBtn);
          actionRow.appendChild(leadBtn);
          row.appendChild(actionRow);
        }
        if (String(j.source || "").toUpperCase() && String(j.source || "").toUpperCase() !== "CURRENT") {
          const actionRow = document.createElement("div");
          actionRow.style.display = "flex";
          actionRow.style.gap = "8px";
          actionRow.style.marginTop = "8px";

          const importBtn = document.createElement("button");
          importBtn.className = "btn btn-orange";
          importBtn.textContent = "Import to Calendar";
          importBtn.addEventListener("click", async (ev) => {
            ev.stopPropagation();
            try {
              const defaultDate = new Date().toISOString().slice(0, 10);
              const chosen = prompt("Dispatch date (YYYY-MM-DD):", defaultDate) || defaultDate;
              const created = await apiPromoteLegacyJob(j.id, chosen);
              alert(`Dispatch ${created.job_number || ""} created.`);
              await refresh();
            } catch (e) {
              alert(e.message || String(e));
            }
          });

          const leadBtn = document.createElement("button");
          leadBtn.className = "btn";
          leadBtn.textContent = "Import Sales Lead";
          leadBtn.addEventListener("click", async (ev) => {
            ev.stopPropagation();
            try {
              const defaultDate = new Date().toISOString().slice(0, 10);
              const chosen = prompt("Sales Lead date (YYYY-MM-DD):", defaultDate) || defaultDate;
              const created = await apiCreateSalesLeadFromLegacy(j.id, chosen);
              alert(`Sales Lead ${created.job_number || ""} created.`);
              await refresh();
            } catch (e) {
              alert(e.message || String(e));
            }
          });

          actionRow.appendChild(importBtn);
          actionRow.appendChild(leadBtn);
          row.appendChild(actionRow);
        }

        row.addEventListener("click", () => openAnyJobCard(j));
        list.appendChild(row);
      });
    }
 
    async function refresh() {
      tabEls.forEach(x => x.btn.classList.toggle("navbtn-active", x.def.status === active));
      for (const t of tabEls) {
        if (t.def.status === "Done") continue;
        if (t.def.status === "__ALL__") {
          const js = await apiListAllJobs({ q: allJobsQuery, limit: 5000 }).catch(() => []);
          t.badge.textContent = String(js.length);
          continue;
        }
        const js = await apiListJobs({ status: t.def.status, limit: 5000 });
        t.badge.textContent = String(js.length);
      }
 
      searchWrap.style.display = active === "__ALL__" ? "flex" : "none";
 
      if (active === "__ALL__") {
        const jobs = await apiListAllJobs({ q: allJobsQuery, limit: 5000 }).catch(() => []);
        renderAllJobsRows(jobs);
        refreshBadges();
        return;
      }
 
      const jobs = await apiListJobs({ status: active, limit: 5000 });
      list.innerHTML = "";
      if (!jobs.length) {
        list.innerHTML = `<div class="hint">No items in ${active}.</div>`;
        refreshBadges();
        return;
      }
 
      jobs.forEach(j => {
        const row = document.createElement("div");
        row.className = "jobrow";
 
        const top = document.createElement("div");
        top.className = "jobrow-top";
 
        const name = document.createElement("div");
        name.className = "jobrow-name";
        const idLine = j.kind === "sales_lead" ? `Sales Lead #${j.job_number}` : `Job #${j.job_number}`;
        name.textContent = j.customer ? `${j.customer} (${idLine})` : idLine;
 
        top.appendChild(name);
        top.appendChild(statusPill(j.status));
 
        const addr = document.createElement("div");
        addr.className = "jobrow-addr";
        addr.textContent = `${mmDdYy(j.date)} - ${j.address || ""}`;
 
        row.appendChild(top);
        row.appendChild(addr);
 
        const techSummary = collectJobTechSummary(j);
        if (techSummary.length && ["Complete/Quote", "Complete", "Done"].includes(j.status)) {
          const meta = document.createElement("div");
          meta.className = "hint";
          meta.style.marginTop = "6px";
          meta.style.fontWeight = "900";
          meta.textContent = techSummary.join(" - ");
          row.appendChild(meta);
        }
 
        row.addEventListener("click", async () => {
          const full = await apiGetJob(j.id);
          openDrawer("Job Details", (drawerBody) => {
            const local = document.createElement("div");
            drawerBody.appendChild(local);
            renderJobDetails(local, full, { afterSave: refresh, afterDelete: refresh });
          });
        });
 
        list.appendChild(row);
      });
 
      refreshBadges();
    }
 
    root.appendChild(tabsRow);
    root.appendChild(searchWrap);
    root.appendChild(list);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    const allJobsInput = searchWrap.querySelector("#all_jobs_search");
    const allJobsBtn = searchWrap.querySelector("#all_jobs_refresh");
    allJobsInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        allJobsQuery = allJobsInput.value.trim();
        refresh();
      }
    });
    allJobsBtn.addEventListener("click", () => {
      allJobsQuery = allJobsInput.value.trim();
      refresh();
    });
 
    currentView = { refresh };
    refresh();
  }
 
  function renderAllJobsView() {
 
    setNavActive(navAllJobs);
    setActiveChip("Work Flow");
    setWorkspace("All Jobs");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const searchWrap = document.createElement("div");
    searchWrap.style.display = "flex";
    searchWrap.style.gap = "8px";
    searchWrap.style.marginBottom = "10px";
    searchWrap.style.alignItems = "center";
    searchWrap.innerHTML = `<input class="input" id="all_jobs_search" placeholder="Search by customer, contact, address, job #, estimate #, invoice #, or PO #" /><button class="btn" id="all_jobs_refresh">Search</button>`;
 
    const list = document.createElement("div");
    let allJobsQuery = "";
 
    function openAnyJobCard(job) {
      if (!job) return;
      const sourceLabel = String(job.source || "").toUpperCase();
      if (sourceLabel.startsWith("LEGACY") || !job.id) {
        openDrawer(`Legacy Job ${job.job_number || "Details"}`, async (drawerBody) => {
          const card = document.createElement("div");
          card.className = "card";
          card.innerHTML = `
            <h3 style="margin:0;">${escapeHtml(job.customer || job.customer_name || "Legacy Job")}</h3>
            <div class="hint" style="margin-top:6px;">${escapeHtml(job.job_number || "")}${job.date ? ` - ${escapeHtml(job.date)}` : ""}${job.source ? ` - ${escapeHtml(String(job.source).toUpperCase())}` : ""}</div>
            <div class="grid2" style="margin-top:12px;">
              <div><div class="label">Customer</div><div class="field">${escapeHtml(job.customer || job.customer_name || "")}</div></div>
              <div><div class="label">Job #</div><div class="field">${escapeHtml(job.job_number || "")}</div></div>
              <div><div class="label">Estimate #</div><div class="field">${formatDocRefDisplay(job.estimate_number || job.estimate_no || "")}</div></div>
              <div><div class="label">Invoice #</div><div class="field">${formatDocRefDisplay(job.invoice_number || job.invoice_no || "")}</div></div>
              <div><div class="label">PO #</div><div class="field">${formatDocRefDisplay(job.po_number || job.po_no || "")}</div></div>
              <div><div class="label">Address</div><div class="field">${escapeHtml(job.address || "")}</div></div>
              <div><div class="label">Date</div><div class="field">${escapeHtml(job.date || "")}</div></div>
              <div><div class="label">Status</div><div class="field">${escapeHtml(job.status || "History")}</div></div>
              <div><div class="label">Contact</div><div class="field">${escapeHtml(job.contact || job.contact_name || "")}</div></div>
            </div>
            <div style="margin-top:10px;"><div class="label">Job Notes</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.job_notes || job.tech_notes || job.description || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Work Performed</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.work_performed || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Additional Recommendations</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.additional_recommendations || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Parts Used</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.parts_used || "")}</div></div>
          `;
          drawerBody.appendChild(card);
        });
        return;
      }
      apiGetJob(job.id).then(full => {
        openDrawer("Job Details", (drawerBody) => {
          const local = document.createElement("div");
          drawerBody.appendChild(local);
          renderJobDetails(local, full, { afterSave: refresh, afterDelete: refresh });
        });
      }).catch(e => alert(e.message || String(e)));
    }
 
    function renderRows(jobs) {
      list.innerHTML = "";
      if (!jobs.length) {
        list.innerHTML = `<div class="hint">No jobs found.</div>`;
        return;
      }
      jobs.forEach(j => {
        const row = document.createElement("div");
        row.className = "jobrow";
        row.style.cursor = "pointer";
        const customer = j.customer || j.customer_name || "Job";
        const estimate = cleanDocRef(j.estimate_number || j.estimate_no || "");
        const invoice = cleanDocRef(j.invoice_number || j.invoice_no || "");
        const sourceLabel = j.source ? String(j.source).toUpperCase() : "CURRENT";
        row.innerHTML = `
          <div class="jobrow-top">
            <div class="jobrow-name">${escapeHtml(customer)} (${escapeHtml(j.job_number || "")})</div>
            <div style="display:flex; gap:8px; align-items:center;"><span class="badge">${escapeHtml(sourceLabel)}</span></div>
          </div>
          <div class="jobrow-addr">${escapeHtml(j.date || j.date_display || "")} - ${escapeHtml(j.address || "")}</div>
          <div class="hint" style="margin-top:6px; font-weight:900;">Estimate: ${formatDocRefDisplay(estimate)} | Invoice: ${formatDocRefDisplay(invoice)} | PO: ${formatDocRefDisplay(j.po_number || j.po_no || "")}</div>
        `;
        row.addEventListener("click", () => openAnyJobCard(j));
        list.appendChild(row);
      });
    }
 
    async function refresh() {
      const jobs = await apiListAllJobs({ q: allJobsQuery, limit: 5000 }).catch(() => []);
      renderRows(jobs);
      refreshBadges();
    }
 
    root.appendChild(searchWrap);
    root.appendChild(list);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    const allJobsInput = searchWrap.querySelector("#all_jobs_search");
    const allJobsBtn = searchWrap.querySelector("#all_jobs_refresh");
    allJobsInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        allJobsQuery = allJobsInput.value.trim();
        refresh();
      }
    });
    allJobsBtn.addEventListener("click", () => {
      allJobsQuery = allJobsInput.value.trim();
      refresh();
    });
 
    currentView = { refresh };
    refresh();
  }
 
  function renderPartsListView() {
    setNavActive(navPartsList);
    setActiveChip("Work Flow");
    setWorkspace("Parts List");
    clearWorkspaceActions();

    const root = document.createElement("div");
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h3>Parts List</h3><div class="hint">Manage manufacturer, part #, description, and price.</div>`;

    const controls = document.createElement("div");
    controls.style.display = "flex";
    controls.style.gap = "8px";
    controls.style.marginTop = "12px";
    controls.innerHTML = `<input class="input" id="parts_search" placeholder="Search manufacturer, part #, or description" /><button class="btn btn-orange" id="parts_add">Add Part</button>`;

    const list = document.createElement("div");
    list.style.display = "grid";
    list.style.gap = "8px";
    list.style.marginTop = "12px";

    async function openPartEditor(item = null) {
      openDrawer(item ? "Edit Part" : "Add Part", (drawerBody, overlay) => {
        const part = item || { id: "", Manufacturer: "", Item: "", Description: "", Price: "" };
        const wrap = document.createElement("div");
        wrap.className = "card";
        wrap.innerHTML = `
          <div class="grid2">
            <div><div class="label">Manufacturer</div><input class="input" id="part_mfg" value="${escapeHtml(part.Manufacturer || part.manufacturer || "")}" /></div>
            <div><div class="label">Part #</div><input class="input" id="part_item" value="${escapeHtml(part.Item || part.item || "")}" /></div>
          </div>
          <div style="margin-top:10px;"><div class="label">Description</div><textarea id="part_desc">${escapeHtml(part.Description || part.description || "")}</textarea></div>
          <div style="margin-top:10px;"><div class="label">Price</div><input class="input" id="part_price" type="number" step="0.01" min="0" value="${escapeHtml(String(part.Price || part.price || ""))}" /></div>
        `;
        const actions = document.createElement("div");
        actions.style.display = "flex"; actions.style.gap = "8px"; actions.style.marginTop = "12px";
        const save = document.createElement("button"); save.className = "btn btn-orange"; save.textContent = "Save";
        const cancel = document.createElement("button"); cancel.className = "btn"; cancel.textContent = "Cancel";
        actions.append(save, cancel);
        if (part.id) { const del = document.createElement("button"); del.className = "btn"; del.textContent = "Delete"; del.style.borderColor = "#fecaca"; del.style.color = "#b91c1c"; del.addEventListener("click", async ()=>{ if(!confirm("Delete this part?")) return; await apiDeletePart(part.id); overlay.remove(); refresh(); }); actions.appendChild(del); }
        wrap.appendChild(actions);
        drawerBody.appendChild(wrap);
        cancel.addEventListener("click", ()=> overlay.remove());
        save.addEventListener("click", async ()=>{
          await apiSavePart({
            id: part.id || "",
            manufacturer: wrap.querySelector("#part_mfg").value.trim(),
            item: wrap.querySelector("#part_item").value.trim(),
            description: wrap.querySelector("#part_desc").value.trim(),
            price: Number(wrap.querySelector("#part_price").value || 0),
          });
          overlay.remove();
          refresh();
        });
      });
    }

    async function refresh() {
      const q = controls.querySelector("#parts_search").value.trim();
      const items = await apiListParts({ q, limit: 500 }).catch(() => []);
      list.innerHTML = "";
      if (!items.length) { list.innerHTML = `<div class="hint">No saved parts yet.</div>`; return; }
      items.forEach(p => {
        const row = document.createElement("div");
        row.className = "jobrow";
        row.style.cursor = "pointer";
        row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${escapeHtml(p.Item || p.item || "")}</div><div class="hint">$${money(p.Price || p.price || 0)}</div></div><div class="jobrow-addr">${escapeHtml(p.Manufacturer || p.manufacturer || "")} - ${escapeHtml(p.Description || p.description || "")}</div>`;
        row.addEventListener("click", ()=> openPartEditor(p));
        list.appendChild(row);
      });
    }

    controls.querySelector("#parts_add").addEventListener("click", ()=> openPartEditor());
    controls.querySelector("#parts_search").addEventListener("keydown", e=>{ if(e.key === "Enter") refresh(); });

    root.appendChild(card);
    root.appendChild(controls);
    root.appendChild(list);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
    currentView = { refresh };
    refresh();
  }

  async function openSignOffView(job = null) {
    const [customers, employees] = await Promise.all([
      apiListCustomers().catch(() => []),
      apiListEmployees().catch(() => []),
    ]);
    let contacts = await apiListContacts(job?.customer ? { company_name: job.customer } : {}).catch(() => []);
    openDrawer("Sign Off", (drawerBody, overlay) => {
      const card = document.createElement("div");
      card.className = "card";
      const customerListId = `so-customer-${Math.random().toString(36).slice(2)}`;
      const techListId = `so-tech-${Math.random().toString(36).slice(2)}`;
      const contactListId = `so-contact-${Math.random().toString(36).slice(2)}`;
      card.innerHTML = `
        <div class="grid2">
          <div><div class="label">Job #</div><input class="input" id="so_job" value="${escapeHtml(job?.job_number || "")}" /></div>
          <div><div class="label">Customer</div><input class="input" id="so_customer" list="${customerListId}" value="${escapeHtml(job?.customer || "")}" /></div>
          <div><div class="label">Date</div><input class="input" id="so_date" type="date" value="${yyyyMmDd(new Date())}" /></div>
          <div><div class="label">Tech</div><input class="input" id="so_techs" list="${techListId}" /></div>
          <div><div class="label">Contact Name</div><input class="input" id="so_contact" list="${contactListId}" value="${escapeHtml(job?.contact || "")}" /></div>
          <div><div class="label">Arrival / Departure</div><input class="input" id="so_times" placeholder="8:00 AM - 10:30 AM" /></div>
        </div>
        <div style="margin-top:10px;"><label style="display:flex; align-items:center; gap:8px; font-weight:700;"><input type="checkbox" id="so_additional" /><span>Additional Techs Onsite</span></label></div>
        <div style="margin-top:10px;"><div class="label">Signature</div><canvas id="so_sig" width="700" height="180" style="width:100%; border:1px solid var(--line); border-radius:12px; background:#fff;"></canvas></div>
      `;
      card.appendChild(buildCustomerDatalist(customerListId, customers));
      const techList = document.createElement('datalist'); techList.id = techListId; techList.innerHTML = employees.map(e => `<option value="${escapeHtml(e.name || '')}"></option>`).join(''); card.appendChild(techList);
      const contactList = document.createElement('datalist'); contactList.id = contactListId; card.appendChild(contactList);
      const renderContactOptions = () => {
        contactList.innerHTML = contacts.map(c => `<option value="${escapeHtml(c.name || '')}"></option>`).join('');
      };
      renderContactOptions();
      const customerInput = card.querySelector('#so_customer');
      customerInput.addEventListener('change', async () => {
        contacts = await apiListContacts({ company_name: customerInput.value.trim() }).catch(() => []);
        renderContactOptions();
      });
      const actions = document.createElement("div");
      actions.style.display = "flex"; actions.style.gap = "8px"; actions.style.marginTop = "12px";
      const clearBtn = document.createElement("button"); clearBtn.className = "btn"; clearBtn.textContent = "Clear Signature";
      const saveBtn = document.createElement("button"); saveBtn.className = "btn btn-orange"; saveBtn.textContent = "Generate Sign Off";
      const cancelBtn = document.createElement("button"); cancelBtn.className = "btn"; cancelBtn.textContent = "Cancel";
      actions.append(clearBtn, saveBtn, cancelBtn);
      card.appendChild(actions);
      drawerBody.appendChild(card);
      const canvas = card.querySelector("#so_sig"); const ctx = canvas.getContext("2d"); let drawing = false;
      const pos = e => { const r = canvas.getBoundingClientRect(); const t = e.touches ? e.touches[0] : e; return { x:(t.clientX-r.left)*(canvas.width/r.width), y:(t.clientY-r.top)*(canvas.height/r.height) }; };
      const start = e => { drawing = true; const p = pos(e); ctx.beginPath(); ctx.moveTo(p.x,p.y); e.preventDefault(); };
      const move = e => { if(!drawing) return; const p = pos(e); ctx.lineWidth = 2; ctx.lineCap = "round"; ctx.strokeStyle = "#111827"; ctx.lineTo(p.x,p.y); ctx.stroke(); e.preventDefault(); };
      const stop = e => { drawing = false; e && e.preventDefault && e.preventDefault(); };
      canvas.addEventListener("mousedown", start); canvas.addEventListener("mousemove", move); canvas.addEventListener("mouseup", stop); canvas.addEventListener("mouseleave", stop);
      canvas.addEventListener("touchstart", start, {passive:false}); canvas.addEventListener("touchmove", move, {passive:false}); canvas.addEventListener("touchend", stop, {passive:false});
      clearBtn.addEventListener("click", ()=> ctx.clearRect(0,0,canvas.width,canvas.height));
      cancelBtn.addEventListener("click", ()=> overlay.remove());
      saveBtn.addEventListener("click", async ()=> {
        const payload = {
          job_id: job?.id || "",
          job_number: card.querySelector("#so_job").value.trim(),
          customer: card.querySelector("#so_customer").value.trim(),
          date: card.querySelector("#so_date").value,
          techs: card.querySelector("#so_techs").value.trim() + (card.querySelector('#so_additional').checked ? ' + Additional Techs Onsite' : ''),
          contact_name: card.querySelector("#so_contact").value.trim(),
          arrival_time: card.querySelector("#so_times").value.trim(),
          departure_time: "",
          signature_data: canvas.toDataURL("image/png"),
        };
        await apiCreateSignoff(payload);
        overlay.remove();
        alert("Sign off generated.");
      });
    });
  }

  function renderSignOffLibraryView() {
    setNavActive(navFormsSignOff || navTakeoffs);
    setActiveChip("Forms");
    setWorkspace("Saved Sign Offs");
    clearWorkspaceActions();
    const root = document.createElement('div');
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `<h3>Saved Sign Offs</h3><div class="hint">Search and open previously generated sign off PDFs.</div>`;
    const controls = document.createElement('div');
    controls.style.display = 'flex'; controls.style.gap = '8px'; controls.style.marginTop = '12px';
    controls.innerHTML = `<input class="input" id="so_search" placeholder="Search job # or customer" /><button class="btn btn-orange" id="so_new">New Sign Off</button>`;
    const list = document.createElement('div'); list.style.display = 'grid'; list.style.gap = '8px'; list.style.marginTop = '12px';
    async function refresh() {
      const q = controls.querySelector('#so_search').value.trim().toLowerCase();
      const docs = await apiListDocuments().catch(() => []);
      const items = docs.filter(d => String(d.type || '').toLowerCase() === 'signoff').filter(d => {
        if (!q) return true;
        return [d.number, d.job_number, d.customer].some(v => String(v || '').toLowerCase().includes(q));
      });
      list.innerHTML = '';
      if (!items.length) { list.innerHTML = `<div class="hint">No saved sign offs yet.</div>`; return; }
      items.sort((a,b)=>String(b.created_at||'').localeCompare(String(a.created_at||''))).forEach(doc => {
        const row = document.createElement('div'); row.className = 'jobrow'; row.style.cursor = 'pointer';
        row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${escapeHtml(doc.job_number || doc.number || '')}</div><div class="hint">${escapeHtml(formatDisplayDate(doc.date || ''))}</div></div><div class="jobrow-addr">${escapeHtml(doc.customer || '')}</div>`;
        row.addEventListener('click', () => window.open(doc.open_url || doc.download_url, '_blank'));
        list.appendChild(row);
      });
    }
    controls.querySelector('#so_search').addEventListener('input', refresh);
    controls.querySelector('#so_new').addEventListener('click', ()=> openSignOffView());
    root.append(card, controls, list); workspaceBody.innerHTML=''; workspaceBody.appendChild(root); currentView={ refresh }; refresh();
  }

  function renderTakeoffsView() {
 
    setNavActive(navTakeoffs);
    setActiveChip("Forms");
    setWorkspace("Takeoffs");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h3>Takeoffs</h3><div class="hint">Download takeoff and order files here.</div>`;
    const list = document.createElement("div");
    list.style.marginTop = "12px";
 
    async function refresh() {
      const forms = await apiListForms();
      list.innerHTML = "";
      if (!forms.length) {
        list.innerHTML = `<div class="hint">No files available.</div>`;
        return;
      }
      forms.forEach(f => {
        const item = document.createElement("div");
        item.className = "jobrow";
 
        const top = document.createElement("div");
        top.className = "jobrow-top";
 
        const name = document.createElement("div");
        name.className = "jobrow-name";
        name.textContent = f.title || f.id;
 
        const btn = document.createElement("button");
        btn.className = "btn";
        btn.textContent = "Open / Download";
        btn.addEventListener("click", async () => {
          await downloadFile(f.download_url, `${(f.title || f.id || "form")}.pdf`);
        });
 
        top.appendChild(name);
        top.appendChild(btn);
 
        const desc = document.createElement("div");
        desc.className = "jobrow-addr";
        desc.textContent = f.description || "";
 
        item.appendChild(top);
        item.appendChild(desc);
        list.appendChild(item);
      });
    }
 
    root.appendChild(card);
    root.appendChild(list);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    currentView = { refresh };
    refresh();
  }
 
 
  function openTimecardEditor(item, refreshFn) {
    openDrawer("Edit Time Card", async (drawerBody, overlay) => {
      const card = document.createElement("div");
      card.className = "card";
      const hrs = calcTimeHours(item.start_time, item.end_time, !!item.lunch_taken, item.lunch_start, item.lunch_end);
      card.innerHTML = `
        <h3 style="margin:0;">${item.technician_name || item.employee_name || item.employee || "Time Card"}</h3>
        <div class="hint" style="margin-top:6px;">${formatDisplayDate(item.date || "")} - ${formatTimeRange12(item.start_time, item.end_time)} - ${hrs} hrs</div>
        <div class="hint" style="margin-top:6px;">${escapeHtml(lunchSummary(item))}${item.supervisor_approved ? ' - Supervisor Approved' : ''}${item.use_pto ? ` - PTO ${escapeHtml(String(item.pto_hours || 0))} hrs` : ''}</div>
        <div style="margin-top:12px;"><div class="label">Notes</div><div class="field" style="white-space:pre-wrap;">${item.notes || ""}</div></div>
      `;
      const actions = document.createElement("div");
      actions.style.display = "flex";
      actions.style.gap = "8px";
      actions.style.marginTop = "12px";
      const close = document.createElement("button");
      close.className = "btn";
      close.textContent = "Close";
      const del = document.createElement("button");
      del.className = "btn";
      del.textContent = "Delete Time Card";
      del.style.borderColor = "#fecaca";
      del.style.color = "#b91c1c";
      close.addEventListener("click", () => { if (overlay && overlay.remove) overlay.remove(); });
      del.addEventListener("click", async () => {
        if (!confirm("Delete this time card?")) return;
        try {
          await apiDeleteTimecard(item.id);
          if (overlay && overlay.remove) overlay.remove();
          await refreshFn();
        } catch (e) {
          alert(e.message || String(e));
        }
      });
      actions.appendChild(close);
      actions.appendChild(del);
      card.appendChild(actions);
      drawerBody.appendChild(card);
    });
  }
 
  function renderTimeCardView() {
    setNavActive(navFormsTimeCard);
    setActiveChip("Forms");
    setWorkspace("Time Card");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h3>Time Card</h3><div class="hint">Fill out and save time card entries.</div>`;
 
    const form = document.createElement("div");
    form.className = "grid2";
    form.style.marginTop = "10px";
    form.innerHTML = `
      <div><div class="label">Employee</div><select class="input" id="tc_employee"></select></div>
      <div><div class="label">Date</div><input class="input" id="tc_date" type="date" /></div>
      <div><div class="label">Start Time</div><input class="input" id="tc_start" type="time" /></div>
      <div><div class="label">End Time</div><input class="input" id="tc_end" type="time" /></div>
      <div><div class="label">Lunch Taken</div><select class="input" id="tc_lunch_taken"><option value="no">No</option><option value="yes">Yes</option></select></div>
      <div><div class="label">Use PTO</div><select class="input" id="tc_use_pto"><option value="no">No</option><option value="yes">Yes</option></select></div>
      <div><div class="label">Lunch Start</div><input class="input" id="tc_lunch_start" type="time" /></div>
      <div><div class="label">Lunch End</div><input class="input" id="tc_lunch_end" type="time" /></div>
      <div><div class="label">PTO Hours</div><input class="input" id="tc_pto_hours" type="number" step="0.25" placeholder="0.00" /></div>
      <div><div class="hint" style="margin-top:28px;">Use for sick time or paid hours not physically worked.</div></div>
    `;
 
    const notes = document.createElement("div");
    notes.style.marginTop = "10px";
    notes.innerHTML = `<div class="label">Notes</div>`;
    const ta = document.createElement("textarea");
    notes.appendChild(ta);
 
    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "8px";
    actions.style.marginTop = "10px";
 
    const btnSave = document.createElement("button");
    btnSave.className = "btn btn-orange";
    btnSave.textContent = "Save Time Card";
 
    const btnRefresh = document.createElement("button");
    btnRefresh.className = "btn";
    btnRefresh.textContent = "Refresh";

    const filterWrap = document.createElement("div");
    filterWrap.style.display = "grid";
    filterWrap.style.gridTemplateColumns = "minmax(220px,320px)";
    filterWrap.style.gap = "8px";
    filterWrap.style.marginTop = "14px";
    filterWrap.innerHTML = `<div><div class="label">Filter by Technician</div><select class="input" id="tc_filter"><option value="">All Technicians</option></select></div>`;
 
    actions.appendChild(btnSave);
    actions.appendChild(btnRefresh);
 
    const list = document.createElement("div");
    list.style.marginTop = "14px";
 
    async function refresh() {
      const employees = await apiListEmployees().catch(() => []);
      const tcSel = form.querySelector("#tc_employee");
      const selfOnly = currentUser && ["tech", "lead"].includes(String(currentUser.role || ""));
      const selfName = (currentUser && (currentUser.name || currentUser.username)) ? String(currentUser.name || currentUser.username) : "";
      const current = tcSel.value;
      if (selfOnly) {
        tcSel.innerHTML = selfName ? `<option value="${escapeHtml(selfName)}">${escapeHtml(selfName)}</option>` : `<option value="">-- Select Employee --</option>`;
        tcSel.value = selfName;
        tcSel.disabled = true;
      } else {
        tcSel.disabled = false;
        tcSel.innerHTML = `<option value="">-- Select Employee --</option>`;
        employees.forEach(e => {
          const opt = document.createElement("option");
          opt.value = e.name;
          opt.textContent = e.name;
          tcSel.appendChild(opt);
        });
        if (current) tcSel.value = current;
      }

      const filterSel = filterWrap.querySelector("#tc_filter");
      const prevFilter = filterSel.value;
      if (selfOnly) {
        filterWrap.style.display = "none";
        filterSel.innerHTML = selfName ? `<option value="${escapeHtml(selfName)}">${escapeHtml(selfName)}</option>` : `<option value="">My Entries</option>`;
        filterSel.value = selfName;
      } else {
        filterWrap.style.display = "grid";
        filterSel.innerHTML = `<option value="">All Technicians</option>` + employees.map(e => `<option value="${escapeHtml(e.name || "")}">${escapeHtml(e.name || "")}</option>`).join("");
        if (prevFilter) filterSel.value = prevFilter;
      }
 
      try {
        const items = await apiListTimecards({ limit: 5000, ...(selfOnly && selfName ? { technician: selfName } : {}) });
        const activeFilter = (selfOnly ? selfName : filterSel.value).trim().toLowerCase();
        const filteredItems = activeFilter
          ? items.filter(t => String(t.technician_name || t.employee_name || t.employee || "").trim().toLowerCase() === activeFilter)
          : items;
        list.innerHTML = "";
        if (!filteredItems.length) {
          list.innerHTML = `<div class="hint">No time cards yet.</div>`;
          return;
        }
        filteredItems.forEach(t => {
          const hrs = calcTimeHours(
            t.start_time,
            t.end_time,
            !!t.lunch_taken,
            t.lunch_start,
            t.lunch_end
          );
 
          const row = document.createElement("div");
          row.className = "jobrow";
          row.innerHTML = `
            <div class="jobrow-top">
              <div class="jobrow-name">${escapeHtml(t.technician_name || t.employee_name || t.employee || "")}</div>
              <div class="hint">${hrs} hrs</div>
            </div>
            <div class="jobrow-addr">
              ${escapeHtml(formatDisplayDate(t.date || ""))} - ${escapeHtml(formatTimeRange12(t.start_time, t.end_time))}${t.notes ? ` - ${escapeHtml(t.notes)}` : ""}
            </div>
            <div class="hint" style="margin-top:6px;">${escapeHtml(lunchSummary(t))}${t.supervisor_approved ? ' - Supervisor Approved' : ''}${t.use_pto ? ` - PTO ${escapeHtml(String(t.pto_hours || 0))} hrs` : ''}</div>
          `;
          row.addEventListener("click", () => openTimecardEditor(t, refresh));
          list.appendChild(row);
        });
      } catch (e) {
        list.innerHTML = `<div class="hint">Time cards unavailable: ${e.message || e}</div>`;
      }
    }
 
    btnSave.addEventListener("click", async () => {
      try {
        await apiCreateTimecard({
          technician_name: ((currentUser && ["tech", "lead"].includes(String(currentUser.role || ""))) ? String(currentUser.name || currentUser.username || "") : form.querySelector("#tc_employee").value.trim()),
          date: form.querySelector("#tc_date").value,
          start_time: form.querySelector("#tc_start").value,
          end_time: form.querySelector("#tc_end").value,
          lunch_taken: form.querySelector("#tc_lunch_taken").value === "yes",
          lunch_start: form.querySelector("#tc_lunch_start").value,
          lunch_end: form.querySelector("#tc_lunch_end").value,
          use_pto: form.querySelector("#tc_use_pto").value === "yes",
          pto_hours: Number(form.querySelector("#tc_pto_hours").value || 0),
          notes: ta.value.trim(),
        });
        ta.value = "";
        form.querySelector("#tc_pto_hours").value = "";
        form.querySelector("#tc_use_pto").value = "no";
        await refresh();
      } catch (e) {
        alert(e.message || String(e));
      }
    });
 
    btnRefresh.addEventListener("click", refresh);
    filterWrap.querySelector("#tc_filter").addEventListener("change", refresh);
 
    root.appendChild(card);
    root.appendChild(form);
    root.appendChild(notes);
    root.appendChild(actions);
    root.appendChild(filterWrap);
    root.appendChild(list);
 
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    currentView = { refresh };
    refresh();
  }
 





  function renderPayrollView() {
    setNavActive(navPayroll);
    setActiveChip("Office Flow");
    setWorkspace("Payroll");
    clearWorkspaceActions();

    const exportBtn = document.createElement("button");
    exportBtn.className = "btn btn-orange";
    exportBtn.textContent = "Export Crew Payroll";
    workspaceActions.appendChild(exportBtn);

    const root = document.createElement("div");

    const controls = document.createElement("div");
    controls.className = "grid2";
    controls.style.marginTop = "12px";
    controls.innerHTML = `
      <div><div class="label">Month</div><input class="input" id="pay_month" type="month" /></div>
      <div></div>
    `;
    root.appendChild(controls);

    const summaryWrap = document.createElement("div");
    summaryWrap.style.display = "grid";
    summaryWrap.style.gridTemplateColumns = "repeat(auto-fit, minmax(190px, 1fr))";
    summaryWrap.style.gap = "12px";
    summaryWrap.style.marginTop = "14px";
    root.appendChild(summaryWrap);

    const list = document.createElement("div");
    list.style.marginTop = "14px";
    root.appendChild(list);

    const metricCard = (label, value, hint = "") => {
      const card = document.createElement("div");
      card.className = "card";
      card.style.padding = "14px";
      card.innerHTML = `
        <div style="font-size:12px;font-weight:800;opacity:.75;margin-bottom:6px;">${escapeHtml(label)}</div>
        <div style="font-size:30px;font-weight:900;line-height:1;">${escapeHtml(value)}</div>
        <div class="hint" style="margin-top:6px;">${escapeHtml(hint)}</div>
      `;
      return card;
    };

    const monthIncludesDate = (monthVal, dateStr) => {
      if (!monthVal) return true;
      if (!dateStr) return false;
      return String(dateStr).slice(0, 7) === monthVal;
    };

    const calcHoursForCard = (t) => calcTimeHours(
      t.start_time,
      t.end_time,
      !!t.lunch_taken,
      t.lunch_start,
      t.lunch_end
    );

    const dailyRegularHours = (hours) => Math.min(8, Math.max(0, hours));
    const dailyOtHours = (hours) => Math.max(0, hours - 8);

    function entryHoursBreakdown(entry) {
      const hours = calcHoursForCard(entry);
      return {
        worked: hours,
        regular: dailyRegularHours(hours),
        ot: dailyOtHours(hours),
      };
    }

    function entriesBreakdown(entries) {
      return entries.reduce((acc, t) => {
        const b = entryHoursBreakdown(t);
        acc.worked += b.worked;
        acc.regular += b.regular;
        acc.ot += b.ot;
        return acc;
      }, { worked: 0, regular: 0, ot: 0 });
    }

    function approvedPtoHoursForEmployee(emp, approvedPto, approvedTimecards) {
      const timeoffHours = approvedPto
        .filter(t => employeeNameOfItem(t) === emp && !!t.use_pto)
        .reduce((sum, t) => sum + ptoHoursFromItem(t), 0);
      const tcHours = approvedTimecards
        .filter(t => employeeNameOfItem(t) === emp && !!t.use_pto)
        .reduce((sum, t) => sum + ptoHoursFromItem(t), 0);
      return timeoffHours + tcHours;
    }

    function buildCrewCsv(monthVal, filtered, approvedPto) {
      const employees = {};
      filtered.forEach(t => {
        const emp = employeeNameOfItem(t);
        if (!emp) return;
        if (!employees[emp]) employees[emp] = [];
        employees[emp].push(t);
      });
      let csv = "Employee,Month,Hours Worked,Regular Hours,OT Hours,OT Bank Adj,OT Total,PTO Bank,PTO Used,PTO Remaining,Approved Cards,Pending Cards\n";
      Object.keys(employees).sort((a,b)=>a.localeCompare(b)).forEach(emp => {
        const entries = employees[emp];
        const breakdown = entriesBreakdown(entries);
        const approvedCards = entries.filter(t => !!t.supervisor_approved).length;
        const pendingCards = entries.filter(t => !t.supervisor_approved).length;
        const ptoBank = getPtoBankHours(emp);
        const ptoUsed = approvedPtoHoursForEmployee(emp, approvedPto, entries.filter(t => !!t.supervisor_approved));
        const ptoRemaining = ptoBank - ptoUsed;
        const otBank = getOtBankHours(emp);
        const otTotal = breakdown.ot + otBank;
        csv += `${emp},${monthVal || ""},${breakdown.worked.toFixed(2)},${breakdown.regular.toFixed(2)},${breakdown.ot.toFixed(2)},${otBank.toFixed(2)},${otTotal.toFixed(2)},${ptoBank.toFixed(2)},${ptoUsed.toFixed(2)},${ptoRemaining.toFixed(2)},${approvedCards},${pendingCards}\n`;
      });
      return csv;
    }

    function downloadCsv(filename, csv) {
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    }

    async function openTechBreakdown(emp, entries, monthVal, approvedPto) {
      const timeoffItems = await apiListTimeOff({ employee: emp, limit: 500 }).catch(() => []);
      const monthTimeoff = timeoffItems.filter(t => monthIncludesDate(monthVal, itemDateOf(t)));

      openDrawer(`${emp} Payroll Breakdown`, (drawerBody, overlay) => {
        const wrap = document.createElement("div");
        wrap.className = "card";
        wrap.innerHTML = `<h3>${escapeHtml(emp)}</h3><div class="hint">${escapeHtml(monthVal || "Current Month")}</div>`;

        const buttonRow = document.createElement("div");
        buttonRow.style.display = "flex";
        buttonRow.style.gap = "8px";
        buttonRow.style.marginTop = "12px";
        buttonRow.style.flexWrap = "wrap";

        const exportEmpBtn = document.createElement("button");
        exportEmpBtn.className = "btn btn-orange";
        exportEmpBtn.textContent = "Export Employee Report";
        exportEmpBtn.addEventListener("click", () => {
          const breakdown = entriesBreakdown(entries);
          const ptoBank = getPtoBankHours(emp);
          const ptoUsed = approvedPtoHoursForEmployee(emp, approvedPto, entries.filter(t => !!t.supervisor_approved));
          const ptoRemaining = ptoBank - ptoUsed;
          const otBank = getOtBankHours(emp);
          const otTotal = breakdown.ot + otBank;
          let csv = "Employee,Month,Hours Worked,Regular Hours,OT Hours,OT Bank Adj,OT Total,PTO Bank,PTO Used,PTO Remaining\n";
          csv += `${emp},${monthVal || ""},${breakdown.worked.toFixed(2)},${breakdown.regular.toFixed(2)},${breakdown.ot.toFixed(2)},${otBank.toFixed(2)},${otTotal.toFixed(2)},${ptoBank.toFixed(2)},${ptoUsed.toFixed(2)},${ptoRemaining.toFixed(2)}\n\n`;
          csv += "Date,Time Range,Worked Hours,Regular Hours,OT Hours,PTO Used,PTO Hours,Approved,Notes\n";
          entries.slice().sort((a,b)=>String(itemDateOf(a)).localeCompare(String(itemDateOf(b)))).forEach(t => {
            const b = entryHoursBreakdown(t);
            csv += `${itemDateOf(t)},${formatTimeRange12(t.start_time, t.end_time)},${b.worked.toFixed(2)},${b.regular.toFixed(2)},${b.ot.toFixed(2)},${t.use_pto ? "YES":"NO"},${Number(t.pto_hours || 0).toFixed(2)},${t.supervisor_approved ? "YES":"NO"},"${String(t.notes || "").replace(/"/g,'""')}"\n`;
          });
          downloadCsv(`${emp.replace(/\s+/g, "_").toLowerCase()}_payroll_report.csv`, csv);
        });

        const ptoBankBtn = document.createElement("button");
        ptoBankBtn.className = "btn";
        ptoBankBtn.textContent = "PTO";
        ptoBankBtn.addEventListener("click", () => {
          const current = getPtoBankHours(emp);
          const next = prompt(`Enter PTO hours available for ${emp}:`, String(current.toFixed(2)));
          if (next === null) return;
          const val = Number(next || 0);
          if (Number.isNaN(val)) return alert("Enter a valid PTO hour amount.");
          setPtoBankHours(emp, val);
          if (overlay && overlay.remove) overlay.remove();
          refresh();
        });

        const otBankBtn = document.createElement("button");
        otBankBtn.className = "btn";
        otBankBtn.textContent = "OT";
        otBankBtn.addEventListener("click", () => {
          const current = getOtBankHours(emp);
          const next = prompt(`Enter OT hours adjustment for ${emp}:`, String(current.toFixed(2)));
          if (next === null) return;
          const val = Number(next || 0);
          if (Number.isNaN(val)) return alert("Enter a valid OT hour amount.");
          setOtBankHours(emp, val);
          if (overlay && overlay.remove) overlay.remove();
          refresh();
        });

        buttonRow.appendChild(exportEmpBtn);
        buttonRow.appendChild(ptoBankBtn);
        buttonRow.appendChild(otBankBtn);
        wrap.appendChild(buttonRow);

        const totals = document.createElement("div");
        totals.style.display = "grid";
        totals.style.gridTemplateColumns = "repeat(auto-fit, minmax(150px, 1fr))";
        totals.style.gap = "10px";
        totals.style.marginTop = "12px";

        const breakdown = entriesBreakdown(entries);
        const approvedCount = entries.filter(t => !!t.supervisor_approved).length;
        const pendingCount = entries.filter(t => !t.supervisor_approved).length;
        const ptoUsed = approvedPtoHoursForEmployee(emp, approvedPto, entries.filter(t => !!t.supervisor_approved));
        const ptoBank = getPtoBankHours(emp);
        const ptoRemaining = ptoBank - ptoUsed;
        const otBank = getOtBankHours(emp);
        const otTotal = breakdown.ot + otBank;

        [
          metricCard("Hours", breakdown.worked.toFixed(2)),
          metricCard("Regular", breakdown.regular.toFixed(2), "Up to 8 per day"),
          metricCard("OT", breakdown.ot.toFixed(2), "Over 8 per day"),
          metricCard("OT Adj", otBank.toFixed(2)),
          metricCard("OT Total", otTotal.toFixed(2)),
          metricCard("Approved", `${approvedCount}/${entries.length}`),
          metricCard("Pending", String(pendingCount)),
          metricCard("PTO Bank", ptoBank.toFixed(2)),
          metricCard("PTO Used", ptoUsed.toFixed(2)),
          metricCard("PTO Remaining", ptoRemaining.toFixed(2)),
        ].forEach(c => totals.appendChild(c));
        wrap.appendChild(totals);

        const rows = document.createElement("div");
        rows.style.display = "grid";
        rows.style.gap = "8px";
        rows.style.marginTop = "12px";

        if (!entries.length) {
          rows.innerHTML = `<div class="hint">No time cards for this month.</div>`;
        } else {
          entries.slice().sort((a,b)=>String(itemDateOf(b)).localeCompare(String(itemDateOf(a)))).forEach(t => {
            const b = entryHoursBreakdown(t);
            const row = document.createElement("div");
            row.className = "jobrow";
            row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${escapeHtml(formatDisplayDate(itemDateOf(t)) || "")}</div><div class="hint">${b.worked.toFixed(2)} hrs</div></div><div class="jobrow-addr">${escapeHtml(formatTimeRange12(t.start_time, t.end_time))}${t.notes ? ` - ${escapeHtml(t.notes)}` : ""}</div><div class="hint" style="margin-top:6px;">Regular ${b.regular.toFixed(2)} | OT ${b.ot.toFixed(2)}${t.supervisor_approved ? ' - Supervisor Approved' : ' - Awaiting Approval'}${t.use_pto ? ` - PTO ${escapeHtml(String(Number(t.pto_hours || 0).toFixed(2)))} hrs` : ''}</div>`;
            const actions = document.createElement("div");
            actions.style.display = "flex";
            actions.style.gap = "8px";
            actions.style.marginTop = "8px";

            const viewBtn = document.createElement("button");
            viewBtn.className = "btn";
            viewBtn.textContent = "View Timecard";
            viewBtn.addEventListener("click", (e) => { e.stopPropagation(); openTimecardEditor(t, refresh); });

            const approveBtn = document.createElement("button");
            approveBtn.className = t.supervisor_approved ? "btn btn-orange" : "btn";
            approveBtn.textContent = t.supervisor_approved ? "Supervisor Approved" : "Supervisal Approval";
            approveBtn.addEventListener("click", async (e) => {
              e.stopPropagation();
              try {
                const payload = { ...t, supervisor_approved: !t.supervisor_approved, supervisor_approved_at: !t.supervisor_approved ? new Date().toISOString() : "" };
                await fetchJSON(`/timecards/${t.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
                const updatedEntries = entries.map(entry => entry.id === t.id ? { ...entry, supervisor_approved: payload.supervisor_approved, supervisor_approved_at: payload.supervisor_approved_at } : entry);
                if (overlay && overlay.remove) overlay.remove();
                await refresh();
                openTechBreakdown(emp, updatedEntries, monthVal, approvedPto);
              } catch (e2) {
                alert(e2.message || String(e2));
              }
            });

            actions.appendChild(viewBtn);
            actions.appendChild(approveBtn);
            row.appendChild(actions);
            row.addEventListener("click", () => openTimecardEditor(t, refresh));
            rows.appendChild(row);
          });
        }
        wrap.appendChild(rows);
        drawerBody.appendChild(wrap);

        const ptoCard = document.createElement("div");
        ptoCard.className = "card";
        ptoCard.style.marginTop = "12px";
        ptoCard.innerHTML = `<h3>PTO / Time Off</h3>`;
        const ptoRows = document.createElement("div");
        ptoRows.style.display = "grid";
        ptoRows.style.gap = "8px";
        ptoRows.style.marginTop = "10px";
        if (!monthTimeoff.length) {
          ptoRows.innerHTML = `<div class="hint">No time off entries for this month.</div>`;
        } else {
          monthTimeoff.slice().sort((a,b)=>String(itemDateOf(b)).localeCompare(String(itemDateOf(a)))).forEach(t => {
            const row = document.createElement("div");
            row.className = "jobrow";
            row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${escapeHtml(formatDisplayDate(itemDateOf(t)) || "")}</div><div class="hint">${escapeHtml(t.status || "")}</div></div><div class="jobrow-addr">${escapeHtml(t.kind || "Time Off")}${t.use_pto ? ` - PTO ${escapeHtml(String(Number(t.pto_hours || 0).toFixed(2)))} hrs` : ''}${t.reason ? ` - ${escapeHtml(t.reason)}` : ""}</div>`;
            ptoRows.appendChild(row);
          });
        }
        ptoCard.appendChild(ptoRows);
        drawerBody.appendChild(ptoCard);
      });
    }

    async function refresh() {
      const items = await apiListTimecards({ limit: 5000 }).catch(() => []);
      const timeoff = await apiListTimeOff({ limit: 500 }).catch(() => []);
      const monthVal = controls.querySelector("#pay_month").value;

      const filtered = monthVal ? items.filter(t => monthIncludesDate(monthVal, itemDateOf(t))) : items.slice();
      const employees = {};
      filtered.forEach(t => {
        const emp = employeeNameOfItem(t);
        if (!emp) return;
        if (!employees[emp]) employees[emp] = [];
        employees[emp].push(t);
      });

      const monthPto = monthVal ? timeoff.filter(t => monthIncludesDate(monthVal, itemDateOf(t))) : timeoff.slice();
      const approvedPto = monthPto.filter(t => String(t.status || "").toLowerCase() === "approved");

      const allBreakdowns = Object.values(employees).map(entriesBreakdown);
      const totalHours = allBreakdowns.reduce((sum, b) => sum + b.worked, 0);
      const totalRegular = allBreakdowns.reduce((sum, b) => sum + b.regular, 0);
      const totalOTWorked = allBreakdowns.reduce((sum, b) => sum + b.ot, 0);
      const totalOTBank = Object.keys(employees).reduce((sum, emp) => sum + getOtBankHours(emp), 0);
      const totalOT = totalOTWorked + totalOTBank;
      const totalPtoBank = Object.keys(employees).reduce((sum, emp) => sum + getPtoBankHours(emp), 0);
      const totalPtoUsed = Object.keys(employees).reduce((sum, emp) => sum + approvedPtoHoursForEmployee(emp, approvedPto, (employees[emp] || []).filter(t => !!t.supervisor_approved)), 0);
      const totalPtoRemaining = totalPtoBank - totalPtoUsed;
      const uniqueEmployees = Object.keys(employees);
      const totalDaysOff = approvedPto.length;
      const pendingCards = filtered.filter(t => !t.supervisor_approved).length;
      const approvedCards = filtered.filter(t => !!t.supervisor_approved).length;
      const approvalRate = filtered.length ? Math.round((approvedCards / filtered.length) * 100) : 0;

      exportBtn.onclick = () => {
        const csv = buildCrewCsv(monthVal, filtered, approvedPto);
        downloadCsv("payroll_report.csv", csv);
      };

      summaryWrap.innerHTML = "";
      [
        metricCard("Employees", String(uniqueEmployees.length), "With timecards"),
        metricCard("Hours Worked", totalHours.toFixed(2), monthVal || "Current"),
        metricCard("Regular Hours", totalRegular.toFixed(2), "Up to 8 per day"),
        metricCard("OT Hours", totalOT.toFixed(2), `Worked ${totalOTWorked.toFixed(2)} + Adj ${totalOTBank.toFixed(2)}`),
        metricCard("PTO Bank", totalPtoBank.toFixed(2), "Entered in payroll"),
        metricCard("PTO Used", totalPtoUsed.toFixed(2), "Approved PTO only"),
        metricCard("PTO Remaining", totalPtoRemaining.toFixed(2), "Bank minus used"),
        metricCard("Days Off", String(totalDaysOff), "Approved entries"),
        metricCard("Cards Pending", String(pendingCards), "Awaiting approval"),
        metricCard("Approval Rate", `${approvalRate}%`, `${approvedCards}/${filtered.length || 0} approved`),
      ].forEach(c => summaryWrap.appendChild(c));

      list.innerHTML = "";
      if (!uniqueEmployees.length) {
        list.innerHTML = `<div class="card"><div class="hint">No employee totals found for this month.</div></div>`;
        return;
      }

      const rows = document.createElement("div");
      rows.style.display = "grid";
      rows.style.gap = "10px";

      uniqueEmployees.sort((a,b)=>a.localeCompare(b)).forEach(emp => {
        const entries = employees[emp] || [];
        const breakdown = entriesBreakdown(entries);
        const empApproved = entries.filter(t => !!t.supervisor_approved).length;
        const empPending = entries.filter(t => !t.supervisor_approved).length;
        const empPtoItems = approvedPto.filter(t => employeeNameOfItem(t) === emp);
        const empDaysOff = empPtoItems.length;
        const empPtoBank = getPtoBankHours(emp);
        const empPtoUsed = approvedPtoHoursForEmployee(emp, approvedPto, entries.filter(t => !!t.supervisor_approved));
        const empPtoRemaining = empPtoBank - empPtoUsed;
        const empOtBank = getOtBankHours(emp);
        const empOtTotal = breakdown.ot + empOtBank;
        const latest = entries.slice().sort((a,b)=>String(itemDateOf(b)).localeCompare(String(itemDateOf(a))))[0];

        const row = document.createElement("div");
        row.className = "jobrow";
        row.innerHTML = `
          <div class="jobrow-top">
            <div class="jobrow-name">${escapeHtml(emp)}</div>
            <div class="hint">${breakdown.worked.toFixed(2)} hrs</div>
          </div>
          <div class="jobrow-addr">Regular ${breakdown.regular.toFixed(2)} | OT ${breakdown.ot.toFixed(2)} | OT Adj ${empOtBank.toFixed(2)} | OT Total ${empOtTotal.toFixed(2)} | PTO Remaining ${empPtoRemaining.toFixed(2)}</div>
          <div class="hint" style="margin-top:6px;">Approved ${empApproved}/${entries.length} | Pending ${empPending} | Days Off ${empDaysOff} | Last card: ${escapeHtml(formatDisplayDate(itemDateOf(latest)) || "—")}</div>
        `;
        row.addEventListener("click", () => openTechBreakdown(emp, entries, monthVal, approvedPto));
        rows.appendChild(row);
      });

      list.appendChild(rows);
    }

    const monthInput = controls.querySelector("#pay_month");
    if (monthInput) {
      const now = new Date();
      monthInput.value = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2, "0")}`;
      monthInput.addEventListener("change", refresh);
    }

    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
    refresh();
  }

  function renderDataCenterView() {
    setNavActive(navDataCenter);
    setActiveChip("Office Flow");
    const leadEstimatorOnly = !!(currentUser && currentUser.role === "lead");
    setWorkspace(leadEstimatorOnly ? "Data Center - Estimator Activity" : "Data Center");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const tabs = document.createElement("div");
    tabs.style.display = "flex";
    tabs.style.gap = "8px";
    tabs.style.flexWrap = "wrap";
 
    const btnDashboard = document.createElement("button"); btnDashboard.className = "btn btn-orange"; btnDashboard.textContent = "Productivity";
    const btnRollUp = document.createElement("button"); btnRollUp.className = "btn"; btnRollUp.textContent = "Roll Up";
    const btnEstimator = document.createElement("button"); btnEstimator.className = leadEstimatorOnly ? "btn btn-orange" : "btn"; btnEstimator.textContent = "Estimator Activity";
    if (leadEstimatorOnly) {
      tabs.appendChild(btnEstimator);
    } else {
      [btnDashboard, btnRollUp, btnEstimator].forEach(b => tabs.appendChild(b));
    }
 
    const monthBar = document.createElement("div");
    monthBar.style.display = "flex";
    monthBar.style.justifyContent = "space-between";
    monthBar.style.alignItems = "center";
    monthBar.style.margin = "12px 0";
    const prevBtn = document.createElement("button"); prevBtn.className = "btn"; prevBtn.innerHTML = "&larr; Prev Month";
    const monthText = document.createElement("div"); monthText.style.fontWeight = "1000"; monthText.style.fontSize = "18px";
    const nextBtn = document.createElement("button"); nextBtn.className = "btn"; nextBtn.innerHTML = "Next Month &rarr;";
    monthBar.append(prevBtn, monthText, nextBtn);
 
    const body = document.createElement("div");
    root.append(tabs, monthBar, body);
 
    let currentMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
    let activeTab = leadEstimatorOnly ? "estimator" : "dashboard";
 
    const monthKey = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}`;
    const monthPretty = d => d.toLocaleDateString(undefined,{month:"long", year:"numeric"});
    const setTab = () => { [[btnDashboard,"dashboard"],[btnRollUp,"rollup"],[btnEstimator,"estimator"]].forEach(([b,k]) => { b.className = activeTab===k ? "btn btn-orange" : "btn"; }); };
 
    async function loadData() {
      const month = monthKey(currentMonth);
      const [jobs, timecards, docs] = await Promise.all([apiListJobs({ limit: 5000 }).catch(() => []), apiListTimecards({ limit: 5000 }).catch(() => []), apiListDocuments().catch(() => [])]);
      return { month, monthJobs: jobs.filter(j => String(j.date || j.created_at || "").startsWith(month)), monthTimecards: timecards.filter(t => String(t.date || t.created_at || "").startsWith(month)), monthDocs: docs.filter(d => String(d.created_at || "").startsWith(month)) };
    }

    async function resolveDataCenterJob(ref) {
      if (!ref) return null;
      const refId = String(ref.id || ref.job_id || "").trim();
      const refJobNumber = String(ref.job_number || "").trim();
      const refEstimate = cleanDocRef(ref.estimate_number || ref.number || "");
      const refCustomer = String(ref.customer || ref.customer_name || "").trim().toLowerCase();
      const jobs = await apiListJobs({ limit: 5000 }).catch(() => []);
      let match = null;
      if (refId) match = jobs.find(j => String(j.id || "").trim() === refId) || null;
      if (!match && refEstimate) {
        match = jobs.find(j => cleanDocRef(j.estimate_number || "") === refEstimate) || null;
      }
      if (!match && refJobNumber) {
        const candidates = jobs.filter(j => String(j.job_number || "").trim() === refJobNumber);
        match = candidates.sort((a,b) => String(b.updated_at || b.created_at || "").localeCompare(String(a.updated_at || a.created_at || "")))[0] || null;
      }
      if (!match && refCustomer && refEstimate) {
        match = jobs.find(j => String(j.customer || "").trim().toLowerCase() === refCustomer && cleanDocRef(j.estimate_number || "") === refEstimate) || null;
      }
      return match || ref || null;
    }

    async function openDataCenterJob(ref) {
      const resolved = await resolveDataCenterJob(ref);
      if (!resolved) return;
      if (resolved.id) {
        try {
          const full = await apiGetJob(resolved.id);
          openDrawer("Job Details", (drawerBody) => {
            const local = document.createElement("div");
            drawerBody.appendChild(local);
            renderJobDetails(local, full, { afterSave: renderActiveTab, afterDelete: renderActiveTab });
          });
          return;
        } catch (e) {}
      }
      openDrawer(`Job ${resolved.job_number || "Details"}`, async (drawerBody) => {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
          <h3 style="margin:0;">${escapeHtml(resolved.customer || resolved.customer_name || resolved.job_number || "Job")}</h3>
          <div class="hint" style="margin-top:6px;">${escapeHtml(resolved.job_number || "")}${resolved.estimate_number ? ` - Est ${escapeHtml(resolved.estimate_number)}` : ""}</div>
          <div class="grid2" style="margin-top:12px;">
            <div><div class="label">Customer</div><div class="field">${escapeHtml(resolved.customer || resolved.customer_name || "")}</div></div>
            <div><div class="label">Job #</div><div class="field">${escapeHtml(resolved.job_number || "")}</div></div>
            <div><div class="label">Estimate #</div><div class="field">${formatDocRefDisplay(resolved.estimate_number || resolved.number || "")}</div></div>
            <div><div class="label">Status</div><div class="field">${escapeHtml(resolved.status || "")}</div></div>
            <div><div class="label">Address</div><div class="field">${escapeHtml(resolved.street_address || resolved.address || "")}</div></div>
            <div><div class="label">Date</div><div class="field">${escapeHtml(formatDisplayDate(resolved.date || ""))}</div></div>
          </div>`;
        drawerBody.appendChild(card);
      });
    }
 
    async function renderDashboardTab() {
      body.innerHTML = "";
      const { month, monthJobs, monthTimecards, monthDocs } = await loadData();
      monthText.textContent = monthPretty(currentMonth);
      nextBtn.disabled = month >= monthKey(new Date());
      const forms = monthJobs.flatMap(j => formsOf(j).map(f => ({ ...f, __job: j })));
      const leads = monthJobs.filter(j => j.kind === "sales_lead");
      const completed = monthJobs.filter(j => ["Complete", "Complete/Quote", "Done"].includes(j.status));
      const dispatch = monthJobs.filter(j => j.status === "Dispatch");
      const estimates = monthDocs.filter(d => d.type === "estimate");
      const invoices = monthDocs.filter(d => d.type === "invoice");
      const onsiteHours = forms.reduce((sum, f) => sum + Number(f.time_onsite_hours || 0), 0);
      const tcHours = monthTimecards.reduce((sum, t) => sum + calcTimeHours(t.start_time, t.end_time, !!t.lunch_taken, t.lunch_start, t.lunch_end), 0);
      const techMap = {};
      forms.forEach(f => { const tech = f.technician_name || "Unassigned"; techMap[tech] = (techMap[tech] || 0) + Number(f.time_onsite_hours || 0); });
      monthTimecards.forEach(t => { const tech = t.technician_name || t.employee_name || t.employee || "Unassigned"; techMap[tech] = (techMap[tech] || 0) + calcTimeHours(t.start_time, t.end_time, !!t.lunch_taken, t.lunch_start, t.lunch_end); });
      const statGrid = document.createElement("div");
      statGrid.style.display = "grid"; statGrid.style.gridTemplateColumns = "repeat(auto-fit, minmax(180px, 1fr))"; statGrid.style.gap = "12px";
      [["Jobs Created", monthJobs.length],["Sales Leads", leads.length],["Dispatch", dispatch.length],["Quote Sent", estimates.length],["Completed", completed.length],["Estimates", estimates.length],["Invoices", invoices.length],["Onsite Hours", onsiteHours.toFixed(2)],["Timecard Hours", tcHours.toFixed(2)]].forEach(([label,val]) => {
        const c = document.createElement("div"); c.className = "card"; c.innerHTML = `<div class="label">${label}</div><div style="font-size:28px; font-weight:1000; margin-top:6px;">${val}</div><div class="hint" style="margin-top:6px;">${monthPretty(currentMonth)}</div>`; statGrid.appendChild(c);
      });
      body.appendChild(statGrid);

      const approved = monthJobs.filter(j => isApprovedEstimateJob(j, month));
      const findLinkedJob = (doc) => monthJobs.find(j => {
        const docEstimate = cleanDocRef(doc.number || doc.estimate_number || "");
        const jobEstimate = cleanDocRef(j.estimate_number || "");
        return (docEstimate && jobEstimate === docEstimate)
          || (String(doc.job_id || "").trim() && String(j.id || "").trim() === String(doc.job_id || "").trim())
          || (String(doc.job_number || "").trim() && String(j.job_number || "").trim() === String(doc.job_number || "").trim());
      }) || null;
      const sentQuotes = [];
      const seenQuoteKeys = new Set();
      estimates
        .slice()
        .sort((a,b) => String(b.date || b.created_at || "").localeCompare(String(a.date || a.created_at || "")))
        .forEach(d => {
          const estimateNo = cleanDocRef(d.number || d.estimate_number || "");
          const key = [estimateNo, String(d.job_id || "").trim(), String(d.job_number || "").trim()].join("|");
          if (seenQuoteKeys.has(key)) return;
          seenQuoteKeys.add(key);
          sentQuotes.push({ doc: d, job: findLinkedJob(d) });
        });

      const makeDataCenterRow = ({ title, statusLabel, statusKind, subtitle, address, clickItem, fallbackJob }) => {
        const row = document.createElement("div");
        row.className = "jobrow";
        row.style.cursor = "pointer";
        row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${escapeHtml(title || "Job")}</div>${statusKind === "approved" ? statusPill("Approved").outerHTML : statusPill(statusLabel || "Quote Sent").outerHTML}</div><div class="jobrow-addr">${escapeHtml(subtitle || "")}</div><div class="hint">${escapeHtml(address || "")}</div>`;
        row.addEventListener("click", () => { openDataCenterJob(clickItem || fallbackJob || {}); });
        return row;
      };

      const approvalLayout=document.createElement("div"); approvalLayout.style.display="grid"; approvalLayout.style.gridTemplateColumns="1fr 1fr"; approvalLayout.style.gap="14px"; approvalLayout.style.marginTop="14px";
      const leftCard=document.createElement("div"); leftCard.className="card"; leftCard.innerHTML=`<h3>Quote Sent</h3><div class="hint">All estimates sent this month, even if later approved or denied.</div>`;
      const leftList=document.createElement("div"); leftList.style.marginTop="12px";
      if (!sentQuotes.length) leftList.innerHTML=`<div class="hint">No estimates were sent this month.</div>`;
      else sentQuotes.forEach(({doc, job})=>{
        const title = job?.customer || doc.customer || doc.customer_name || doc.job_number || cleanDocRef(doc.number || doc.estimate_number || "") || "Estimate";
        const subtitle = `${job?.job_number ? `Job #${job.job_number}` : (doc.job_number ? `Job #${doc.job_number}` : "")}${cleanDocRef(doc.number || doc.estimate_number || "") ? `${(job?.job_number || doc.job_number) ? ' - ' : ''}Est ${cleanDocRef(doc.number || doc.estimate_number || '')}` : ""}${job?.status ? ` - ${job.status}` : ""}`;
        const address = job?.street_address || job?.address || doc.address || "";
        leftList.appendChild(makeDataCenterRow({ title, statusLabel: job?.status || "Quote Sent", subtitle, address, clickItem: job || { id: doc.job_id, job_number: doc.job_number, customer: doc.customer || doc.customer_name || "", address: doc.address || "", estimate_number: cleanDocRef(doc.number || doc.estimate_number || ""), status: job?.status || "Quote Sent" }, fallbackJob: job }));
      });
      leftCard.appendChild(leftList);
      const rightCard=document.createElement("div"); rightCard.className="card"; rightCard.innerHTML=`<h3>Approved Jobs</h3><div class="hint">Customer - Job # - Estimate #</div>`;
      const rightList=document.createElement("div"); rightList.style.marginTop="12px";
      if (!approved.length) rightList.innerHTML=`<div class="hint">No approved jobs yet.</div>`;
      else approved.forEach(j=>{
        const subtitle = `${j.job_number ? `Job #${j.job_number}` : ""}${j.estimate_number ? `${j.job_number ? ' - ' : ''}Est ${j.estimate_number}` : ""}`;
        rightList.appendChild(makeDataCenterRow({ title: j.customer||j.job_number, statusKind: "approved", subtitle, address: j.street_address || j.address || "", clickItem: j, fallbackJob: j }));
      });
      rightCard.appendChild(rightList);
      approvalLayout.append(leftCard,rightCard);
      body.appendChild(approvalLayout);
    }
 


    async function renderRollUpTab() {
      body.innerHTML = "";
      const { month, monthJobs, monthTimecards } = await loadData();
      monthText.textContent = monthPretty(currentMonth);
      nextBtn.disabled = month >= monthKey(new Date());

      const formsForJob = (j) => formsOf(j).filter(f => String(f.door_type || "").toLowerCase() === "roll up");
      const rollUps = monthJobs.filter(j => formsForJob(j).length > 0);

      const timecardRollups = monthTimecards.filter(t => {
        const note = `${t.customer || ""} ${t.job_number || ""} ${t.notes || t.description || ""}`.toLowerCase();
        return note.includes("roll up") || note.includes("rollup");
      });

      const techTotals = {};
      const detailRows = [];
      let totalFormHours = 0;
      let totalTimecardRollupHours = 0;

      rollUps.forEach(j => {
        const forms = formsForJob(j);
        forms.forEach(f => {
          const tech = String(f.technician_name || "Unassigned").trim() || "Unassigned";
          const hrs = Number(f.time_onsite_hours || 0);
          totalFormHours += hrs;
          techTotals[tech] = techTotals[tech] || { total: 0, jobs: 0 };
          techTotals[tech].total += hrs;
          techTotals[tech].jobs += 1;
          detailRows.push({
            date: j.date || j.created_at || "",
            customer: j.customer || j.customer_name || "",
            address: j.street_address || j.address || "",
            technician: tech,
            hours: hrs,
            status: j.status || "",
            job_number: j.job_number || "",
            door_location: f.door_location || "",
            source: "Completion Form",
            jobRef: j,
          });
        });
      });

      timecardRollups.forEach(t => {
        const tech = String(t.technician_name || t.employee_name || t.employee || "Unassigned").trim() || "Unassigned";
        const hrs = calcTimeHours(t.start_time, t.end_time, !!t.lunch_taken, t.lunch_start, t.lunch_end);
        totalTimecardRollupHours += hrs;
        techTotals[tech] = techTotals[tech] || { total: 0, jobs: 0 };
        techTotals[tech].total += hrs;
        detailRows.push({
          date: t.date || t.created_at || "",
          customer: t.customer || "",
          address: t.address || "",
          technician: tech,
          hours: hrs,
          status: "Timecard",
          job_number: t.job_number || "",
          door_location: "",
          source: "Timecard",
          jobRef: null,
        });
      });

      const totalHours = totalFormHours + totalTimecardRollupHours;
      const totalJobs = rollUps.length;
      const uniqueTechs = Object.keys(techTotals).length;
      const totalCost = Object.entries(techTotals).reduce((sum, [tech, data]) => {
        const prof = getRollupProfile(tech, currentMonth);
        return sum + (Number(data.total || 0) * Number(prof.wage || 0));
      }, 0);

      const exportBtn = document.createElement("button");
      exportBtn.className = "btn btn-orange";
      exportBtn.textContent = "Export Roll Up Report";
      exportBtn.addEventListener("click", () => {
        let csv = "Date,Customer,Address,Technician,Hours,Job Status,Job Number,Door Location,Source,Wage,Total Cost\n";
        detailRows.slice().sort((a,b)=>String(a.date).localeCompare(String(b.date))).forEach(r => {
          const prof = getRollupProfileForDate(r.technician, r.date || currentMonth);
          const cost = Number(r.hours || 0) * Number(prof.wage || 0);
          const esc = (v) => `"${String(v || "").replace(/"/g, '""')}"`;
          csv += [esc(r.date), esc(r.customer), esc(r.address), esc(r.technician), Number(r.hours || 0).toFixed(2), esc(r.status), esc(r.job_number), esc(r.door_location), esc(r.source), Number(prof.wage || 0).toFixed(2), cost.toFixed(2)].join(",") + "\n";
        });
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "rollup_report.csv";
        a.click();
        URL.revokeObjectURL(url);
      });
      body.appendChild(exportBtn);

      const summaryWrap = document.createElement("div");
      summaryWrap.style.display = "grid";
      summaryWrap.style.gridTemplateColumns = "repeat(auto-fit, minmax(180px, 1fr))";
      summaryWrap.style.gap = "12px";
      summaryWrap.style.margin = "14px 0";

      const metricCard = (label, value, hint = "") => {
        const card = document.createElement("div");
        card.className = "card";
        card.style.padding = "14px";
        card.innerHTML = `
          <div style="font-size:12px;font-weight:800;opacity:.75;margin-bottom:6px;">${escapeHtml(label)}</div>
          <div style="font-size:30px;font-weight:900;line-height:1;">${escapeHtml(value)}</div>
          <div class="hint" style="margin-top:6px;">${escapeHtml(hint)}</div>
        `;
        return card;
      };

      [
        metricCard("Roll Up Jobs", String(totalJobs), monthPretty(currentMonth)),
        metricCard("Entries", String(detailRows.length), "Logged roll up entries"),
        metricCard("Total Hours", totalHours.toFixed(2), "All technicians"),
        metricCard("Technicians", String(uniqueTechs), "With roll up hours"),
        metricCard("Total Cost", totalCost.toFixed(2), "Hours × wage"),
      ].forEach(c => summaryWrap.appendChild(c));
      body.appendChild(summaryWrap);

      const layout = document.createElement("div");
      layout.style.display = "grid";
      layout.style.gridTemplateColumns = "1.35fr 1fr";
      layout.style.gap = "14px";

      const leftCard = document.createElement("div");
      leftCard.className = "card";
      leftCard.innerHTML = `<h3>Roll Up Log</h3><div class="hint">${totalJobs} jobs | ${detailRows.length} entries | ${totalHours.toFixed(2)} hrs</div>`;

      const leftList = document.createElement("div");
      leftList.style.marginTop = "12px";
      if (!detailRows.length) {
        leftList.innerHTML = `<div class="hint">No matching roll up jobs for this month.</div>`;
      } else {
        detailRows
          .slice()
          .sort((a, b) => String(b.date || "").localeCompare(String(a.date || "")))
          .forEach(r => {
            const prof = getRollupProfileForDate(r.technician, r.date || currentMonth);
            const cost = Number(r.hours || 0) * Number(prof.wage || 0);
            const row = document.createElement("div");
            row.className = "jobrow";
            row.style.cursor = r.jobRef ? "pointer" : "default";
            row.innerHTML = `
              <div class="jobrow-top">
                <div class="jobrow-name">${escapeHtml(formatDisplayDate(r.date) || r.customer || r.job_number || "Roll Up Entry")}</div>
                <div class="hint">${Number(r.hours || 0).toFixed(2)} hrs</div>
              </div>
              <div class="jobrow-addr">${escapeHtml(r.customer || "")}${r.job_number ? ` - Job #${escapeHtml(r.job_number)}` : ""}${r.door_location ? ` - ${escapeHtml(r.door_location)}` : ""}</div>
              <div class="hint" style="margin-top:6px;">${escapeHtml(r.address || "")}</div>
              <div class="hint" style="margin-top:6px;">${escapeHtml(r.technician)} - ${escapeHtml(r.status || "")} - Wage ${Number(prof.wage || 0).toFixed(2)} - Cost ${cost.toFixed(2)}</div>
            `;
            if (r.jobRef) row.addEventListener("click", () => openDataCenterJob(r.jobRef));
            leftList.appendChild(row);
          });
      }
      leftCard.appendChild(leftList);

      const rightCard = document.createElement("div");
      rightCard.className = "card";
      rightCard.innerHTML = `<h3>Technician Roll Up Report</h3><div class="hint">${monthPretty(currentMonth)}</div>`;

      const rightList = document.createElement("div");
      rightList.style.marginTop = "12px";
      const techRows = Object.entries(techTotals)
        .map(([tech, data]) => {
          const total = Number(data.total || 0);
          return [tech, { ...data, total }];
        })
        .sort((a, b) => b[1].total - a[1].total);

      if (!techRows.length) {
        rightList.innerHTML = `<div class="hint">No technician hours logged yet.</div>`;
      } else {
        techRows.forEach(([tech, data]) => {
          const prof = getRollupProfile(tech, currentMonth);
          const totalCostTech = data.total * Number(prof.wage || 0);

          const row = document.createElement("div");
          row.className = "jobrow";
          row.innerHTML = `
            <div class="jobrow-top">
              <div class="jobrow-name">${escapeHtml(tech)}</div>
              <div class="hint">${Number(data.total).toFixed(2)} hrs</div>
            </div>
            <div class="jobrow-addr">Total Hours ${Number(data.total).toFixed(2)} | Jobs ${data.jobs || 0}</div>
            <div class="hint" style="margin-top:6px;">Wage ${Number(prof.wage || 0).toFixed(2)} | Total Cost ${totalCostTech.toFixed(2)}</div>
          `;

          const actions = document.createElement("div");
          actions.style.display = "flex";
          actions.style.gap = "8px";
          actions.style.marginTop = "8px";

          const editBtn = document.createElement("button");
          editBtn.className = "btn";
          editBtn.textContent = "Edit";
          editBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const wage = prompt(`Hourly wage for ${tech}:`, String(Number(prof.wage || 0).toFixed(2)));
            if (wage === null) return;
            const wageNum = Number(wage || 0);
            if (Number.isNaN(wageNum)) return alert("Enter a valid wage.");
            setRollupProfile(tech, wageNum, 1, currentMonth);
            renderActiveTab();
          });

          const exportTechBtn = document.createElement("button");
          exportTechBtn.className = "btn btn-orange";
          exportTechBtn.textContent = "Export";
          exportTechBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            let csv = "Date,Customer,Address,Technician,Hours,Job Status,Job Number,Door Location,Source,Wage,Total Cost\n";
            detailRows.filter(r => r.technician === tech).forEach(r => {
              const p = getRollupProfileForDate(tech, r.date || currentMonth);
              const cost = Number(r.hours || 0) * Number(p.wage || 0);
              const esc = (v) => `"${String(v || "").replace(/"/g, '""')}"`;
              csv += [esc(r.date), esc(r.customer), esc(r.address), esc(r.technician), Number(r.hours || 0).toFixed(2), esc(r.status), esc(r.job_number), esc(r.door_location), esc(r.source), Number(p.wage || 0).toFixed(2), cost.toFixed(2)].join(",") + "\n";
            });
            const blob = new Blob([csv], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${tech.replace(/\s+/g, "_").toLowerCase()}_rollup_report.csv`;
            a.click();
            URL.revokeObjectURL(url);
          });

          actions.appendChild(editBtn);
          actions.appendChild(exportTechBtn);
          row.appendChild(actions);
          rightList.appendChild(row);
        });
      }
      rightCard.appendChild(rightList);

      layout.append(leftCard, rightCard);
      body.appendChild(layout);
    }

    async function renderApprovalTab() {
      body.innerHTML="";
      const { month, monthJobs } = await loadData();
      monthText.textContent = monthPretty(currentMonth); nextBtn.disabled = month >= monthKey(new Date());
      const quoteSent = monthJobs.filter(j => j.status === "Quote Sent");
      const approved = monthJobs.filter(j => isApprovedEstimateJob(j, month));
      const layout=document.createElement("div"); layout.style.display="grid"; layout.style.gridTemplateColumns="1fr 1fr"; layout.style.gap="14px";
      const leftCard=document.createElement("div"); leftCard.className="card"; leftCard.innerHTML=`<h3>Quote Sent</h3><div class="hint">Waiting on approval</div>`;
      const leftList=document.createElement("div"); leftList.style.marginTop="12px";
      if (!quoteSent.length) leftList.innerHTML=`<div class="hint">No records currently in Quote Sent.</div>`;
      else quoteSent.forEach(j=>{ const row=document.createElement("div"); row.className="jobrow"; row.innerHTML=`<div class="jobrow-top"><div class="jobrow-name">${j.customer||j.job_number}</div>${statusPill(j.status).outerHTML}</div><div class="jobrow-addr">${j.customer||""}${j.job_number?` - Job #${j.job_number}`:""}${j.estimate_number?` - Est ${j.estimate_number}`:""}</div><div class="hint">${j.street_address || j.address || ""}</div>`; leftList.appendChild(row);});
      leftCard.appendChild(leftList);
      const rightCard=document.createElement("div"); rightCard.className="card"; rightCard.innerHTML=`<h3>Approved Jobs</h3><div class="hint">Customer - Job # - Estimate #</div>`;
      const rightList=document.createElement("div"); rightList.style.marginTop="12px";
      if (!approved.length) rightList.innerHTML=`<div class="hint">No approved jobs yet.</div>`;
      else approved.forEach(j=>{ const row=document.createElement("div"); row.className="jobrow"; row.innerHTML=`<div class="jobrow-top"><div class="jobrow-name">${j.customer||j.job_number}</div><div class="hint">Approved</div></div><div class="jobrow-addr">${j.customer||""}${j.job_number?` - Job #${j.job_number}`:""}${j.estimate_number?` - Est ${j.estimate_number}`:""}</div><div class="hint">${j.street_address || j.address || ""}</div>`; rightList.appendChild(row);});
      rightCard.appendChild(rightList); layout.append(leftCard,rightCard); body.appendChild(layout);
    }
 
    async function renderEstimatorTab() {
      body.innerHTML = "";
      const { month, monthJobs, monthDocs } = await loadData();
      monthText.textContent = monthPretty(currentMonth);
      nextBtn.disabled = month >= monthKey(new Date());

      const approvedJobs = monthJobs.filter(j => isApprovedEstimateJob(j, month));
      const approvedEstimateNumbers = new Set(
        approvedJobs.map(j => cleanDocRef(j.estimate_number || j.estimate_no || "")).filter(Boolean)
      );
      const approvedJobIds = new Set(approvedJobs.map(j => String(j.id || "").trim()).filter(Boolean));
      const approvedJobNumbers = new Set(approvedJobs.map(j => String(j.job_number || "").trim()).filter(Boolean));

      const estimateDetailsByEmployee = {};
      monthDocs.filter(d => d.type === "estimate").forEach(d => {
        const who = String(d.completed_by || d.created_by || "Unassigned").trim() || "Unassigned";
        if (!estimateDetailsByEmployee[who]) estimateDetailsByEmployee[who] = [];
        const estimateNo = cleanDocRef(d.number || d.estimate_number || d.estimate_no || "");
        const docJobId = String(d.job_id || "").trim();
        const docJobNumber = String(d.job_number || "").trim();
        const linkedJob = monthJobs.find(j => {
          const jobEstimate = cleanDocRef(j.estimate_number || j.estimate_no || "");
          return (estimateNo && jobEstimate === estimateNo)
            || (docJobId && String(j.id || "").trim() === docJobId)
            || (docJobNumber && String(j.job_number || "").trim() === docJobNumber);
        }) || null;

        const isApproved = !!(
          (estimateNo && approvedEstimateNumbers.has(estimateNo)) ||
          (docJobId && approvedJobIds.has(docJobId)) ||
          (docJobNumber && approvedJobNumbers.has(docJobNumber)) ||
          (linkedJob && isApprovedEstimateJob(linkedJob, month))
        );

        estimateDetailsByEmployee[who].push({
          ...d,
          __estimateNo: estimateNo,
          __approved: isApproved,
          __linkedJob: linkedJob
        });
      });

      const leaderboard = Object.entries(estimateDetailsByEmployee).map(([name, docs]) => {
        const sent = docs.length;
        const approved = docs.filter(d => d.__approved).length;
        return {
          name,
          sent,
          approved,
          docs: docs.slice().sort((a,b) => String(b.date || b.created_at || "").localeCompare(String(a.date || a.created_at || "")))
        };
      }).sort((a,b) => (b.sent - a.sent) || (b.approved - a.approved) || a.name.localeCompare(b.name));

      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `<h3>Employee Estimate Activity</h3><div class="hint">${monthPretty(currentMonth)} - ranked by estimates sent</div>`;

      const list = document.createElement("div");
      list.style.marginTop = "12px";

      if (!leaderboard.length) {
        list.innerHTML = `<div class="hint">No employee estimates found for this month.</div>`;
      } else {
        leaderboard.forEach((entry) => {
          const rowWrap = document.createElement("div");
          rowWrap.style.marginBottom = "10px";

          const row = document.createElement("div");
          row.className = "jobrow estimator-parent-row";
          row.style.cursor = "pointer";
          row.innerHTML = `
            <div class="jobrow-top">
              <div class="jobrow-name">${escapeHtml(entry.name)}</div>
              <div class="hint">${entry.sent} sent • ${entry.approved} approved</div>
            </div>
            <div class="hint" style="margin-top:6px;">Click to view estimate numbers</div>
          `;

          const inline = document.createElement("div");
          inline.className = "estimator-inline-list";
          inline.style.display = "none";
          inline.style.margin = "8px 0 0 14px";

          const renderInline = () => {
            inline.innerHTML = "";
            if (!entry.docs.length) {
              inline.innerHTML = `<div class="hint" style="padding:6px 0 2px 0;">No estimates found for ${escapeHtml(entry.name)}.</div>`;
              return;
            }
            entry.docs.forEach((d) => {
              const estimateNo = d.__estimateNo || cleanDocRef(d.number || d.estimate_number || d.estimate_no || "") || "Estimate";
              const linkedJob = d.__linkedJob;
              const customer = (linkedJob && linkedJob.customer) || d.customer || d.customer_name || "";
              const jobNo = (linkedJob && linkedJob.job_number) || d.job_number || "";
              const docDate = formatDisplayDate(d.date || d.created_at || "");
              const item = document.createElement("div");
              item.className = "jobrow";
              item.style.cursor = linkedJob ? "pointer" : "default";
              item.style.marginBottom = "8px";
              item.innerHTML = `
                <div class="jobrow-top">
                  <div class="jobrow-name">${escapeHtml(estimateNo)}</div>
                  <div class="hint">${d.__approved ? "Approved" : "Sent"}</div>
                </div>
                <div class="jobrow-addr">${escapeHtml(customer || "")}${jobNo ? ` - Job #${escapeHtml(jobNo)}` : ""}</div>
                <div class="hint" style="margin-top:6px;">${escapeHtml(docDate || "")}</div>
              `;
              if (linkedJob) item.addEventListener("click", (ev) => { ev.stopPropagation(); openDataCenterJob(linkedJob); });
              inline.appendChild(item);
            });
          };

          row.addEventListener("click", () => {
            const willOpen = inline.style.display === "none";
            list.querySelectorAll(".estimator-inline-list").forEach(el => { el.style.display = "none"; });
            list.querySelectorAll(".estimator-parent-row").forEach(el => { el.classList.remove("navbtn-active"); });
            if (willOpen) {
              renderInline();
              inline.style.display = "block";
              row.classList.add("navbtn-active");
            } else {
              inline.style.display = "none";
              row.classList.remove("navbtn-active");
            }
          });

          rowWrap.appendChild(row);
          rowWrap.appendChild(inline);
          list.appendChild(rowWrap);
        });
      }

      card.appendChild(list);
      body.appendChild(card);
    }

    async function renderActiveTab() { setTab(); if (activeTab==="rollup") return renderRollUpTab(); if (activeTab==="estimator") return renderEstimatorTab(); return renderDashboardTab(); }
    if (!leadEstimatorOnly) btnDashboard.addEventListener("click",()=>{activeTab="dashboard";renderActiveTab();});
    if (!leadEstimatorOnly) btnRollUp.addEventListener("click",()=>{activeTab="rollup";renderActiveTab();});
    btnEstimator.addEventListener("click",()=>{activeTab="estimator";renderActiveTab();});
    prevBtn.addEventListener("click",()=>{currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth()-1, 1); renderActiveTab();});
    nextBtn.addEventListener("click",()=>{currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth()+1, 1); renderActiveTab();});
    workspaceBody.innerHTML=""; workspaceBody.appendChild(root); currentView={ refresh: renderActiveTab }; renderActiveTab();
  }
 
function renderCustomersView() {
    setNavActive(navCustomers);
    setActiveChip("Work Flow");
    setWorkspace("Customers / Contacts");
    clearWorkspaceActions();

    const root = document.createElement("div");
    const hero = document.createElement("div");
    hero.className = "card";
    hero.innerHTML = `<h3>Customers / Contacts</h3><div class="hint">Search customers, open a customer record, and view all linked contacts in one place.</div>`;

    const controls = document.createElement("div");
    controls.className = "card";
    controls.style.marginTop = "12px";
    controls.innerHTML = `
      <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
        <button class="btn btn-orange" id="cc_add_customer">Add Customer</button>
        <button class="btn" id="cc_add_contact">Add Contact</button>
        <input class="input" id="cc_search" placeholder="Search customer, contact, phone, email, address, notes" style="max-width:420px; margin-left:auto;" />
        <button class="btn" id="cc_search_btn">Search</button>
        <button class="btn" id="cc_clear_btn">Clear</button>
      </div>
    `;

    const list = document.createElement("div");
    list.style.display = "grid";
    list.style.gap = "8px";
    list.style.marginTop = "12px";

    let query = "";

    function openContactDrawer(contact, customer = null) {
      openDrawer(contact.name || "Contact", async (drawerBody) => {
        const customers = await apiListCustomers().catch(() => []);
        const linkedCustomer = customer || customers.find(c => String(c.id || "") === String(contact.customer_id || "")) || null;

        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
          <h3 style="margin:0;">${escapeHtml(contact.name || "")}</h3>
          <div class="hint" style="margin-top:6px;">${escapeHtml(linkedCustomer?.company_name || contact.company_name || "")}</div>
          <div class="grid2" style="margin-top:12px;">
            <div><div class="label">Phone</div><div class="field">${escapeHtml(contact.phone_number || "")}</div></div>
            <div><div class="label">Cell</div><div class="field">${escapeHtml(contact.cell_phone || "")}</div></div>
            <div><div class="label">Email</div><div class="field">${escapeHtml(contact.email || "")}</div></div>
            <div><div class="label">Title</div><div class="field">${escapeHtml(contact.title || "")}</div></div>
          </div>
          <div style="margin-top:10px;"><div class="label">Notes</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(contact.notes || "")}</div></div>
        `;

        const actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "8px";
        actions.style.marginTop = "12px";

        const editBtn = document.createElement("button");
        editBtn.className = "btn";
        editBtn.textContent = "Edit Contact";
        editBtn.addEventListener("click", async () => {
          try {
            const name = prompt("Name:", contact.name || "") ?? contact.name;
            if (!String(name || "").trim()) return;
            const company_name = prompt("Company:", linkedCustomer?.company_name || contact.company_name || "") ?? (linkedCustomer?.company_name || contact.company_name || "");
            const phone_number = prompt("Phone:", contact.phone_number || "") ?? contact.phone_number;
            const cell_phone = prompt("Cell:", contact.cell_phone || "") ?? contact.cell_phone;
            const email = prompt("Email:", contact.email || "") ?? contact.email;
            const title = prompt("Title:", contact.title || "") ?? contact.title;
            const notes = prompt("Notes:", contact.notes || "") ?? contact.notes;
            const matched = customers.find(c => normalizeText(c.company_name) === normalizeText(company_name));
            await apiUpdateContact(contact.id, { name, company_name, customer_id: matched?.id || "", phone_number, cell_phone, email, title, notes });
            if (currentView && currentView.refresh) await currentView.refresh();
          } catch (e) { alert(e.message || String(e)); }
        });
        actions.appendChild(editBtn);
        card.appendChild(actions);

        drawerBody.appendChild(card);
      });
    }

    function openCustomerDrawer(customer, contacts) {
      openDrawer(customer.company_name || "Customer", (drawerBody) => {
        const linked = (contacts || []).filter(c => {
          const cid = String(c.customer_id || "").trim();
          return (cid && cid === String(customer.id || "").trim()) || companyMatches(c.company_name, customer.company_name);
        });

        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
          <h3 style="margin:0;">${escapeHtml(customer.company_name || "")}</h3>
          <div class="hint" style="margin-top:6px;">${escapeHtml([customer.address, customer.city, customer.state, customer.zip_code].filter(Boolean).join(", "))}</div>
          <div class="grid2" style="margin-top:12px;">
            <div><div class="label">Phone</div><div class="field">${escapeHtml(customer.phone_number || "")}</div></div>
            <div><div class="label">Email</div><div class="field">${escapeHtml(customer.email || "")}</div></div>
          </div>
          <div style="margin-top:10px;"><div class="label">Notes</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(customer.notes || "")}</div></div>
          <div style="margin-top:14px;"><div class="label">Contacts</div></div>
        `;

        const linkedWrap = document.createElement("div");
        linkedWrap.style.display = "grid";
        linkedWrap.style.gap = "8px";
        linkedWrap.style.marginTop = "8px";
        if (!linked.length) {
          linkedWrap.innerHTML = `<div class="hint">No linked contacts yet.</div>`;
        } else {
          linked.forEach(contact => {
            const row = document.createElement("div");
            row.className = "jobrow";
            row.style.cursor = "pointer";
            row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${escapeHtml(contact.name || "")}</div></div><div class="jobrow-addr">${escapeHtml(contact.phone_number || contact.cell_phone || "")}${contact.email ? ` - ${escapeHtml(contact.email)}` : ""}</div>`;
            row.addEventListener("click", () => openContactDrawer(contact, customer));
            linkedWrap.appendChild(row);
          });
        }
        card.appendChild(linkedWrap);

        const actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.gap = "8px";
        actions.style.marginTop = "12px";

        const editBtn = document.createElement("button");
        editBtn.className = "btn";
        editBtn.textContent = "Edit Customer";
        editBtn.addEventListener("click", async () => {
          try {
            const company_name = prompt("Company Name:", customer.company_name || "") ?? customer.company_name;
            if (!String(company_name || "").trim()) return;
            const address = prompt("Address:", customer.address || "") ?? customer.address;
            const city = prompt("City:", customer.city || "") ?? customer.city;
            const state = prompt("State:", customer.state || "") ?? customer.state;
            const zip_code = prompt("ZIP:", customer.zip_code || "") ?? customer.zip_code;
            const phone_number = prompt("Phone:", customer.phone_number || "") ?? customer.phone_number;
            const email = prompt("Email:", customer.email || "") ?? customer.email;
            const notes = prompt("Notes:", customer.notes || "") ?? customer.notes;
            await apiUpdateCustomer(customer.id, { company_name, address, city, state, zip_code, phone_number, email, notes });
            if (currentView && currentView.refresh) await currentView.refresh();
          } catch (e) { alert(e.message || String(e)); }
        });

        const addContactBtn = document.createElement("button");
        addContactBtn.className = "btn btn-orange";
        addContactBtn.textContent = "Add Contact";
        addContactBtn.addEventListener("click", async () => {
          try {
            const name = (prompt("Contact name:") || "").trim();
            if (!name) return;
            const phone_number = (prompt("Phone:", "") || "").trim();
            const cell_phone = (prompt("Cell:", "") || "").trim();
            const email = (prompt("Email:", "") || "").trim();
            const title = (prompt("Title:", "") || "").trim();
            const notes = (prompt("Notes:", "") || "").trim();
            await apiCreateContact({ name, company_name: customer.company_name || "", customer_id: customer.id || "", phone_number, cell_phone, email, title, notes });
            if (currentView && currentView.refresh) await currentView.refresh();
          } catch (e) { alert(e.message || String(e)); }
        });

        actions.append(editBtn, addContactBtn);
        card.appendChild(actions);
        drawerBody.appendChild(card);
      });
    }

    async function renderList() {
      const [customers, contacts] = await Promise.all([
        apiListCustomers().catch(() => []),
        apiListContacts().catch(() => []),
      ]);
      list.innerHTML = "";
      const q = normalizeText(query);
      let rows = customers.slice();
      if (q) {
        rows = rows.filter(customer => {
          const linked = contacts.filter(c => {
            const cid = String(c.customer_id || "").trim();
            return (cid && cid === String(customer.id || "").trim()) || companyMatches(c.company_name, customer.company_name);
          });
          const customerHit = [customer.company_name, customer.address, customer.city, customer.state, customer.zip_code, customer.phone_number, customer.email, customer.notes].some(v => normalizeText(v).includes(q));
          const contactHit = linked.some(c => [c.name, c.company_name, c.phone_number, c.cell_phone, c.email, c.title, c.notes].some(v => normalizeText(v).includes(q)));
          return customerHit || contactHit;
        });
      }

      if (!rows.length) {
        list.innerHTML = `<div class="hint">No customers found.</div>`;
        return;
      }

      rows.forEach(customer => {
        const linked = contacts.filter(c => {
          const cid = String(c.customer_id || "").trim();
          return (cid && cid === String(customer.id || "").trim()) || companyMatches(c.company_name, customer.company_name);
        });
        const row = document.createElement("div");
        row.className = "jobrow";
        row.style.cursor = "pointer";
        row.innerHTML = `
          <div class="jobrow-top">
            <div class="jobrow-name">${escapeHtml(customer.company_name || "")}</div>
            <div class="hint">${linked.length} contact${linked.length === 1 ? "" : "s"}</div>
          </div>
          <div class="jobrow-addr">${escapeHtml([customer.address, customer.city, customer.state, customer.zip_code].filter(Boolean).join(", "))}</div>
          <div class="hint" style="margin-top:6px;">${escapeHtml(customer.phone_number || "")}${customer.email ? ` - ${escapeHtml(customer.email)}` : ""}</div>
        `;

        const preview = document.createElement("div");
        preview.style.display = "grid";
        preview.style.gap = "4px";
        preview.style.marginTop = "8px";
        linked.slice(0, 4).forEach(contact => {
          const line = document.createElement("div");
          line.className = "hint";
          line.style.paddingLeft = "8px";
          line.textContent = `${contact.name || ""}${contact.phone_number || contact.cell_phone ? ` - ${contact.phone_number || contact.cell_phone}` : ""}`;
          preview.appendChild(line);
        });
        if (linked.length > 4) {
          const more = document.createElement("div");
          more.className = "hint";
          more.style.paddingLeft = "8px";
          more.textContent = `+ ${linked.length - 4} more`;
          preview.appendChild(more);
        }
        row.appendChild(preview);
        row.addEventListener("click", () => openCustomerDrawer(customer, contacts));
        list.appendChild(row);
      });
    }

    controls.querySelector("#cc_search_btn").addEventListener("click", async () => {
      query = controls.querySelector("#cc_search").value || "";
      await renderList();
    });
    controls.querySelector("#cc_clear_btn").addEventListener("click", async () => {
      query = "";
      controls.querySelector("#cc_search").value = "";
      await renderList();
    });
    controls.querySelector("#cc_search").addEventListener("keydown", async (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        query = controls.querySelector("#cc_search").value || "";
        await renderList();
      }
    });

    controls.querySelector("#cc_add_customer").addEventListener("click", async () => {
      const company_name = (prompt("Customer name:") || "").trim();
      if (!company_name) return;
      const address = (prompt("Address (optional):") || "").trim();
      const city = (prompt("City (optional):") || "").trim();
      const state = (prompt("State (optional):") || "").trim();
      const zip_code = (prompt("ZIP (optional):") || "").trim();
      const phone_number = (prompt("Phone (optional):") || "").trim();
      const email = (prompt("Email (optional):") || "").trim();
      const notes = (prompt("Notes (optional):") || "").trim();
      const created = await apiCreateCustomer({ company_name, address, city, state, zip_code, phone_number, email, notes });
      if (created && created.id) {
        try { await apiUpdateCustomer(created.id, { company_name, address, city, state, zip_code, phone_number, email, notes }); } catch {}
      }
      await renderList();
    });

    controls.querySelector("#cc_add_contact").addEventListener("click", async () => {
      const customers = await apiListCustomers().catch(() => []);
      const name = (prompt("Contact name:") || "").trim();
      if (!name) return;
      const company_name = (prompt("Company:", "") || "").trim();
      const matched = customers.find(c => normalizeText(c.company_name) === normalizeText(company_name));
      const phone_number = (prompt("Phone:", "") || "").trim();
      const cell_phone = (prompt("Cell:", "") || "").trim();
      const email = (prompt("Email:", "") || "").trim();
      const title = (prompt("Title:", "") || "").trim();
      const notes = (prompt("Notes:", "") || "").trim();
      await apiCreateContact({ name, company_name, customer_id: matched?.id || "", phone_number, cell_phone, email, title, notes });
      await renderList();
    });

    root.appendChild(hero);
    root.appendChild(controls);
    root.appendChild(list);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);

    currentView = { refresh: renderList };
    renderList();
  }
  function renderContactsView() {
    renderCustomersView();
  }

function renderEmployeesView() {
    setNavActive(navEmployees);
    setActiveChip("Office Flow");
    setWorkspace("Employees / Users");
    clearWorkspaceActions();

    const root = document.createElement("div");

    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h3>Employees / Users</h3><div class="hint">Create employee records for forms and matching login users for Doorks access. Leads can create/edit dispatches and sales leads. Office Admin can manage user credentials.</div>`;

    const form = document.createElement("div");
    form.className = "grid2";
    form.style.marginTop = "10px";
    form.innerHTML = `
      <div><div class="label">Full Name</div><input class="input" id="e_name" /></div>
      <div><div class="label">Username</div><input class="input" id="e_username" placeholder="Defaults to full name" /></div>
      <div><div class="label">Role</div>
        <select class="input" id="e_role">
          <option value="tech">tech</option>
          <option value="lead">lead</option>
          <option value="office">office</option>
          <option value="office_admin">office_admin</option>
        </select>
      </div>
      <div><div class="label">Phone</div><input class="input" id="e_phone" placeholder="Used for default PIN if left blank" /></div>
      <div><div class="label">Email</div><input class="input" id="e_email" /></div>
      <div><div class="label">Address</div><input class="input" id="e_address" /></div>
      <div><div class="label">Password</div><input type="password" class="input" id="e_pw" placeholder="Required for login" /></div>
      <div><div class="label">PIN</div><input class="input" id="e_pin" maxlength="4" inputmode="numeric" placeholder="Defaults to last 4 of phone" /></div>
    `;

    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "8px";
    actions.style.marginTop = "10px";

    const btnAdd = document.createElement("button");
    btnAdd.className = "btn btn-orange";
    btnAdd.textContent = "Add Employee / User";

    const btnRefresh = document.createElement("button");
    btnRefresh.className = "btn";
    btnRefresh.textContent = "Refresh";

    actions.appendChild(btnAdd);
    actions.appendChild(btnRefresh);

    const userList = document.createElement("div");
    userList.style.marginTop = "12px";

    const employeeList = document.createElement("div");
    employeeList.style.marginTop = "16px";

    function normalizePin(pinRaw, phoneRaw) {
      const pin = String(pinRaw || "").replace(/\D/g, "").slice(-4);
      if (pin.length === 4) return pin;
      const phone = String(phoneRaw || "").replace(/\D/g, "").slice(-4);
      return phone;
    }

    async function refresh() {
      const [users, employees] = await Promise.all([
        apiListAuthUsers().catch(() => []),
        apiListEmployees().catch(() => []),
      ]);

      userList.innerHTML = `<div class="card"><h3 style="margin:0 0 10px 0;">Doorks Login Users</h3></div>`;
      const userWrap = document.createElement("div");
      userWrap.style.display = "grid";
      userWrap.style.gap = "8px";
      if (!users.length) {
        userWrap.innerHTML = `<div class="hint">No login users yet.</div>`;
      } else {
        users.forEach(u => {
          const row = document.createElement("div");
          row.className = "jobrow";
          const top = document.createElement("div");
          top.className = "jobrow-top";
          const name = document.createElement("div");
          name.className = "jobrow-name";
          name.textContent = `${u.name || u.username || "User"} (${u.role})`;
          top.appendChild(name);
          const pill = document.createElement("span");
          pill.className = "pill";
          pill.textContent = u.active === false ? "disabled" : u.role;
          pill.style.background = u.role === "office_admin" ? "#111827" : (u.role === "office" ? "#2563eb" : (u.role === "lead" ? "#b45309" : "#7c3aed"));
          top.appendChild(pill);
          const meta = document.createElement("div");
          meta.className = "jobrow-addr";
          meta.textContent = `${u.username || ""}${u.email ? ` - ${u.email}` : ""}`;

          const btnRow = document.createElement("div");
          btnRow.style.display = "flex";
          btnRow.style.gap = "8px";
          btnRow.style.marginTop = "8px";
          btnRow.style.flexWrap = "wrap";

          const roleSel = document.createElement("select");
          roleSel.className = "input";
          roleSel.style.maxWidth = "180px";
          roleSel.innerHTML = `
            <option value="tech">tech</option>
            <option value="lead">lead</option>
            <option value="office">office</option>
            <option value="office_admin">office_admin</option>
          `;
          roleSel.value = u.role || "tech";

          const saveRole = document.createElement("button");
          saveRole.className = "btn";
          saveRole.textContent = "Save Role";
          saveRole.addEventListener("click", async () => {
            try {
              await apiUpdateAuthUser(u.id, { role: roleSel.value, active: u.active !== false });
              await refresh();
            } catch (err) { alert(err.message || String(err)); }
          });

          const resetPw = document.createElement("button");
          resetPw.className = "btn";
          resetPw.textContent = "Reset Password";
          resetPw.addEventListener("click", async () => {
            const next = prompt(`New password for ${u.username || u.name}:`);
            if (!next) return;
            try {
              await apiSetAuthUserPassword(u.id, next);
              alert("Password updated.");
            } catch (err) { alert(err.message || String(err)); }
          });

          const resetPin = document.createElement("button");
          resetPin.className = "btn";
          resetPin.textContent = "Reset PIN";
          resetPin.addEventListener("click", async () => {
            const next = prompt(`New 4-digit PIN for ${u.username || u.name}:`);
            if (!next) return;
            try {
              await apiSetAuthUserPin(u.id, next);
              alert("PIN updated.");
            } catch (err) { alert(err.message || String(err)); }
          });

          const toggle = document.createElement("button");
          toggle.className = "btn";
          toggle.textContent = u.active === false ? "Enable" : "Disable";
          toggle.addEventListener("click", async () => {
            try {
              await apiSetAuthUserActive(u.id, u.active === false);
              await refresh();
            } catch (err) { alert(err.message || String(err)); }
          });

          const del = document.createElement("button");
          del.className = "btn";
          del.style.borderColor = "#fecaca";
          del.style.color = "#b91c1c";
          del.textContent = "Delete User";
          del.addEventListener("click", async () => {
            if (!confirm(`Delete login for ${u.username || u.name}?`)) return;
            try {
              await apiDeleteAuthUser(u.id);
              await refresh();
            } catch (err) { alert(err.message || String(err)); }
          });

          btnRow.appendChild(roleSel);
          btnRow.appendChild(saveRole);
          btnRow.appendChild(resetPw);
          btnRow.appendChild(resetPin);
          btnRow.appendChild(toggle);
          if (!(u.role === "office_admin" && String(u.username || "").toLowerCase() === "jason brewster")) btnRow.appendChild(del);

          row.appendChild(top);
          row.appendChild(meta);
          row.appendChild(btnRow);
          userWrap.appendChild(row);
        });
      }
      userList.appendChild(userWrap);

      employeeList.innerHTML = `<div class="card"><h3 style="margin:0 0 10px 0;">Employee Records</h3><div class="hint">These are used in technician dropdowns, forms, payroll, and time cards.</div></div>`;
      const empWrap = document.createElement("div");
      empWrap.style.display = "grid";
      empWrap.style.gap = "8px";
      if (!employees.length) {
        empWrap.innerHTML = `<div class="hint">No employees yet.</div>`;
      } else {
        employees.forEach(e => {
          const row = document.createElement("div");
          row.className = "jobrow";
          const top = document.createElement("div");
          top.className = "jobrow-top";
          const name = document.createElement("div");
          name.className = "jobrow-name";
          name.textContent = `${e.name} (${e.role})`;
          top.appendChild(name);
          const pill = document.createElement("span");
          pill.className = "pill";
          pill.style.background = e.role === "office_admin" ? "#111827" : (e.role === "office" ? "#2563eb" : (e.role === "lead" ? "#b45309" : "#7c3aed"));
          pill.textContent = e.role;
          top.appendChild(pill);
          const meta = document.createElement("div");
          meta.className = "jobrow-addr";
          meta.textContent = `${e.phone || ""}${e.email ? ` - ${e.email}` : ""}`;
          const a = document.createElement("div");
          a.style.display = "flex";
          a.style.gap = "8px";
          a.style.marginTop = "8px";
          const del = document.createElement("button");
          del.className = "btn";
          del.textContent = "Delete Employee";
          del.style.borderColor = "#fecaca";
          del.style.color = "#b91c1c";
          del.addEventListener("click", async () => {
            if (!confirm("Delete employee record?")) return;
            try {
              await apiDeleteEmployee(e.id);
              await refresh();
            } catch (err) { alert(err.message || String(err)); }
          });
          a.appendChild(del);
          row.appendChild(top);
          row.appendChild(meta);
          row.appendChild(a);
          empWrap.appendChild(row);
        });
      }
      employeeList.appendChild(empWrap);
    }

    btnAdd.addEventListener("click", async () => {
      try {
        const name = form.querySelector("#e_name").value.trim();
        const username = (form.querySelector("#e_username").value.trim() || name).trim();
        const role = form.querySelector("#e_role").value;
        const phone = form.querySelector("#e_phone").value.trim();
        const email = form.querySelector("#e_email").value.trim();
        const address = form.querySelector("#e_address").value.trim();
        const password = form.querySelector("#e_pw").value.trim();
        const pin = normalizePin(form.querySelector("#e_pin").value.trim(), phone);
        if (!name) throw new Error("Full name is required.");
        if (!username) throw new Error("Username is required.");
        if (!password) throw new Error("Password is required.");
        if (!pin || pin.length !== 4) throw new Error("PIN must be 4 digits or derive from phone.");

        await apiCreateEmployee({ name, role, phone, email, address, password }).catch(() => null);
        await apiCreateAuthUser({ username, name, email, role, password, pin, active: true });

        ["#e_name", "#e_username", "#e_phone", "#e_email", "#e_address", "#e_pw", "#e_pin"].forEach(sel => {
          const el = form.querySelector(sel);
          if (el) el.value = "";
        });
        form.querySelector("#e_role").value = "tech";
        await refresh();
      } catch (e) {
        alert(e.message || String(e));
      }
    });

    btnRefresh.addEventListener("click", refresh);

    root.appendChild(card);
    root.appendChild(form);
    root.appendChild(actions);
    root.appendChild(userList);
    root.appendChild(employeeList);

    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);

    currentView = { refresh };
    refresh();
  }
 
  function money(v) {
    const n = Number(v || 0);
    return Number.isFinite(n) ? n.toFixed(2) : "0.00";
  }
 
  function createDocLineItem(item = {}) {
    const kind = item.kind || "part";
    return {
      code: item.code || "",
      description: item.description || "",
      qty: Number(item.qty ?? 1),
      rate: Number(item.rate || 0),
      kind,
      taxable: typeof item.taxable === "boolean" ? item.taxable : !(kind === "labor" || kind === "fee"),
    };
  }
 
  function defaultDocItems() {
    return [
      createDocLineItem({ code: "TRIP", description: "Trip Charge", qty: 1, rate: 175, kind: "fee", taxable: false }),
      createDocLineItem({ code: "FUEL", description: "Fuel Surcharge", qty: 1, rate: 20, kind: "fee", taxable: false }),
    ];
  }
 
  function serializeDocItems(items, laborOnly) {
    return items
      .filter(it => laborOnly ? it.kind === "labor" : it.kind !== "labor")
      .map(it => `${it.code || "ITEM"} - ${it.description} | Qty ${Number(it.qty || 0)} @ $${money(it.rate)} = $${money(Number(it.qty) * Number(it.rate))}${it.taxable === false ? " | Non-Taxable" : ""}`)
      .join("\n");
  }
 
  function openEstimateInvoiceDrawer(job = null, initialType = "estimate", container = null, ctx = null) {
    openDrawer("Estimate / Invoice", async (drawerBody, overlay) => {
      const editDoc = job && job.__docEdit ? job.__docEdit : null;
      const [customers, employees] = await Promise.all([apiListCustomers().catch(() => []), apiListEmployees().catch(() => [])]);
      let docType = editDoc ? (editDoc.type || initialType) : initialType;
      let items = Array.isArray(editDoc?.items) && editDoc.items.length ? editDoc.items.map(createDocLineItem) : defaultDocItems().map(it => ({ ...it, kind: it.code === "TRIP" ? "trip" : (it.code === "FUEL" ? "fuel" : (it.kind || "other")) }));
      let currentPartResults = [];
      drawerBody.innerHTML = "";
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; gap:16px; flex-wrap:wrap; align-items:flex-start;">
          <div>
            <div style="font-size:28px; font-weight:1000; letter-spacing:.04em;">PRIORITY DOOR SYSTEMS</div>
            <div class="hint">836 W. Washington Ave. - Escondido, CA 92025 - 760-233-5037 - www.prioritydoors.com</div>
          </div>
          <div class="card" style="min-width:260px; padding:12px;">
            <div class="label">Document Type</div>
            <select class="input" id="doc_type"><option value="estimate">Estimate</option><option value="invoice">Invoice</option></select>
            <div class="label" style="margin-top:8px;">Date</div>
            <input class="input" id="doc_date" type="date" />
            <div class="label" style="margin-top:8px;">Sales Tax %</div>
            <select class="input" id="doc_tax_rate_select">
              <option value="">-- Select city / rate --</option>
            </select>
            <input class="input" id="doc_tax_rate_custom" type="number" min="0" step="0.01" placeholder="Enter custom tax %" style="margin-top:8px; display:none;" />
            <div class="hint" id="doc_tax_rate_hint" style="margin-top:6px;">Choose a city tax rate or select Custom.</div>
            <div class="label" style="margin-top:8px;">Prepared By</div>
            <select class="input" id="doc_completed_by"><option value="">-- Select employee --</option></select>
          </div>
        </div>
        <div class="grid2" style="margin-top:12px; align-items:start;">
          <div class="card" style="padding:12px;">
            <div class="label">Name / Address</div>
            <input class="input" id="doc_customer" list="doc_customer_list" placeholder="Customer" style="margin-top:6px;" />
            <input class="input" id="doc_address" name="doc_address" placeholder="Address" autocomplete="off" autocapitalize="off" spellcheck="false" data-lpignore="true" data-1p-ignore="true" style="margin-top:8px;" />
          </div>
          <div class="card" style="padding:12px;">
            <div class="label">Ship To / Bill To</div>
            <input class="input" id="doc_ship" placeholder="Ship To / Bill To" style="margin-top:6px;" />
            <div class="grid2" style="margin-top:8px;">
              <div><div class="label">PO #</div><input class="input" id="doc_po" /></div>
              <div><div class="label">Work Order / Job #</div><input class="input" id="doc_job" /></div>
            </div>
            <div style="margin-top:8px;"><div class="label" id="doc_number_label">Estimate #</div><input class="input" id="doc_number" /></div>
          </div>
        </div>
        <div style="margin-top:12px;"><div class="label">Proposal / Invoice Body</div><textarea id="doc_work" placeholder="Proposal Includes / Invoice Includes..." style="min-height:140px;"></textarea></div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; align-items:center;">
          <button class="btn" id="add_trip">Trip Charge</button>
          <button class="btn" id="add_fuel">Fuel Surcharge</button>
          <button class="btn" id="add_single">Single Tech Labor</button>
          <button class="btn" id="add_crew">Crew Tech Labor</button>
          <button class="btn" id="add_blank">Add Blank Line</button>
        </div>
        <div class="card" style="padding:12px; margin-top:12px;">
          <div class="label">Find Existing Parts</div>
          <input class="input" id="part_lookup" placeholder="Type item number or description" autocomplete="off" />
          <div class="hint" id="part_lookup_hint" style="margin-top:6px;">Start typing to search your saved parts list.</div>
          <div id="part_lookup_results" style="display:grid; gap:8px; margin-top:8px;"></div>
        </div>
        <div style="margin-top:12px; overflow:auto;"><table style="width:100%; border-collapse:collapse; min-width:920px;"><thead><tr>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; min-width:130px;">Item</th>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; min-width:320px;">Description</th>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; width:90px;">Qty</th>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; width:110px;">Price</th>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; width:90px;">Taxable</th>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; width:110px;">Total</th>
          <th style="text-align:left; padding:8px; border-bottom:1px solid #e5e7eb; width:60px;"></th>
        </tr></thead><tbody id="doc_items"></tbody></table></div>
        <div style="display:grid; grid-template-columns:1fr 320px; gap:12px; margin-top:12px;">
          <div class="card" style="padding:12px;"><div class="jobrow-top"><div class="jobrow-name">Cost Breakdown</div></div>
            <div class="jobrow-top" style="margin-top:8px;"><div>Trip Charges</div><div id="doc_trip_total">$0.00</div></div>
            <div class="jobrow-top"><div>Fuel Surcharges</div><div id="doc_fuel_total">$0.00</div></div>
            <div class="jobrow-top"><div>Labor</div><div id="doc_labor_total">$0.00</div></div>
            <div class="jobrow-top"><div>Parts</div><div id="doc_parts_total">$0.00</div></div>
            <div class="jobrow-top"><div>Other</div><div id="doc_other_total">$0.00</div></div>
          </div>
          <div class="card" style="padding:12px;"><div class="jobrow-top"><div class="jobrow-name">Totals</div></div>
            <div class="jobrow-top" style="margin-top:8px;"><div>Subtotal</div><div id="doc_subtotal">$0.00</div></div>
            <div class="jobrow-top"><div>Taxable Subtotal</div><div id="doc_taxable">$0.00</div></div>
            <div class="jobrow-top"><div>Sales Tax</div><div id="doc_tax">$0.00</div></div>
            <div class="jobrow-top" style="font-weight:1000; margin-top:6px;"><div>Total</div><div id="doc_total">$0.00</div></div>
          </div>
        </div>
        <div style="display:flex; gap:8px; margin-top:12px;"><button class="btn btn-orange" id="doc_generate">Generate PDF</button><button class="btn" id="doc_cancel">Cancel</button></div>`;
      drawerBody.appendChild(card);
      card.appendChild(buildCustomerDatalist("doc_customer_list", customers));
      const completedSel = card.querySelector("#doc_completed_by");
      employees.forEach(e => { const opt=document.createElement("option"); opt.value=e.name||""; opt.textContent=e.name||""; completedSel.appendChild(opt); });
      const dom = { type:card.querySelector("#doc_type"), date:card.querySelector("#doc_date"), customer:card.querySelector("#doc_customer"), address:card.querySelector("#doc_address"), ship:card.querySelector("#doc_ship"), po:card.querySelector("#doc_po"), job:card.querySelector("#doc_job"), number:card.querySelector("#doc_number"), numberLabel:card.querySelector("#doc_number_label"), work:card.querySelector("#doc_work"), tbody:card.querySelector("#doc_items"), subtotal:card.querySelector("#doc_subtotal"), taxable:card.querySelector("#doc_taxable"), tax:card.querySelector("#doc_tax"), total:card.querySelector("#doc_total"), taxRateSelect:card.querySelector("#doc_tax_rate_select"), taxRateCustom:card.querySelector("#doc_tax_rate_custom"), taxRateHint:card.querySelector("#doc_tax_rate_hint"), partLookup:card.querySelector("#part_lookup"), partLookupHint:card.querySelector("#part_lookup_hint"), partResults:card.querySelector("#part_lookup_results"), tripTotal:card.querySelector("#doc_trip_total"), fuelTotal:card.querySelector("#doc_fuel_total"), laborTotal:card.querySelector("#doc_labor_total"), partsTotal:card.querySelector("#doc_parts_total"), otherTotal:card.querySelector("#doc_other_total"), completedBy:completedSel };
      SALES_TAX_OPTIONS.forEach(opt => { const o=document.createElement("option"); o.value=String(opt.rate); o.textContent=`${opt.city} — ${Number(opt.rate).toFixed(2)}%`; o.dataset.city=opt.city; dom.taxRateSelect.appendChild(o); });
      const customOpt=document.createElement("option"); customOpt.value="__custom__"; customOpt.textContent="Custom"; dom.taxRateSelect.appendChild(customOpt);
      function setTaxRateValue(rate, city="") { const normalized = String(rate == null ? "" : rate).trim(); const known = normalized && SALES_TAX_OPTIONS.some(opt => String(opt.rate) === normalized);
        if (known) { dom.taxRateSelect.value = normalized; dom.taxRateCustom.value = normalized; dom.taxRateCustom.style.display = "none"; dom.taxRateHint.textContent = city ? `${city} selected.` : "City tax rate selected."; return; }
        if (normalized) { dom.taxRateSelect.value = "__custom__"; dom.taxRateCustom.value = normalized; dom.taxRateCustom.style.display = "block"; dom.taxRateHint.textContent = "Custom sales tax entered."; return; }
        dom.taxRateSelect.value = ""; dom.taxRateCustom.value = ""; dom.taxRateCustom.style.display = "none"; dom.taxRateHint.textContent = "Choose a city tax rate or select Custom."; }
      function getCurrentTaxRateValue() { return dom.taxRateSelect.value === "__custom__" ? String(dom.taxRateCustom.value || "").trim() : String(dom.taxRateSelect.value || "").trim(); }
      dom.type.value = docType; dom.date.value = (editDoc && editDoc.date) || yyyyMmDd(new Date()); wireAddressSuggestions(dom.address, customers.map(c => c.address).filter(Boolean)); if (editDoc && editDoc.tax_rate != null) setTaxRateValue(editDoc.tax_rate); else setTaxRateValue("");
      if (job) { dom.customer.value = (editDoc && editDoc.customer) || job.customer || ""; dom.address.value = (editDoc && editDoc.address) || job.address || ""; dom.ship.value = (editDoc && editDoc.ship_to) || job.address || job.customer || ""; dom.po.value = (editDoc && editDoc.po_number) || job.po_number || ""; dom.job.value = (editDoc && editDoc.job_number) || job.job_number || ""; const inferred = inferTaxCityFromAddress(dom.address.value); if (!editDoc && inferred) setTaxRateValue(inferred.rate, inferred.city); }
      if (editDoc) { dom.work.value = editDoc.work || ""; setTaxRateValue(editDoc.tax_rate ?? 7.75); dom.completedBy.value = editDoc.completed_by || ""; dom.number.value = editDoc.number || ""; }
      function applyDocTypeMeta(){ docType=dom.type.value; const defaultNumber=nextDocNumberFromStorage(docType); dom.numberLabel.textContent = docType === "estimate" ? "Estimate #" : "Invoice #"; if (editDoc) return; if (!String(dom.number.value||"").trim() || (docType==="estimate" && String(dom.number.value||"").startsWith("JS")) || (docType==="invoice" && String(dom.number.value||"").startsWith("RE"))) dom.number.value = docType === "estimate" ? (job?.estimate_number || defaultNumber) : (job?.invoice_number || defaultNumber); }
      function categoryTotals(){ const sums={trip:0,fuel:0,labor:0,parts:0,other:0}; items.forEach(it=>{ const total=Number(it.qty||0)*Number(it.rate||0); const kind=String(it.kind||"other").toLowerCase(); if (kind==="trip") sums.trip+=total; else if (kind==="fuel") sums.fuel+=total; else if (kind==="labor") sums.labor+=total; else if (kind==="part") sums.parts+=total; else sums.other+=total;}); return sums; }
      function updateTotals(){ const subtotal=items.reduce((s,it)=>s+(Number(it.qty||0)*Number(it.rate||0)),0); const taxableSubtotal=getTaxableSubtotal(items); const taxRate=Number(getCurrentTaxRateValue()||0)/100; const tax=taxableSubtotal*taxRate; const sums=categoryTotals(); dom.subtotal.textContent=`$${money(subtotal)}`; dom.taxable.textContent=`$${money(taxableSubtotal)}`; dom.tax.textContent=`$${money(tax)}`; dom.total.textContent=`$${money(subtotal+tax)}`; dom.tripTotal.textContent=`$${money(sums.trip)}`; dom.fuelTotal.textContent=`$${money(sums.fuel)}`; dom.laborTotal.textContent=`$${money(sums.labor)}`; dom.partsTotal.textContent=`$${money(sums.parts)}`; dom.otherTotal.textContent=`$${money(sums.other)}`; }
      function renderPartLookupResults(results){ currentPartResults=Array.isArray(results)?results:[]; dom.partResults.innerHTML=""; dom.partLookupHint.textContent=currentPartResults.length?`${currentPartResults.length} matching part${currentPartResults.length===1?"":"s"}`:"No matching parts found yet."; currentPartResults.slice(0,10).forEach(p=>{ const row=document.createElement("button"); row.className="btn"; row.style.textAlign="left"; row.innerHTML=`<strong>${escapeHtml(p.Item||"")}</strong><br><span class="hint">${escapeHtml(p.Description||"")}${p.Price?` - $${money(p.Price)}`:""}</span>`; row.addEventListener("click",()=>addPartToItems(p)); dom.partResults.appendChild(row); }); }
      let searchTimer=null; async function searchParts(q){ try{ renderPartLookupResults(await apiListParts({ q, limit:25 })); } catch { renderPartLookupResults([]); } }
      function addPartToItems(part){ if(!part) return; items.push(createDocLineItem({ code:part.Item||"", description:part.Description||"", qty:1, rate:Number(part.Price||0), kind:"part", taxable:true })); dom.partLookup.value=""; renderPartLookupResults([]); renderItems(); }
      function findPartMatch(q){ const n=String(q||"").trim().toLowerCase(); if(!n) return null; return currentPartResults.find(p=>String(p.Item||"").trim().toLowerCase()===n) || currentPartResults.find(p=>String(p.Description||"").trim().toLowerCase()===n) || currentPartResults.find(p=>`${p.Item||""} ${p.Description||""}`.toLowerCase().includes(n)) || null; }
      function makeRow(item,idx){ const tr=document.createElement("tr"); const total=Number(item.qty||0)*Number(item.rate||0); tr.innerHTML=`<td style="padding:8px; border-bottom:1px solid #f3f4f6;"><input class="input" data-k="code" value="${item.code||""}" /></td><td style="padding:8px; border-bottom:1px solid #f3f4f6;"><input class="input" data-k="description" value="${item.description||""}" /></td><td style="padding:8px; border-bottom:1px solid #f3f4f6;"><input class="input" style="min-width:72px;" data-k="qty" type="number" min="0" step="0.25" value="${Number(item.qty||0)}" /></td><td style="padding:8px; border-bottom:1px solid #f3f4f6;"><input class="input" style="min-width:96px;" data-k="rate" type="number" min="0" step="0.01" value="${Number(item.rate||0)}" /></td><td style="padding:8px; border-bottom:1px solid #f3f4f6;"><label style="display:flex; align-items:center; gap:6px;"><input type="checkbox" data-k="taxable" ${item.taxable===false?"":"checked"}/> <span class="hint">Tax</span></label></td><td style="padding:8px; border-bottom:1px solid #f3f4f6; white-space:nowrap;" data-k="line_total">$${money(total)}</td><td style="padding:8px; border-bottom:1px solid #f3f4f6;"><button class="btn" data-k="del">&times;</button></td>`; const updateLine=()=>{ tr.querySelector('[data-k="line_total"]').textContent=`$${money(Number(item.qty||0)*Number(item.rate||0))}`; updateTotals(); }; tr.querySelector('[data-k="code"]').addEventListener("change", async e => { item.code=e.target.value; const hit=await apiListParts({ q:item.code, limit:10 }).catch(()=>[]); const part=hit.find(p=>String(p.Item||"").trim().toLowerCase()===String(item.code||"").trim().toLowerCase())||hit[0]; if(part){ item.code=part.Item||item.code; item.description=part.Description||item.description; item.rate=Number(part.Price||item.rate||0); item.kind="part"; item.taxable=true; renderItems(); return; } updateLine(); }); tr.querySelector('[data-k="description"]').addEventListener("input", e => { item.description=e.target.value; }); tr.querySelector('[data-k="qty"]').addEventListener("input", e => { item.qty=Number(e.target.value||0); updateLine(); }); tr.querySelector('[data-k="rate"]').addEventListener("input", e => { item.rate=Number(e.target.value||0); updateLine(); }); tr.querySelector('[data-k="taxable"]').addEventListener("change", e => { item.taxable=!!e.target.checked; updateLine(); }); tr.querySelector('[data-k="del"]').addEventListener("click", ()=>{ items.splice(idx,1); renderItems(); }); return tr; }
      function renderItems(){ applyDocTypeMeta(); dom.tbody.innerHTML=""; items.forEach((item,idx)=>dom.tbody.appendChild(makeRow(item,idx))); updateTotals(); }
      dom.partLookup.addEventListener("input", ()=>{ clearTimeout(searchTimer); const q=dom.partLookup.value.trim(); if(!q){ renderPartLookupResults([]); return; } searchTimer=setTimeout(()=>searchParts(q), 180); });
      dom.partLookup.addEventListener("keydown", e=>{ if(e.key==="Enter"){ e.preventDefault(); addPartToItems(findPartMatch(dom.partLookup.value)||currentPartResults[0]); }});
      card.querySelector("#add_trip").addEventListener("click", ()=>{ items.push(createDocLineItem({ code:"TRIP", description:"Trip Charge", qty:1, rate:175, kind:"trip", taxable:false })); renderItems(); });
      card.querySelector("#add_fuel").addEventListener("click", ()=>{ items.push(createDocLineItem({ code:"FUEL", description:"Fuel Surcharge", qty:1, rate:20, kind:"fuel", taxable:false })); renderItems(); });
      card.querySelector("#add_single").addEventListener("click", ()=>{ items.push(createDocLineItem({ code:"LABOR", description:"Single Tech Labor", qty:1, rate:175, kind:"labor", taxable:false })); renderItems(); });
      card.querySelector("#add_crew").addEventListener("click", ()=>{ items.push(createDocLineItem({ code:"CREW", description:"Crew Tech Labor", qty:1, rate:235, kind:"labor", taxable:false })); renderItems(); });
      card.querySelector("#add_blank").addEventListener("click", ()=>{ items.push(createDocLineItem({ kind:"other" })); renderItems(); });
      card.querySelector("#doc_cancel").addEventListener("click", ()=> overlay.remove());
      dom.type.addEventListener("change", renderItems);
      dom.taxRateSelect.addEventListener("change", ()=>{
        if (dom.taxRateSelect.value === "__custom__") {
          dom.taxRateCustom.style.display = "block";
          dom.taxRateHint.textContent = "Enter a custom sales tax %.";
          if (!String(dom.taxRateCustom.value || "").trim()) dom.taxRateCustom.value = "7.75";
          dom.taxRateCustom.focus();
        } else {
          dom.taxRateCustom.style.display = "none";
          const selected = dom.taxRateSelect.options[dom.taxRateSelect.selectedIndex];
          dom.taxRateHint.textContent = selected && selected.dataset && selected.dataset.city ? `${selected.dataset.city} selected.` : "Choose a city tax rate or select Custom.";
        }
        updateTotals();
      });
      dom.taxRateCustom.addEventListener("input", updateTotals);
      dom.address.addEventListener("blur", ()=>{ if (dom.taxRateSelect.value === "__custom__") return; const inferred = inferTaxCityFromAddress(dom.address.value); if (inferred) setTaxRateValue(inferred.rate, inferred.city); });
      renderItems();
      card.querySelector("#doc_generate").addEventListener("click", async ()=>{ try { if (!String(dom.completedBy.value || "").trim()) { alert("Please select who prepared this document before saving."); dom.completedBy.focus(); return; } if (!String(getCurrentTaxRateValue() || "").trim()) { alert("Sales tax must be selected."); if (dom.taxRateSelect.value === "__custom__") dom.taxRateCustom.focus(); else dom.taxRateSelect.focus(); return; } const payload={ job_id: job ? job.id : ((editDoc && editDoc.job_id) || ""), customer:dom.customer.value.trim(), address:dom.address.value.trim(), work:dom.work.value.trim(), labor:serializeDocItems(items,true), parts:serializeDocItems(items,false), number:dom.number.value.trim(), po_number:dom.po.value.trim(), invoice_number: docType === "invoice" ? dom.number.value.trim() : "", job_number:dom.job.value.trim(), tax_rate:Number(getCurrentTaxRateValue()||0), completed_by: dom.completedBy.value || "", items: items, date: dom.date.value || "", ship_to: dom.ship.value.trim() }; const resp = editDoc ? await apiUpdateDocument(editDoc.filename, { ...payload, type: docType }) : (docType === "invoice" ? await apiCreateInvoice(payload) : await apiCreateEstimate(payload)); if (job && !editDoc) { const updated = await apiUpdateJob(job.id, { po_number:dom.po.value.trim(), estimate_number: docType === "estimate" ? ((resp.doc && resp.doc.number) || dom.number.value.trim()) : (job.estimate_number || ""), invoice_number: docType === "invoice" ? ((resp.doc && resp.doc.number) || dom.number.value.trim()) : (job.invoice_number || ""), status: docType === "invoice" ? "Done" : "Quote Sent" }); if (overlay) overlay.remove(); if (ctx && ctx.afterSave) await ctx.afterSave(); if (container) renderJobDetails(container, updated, ctx); refreshBadges(); return; } if (overlay) overlay.remove(); if (ctx && ctx.refreshDocs) await ctx.refreshDocs(); if (currentView && currentView.refresh) currentView.refresh(); } catch(e){ alert(e.message || String(e)); } });
    });
  }
 
function openEstimateDrawer(job, container = null, ctx = null) {
    return openEstimateInvoiceDrawer(job, "estimate", container, ctx);
  }
 
  function openInvoiceDrawer(job, container = null, ctx = null) {
    return openEstimateInvoiceDrawer(job, "invoice", container, ctx);
  }
 
  function renderEstimatePage() {
    setNavActive(primaryEstimateNav);
    setActiveChip("Office Flow");
    setWorkspace("Estimate/Invoice");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    const tabs = document.createElement("div");
    tabs.style.display = "flex";
    tabs.style.gap = "8px";
    tabs.style.flexWrap = "wrap";
    tabs.style.marginBottom = "12px";
 
    const btnGen = document.createElement("button");
    btnGen.className = "navbtn navbtn-active";
    btnGen.style.width = "auto";
    btnGen.innerHTML = `<span>Generator</span>`;
    const btnEst = document.createElement("button");
    btnEst.className = "navbtn";
    btnEst.style.width = "auto";
    btnEst.innerHTML = `<span>Estimates</span>`;
    const btnInv = document.createElement("button");
    btnInv.className = "navbtn";
    btnInv.style.width = "auto";
    btnInv.innerHTML = `<span>Invoices</span>`;
    tabs.append(btnGen, btnEst, btnInv);
 
    const body = document.createElement("div");
    root.append(tabs, body);
 
    let activeTab = "generator";
    function syncTabs() {
      btnGen.classList.toggle("navbtn-active", activeTab === "generator");
      btnEst.classList.toggle("navbtn-active", activeTab === "estimates");
      btnInv.classList.toggle("navbtn-active", activeTab === "invoices");
    }
 
    async function renderDocList(type) {
      body.innerHTML = "";
      const docs = await apiListDocuments({ type }).catch(() => []);
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `<h3>${type === "estimate" ? "Saved Estimates" : "Saved Invoices"}</h3><div class="hint">View, edit, or delete saved documents.</div>`;
      const list = document.createElement("div");
      list.style.display = "grid";
      list.style.gap = "8px";
      list.style.marginTop = "12px";
      if (!docs.length) {
        list.innerHTML = `<div class="hint">No ${type}s saved yet.</div>`;
      } else {
        docs.forEach(doc => {
          const row = document.createElement("div");
          row.className = "jobrow";
          row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${type === "invoice" ? "Invoice" : "Estimate"} ${escapeHtml(doc.number || "")}</div>${statusPill(type === "invoice" ? "Done" : "Quote Sent").outerHTML}</div><div class="jobrow-addr">${escapeHtml(doc.customer || "")}${doc.job_number ? ` - Job #${escapeHtml(doc.job_number)}` : ""}</div><div class="hint">${escapeHtml(doc.address || "")}</div><div class="hint">Prepared By: ${escapeHtml(doc.completed_by || "")}</div>`;
          const actions = document.createElement("div");
          actions.style.display = "flex";
          actions.style.gap = "8px";
          actions.style.marginTop = "8px";
          const open = document.createElement("a");
          open.href = doc.open_url || doc.download_url || "#";
          open.target = "_blank";
          open.rel = "noopener noreferrer";
          open.textContent = "Open";
          styleActionButton(open, "blue", true);
          const edit = document.createElement("button");
          edit.type = "button";
          edit.textContent = "Edit";
          styleActionButton(edit, "ghost", true);
          edit.addEventListener("click", () => {
            const fakeJob = { id: doc.job_id || "", customer: doc.customer || "", address: doc.address || "", po_number: doc.po_number || "", job_number: doc.job_number || "", __docEdit: doc };
            openEstimateInvoiceDrawer(fakeJob, doc.type || type, null, { refreshDocs: () => renderDocList(type) });
          });
          const del = document.createElement("button");
          del.type = "button";
          del.textContent = "Delete";
          styleActionButton(del, "danger", true);
          del.addEventListener("click", async () => {
            if (!confirm(`Delete ${doc.number || doc.filename || "this document"}?`)) return;
            await apiDeleteDocument(doc.filename);
            renderDocList(type);
          });
          actions.append(open, edit, del);
          row.appendChild(actions);
          list.appendChild(row);
        });
      }
      card.appendChild(list);
      body.appendChild(card);
    }
 
    function renderGeneratorTab() {
      body.innerHTML = `<div class="card"><h3>Estimate / Invoice</h3><div class="hint">Open a blank document and choose estimate or invoice inside the builder.</div><div style="margin-top:10px"><button class="btn btn-orange" id="openDocBuilder">Open Builder</button></div></div>`;
      const btn = document.getElementById("openDocBuilder");
      if (btn) btn.addEventListener("click", () => openEstimateInvoiceDrawer(null, "estimate", null, { refreshDocs: renderActiveTab }));
    }
 
    async function renderActiveTab() {
      syncTabs();
      if (activeTab === "estimates") return renderDocList("estimate");
      if (activeTab === "invoices") return renderDocList("invoice");
      renderGeneratorTab();
    }
 
    btnGen.addEventListener("click", () => { activeTab = "generator"; renderActiveTab(); });
    btnEst.addEventListener("click", () => { activeTab = "estimates"; renderActiveTab(); });
    btnInv.addEventListener("click", () => { activeTab = "invoices"; renderActiveTab(); });
 
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
    currentView = { refresh: renderActiveTab };
    renderActiveTab();
  }
 
  function renderInvoicePage() {
    renderEstimatePage();
  }
 
  function renderTimeOffView() {
    setNavActive(navFormsTimeOff);
    setActiveChip("Forms");
    setWorkspace("Time Off Request");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    root.style.display = "grid";
    root.style.gridTemplateColumns = "1.1fr 1fr";
    root.style.gap = "14px";
 
    const formCard = document.createElement("div");
    formCard.className = "card";
    formCard.innerHTML = `
      <h3>Request Time Off</h3>
      <div class="hint">Submit a request for approval.</div>
      <div style="margin-top:12px;">
        <div class="label">Employee</div>
        <select class="input" id="tor_employee"></select>
      </div>
      <div class="grid2" style="margin-top:10px;">
        <div><div class="label">Start Date</div><input class="input" id="tor_start" type="date" /></div>
        <div><div class="label">End Date</div><input class="input" id="tor_end" type="date" /></div>
      </div>
      <div style="margin-top:10px;">
        <label style="display:flex; align-items:center; gap:8px; font-weight:700;">
          <input type="checkbox" id="tor_emergency" />
          <span>Emergency</span>
        </label>
        <div class="hint" style="margin-top:4px;">Use for same-day call-outs, illness, or immediate emergencies.</div>
      </div>
      <div class="grid2" style="margin-top:10px;">
        <div>
          <label style="display:flex; align-items:center; gap:8px; font-weight:700;">
            <input type="checkbox" id="tor_use_pto" />
            <span>Use PTO</span>
          </label>
        </div>
        <div><div class="label">PTO Hours</div><input class="input" id="tor_pto_hours" type="number" step="0.25" placeholder="0.00" /></div>
      </div>
      <div style="margin-top:10px;">
        <div class="label">Notes</div>
        <textarea id="tor_notes" placeholder="Reason / notes" style="min-height:100px;"></textarea>
      </div>
      <div style="display:flex; gap:8px; margin-top:12px;">
        <button class="btn btn-orange" id="tor_submit">Submit Request</button>
      </div>
    `;
 
    const listCard = document.createElement("div");
    listCard.className = "card";
    listCard.innerHTML = `<h3>Requests</h3><div class="hint">Pending, approved, and declined time off.</div>`;
    const list = document.createElement("div");
    list.style.display = "grid";
    list.style.gap = "8px";
    list.style.marginTop = "12px";
    listCard.appendChild(list);
 
    root.append(formCard, listCard);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    async function refresh() {
      const selfOnly = currentUser && ["tech", "lead"].includes(String(currentUser.role || ""));
      const selfName = (currentUser && (currentUser.name || currentUser.username)) ? String(currentUser.name || currentUser.username) : "";
      const [employees, requestsRaw] = await Promise.all([apiListEmployees().catch(() => []), apiListTimeOff({ limit: 500, ...(selfOnly && selfName ? { employee_name: selfName } : {}) }).catch(() => [])]);
      const requests = [...requestsRaw].sort((a, b) => {
        const ap = a && a.emergency ? 1 : 0;
        const bp = b && b.emergency ? 1 : 0;
        if (bp !== ap) return bp - ap;
        return String(b.created_at || "").localeCompare(String(a.created_at || ""));
      });
      const sel = formCard.querySelector("#tor_employee");
      const prevVal = sel.value;
      if (selfOnly) {
        sel.innerHTML = selfName ? `<option value="${escapeHtml(selfName)}">${escapeHtml(selfName)}</option>` : `<option value="">-- Select employee --</option>`;
        sel.value = selfName;
        sel.disabled = true;
      } else {
        sel.disabled = false;
        sel.innerHTML = `<option value="">-- Select employee --</option>` + employees.map(e => `<option value="${escapeHtml(e.name || "")}">${escapeHtml(e.name || "")}</option>`).join("");
        if (prevVal) sel.value = prevVal;
      }
 
      const pendingCount = requests.filter(item => String(item.status || '').toLowerCase() === 'pending' || !!item.emergency).length;
      const timeOffBadge = el('badgeTimeOff');
      if (timeOffBadge) {
        timeOffBadge.textContent = String(pendingCount);
        timeOffBadge.style.display = pendingCount ? 'inline-flex' : 'none';
      }
      list.innerHTML = "";
      if (!requests.length) {
        list.innerHTML = `<div class="hint">No time off requests yet.</div>`;
        return;
      }
      requests.forEach(item => {
        const pillStatus = item.status === "approved" ? "Approved" : item.status === "declined" ? "Denied" : "Pending";
        const row = document.createElement("div");
        row.className = "jobrow";
        row.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">${escapeHtml(item.employee_name || "")}${item.emergency ? ` <span style="margin-left:8px; font-size:12px; color:#b91c1c;">EMERGENCY</span>` : ""}</div>${statusPill(pillStatus).outerHTML}</div><div class="jobrow-addr">${escapeHtml(formatDisplayDate(item.start_date || ""))}${item.end_date && item.end_date !== item.start_date ? ` - ${escapeHtml(formatDisplayDate(item.end_date))}` : ""}${item.use_pto ? ` - PTO ${escapeHtml(String(item.pto_hours || 0))} hrs` : ""}</div><div class="hint">${escapeHtml(item.notes || "")}</div>`;
        const actions = document.createElement("div");
        actions.style.display = "flex"; actions.style.gap = "8px"; actions.style.marginTop = "8px";
        if (!selfOnly && item.status === "pending") {
          const approve = document.createElement("button"); approve.type = "button"; approve.textContent = "Approve"; styleActionButton(approve, "green", true);
          approve.addEventListener("click", async () => { await apiUpdateTimeOff(item.id, { status: "approved" }); refresh(); });
          const decline = document.createElement("button"); decline.type = "button"; decline.textContent = "Decline"; styleActionButton(decline, "ghost", true);
          decline.addEventListener("click", async () => { await apiUpdateTimeOff(item.id, { status: "declined" }); refresh(); });
          actions.append(approve, decline);
        }
        if (!selfOnly || String(item.status || "").toLowerCase() === "pending") {
          const del = document.createElement("button"); del.type = "button"; del.textContent = "Delete"; styleActionButton(del, "danger", true);
          del.addEventListener("click", async () => { if (!confirm("Delete this time off request?")) return; await apiDeleteTimeOff(item.id); refresh(); });
          actions.appendChild(del);
        }
        row.appendChild(actions);
        list.appendChild(row);
      });
    }
 
    formCard.querySelector("#tor_submit").addEventListener("click", async () => {
      const employee = ((currentUser && ["tech", "lead"].includes(String(currentUser.role || ""))) ? String(currentUser.name || currentUser.username || "") : formCard.querySelector("#tor_employee").value.trim());
      const start = formCard.querySelector("#tor_start").value;
      const end = formCard.querySelector("#tor_end").value || start;
      const notes = formCard.querySelector("#tor_notes").value.trim();
      if (!employee) return alert("Please select an employee.");
      if (!start) return alert("Please choose a start date.");
      await apiCreateTimeOff({ employee_name: employee, start_date: start, end_date: end, notes, emergency: !!formCard.querySelector("#tor_emergency").checked, use_pto: !!formCard.querySelector("#tor_use_pto").checked, pto_hours: Number(formCard.querySelector("#tor_pto_hours").value || 0), status: "pending" });
      formCard.querySelector("#tor_start").value = "";
      formCard.querySelector("#tor_end").value = "";
      formCard.querySelector("#tor_notes").value = "";
      formCard.querySelector("#tor_emergency").checked = false;
      formCard.querySelector("#tor_use_pto").checked = false;
      formCard.querySelector("#tor_pto_hours").value = "";
      refresh();
    });
 
    currentView = { refresh };
    refresh();
  }
 
  function renderNotificationsView() {
    setNavActive(navNotifications);
    setActiveChip("Notifications");
    setWorkspace("Team Messages");
    clearWorkspaceActions();

    const root = document.createElement("div");
    root.style.display = "grid";
    root.style.gridTemplateColumns = "320px 1fr";
    root.style.gap = "14px";

    const left = document.createElement("div");
    left.className = "card";
    left.innerHTML = `
      <h3>Messages</h3>
      <div class="hint">All Hands and direct messages.</div>
      <div style="display:flex; gap:8px; margin-top:12px; flex-wrap:wrap;">
        <button class="btn btn-orange" id="msg_filter_inbox">Inbox</button>
        <button class="btn" id="msg_filter_direct">Direct</button>
        <button class="btn" id="msg_filter_all">All</button>
      </div>
      <div style="margin-top:10px;"><input class="input" id="msg_search" placeholder="Search messages..." /></div>
      <div id="msg_threads" style="display:grid; gap:8px; margin-top:12px;"></div>
    `;

    const right = document.createElement("div");
    right.className = "card";
    right.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">
        <div>
          <h3 id="msg_title" style="margin:0;">All Hands</h3>
          <div class="hint" id="msg_subtitle">Team-wide messages</div>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <button class="btn" id="msg_mark_read">Mark Read</button>
          <button class="btn" id="msg_refresh">Refresh</button>
        </div>
      </div>
      <div id="msg_feed" style="display:grid; gap:10px; margin-top:14px; min-height:260px;"></div>
      <div style="border-top:1px solid var(--line); margin-top:14px; padding-top:14px; display:grid; gap:10px;">
        <div>
          <div class="label">Send To</div>
          <select class="input" id="msg_to"><option value="__ALL__">All Hands</option></select>
        </div>
        <div>
          <div class="label">Message</div>
          <textarea id="msg_body" placeholder="Type a message..." style="min-height:110px;"></textarea>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end;">
          <button class="btn" id="msg_clear">Clear</button>
          <button class="btn btn-orange" id="msg_send">Send Message</button>
        </div>
      </div>
    `;

    root.append(left, right);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);

    const threadsEl = left.querySelector("#msg_threads");
    const feedEl = right.querySelector("#msg_feed");
    const titleEl = right.querySelector("#msg_title");
    const subtitleEl = right.querySelector("#msg_subtitle");
    const toSel = right.querySelector("#msg_to");
    const bodyInput = right.querySelector("#msg_body");
    const searchInput = left.querySelector("#msg_search");
    const filterInbox = left.querySelector("#msg_filter_inbox");
    const filterDirect = left.querySelector("#msg_filter_direct");
    const filterAll = left.querySelector("#msg_filter_all");

    let filterMode = "inbox";
    let threadMode = "allhands";
    let threadPeer = "";
    let threadCache = [];

    function setFilterUi() {
      [filterInbox, filterDirect, filterAll].forEach(btn => {
        btn.classList.remove("btn-orange");
        btn.classList.add("btn");
      });
      const active = filterMode === "inbox" ? filterInbox : filterMode === "direct" ? filterDirect : filterAll;
      active.classList.add("btn-orange");
    }

    function initials(name) {
      const parts = String(name || "").trim().split(/\s+/).filter(Boolean);
      return (parts.slice(0,2).map(p => p[0] || "").join("") || "?").toUpperCase();
    }

    async function refreshRecipients() {
      const prev = toSel.value;
      const items = await apiNotificationRecipients().catch(() => []);
      toSel.innerHTML = `<option value="__ALL__">All Hands</option>`;
      items.filter(u => String(u.username || "").toLowerCase() !== String((currentUser && currentUser.username) || "").toLowerCase()).forEach(u => {
        const opt = document.createElement("option");
        opt.value = u.username || u.id || "";
        opt.textContent = u.name || u.username || "User";
        toSel.appendChild(opt);
      });
      if ([...toSel.options].some(o => o.value === prev)) toSel.value = prev;
    }

    function buildThreads(items) {
      const me = String((currentUser && currentUser.username) || "").toLowerCase();
      const q = String(searchInput.value || "").trim().toLowerCase();
      const threads = [];
      const allhands = items.filter(item => item.kind !== "direct");
      const allhandsUnread = allhands.filter(item => !item.is_mine && !item.read).length;
      const allhandsLast = allhands[0];
      if (filterMode !== "direct") {
        threads.push({
          key: "allhands",
          mode: "allhands",
          title: "All Hands",
          subtitle: allhandsLast ? (allhandsLast.message || "") : "No team messages yet.",
          unread: allhandsUnread,
          stamp: allhandsLast ? String(allhandsLast.created_at || "").replace("T", " ").slice(0,16) : "",
          avatar: "AH"
        });
      }
      const peerMap = new Map();
      items.filter(item => item.kind === "direct").forEach(item => {
        const from = String(item.from || "");
        const to = String(item.to || "");
        const peer = String(from).toLowerCase() === me ? to : from;
        if (!peer) return;
        if (!peerMap.has(peer)) peerMap.set(peer, []);
        peerMap.get(peer).push(item);
      });
      [...peerMap.entries()].forEach(([peer, msgs]) => {
        const last = msgs[0];
        const unread = msgs.filter(item => !item.is_mine && !item.read).length;
        const peerName = last.is_mine ? (last.to_name || peer) : (last.from_name || peer);
        threads.push({
          key: `direct:${peer}`,
          mode: "direct",
          peer,
          title: peerName,
          subtitle: last.message || "",
          unread,
          stamp: String(last.created_at || "").replace("T", " ").slice(0,16),
          avatar: initials(peerName)
        });
      });
      let filtered = threads;
      if (q) {
        filtered = threads.filter(t => [t.title, t.subtitle, t.peer || ""].join(" ").toLowerCase().includes(q));
      }
      return filtered;
    }

    function renderThreads(items) {
      threadsEl.innerHTML = "";
      const threads = buildThreads(items);
      if (!threads.length) {
        threadsEl.innerHTML = `<div class="hint">No messages found.</div>`;
        return;
      }
      threads.forEach(thread => {
        const row = document.createElement("div");
        row.className = "jobrow";
        row.style.cursor = "pointer";
        row.style.border = (thread.mode === threadMode && (thread.mode !== "direct" || thread.peer === threadPeer)) ? "1px solid #f97316" : "1px solid var(--line)";
        row.innerHTML = `
          <div style="display:flex; gap:10px; align-items:flex-start;">
            <div style="width:42px; height:42px; border-radius:999px; background:linear-gradient(135deg,#3b82f6,#60a5fa); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:900; flex:0 0 42px;">${escapeHtml(thread.avatar)}</div>
            <div style="min-width:0; flex:1;">
              <div class="jobrow-top">
                <div class="jobrow-name">${escapeHtml(thread.title)}</div>
                <div style="display:flex; gap:8px; align-items:center;">${thread.unread ? `<span class="badge" style="background:#f97316;color:#fff;">${thread.unread}</span>` : ""}</div>
              </div>
              <div class="hint" style="margin-top:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(thread.subtitle)}</div>
              <div class="hint" style="margin-top:4px;">${escapeHtml(thread.stamp)}</div>
            </div>
          </div>
        `;
        row.addEventListener("click", () => {
          threadMode = thread.mode;
          threadPeer = thread.peer || "";
          if (thread.mode === "direct" && thread.peer) toSel.value = thread.peer;
          if (thread.mode === "allhands") toSel.value = "__ALL__";
          renderThreads(threadCache);
          renderFeed(threadCache);
        });
        threadsEl.appendChild(row);
      });
    }

    function renderFeed(items) {
      const visible = items.filter(item => {
        if (threadMode === "allhands") return item.kind !== "direct";
        const me = String((currentUser && currentUser.username) || "").toLowerCase();
        const from = String(item.from || "").toLowerCase();
        const to = String(item.to || "").toLowerCase();
        return item.kind === "direct" && ((from === me && to === String(threadPeer || "").toLowerCase()) || (to === me && from === String(threadPeer || "").toLowerCase()));
      });
      titleEl.textContent = threadMode === "allhands" ? "All Hands" : (buildThreads(items).find(t => t.mode === "direct" && t.peer === threadPeer)?.title || "Direct Message");
      subtitleEl.textContent = threadMode === "allhands" ? "Team-wide messages" : "Private conversation";
      feedEl.innerHTML = "";
      if (!visible.length) {
        feedEl.innerHTML = `<div class="hint">No messages in this conversation yet.</div>`;
        return;
      }
      visible.slice().reverse().forEach(item => {
        const mine = !!item.is_mine;
        const wrap = document.createElement("div");
        wrap.style.display = "flex";
        wrap.style.justifyContent = mine ? "flex-end" : "flex-start";
        const bubble = document.createElement("div");
        bubble.style.maxWidth = "78%";
        bubble.style.border = "1px solid var(--line)";
        bubble.style.borderRadius = "14px";
        bubble.style.padding = "12px 14px";
        bubble.style.background = mine ? "#fff7ed" : "#fff";
        bubble.innerHTML = `
          <div class="label" style="margin-bottom:6px;">${escapeHtml(mine ? "You" : (item.from_name || item.from || "User"))}</div>
          <div style="white-space:pre-wrap; font-weight:800;">${escapeHtml(item.message || "")}</div>
          <div class="hint" style="margin-top:8px; display:flex; justify-content:space-between; gap:12px; align-items:center;">
            <span>${escapeHtml(String(item.created_at || "").replace("T"," ").slice(0,16))}</span>
            <span>${!mine && !item.read ? `<span class="badge" style="background:#f97316;color:#fff;">New</span>` : ""}</span>
          </div>
        `;
        if (!mine && !item.read) {
          bubble.addEventListener("click", async () => {
            try { await apiMarkNotificationRead(item.id, true); } catch {}
            await refreshAll();
          });
          bubble.style.cursor = "pointer";
        }
        if (mine) {
          const actions = document.createElement("div");
          actions.style.display = "flex";
          actions.style.justifyContent = "flex-end";
          actions.style.marginTop = "8px";
          const del = document.createElement("button");
          del.type = "button";
          del.textContent = "Delete";
          styleActionButton(del, "danger", true);
          del.addEventListener("click", async (e) => {
            e.stopPropagation();
            if (!confirm("Delete this message?")) return;
            await apiDeleteNotification(item.id);
            await refreshAll();
          });
          actions.appendChild(del);
          bubble.appendChild(actions);
        }
        wrap.appendChild(bubble);
        feedEl.appendChild(wrap);
      });
    }

    async function refreshAll() {
      setFilterUi();
      const items = await apiListNotifications({ limit: 300 }).catch(() => []);
      threadCache = items.filter(item => {
        if (filterMode === "direct") return item.kind === "direct";
        if (filterMode === "inbox") return !item.is_mine;
        return true;
      });
      renderThreads(threadCache);
      renderFeed(threadCache);
      refreshBadges();
    }

    filterInbox.addEventListener("click", () => { filterMode = "inbox"; if (threadMode !== "allhands" && filterMode === "inbox") threadMode = "allhands"; refreshAll(); });
    filterDirect.addEventListener("click", () => { filterMode = "direct"; if (threadMode === "allhands") threadPeer = ""; refreshAll(); });
    filterAll.addEventListener("click", () => { filterMode = "all"; refreshAll(); });
    searchInput.addEventListener("input", () => renderThreads(threadCache));
    right.querySelector("#msg_refresh").addEventListener("click", refreshAll);
    right.querySelector("#msg_clear").addEventListener("click", () => { bodyInput.value = ""; });
    right.querySelector("#msg_mark_read").addEventListener("click", async () => {
      const target = threadCache.filter(item => {
        if (item.is_mine || item.read) return false;
        if (threadMode === "allhands") return item.kind !== "direct";
        const me = String((currentUser && currentUser.username) || "").toLowerCase();
        const from = String(item.from || "").toLowerCase();
        const to = String(item.to || "").toLowerCase();
        return item.kind === "direct" && to === me && from === String(threadPeer || "").toLowerCase();
      });
      for (const item of target) {
        try { await apiMarkNotificationRead(item.id, true); } catch {}
      }
      await refreshAll();
    });
    right.querySelector("#msg_send").addEventListener("click", async () => {
      const to = toSel.value;
      const message = bodyInput.value.trim();
      if (!message) return alert("Please enter a message.");
      await apiCreateNotification({ to, message });
      bodyInput.value = "";
      threadMode = to === "__ALL__" ? "allhands" : "direct";
      threadPeer = to === "__ALL__" ? "" : to;
      await refreshAll();
    });

    currentView = { refresh: async () => { await refreshRecipients(); await refreshAll(); } };
    refreshRecipients();
    refreshAll();
  }

  function renderChatView(mode) {
    setNavActive(mode === "tech" ? navAtlas : navMoses);
    setActiveChip(mode === "tech" ? "Atlas" : "Moses");
    setWorkspace(mode === "tech" ? "Atlas" : "Moses");
    clearWorkspaceActions();
 
    const root = document.createElement("div");
    root.className = "card";
 
    const title = document.createElement("h3");
    title.textContent = mode === "tech" ? "Atlas" : "Moses";
 
    const sub = document.createElement("div");
    sub.className = "hint";
    sub.textContent = mode === "tech" ? "Tech Support" : "Office Support";
 
    const msgs = document.createElement("div");
    msgs.style.marginTop = "10px";
    msgs.style.border = "1px solid var(--line)";
    msgs.style.borderRadius = "12px";
    msgs.style.padding = "10px";
    msgs.style.height = "360px";
    msgs.style.overflow = "auto";
    msgs.style.background = "#fff";
 
    const row = document.createElement("div");
    row.style.display = "flex";
    row.style.gap = "8px";
    row.style.marginTop = "10px";
 
    const input = document.createElement("input");
    input.className = "input";
    input.placeholder = mode === "tech" ? "Ask a tech question..." : "Ask an office question...";
 
    const btn = document.createElement("button");
    btn.className = "btn btn-orange";
    btn.textContent = "Send";
 
    row.appendChild(input);
    row.appendChild(btn);
 
    function addMsg(who, text) {
      const wrap = document.createElement("div");
      wrap.style.marginBottom = "10px";
 
      const meta = document.createElement("div");
      meta.className = "label";
      meta.style.marginBottom = "4px";
      meta.textContent = who;
 
      const body = document.createElement("div");
      body.style.whiteSpace = "pre-wrap";
      body.style.fontWeight = "900";
      body.textContent = text;
 
      wrap.appendChild(meta);
      wrap.appendChild(body);
      msgs.appendChild(wrap);
      msgs.scrollTop = msgs.scrollHeight;
    }
 
    let conversationId = "";
 
    function openAnyJobCard(job) {
      if (!job) return;
      const sourceLabel = String(job.source || "").toUpperCase();
      if (sourceLabel.startsWith("LEGACY") || !job.id) {
        openDrawer(`Legacy Job ${job.job_number || "Details"}`, async (drawerBody) => {
          const card = document.createElement("div");
          card.className = "card";
          card.innerHTML = `
            <h3 style="margin:0;">${escapeHtml(job.customer || job.customer_name || "Legacy Job")}</h3>
            <div class="hint" style="margin-top:6px;">${escapeHtml(job.job_number || "")}${job.date ? ` - ${escapeHtml(job.date)}` : ""}${job.source ? ` - ${escapeHtml(String(job.source).toUpperCase())}` : ""}</div>
            <div class="grid2" style="margin-top:12px;">
              <div><div class="label">Customer</div><div class="field">${escapeHtml(job.customer || job.customer_name || "")}</div></div>
              <div><div class="label">Job #</div><div class="field">${escapeHtml(job.job_number || "")}</div></div>
              <div><div class="label">Estimate #</div><div class="field">${formatDocRefDisplay(job.estimate_number || job.estimate_no || "")}</div></div>
              <div><div class="label">Invoice #</div><div class="field">${formatDocRefDisplay(job.invoice_number || job.invoice_no || "")}</div></div>
              <div><div class="label">PO #</div><div class="field">${formatDocRefDisplay(job.po_number || job.po_no || "")}</div></div>
              <div><div class="label">Address</div><div class="field">${escapeHtml(job.address || "")}</div></div>
              <div><div class="label">Date</div><div class="field">${escapeHtml(job.date || "")}</div></div>
              <div><div class="label">Status</div><div class="field">${escapeHtml(job.status || "")}</div></div>
              <div><div class="label">Contact</div><div class="field">${escapeHtml(job.contact || job.contact_name || "")}</div></div>
            </div>
            <div style="margin-top:10px;"><div class="label">Job Notes</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.job_notes || job.tech_notes || job.description || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Work Performed</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.work_performed || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Additional Recommendations</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.additional_recommendations || "")}</div></div>
            <div style="margin-top:10px;"><div class="label">Parts Used</div><div class="field" style="white-space:pre-wrap;">${escapeHtml(job.parts_used || "")}</div></div>
          `;
          drawerBody.appendChild(card);
        });
        return;
      }
      apiGetJob(job.id).then(full => {
        openDrawer(`Job ${full.job_number || "Details"}`, async (bd) => renderJobDetails(bd, full, { afterSave: async () => {}, afterDelete: async () => {} }));
      }).catch(e => alert(e.message || String(e)));
    }
 
    function openJobResultsPanel(items) {
      const panel = document.createElement("div");
      panel.style.position = "fixed";
      panel.style.top = "0";
      panel.style.right = "0";
      panel.style.width = "420px";
      panel.style.maxWidth = "92vw";
      panel.style.height = "100vh";
      panel.style.background = "#0f172a";
      panel.style.borderLeft = "1px solid rgba(255,255,255,.15)";
      panel.style.zIndex = "9999";
      panel.style.overflowY = "auto";
      panel.style.padding = "16px";
      const inner = document.createElement("div");
      inner.style.display = "grid";
      inner.style.gap = "8px";
      const close = document.createElement("button");
      close.className = "btn";
      close.textContent = "Close";
      close.addEventListener("click", () => panel.remove());
      panel.appendChild(close);
      panel.appendChild(inner);
      const sorted = [...items].sort((a,b)=>String(b.date||"").localeCompare(String(a.date||"")));
      sorted.forEach(j => {
        const card = document.createElement("div");
        card.className = "jobrow";
        card.style.cursor = "pointer";
        const customer = j.customer || j.customer_name || "Job";
        const estimate = j.estimate_number || j.estimate_no || "";
        const invoice = j.invoice_number || j.invoice_no || "";
        const address = j.address || "";
        const date = j.date || j.date_display || "";
        const sourceLabel = j.source ? String(j.source).toUpperCase() : "CURRENT";
        card.innerHTML = `
          <div class="jobrow-top">
            <div class="jobrow-name">${escapeHtml(customer)}</div>
            <div style="display:flex; gap:8px; align-items:center;">${statusPill(j.status || "Dispatch").outerHTML}<span class="badge">${escapeHtml(sourceLabel)}</span></div>
          </div>
          <div class="jobrow-addr">Job #: ${escapeHtml(j.job_number || "")}${date ? ` - ${escapeHtml(date)}` : ""}</div>
          <div class="hint" style="margin-top:6px; font-weight:900;">Estimate: ${formatDocRefDisplay(estimate)} | Invoice: ${formatDocRefDisplay(invoice)} | PO: ${formatDocRefDisplay(j.po_number || j.po_no || "")}</div>
          <div class="hint" style="margin-top:4px;">${escapeHtml(address || "")}</div>
        `;
        card.addEventListener("click", () => openAnyJobCard(j));
        inner.appendChild(card);
      });
      document.body.appendChild(panel);
    }

    function addJobCards(items) {
      if (!Array.isArray(items) || !items.length) return;
      const wrap = document.createElement("div");
      wrap.style.display = "grid";
      wrap.style.gap = "8px";
      wrap.style.marginBottom = "10px";
      if (items.length > 5) {
        const more = document.createElement("div");
        more.className = "jobrow";
        more.style.cursor = "pointer";
        more.innerHTML = `<div class="jobrow-top"><div class="jobrow-name">View All Results</div></div><div class="jobrow-addr">${items.length} matching jobs</div><div class="hint" style="margin-top:4px;">Open full results newest to oldest</div>`;
        more.addEventListener("click", () => openJobResultsPanel(items));
        wrap.appendChild(more);
      }
      items.slice(0, 5).forEach(j => {
        const card = document.createElement("div");
        card.className = "jobrow";
        card.style.cursor = "pointer";
        const customer = j.customer || j.customer_name || "Job";
        const estimate = j.estimate_number || j.estimate_no || "";
        const invoice = j.invoice_number || j.invoice_no || "";
        const address = j.address || "";
        const date = j.date || j.date_display || "";
        const sourceLabel = j.source ? String(j.source).toUpperCase() : "CURRENT";
        card.innerHTML = `
          <div class="jobrow-top">
            <div class="jobrow-name">${escapeHtml(customer)}</div>
            <div style="display:flex; gap:8px; align-items:center;">${statusPill(j.status || "Dispatch").outerHTML}<span class="badge">${escapeHtml(sourceLabel)}</span></div>
          </div>
          <div class="jobrow-addr">Job #: ${escapeHtml(j.job_number || "")}${date ? ` - ${escapeHtml(date)}` : ""}</div>
          <div class="hint" style="margin-top:6px; font-weight:900;">Estimate: ${formatDocRefDisplay(estimate || "")} | Invoice: ${formatDocRefDisplay(invoice || "")} | PO: ${formatDocRefDisplay(j.po_number || j.po_no || "")}</div>
          <div class="hint" style="margin-top:4px;">${escapeHtml(address || "")}</div>
        `;
        card.addEventListener("click", () => openAnyJobCard(j));
        wrap.appendChild(card);
      });
      msgs.appendChild(wrap);
      msgs.scrollTop = msgs.scrollHeight;
    }
 
    async function send() {
 
      const q = input.value.trim();
      if (!q) return;
      addMsg("You", q);
      input.value = "";
      try {
        const data = await fetchJSON("/atlas/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ q, mode: mode === "tech" ? "tech" : "office", conversation_id: conversationId || "" }),
        });
        conversationId = data.conversation_id || conversationId || "";
        addMsg(mode === "tech" ? "Atlas" : "Moses", data.answer_md || (data.moses && data.moses.jobs && data.moses.jobs.length ? "Found matching jobs." : "No matching jobs found."));
        if (mode === "office") {
          if (data.moses && data.moses.job) addJobCards([data.moses.job]);
          if (data.moses && Array.isArray(data.moses.jobs) && data.moses.jobs.length) addJobCards(data.moses.jobs);
        }
      } catch (e) {
        addMsg(mode === "tech" ? "Atlas" : "Moses", `Error: ${e.message || e}`);
      }
    }
 
    btn.addEventListener("click", send);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") send();
    });
 
    root.appendChild(title);
    root.appendChild(sub);
    root.appendChild(msgs);
    root.appendChild(row);
 
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
 
    currentView = { refresh: async () => {} };
  }
 
  if (loginBtn) loginBtn.addEventListener("click", handleLogin);
  if (pinBtn) pinBtn.addEventListener("click", handlePinLogin);
  if (logoutBtn) logoutBtn.addEventListener("click", handleLogout);
  if (passwordInput) passwordInput.addEventListener("keydown", (e) => { if (e.key === "Enter") handleLogin(); });
  if (usernameInput) usernameInput.addEventListener("keydown", (e) => { if (e.key === "Enter") handleLogin(); });
  if (pinInput) pinInput.addEventListener("keydown", (e) => { if (e.key === "Enter") handlePinLogin(); });

  if (headerCalendarBtn) headerCalendarBtn.addEventListener("click", renderCalendarView);
 
  if (navFormsTimeCard) navFormsTimeCard.addEventListener("click", renderTimeCardView);
  if (navFormsTimeOff) navFormsTimeOff.addEventListener("click", renderTimeOffView);
  if (navTakeoffs) navTakeoffs.addEventListener("click", renderTakeoffsView);
  if (navFormsSignOff) navFormsSignOff.addEventListener("click", renderSignOffLibraryView);
 
  if (navDataCenter) {
    const small = navDataCenter.querySelector("small");
    if (small) small.textContent = "Monthly Dashboard";
  }
 
  if (navJobFlow) navJobFlow.addEventListener("click", () => renderJobFlowView("Dispatch"));
  if (navAllJobs) navAllJobs.addEventListener("click", renderAllJobsView);
  if (navEstimateInvoice) navEstimateInvoice.addEventListener("click", renderEstimatePage);
  if (navEstimatePage && !navEstimateInvoice) navEstimatePage.addEventListener("click", renderEstimatePage);
  if (navInvoicePage && !navEstimateInvoice) navInvoicePage.addEventListener("click", renderInvoicePage);
  if (navCustomers) navCustomers.addEventListener("click", renderCustomersView);
  if (navContacts) navContacts.addEventListener("click", renderContactsView);
  if (navPartsList) navPartsList.addEventListener("click", renderPartsListView);
 

function renderDataUploadView() {
    setNavActive(navDataUpload);
    setActiveChip("Office Flow");
    setWorkspace("Data Upload");
    clearWorkspaceActions();

    const root = document.createElement("div");
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h3>Admin Data Upload</h3>
      <div class="hint">Upload only billable_time.csv or tech_notes.csv to the live Render disk.</div>
      <div class="grid2" style="margin-top:12px;">
        <div>
          <div class="label">billable_time.csv</div>
          <input class="input" id="upload_billable" type="file" accept=".csv" />
          <button class="btn btn-orange" id="upload_billable_btn" style="margin-top:10px;">Upload billable_time.csv</button>
          <div class="hint" id="upload_billable_status" style="margin-top:8px;"></div>
        </div>
        <div>
          <div class="label">tech_notes.csv</div>
          <input class="input" id="upload_notes" type="file" accept=".csv" />
          <button class="btn btn-orange" id="upload_notes_btn" style="margin-top:10px;">Upload tech_notes.csv</button>
          <div class="hint" id="upload_notes_status" style="margin-top:8px;"></div>
        </div>
        <div>
          <div class="label">customers.csv</div>
          <input class="input" id="upload_customers" type="file" accept=".csv" />
          <button class="btn btn-orange" id="upload_customers_btn" style="margin-top:10px;">Upload customers.csv</button>
          <div class="hint" id="upload_customers_status" style="margin-top:8px;"></div>
        </div>
        <div>
          <div class="label">contacts.csv</div>
          <input class="input" id="upload_contacts" type="file" accept=".csv" />
          <button class="btn btn-orange" id="upload_contacts_btn" style="margin-top:10px;">Upload contacts.csv</button>
          <div class="hint" id="upload_contacts_status" style="margin-top:8px;"></div>
        </div>
      </div>
      <div class="card" style="margin-top:14px; padding:14px;">
        <div style="font-weight:900; margin-bottom:6px;">How to use</div>
        <div class="hint">billable_time.csv and tech_notes.csv overwrite those live files directly. customers.csv and contacts.csv are converted into customers_db.json and contacts_db.json on the live Render disk. Restart the Render service once after upload to refresh references.</div>
      </div>
    `;

    const wireUploader = (inputId, buttonId, statusId, expectedName) => {
      const input = card.querySelector(inputId);
      const button = card.querySelector(buttonId);
      const status = card.querySelector(statusId);
      button.addEventListener("click", async () => {
        try {
          const file = input.files && input.files[0];
          if (!file) {
            status.textContent = "Choose a CSV first.";
            return;
          }
          if (file.name !== expectedName) {
            status.textContent = `Please choose ${expectedName}.`;
            return;
          }
          status.textContent = "Uploading...";
          const result = await uploadAdminDataFile(file);
          status.textContent = `Uploaded ${result.filename} successfully. Restart Render once to refresh references.`;
          input.value = "";
        } catch (e) {
          status.textContent = e.message || String(e);
        }
      });
    };

    wireUploader("#upload_billable", "#upload_billable_btn", "#upload_billable_status", "billable_time.csv");
    wireUploader("#upload_notes", "#upload_notes_btn", "#upload_notes_status", "tech_notes.csv");
    wireUploader("#upload_customers", "#upload_customers_btn", "#upload_customers_status", "customers.csv");
    wireUploader("#upload_contacts", "#upload_contacts_btn", "#upload_contacts_status", "contacts.csv");

    root.appendChild(card);
    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
  }

function renderSaddlebackView() {
    setNavActive(navSaddleback);
    setActiveChip("Office Flow");
    setWorkspace("Saddleback Design Co.");
    clearWorkspaceActions();

    const STORE_KEY = "doorks_saddleback_design_co_v3";
    const loadStore = () => {
      try {
        const raw = localStorage.getItem(STORE_KEY);
        const parsed = raw ? JSON.parse(raw) : null;
        return parsed && typeof parsed === "object" ? parsed : { orders: [], expenses: [], purchases: [] };
      } catch {
        return { orders: [], expenses: [], purchases: [] };
      }
    };
    const saveStore = (data) => localStorage.setItem(STORE_KEY, JSON.stringify(data));
    let state = loadStore();

    const money = (n) => `$${(Number(n || 0)).toFixed(2)}`;
    const monthKey = (iso) => String(iso || "").slice(0, 7);

    const root = document.createElement("div");
    const tabs = document.createElement("div");
    tabs.style.display = "flex";
    tabs.style.gap = "8px";
    tabs.style.flexWrap = "wrap";
    tabs.style.marginBottom = "12px";

    const btnOrders = document.createElement("button");
    btnOrders.className = "btn btn-orange";
    btnOrders.textContent = "Orders";
    const btnExpenses = document.createElement("button");
    btnExpenses.className = "btn";
    btnExpenses.textContent = "Expenses";
    const btnPurchases = document.createElement("button");
    btnPurchases.className = "btn";
    btnPurchases.textContent = "Purchases";
    const btnTaxes = document.createElement("button");
    btnTaxes.className = "btn";
    btnTaxes.textContent = "Tax Snapshot";
    [btnOrders, btnExpenses, btnPurchases, btnTaxes].forEach(b => tabs.appendChild(b));
    root.appendChild(tabs);

    const host = document.createElement("div");
    root.appendChild(host);

    function renderTable(items, columns, allowDelete = true) {
      if (!items.length) {
        const empty = document.createElement("div");
        empty.className = "card";
        empty.innerHTML = `<div class="hint">No records yet.</div>`;
        return empty;
      }
      const card = document.createElement("div");
      card.className = "card";
      const table = document.createElement("table");
      table.className = "table";
      const thead = document.createElement("thead");
      const trh = document.createElement("tr");
      columns.forEach(col => {
        const th = document.createElement("th");
        th.textContent = col.label;
        trh.appendChild(th);
      });
      if (allowDelete) {
        const thDel = document.createElement("th");
        thDel.textContent = "";
        trh.appendChild(thDel);
      }
      thead.appendChild(trh);
      table.appendChild(thead);
      const tbody = document.createElement("tbody");
      items.forEach((item) => {
        const tr = document.createElement("tr");
        columns.forEach(col => {
          const td = document.createElement("td");
          td.textContent = col.render ? col.render(item) : String(item[col.key] || "");
          tr.appendChild(td);
        });
        if (allowDelete) {
          const tdDel = document.createElement("td");
          const del = document.createElement("button");
          del.className = "btn";
          del.textContent = "Delete";
          del.addEventListener("click", () => {
            state[item.bucket] = state[item.bucket].filter(x => x.id !== item.id);
            saveStore(state);
            renderCurrent();
          });
          tdDel.appendChild(del);
          tr.appendChild(tdDel);
        }
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      card.appendChild(table);
      return card;
    }

    function summaryCard(title, value, hint = "") {
      const card = document.createElement("div");
      card.className = "metric";
      card.innerHTML = `<div class="metric-label">${title}</div><div class="metric-value">${value}</div><div class="metric-sub">${hint}</div>`;
      return card;
    }

    function exportSdcRows(filename, headers, rows) {
      downloadCsv(filename, headers, rows);
    }


    function renderOrders() {
      host.innerHTML = "";
      btnOrders.className = "btn btn-orange";
      btnExpenses.className = btnPurchases.className = btnTaxes.className = "btn";

      const form = document.createElement("div");
      form.className = "card";
      form.innerHTML = `
        <h3>Orders</h3>
        <div class="hint">Track Etsy or in-person orders, shipping, production status, and delivery.</div>
        <div class="grid2" style="margin-top:12px;">
          <div><div class="label">Date</div><input class="input" id="sdc_order_date" type="date" /></div>
          <div><div class="label">Channel</div><input class="input" id="sdc_order_channel" placeholder="Etsy / In Person" /></div>
          <div><div class="label">Customer</div><input class="input" id="sdc_order_customer" placeholder="Customer name" /></div>
          <div><div class="label">Address</div><input class="input" id="sdc_order_address" placeholder="Customer address" /></div>
          <div><div class="label">Item</div><input class="input" id="sdc_order_item" placeholder="Door / style / finish" /></div>
          <div><div class="label">Order ID</div><input class="input" id="sdc_order_ref" placeholder="Etsy order / invoice #" /></div>
          <div><div class="label">Total Amount</div><input class="input" id="sdc_order_total" type="number" step="0.01" placeholder="0.00" /></div>
          <div><div class="label">Shipping Cost</div><input class="input" id="sdc_order_shipping" type="number" step="0.01" placeholder="0.00" /></div>
          <div><div class="label">Sales Tax</div><input class="input" id="sdc_order_tax" type="number" step="0.01" placeholder="0.00" /></div>
          <div><div class="label">Status</div>
            <select class="input" id="sdc_order_status">
              <option value="Open">Open</option>
              <option value="In Production">In Production</option>
              <option value="Shipped">Shipped</option>
              <option value="Delivered">Delivered</option>
            </select>
          </div>
          <div style="grid-column:1 / -1;"><div class="label">Notes</div><input class="input" id="sdc_order_notes" placeholder="Notes" /></div>
        </div>
        <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;"><button class="btn btn-orange" id="sdc_save_order">Save Order</button><button class="btn" id="sdc_export_orders">Export Orders CSV</button></div>
      `;
      host.appendChild(form);

      const filters = document.createElement("div");
      filters.className = "card";
      filters.style.marginTop = "12px";
      filters.innerHTML = `
        <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
          <button class="btn btn-orange" data-status="All">All</button>
          <button class="btn" data-status="Open">Open</button>
          <button class="btn" data-status="In Production">In Production</button>
          <button class="btn" data-status="Shipped">Shipped</button>
          <button class="btn" data-status="Delivered">Delivered</button>
          <input class="input" id="sdc_order_search" placeholder="Search customer, address, order id, item, notes" style="max-width:360px; margin-left:auto;" />
        </div>
      `;
      host.appendChild(filters);

      let activeStatus = "All";
      const searchInput = filters.querySelector("#sdc_order_search");

      const renderOrderList = () => {
        let rows = state.orders.slice();
        if (activeStatus !== "All") rows = rows.filter(x => String(x.status || "") === activeStatus);
        const q = String(searchInput.value || "").trim().toLowerCase();
        if (q) {
          rows = rows.filter(x => [x.customer, x.address, x.ref, x.item, x.notes].some(v => String(v || "").toLowerCase().includes(q)));
        }
        if (rows.length) {
          rows.sort((a,b) => String(b.date || "").localeCompare(String(a.date || "")));
        }

        const existing = host.querySelector(".sdc-order-list-wrap");
        if (existing) existing.remove();

        const wrap = document.createElement("div");
        wrap.className = "sdc-order-list-wrap";
        wrap.style.marginTop = "12px";
        wrap.appendChild(renderTable(rows, [
          { key: "date", label: "Date" },
          { key: "channel", label: "Channel" },
          { key: "customer", label: "Customer" },
          { key: "address", label: "Address" },
          { key: "ref", label: "Order ID" },
          { key: "item", label: "Item" },
          { key: "status", label: "Status" },
          { key: "notes", label: "Notes" },
          { key: "total", label: "Total", render: (x) => money(x.total) },
          { key: "shipping", label: "Shipping", render: (x) => money(x.shipping) },
        { key: "tax", label: "Tax", render: (x) => money(x.tax) },
        ]));
        host.appendChild(wrap);
      };

      filters.querySelectorAll("button[data-status]").forEach(btn => {
        btn.addEventListener("click", () => {
          activeStatus = btn.getAttribute("data-status");
          filters.querySelectorAll("button[data-status]").forEach(b => b.className = b === btn ? "btn btn-orange" : "btn");
          renderOrderList();
        });
      });
      searchInput.addEventListener("input", renderOrderList);

      form.querySelector("#sdc_export_orders").addEventListener("click", () => {
        const rows = state.orders.slice().sort((a,b) => String(b.date||"").localeCompare(String(a.date||""))).map(x => [x.date, x.channel, x.customer, x.address, x.ref, x.item, x.status, x.notes, x.total, x.shipping, x.tax, x.channel_fee, x.profit]);
        exportSdcRows("saddleback_orders.csv", ["Date","Channel","Customer","Address","Order ID","Item","Status","Notes","Total Amount","Shipping Cost","Sales Tax","Channel Fee","Profit"], rows);
      });

      form.querySelector("#sdc_save_order").addEventListener("click", () => {
        const row = {
          id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          bucket: "orders",
          date: form.querySelector("#sdc_order_date").value,
          channel: form.querySelector("#sdc_order_channel").value.trim(),
          customer: form.querySelector("#sdc_order_customer").value.trim(),
          address: form.querySelector("#sdc_order_address").value.trim(),
          item: form.querySelector("#sdc_order_item").value.trim(),
          ref: form.querySelector("#sdc_order_ref").value.trim(),
          total: Number(form.querySelector("#sdc_order_total").value || 0),
          shipping: Number(form.querySelector("#sdc_order_shipping").value || 0),
          tax: Number(form.querySelector("#sdc_order_tax").value || 0),
          status: form.querySelector("#sdc_order_status").value,
          notes: form.querySelector("#sdc_order_notes").value.trim(),
        };
        if (!row.date || !row.customer || !row.item) return alert("Date, customer, and item are required.");
        state.orders.unshift(row);
        saveStore(state);
        renderOrders();
      });

      renderOrderList();
    }

    function renderExpenses() {
      host.innerHTML = "";
      btnExpenses.className = "btn btn-orange";
      btnOrders.className = btnPurchases.className = btnTaxes.className = "btn";
      const form = document.createElement("div");
      form.className = "card";
      form.innerHTML = `
        <h3>Expenses</h3>
        <div class="hint">Track recurring business costs like Etsy fees, mileage, tools, software, fuel, marketing, and home office items.</div>
        <div class="grid2" style="margin-top:12px;">
          <div><div class="label">Date</div><input class="input" id="sdc_exp_date" type="date" /></div>
          <div><div class="label">Category</div><input class="input" id="sdc_exp_cat" placeholder="Fees / Fuel / Tools / Marketing" /></div>
          <div><div class="label">Vendor</div><input class="input" id="sdc_exp_vendor" placeholder="Vendor" /></div>
          <div><div class="label">Amount</div><input class="input" id="sdc_exp_amt" type="number" step="0.01" placeholder="0.00" /></div>
          <div style="grid-column:1 / -1;"><div class="label">Notes</div><input class="input" id="sdc_exp_notes" placeholder="Notes" /></div>
        </div>
        <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;"><button class="btn btn-orange" id="sdc_save_exp">Save Expense</button><button class="btn" id="sdc_export_exp">Export Expenses CSV</button></div>
      `;
      host.appendChild(form);
      form.querySelector("#sdc_export_exp").addEventListener("click", () => {
        const rows = state.expenses.slice().sort((a,b) => String(b.date||"").localeCompare(String(a.date||""))).map(x => [x.date, x.category, x.vendor, x.amount, x.notes]);
        exportSdcRows("saddleback_expenses.csv", ["Date","Category","Vendor","Amount","Notes"], rows);
      });

      form.querySelector("#sdc_save_exp").addEventListener("click", () => {
        const row = {
          id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          bucket: "expenses",
          date: form.querySelector("#sdc_exp_date").value,
          category: form.querySelector("#sdc_exp_cat").value.trim(),
          vendor: form.querySelector("#sdc_exp_vendor").value.trim(),
          amount: Number(form.querySelector("#sdc_exp_amt").value || 0),
          notes: form.querySelector("#sdc_exp_notes").value.trim(),
        };
        if (!row.date || !row.category) return alert("Date and category are required.");
        state.expenses.unshift(row);
        saveStore(state);
        renderExpenses();
      });
      host.appendChild(renderTable(state.expenses, [
        { key: "date", label: "Date" },
        { key: "category", label: "Category" },
        { key: "vendor", label: "Vendor" },
        { key: "notes", label: "Notes" },
        { key: "amount", label: "Amount", render: (x) => money(x.amount) },
      ]));
    }

    function renderPurchases() {
      host.innerHTML = "";
      btnPurchases.className = "btn btn-orange";
      btnOrders.className = btnExpenses.className = btnTaxes.className = "btn";
      const form = document.createElement("div");
      form.className = "card";
      form.innerHTML = `
        <h3>Material Purchases</h3>
        <div class="hint">Track wood, hardware, finish, shipping materials, and outsourced labor tied to orders.</div>
        <div class="grid2" style="margin-top:12px;">
          <div><div class="label">Date</div><input class="input" id="sdc_pur_date" type="date" /></div>
          <div><div class="label">Vendor</div><input class="input" id="sdc_pur_vendor" placeholder="Vendor" /></div>
          <div><div class="label">Material / Item</div><input class="input" id="sdc_pur_item" placeholder="Oak slab / rails / hinges / stain" /></div>
          <div><div class="label">Linked Order</div><input class="input" id="sdc_pur_order" placeholder="Customer / order #" /></div>
          <div><div class="label">Amount</div><input class="input" id="sdc_pur_amt" type="number" step="0.01" placeholder="0.00" /></div>
          <div><div class="label">Tax Paid</div><input class="input" id="sdc_pur_tax" type="number" step="0.01" placeholder="0.00" /></div>
        </div>
        <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;"><button class="btn btn-orange" id="sdc_save_pur">Save Purchase</button><button class="btn" id="sdc_export_pur">Export Purchases CSV</button></div>
      `;
      host.appendChild(form);
      form.querySelector("#sdc_export_pur").addEventListener("click", () => {
        const rows = state.purchases.slice().sort((a,b) => String(b.date||"").localeCompare(String(a.date||""))).map(x => [x.date, x.vendor, x.item, x.order_ref, x.amount, x.tax_paid]);
        exportSdcRows("saddleback_purchases.csv", ["Date","Vendor","Material / Item","Linked Order","Amount","Tax Paid"], rows);
      });
      form.querySelector("#sdc_save_pur").addEventListener("click", () => {
        const row = {
          id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          bucket: "purchases",
          date: form.querySelector("#sdc_pur_date").value,
          vendor: form.querySelector("#sdc_pur_vendor").value.trim(),
          item: form.querySelector("#sdc_pur_item").value.trim(),
          order_ref: form.querySelector("#sdc_pur_order").value.trim(),
          amount: Number(form.querySelector("#sdc_pur_amt").value || 0),
          tax_paid: Number(form.querySelector("#sdc_pur_tax").value || 0),
        };
        if (!row.date || !row.item) return alert("Date and item are required.");
        state.purchases.unshift(row);
        saveStore(state);
        renderPurchases();
      });
      host.appendChild(renderTable(state.purchases, [
        { key: "date", label: "Date" },
        { key: "vendor", label: "Vendor" },
        { key: "item", label: "Item" },
        { key: "order_ref", label: "Linked Order" },
        { key: "amount", label: "Amount", render: (x) => money(x.amount) },
        { key: "tax_paid", label: "Tax Paid", render: (x) => money(x.tax_paid) },
      ]));
    }

    function renderTaxes() {
      host.innerHTML = "";
      btnTaxes.className = "btn btn-orange";
      btnOrders.className = btnExpenses.className = btnPurchases.className = "btn";

      const exportRow = document.createElement("div");
      exportRow.style.display = "flex";
      exportRow.style.gap = "8px";
      exportRow.style.marginBottom = "12px";
      const exportBtn = document.createElement("button");
      exportBtn.className = "btn";
      exportBtn.textContent = "Export Tax Snapshot CSV";
      exportRow.appendChild(exportBtn);
      host.appendChild(exportRow);

      const wrap = document.createElement("div");
      wrap.style.display = "grid";
      wrap.style.gridTemplateColumns = "repeat(auto-fit, minmax(220px, 1fr))";
      wrap.style.gap = "12px";

      const revenue = state.orders.reduce((sum, x) => sum + Number(x.total || 0), 0);
      const shipping = state.orders.reduce((sum, x) => sum + Number(x.shipping || 0), 0);
      const salesTax = state.orders.reduce((sum, x) => sum + Number(x.tax || 0), 0);
      const expenses = state.expenses.reduce((sum, x) => sum + Number(x.amount || 0), 0);
      const purchases = state.purchases.reduce((sum, x) => sum + Number(x.amount || 0), 0);
      const purchaseTax = state.purchases.reduce((sum, x) => sum + Number(x.tax_paid || 0), 0);
      const estProfit = revenue - expenses - purchases;

      [
        summaryCard("Gross Revenue", money(revenue), "All saved orders"),
        summaryCard("Shipping", money(shipping), "Shipping charged on saved orders"),
        summaryCard("Expenses", money(expenses), "Recurring business costs"),
        summaryCard("Material Purchases", money(purchases), "Order-related material spend"),
        summaryCard("Tax Paid on Purchases", money(purchaseTax), "Helpful for bookkeeping"),
        summaryCard("Est. Profit", money(estProfit), "Revenue - expenses - purchases"),
      ].forEach(card => wrap.appendChild(card));
      host.appendChild(wrap);

      const months = {};
      [...state.orders, ...state.expenses, ...state.purchases].forEach(item => {
        const key = monthKey(item.date) || "No Date";
        months[key] = months[key] || { revenue: 0, expenses: 0, purchases: 0 };
        if (item.bucket === "orders") months[key].revenue += Number(item.total || 0);
        if (item.bucket === "expenses") months[key].expenses += Number(item.amount || 0);
        if (item.bucket === "purchases") months[key].purchases += Number(item.amount || 0);
      });

      const monthly = Object.keys(months).sort().reverse().map(key => ({
        month: key,
        revenue: months[key].revenue,
        expenses: months[key].expenses,
        purchases: months[key].purchases,
        net: months[key].revenue - months[key].expenses - months[key].purchases,
      }));

      exportBtn.addEventListener("click", () => {
        const rows = monthly.map(x => [x.month, x.revenue, x.expenses, x.purchases, x.net]);
        exportSdcRows("saddleback_tax_snapshot.csv", ["Month","Revenue","Expenses","Purchases","Net"], rows);
      });

      host.appendChild(renderTable(monthly, [
        { key: "month", label: "Month" },
        { key: "revenue", label: "Revenue", render: (x) => money(x.revenue) },
        { key: "expenses", label: "Expenses", render: (x) => money(x.expenses) },
        { key: "purchases", label: "Purchases", render: (x) => money(x.purchases) },
        { key: "net", label: "Net", render: (x) => money(x.net) },
      ], false));
    }

    function renderCurrent() {
      if (btnOrders.className.includes("btn-orange")) return renderOrders();
      if (btnExpenses.className.includes("btn-orange")) return renderExpenses();
      if (btnPurchases.className.includes("btn-orange")) return renderPurchases();
      return renderTaxes();
    }

    btnOrders.addEventListener("click", renderOrders);
    btnExpenses.addEventListener("click", renderExpenses);
    btnPurchases.addEventListener("click", renderPurchases);
    btnTaxes.addEventListener("click", renderTaxes);

    workspaceBody.innerHTML = "";
    workspaceBody.appendChild(root);
    renderOrders();
  }

  if (navDataCenter)
  if (navDataCenter) navDataCenter.addEventListener("click", renderDataCenterView);
  if (navPayroll) navPayroll.addEventListener("click", renderPayrollView);
  if (navEmployees) navEmployees.addEventListener("click", renderEmployeesView);
  if (navDataUpload) navDataUpload.addEventListener("click", renderDataUploadView);
  if (navSaddleback) navSaddleback.addEventListener("click", renderSaddlebackView);
 
  if (navAtlas) navAtlas.addEventListener("click", () => renderChatView("tech"));
  if (navMoses) navMoses.addEventListener("click", () => renderChatView("office"));
 
  if (navNotifications) {
    navNotifications.addEventListener("click", renderNotificationsView);
  }
 
  (async () => {
    if (loginBody) loginBody.style.display = "none";
    if (formsBody) formsBody.style.display = "none";
    if (loginChev) loginChev.innerHTML = "&#9656;";
    if (formsChev) formsChev.innerHTML = "&#9656;";
    const me = await apiAuthMe().catch(() => ({ logged_in: false, user: null }));
    currentUser = me && me.logged_in ? me.user : null;
    pendingPinUser = null;
    applyRoleAccess(currentUser ? currentUser.role : null);
    updateLoginUi();
    if (!currentUser) {
      showLoggedOutSplash();
      return;
    }
    renderCalendarView();
    apiListTimeOff({ limit: 500 }).then(items => {
      const pendingCount = (items || []).filter(item => String(item.status || '').toLowerCase() === 'pending' || !!item.emergency).length;
      const timeOffBadge = el('badgeTimeOff');
      if (timeOffBadge) {
        timeOffBadge.textContent = String(pendingCount);
        timeOffBadge.style.display = pendingCount ? 'inline-flex' : 'none';
      }
    }).catch(() => {});
    refreshBadges();
  })();
})();
