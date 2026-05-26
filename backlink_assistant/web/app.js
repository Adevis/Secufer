"use strict";

const state = { sites: [], currentSiteId: null };

// ---- API helpers ---------------------------------------------------------
async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Erreur ${res.status}`);
  return data;
}

function toast(message, isError) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.toggle("error", !!isError);
  el.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.add("hidden"), 2600);
}

function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

const STATUS_LABEL = { todo: "À faire", submitted: "Soumis", approved: "Validé", rejected: "Refusé" };
const STATUS_NEXT = { todo: "submitted", submitted: "approved", approved: "todo", rejected: "todo" };

// ---- Tabs ----------------------------------------------------------------
document.querySelectorAll(".tabs button").forEach((btn) => {
  btn.addEventListener("click", () => activateTab(btn.dataset.tab));
});

function activateTab(tab) {
  document.querySelectorAll(".tabs button").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".tab").forEach((s) =>
    s.classList.toggle("active", s.id === `tab-${tab}`));
  if (tab === "opportunities") renderOpportunities();
  if (tab === "tracker") renderTracker();
  if (tab === "today") renderToday();
}

// ---- Sites ---------------------------------------------------------------
async function loadSites() {
  const data = await api("GET", "/api/sites");
  state.sites = data.sites;
  if (!state.currentSiteId && state.sites.length) state.currentSiteId = state.sites[0].id;
  renderSiteList();
}

function renderSiteList() {
  const el = document.getElementById("site-list");
  if (!state.sites.length) {
    el.innerHTML = `<p class="empty">Aucun site pour l'instant. Ajoutez-en un ci-dessus.</p>`;
    return;
  }
  el.innerHTML = state.sites.map((s) => `
    <div class="item ${s.id === state.currentSiteId ? "selected" : ""}">
      <div>
        <h3>${escapeHtml(s.name)}</h3>
        <div class="meta">${escapeHtml(s.url)}</div>
        <div class="meta">${escapeHtml(s.keywords || "Pas encore de mots-clés")}</div>
      </div>
      <div class="actions">
        <button class="secondary" data-select="${s.id}">
          ${s.id === state.currentSiteId ? "Sélectionné" : "Choisir"}</button>
        <button class="ghost" data-delete="${s.id}">Supprimer</button>
      </div>
    </div>`).join("");

  el.querySelectorAll("[data-select]").forEach((b) =>
    b.addEventListener("click", () => { state.currentSiteId = +b.dataset.select; renderSiteList(); }));
  el.querySelectorAll("[data-delete]").forEach((b) =>
    b.addEventListener("click", () => deleteSite(+b.dataset.delete)));
}

async function deleteSite(id) {
  if (!confirm("Supprimer ce site et son suivi ?")) return;
  await api("DELETE", `/api/sites/${id}`);
  if (state.currentSiteId === id) state.currentSiteId = null;
  await loadSites();
  toast("Site supprimé.");
}

document.getElementById("site-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const payload = Object.fromEntries(fd.entries());
  try {
    const site = await api("POST", "/api/sites", payload);
    e.target.reset();
    e.target.querySelector('[name="country"]').value = "FR";
    state.currentSiteId = site.id;
    await loadSites();
    toast("Site enregistré.");
  } catch (err) { toast(err.message, true); }
});

document.getElementById("analyze-btn").addEventListener("click", async () => {
  const form = document.getElementById("site-form");
  const url = form.querySelector('[name="url"]').value.trim();
  const status = document.getElementById("analyze-status");
  if (!url) { status.textContent = "Renseignez d'abord l'URL."; return; }
  status.textContent = "Analyse en cours…";
  try {
    const res = await api("POST", "/api/analyze", { url });
    applyAnalysis(form, res);
    status.textContent = "Thématique détectée.";
  } catch (err) { status.textContent = err.message; }
});

function applyAnalysis(form, res) {
  if (res.keywords && res.keywords.length && !form.keywords.value.trim())
    form.keywords.value = res.keywords.join(", ");
  if (res.description && !form.description.value.trim())
    form.description.value = res.description;
  if (res.title && !form.name.value.trim())
    form.name.value = res.title;
}

// ---- Opportunities -------------------------------------------------------
function currentSite() {
  return state.sites.find((s) => s.id === state.currentSiteId) || null;
}

async function renderOpportunities() {
  const label = document.getElementById("opp-site-label");
  const el = document.getElementById("opp-list");
  const site = currentSite();
  if (!site) { label.textContent = ""; el.innerHTML = `<p class="empty">Choisissez d'abord un site dans « Mes sites ».</p>`; return; }
  label.textContent = `Site : ${site.name} — annuaires classés par pertinence.`;
  const data = await api("GET", `/api/sites/${site.id}/opportunities`);
  el.innerHTML = data.opportunities.map(oppItem).join("");
  bindOppActions(el);
}

function oppItem(o) {
  const apiBadge = o.api
    ? `<span class="badge api">API officielle</span>`
    : `<span class="badge manual">Soumission manuelle</span>`;
  const cost = o.cost === "payant" ? `<span class="badge paid">payant</span>`
    : `<span class="badge">${escapeHtml(o.cost)}</span>`;
  const follow = `<span class="badge">${escapeHtml(o.dofollow)}</span>`;
  return `
    <div class="item">
      <div>
        <h3>${escapeHtml(o.name)}</h3>
        <div class="meta">${escapeHtml(o.notes)}</div>
        <div class="badges">
          <span class="badge score">score ${o.score}</span>
          ${apiBadge} ${cost} ${follow}
          <span class="status ${o.status}">${STATUS_LABEL[o.status]}</span>
        </div>
      </div>
      <div class="actions">
        <button data-listing="${escapeHtml(o.slug)}">Préparer la fiche</button>
        <a href="${escapeHtml(o.submit_url)}" target="_blank" rel="noopener">
          <button class="secondary">Ouvrir le site ↗</button></a>
        <button class="ghost" data-cycle="${escapeHtml(o.slug)}" data-status="${o.status}">
          Marquer : ${STATUS_LABEL[STATUS_NEXT[o.status]]}</button>
      </div>
    </div>`;
}

function bindOppActions(scope) {
  scope.querySelectorAll("[data-listing]").forEach((b) =>
    b.addEventListener("click", () => showListing(b.dataset.listing)));
  scope.querySelectorAll("[data-cycle]").forEach((b) =>
    b.addEventListener("click", async () => {
      await setStatus(b.dataset.cycle, STATUS_NEXT[b.dataset.status]);
      renderOpportunities();
    }));
}

async function setStatus(slug, status) {
  await api("POST", "/api/submissions", {
    site_id: state.currentSiteId, directory_slug: slug, status,
  });
  toast(`Statut : ${STATUS_LABEL[status]}.`);
}

// ---- Listing modal -------------------------------------------------------
async function showListing(slug) {
  const data = await api("GET", `/api/sites/${state.currentSiteId}/listing?slug=${encodeURIComponent(slug)}`);
  const f = data.fields;
  const order = [
    ["title", "Titre"], ["url", "URL"], ["short_description", "Description courte"],
    ["long_description", "Description longue"], ["category", "Catégorie"],
    ["keywords", "Mots-clés"], ["contact_email", "Email"], ["phone", "Téléphone"],
    ["address", "Adresse"], ["city", "Ville"], ["country", "Pays"],
  ];
  const fields = order.filter(([k]) => f[k]).map(([k, label]) => `
    <div class="field-block">
      <div class="label">${label}</div>
      <div class="value">
        <span id="fv-${k}">${escapeHtml(f[k])}</span>
        <button class="ghost" data-copy="${k}">Copier</button>
      </div>
    </div>`).join("");
  const hints = data.hints.map((h) => `<li>${escapeHtml(h)}</li>`).join("");
  document.getElementById("modal-content").innerHTML = `
    <h2>${escapeHtml(data.directory.name)}</h2>
    <p class="hint">Champs prêts à coller dans le formulaire de l'annuaire.</p>
    ${fields}
    <ul class="hints">${hints}</ul>
    <div class="row" style="margin-top:1rem">
      <a href="${escapeHtml(data.directory.submit_url)}" target="_blank" rel="noopener">
        <button>Ouvrir le formulaire ↗</button></a>
      <button class="secondary" data-mark="${escapeHtml(data.directory.slug)}">
        J'ai soumis ✓</button>
    </div>`;
  document.querySelectorAll("[data-copy]").forEach((b) =>
    b.addEventListener("click", () => {
      const text = document.getElementById(`fv-${b.dataset.copy}`).textContent;
      navigator.clipboard.writeText(text).then(() => toast("Copié."),
        () => toast("Copie impossible (navigateur).", true));
    }));
  const mark = document.querySelector("[data-mark]");
  mark.addEventListener("click", async () => {
    await setStatus(mark.dataset.mark, "submitted");
    closeModal();
    if (document.getElementById("tab-opportunities").classList.contains("active")) renderOpportunities();
  });
  openModal();
}

function openModal() { document.getElementById("modal").classList.remove("hidden"); }
function closeModal() { document.getElementById("modal").classList.add("hidden"); }
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("modal").addEventListener("click", (e) => {
  if (e.target.id === "modal") closeModal();
});

// ---- Today ---------------------------------------------------------------
async function renderToday() {
  const el = document.getElementById("today-content");
  const site = currentSite();
  if (!site) { el.innerHTML = `<p class="empty">Choisissez d'abord un site.</p>`; return; }
  const data = await api("GET", `/api/sites/${site.id}/today`);
  if (!data.suggestion) {
    el.innerHTML = `<p class="empty">Bravo : plus aucune soumission en attente pour ${escapeHtml(site.name)}.</p>`;
    return;
  }
  const o = data.suggestion;
  el.innerHTML = `
    <h3>${escapeHtml(o.name)}</h3>
    <div class="meta">${escapeHtml(o.notes)}</div>
    <div class="badges">
      <span class="badge score">score ${o.score}</span>
      ${o.api ? '<span class="badge api">API officielle</span>' : '<span class="badge manual">Soumission manuelle</span>'}
    </div>
    <div class="row" style="margin-top:1rem">
      <button data-listing="${escapeHtml(o.slug)}">Préparer la fiche</button>
      <a href="${escapeHtml(o.submit_url)}" target="_blank" rel="noopener">
        <button class="secondary">Ouvrir le site ↗</button></a>
    </div>`;
  bindOppActions(el);
}

// ---- Tracker -------------------------------------------------------------
async function renderTracker() {
  const el = document.getElementById("tracker-list");
  const site = currentSite();
  if (!site) { el.innerHTML = `<p class="empty">Choisissez d'abord un site.</p>`; return; }
  const data = await api("GET", `/api/sites/${site.id}/submissions`);
  if (!data.submissions.length) {
    el.innerHTML = `<p class="empty">Aucune soumission suivie pour ${escapeHtml(site.name)}.</p>`;
    return;
  }
  el.innerHTML = data.submissions.map((s) => {
    const dir = window.__catalog[s.directory_slug];
    return `
      <div class="item">
        <div>
          <h3>${escapeHtml(dir ? dir.name : s.directory_slug)}</h3>
          <div class="meta">${s.submitted_at ? "Soumis le " + escapeHtml(s.submitted_at) : "Pas encore soumis"}</div>
        </div>
        <div class="actions">
          <span class="status ${s.status}">${STATUS_LABEL[s.status]}</span>
          <button class="ghost" data-cycle="${escapeHtml(s.directory_slug)}" data-status="${s.status}">
            Marquer : ${STATUS_LABEL[STATUS_NEXT[s.status]]}</button>
        </div>
      </div>`;
  }).join("");
  el.querySelectorAll("[data-cycle]").forEach((b) =>
    b.addEventListener("click", async () => {
      await setStatus(b.dataset.cycle, STATUS_NEXT[b.dataset.status]);
      renderTracker();
    }));
}

// ---- Boot ----------------------------------------------------------------
async function boot() {
  try {
    const cat = await api("GET", "/api/catalog");
    window.__catalog = Object.fromEntries(cat.directories.map((d) => [d.slug, d]));
    await loadSites();
  } catch (err) { toast(err.message, true); }
}
boot();
