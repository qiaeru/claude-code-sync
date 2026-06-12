"use strict";

// -- API helpers ------------------------------------------------------------

async function api(path, body) {
  const opts = { method: body ? "POST" : "GET" };
  if (body) {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Request failed (${res.status})`);
  }
  return data;
}

async function uploadArchive(file) {
  const res = await fetch("/api/upload", {
    method: "POST",
    headers: { "X-Filename": encodeURIComponent(file.name) },
    body: await file.arrayBuffer(),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Upload failed");
  return data;
}

const $ = (id) => document.getElementById(id);

// -- Status toast -----------------------------------------------------------

let statusTimer = null;
const STATUS_TIMEOUT = { ok: 4000, info: 4000 };

function setStatus(message, kind = "info") {
  const el = $("status");
  if (statusTimer) {
    clearTimeout(statusTimer);
    statusTimer = null;
  }
  el.innerHTML = `<span class="status-text"></span>`;
  el.querySelector(".status-text").textContent = message;
  el.title = message;
  el.className = `status ${kind}`;
  el.classList.remove("hidden", "fade-out");

  const timeout = STATUS_TIMEOUT[kind];
  if (timeout) statusTimer = setTimeout(hideStatus, timeout);
}

function hideStatus() {
  const el = $("status");
  el.classList.add("fade-out");
  statusTimer = setTimeout(() => el.classList.add("hidden"), 300);
}

// -- Small utilities --------------------------------------------------------

function humanSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let n = bytes / 1024;
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(1)} ${units[i]}`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

async function withLoading(btn, fn) {
  btn.classList.add("loading");
  setActionsDisabled(true);
  try {
    return await fn();
  } finally {
    btn.classList.remove("loading");
    setActionsDisabled(false);
  }
}

function setActionsDisabled(disabled) {
  document
    .querySelectorAll(".actions .btn, .btn-browse")
    .forEach((b) => (b.disabled = disabled));
}

// -- Icons (Heroicons, outline, MIT) ---------------------------------------

const ICONS = {
  eye:
    '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /></svg>',
  eyeSlash:
    '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" /></svg>',
  copy:
    '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184" /></svg>',
};

// -- Theme (Auto / Light / Dark) -------------------------------------------

const THEME_ORDER = ["system", "light", "dark"];
const THEME_ICONS = {
  system:
    '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M4.098 19.902a3.75 3.75 0 0 0 5.304 0l6.401-6.402M6.75 21A3.75 3.75 0 0 1 3 17.25V4.125C3 3.504 3.504 3 4.125 3h5.25c.621 0 1.125.504 1.125 1.125v4.072M6.75 21a3.75 3.75 0 0 0 3.75-3.75V8.197M6.75 21h13.125c.621 0 1.125-.504 1.125-1.125v-5.25c0-.621-.504-1.125-1.125-1.125h-4.072M10.5 8.197l2.88-2.88c.438-.439 1.15-.439 1.59 0l3.712 3.713c.44.44.44 1.152 0 1.59l-2.879 2.88M6.75 17.25h.008v.008H6.75v-.008Z" /></svg>',
  light:
    '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" /></svg>',
  dark:
    '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M21.752 15.002A9.718 9.718 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" /></svg>',
};
const THEME_LABELS = { system: "Auto", light: "Light", dark: "Dark" };

function currentTheme() {
  let stored = null;
  try {
    stored = localStorage.getItem("theme");
  } catch {}
  return stored === "light" || stored === "dark" ? stored : "system";
}

function applyTheme(theme) {
  if (theme === "system") {
    document.documentElement.removeAttribute("data-theme");
    try {
      localStorage.removeItem("theme");
    } catch {}
  } else {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("theme", theme);
    } catch {}
  }
  const btn = $("theme-btn");
  btn.querySelector(".theme-icon").innerHTML = THEME_ICONS[theme];
  btn.querySelector(".theme-label").textContent = THEME_LABELS[theme];
  btn.title = `Theme: ${THEME_LABELS[theme]} (click to change)`;
}

$("theme-btn").addEventListener("click", () => {
  const next = THEME_ORDER[(THEME_ORDER.indexOf(currentTheme()) + 1) % THEME_ORDER.length];
  applyTheme(next);
});
applyTheme(currentTheme());

// -- Tabs (accessible) ------------------------------------------------------

const tabs = [...document.querySelectorAll(".tab")];

function activateTab(tab) {
  tabs.forEach((t) => {
    const on = t === tab;
    t.classList.toggle("active", on);
    t.setAttribute("aria-selected", on ? "true" : "false");
    t.tabIndex = on ? 0 : -1;
  });
  document.querySelectorAll(".panel").forEach((p) => {
    const on = p.id === `tab-${tab.dataset.tab}`;
    p.classList.toggle("active", on);
    p.hidden = !on;
  });
  if (tab.dataset.tab === "backups") loadBackups();
}

tabs.forEach((tab, i) => {
  tab.addEventListener("click", () => activateTab(tab));
  tab.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      const dir = e.key === "ArrowRight" ? 1 : -1;
      const next = tabs[(i + dir + tabs.length) % tabs.length];
      next.focus();
      activateTab(next);
    }
  });
});

// -- Reveal password toggles ------------------------------------------------

document.querySelectorAll(".reveal-btn").forEach((btn) => {
  btn.innerHTML = ICONS.eye;
  btn.addEventListener("click", () => {
    const input = $(btn.dataset.reveal);
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.innerHTML = show ? ICONS.eyeSlash : ICONS.eye;
    const lbl = show ? "Hide password" : "Show password";
    btn.setAttribute("aria-label", lbl);
    btn.title = lbl;
  });
});

// -- Password strength + match ---------------------------------------------

function pwScore(pw) {
  if (!pw) return 0;
  let s = 0;
  if (pw.length >= 8) s++;
  if (pw.length >= 12) s++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) s++;
  if (/\d/.test(pw)) s++;
  if (/[^A-Za-z0-9]/.test(pw)) s++;
  return Math.min(4, Math.max(1, s));
}
const PW_WORDS = { 1: "Weak", 2: "Fair", 3: "Good", 4: "Strong" };

function updateStrength() {
  const pw = $("export-password").value;
  const box = $("pw-strength");
  if (!pw) {
    box.classList.add("hidden");
    return;
  }
  const level = pwScore(pw);
  box.classList.remove("hidden");
  box.dataset.level = String(level);
  box.querySelector(".pw-label").textContent = PW_WORDS[level];
  updateMatch();
}

function updateMatch() {
  const a = $("export-password").value;
  const b = $("export-password2").value;
  const hint = $("pw-match");
  if (!b) {
    hint.textContent = "";
    hint.className = "field-hint";
    return;
  }
  if (a === b) {
    hint.textContent = "Passwords match.";
    hint.className = "field-hint ok";
  } else {
    hint.textContent = "Passwords do not match.";
    hint.className = "field-hint error";
  }
}

$("export-password").addEventListener("input", updateStrength);
$("export-password2").addEventListener("input", updateMatch);

// -- Browse (native dialog) -------------------------------------------------

document.querySelectorAll("[data-pick]").forEach((btn) => {
  btn.addEventListener("click", () =>
    withLoading(btn, async () => {
      try {
        const { path } = await api("/api/pick", { kind: btn.dataset.pick });
        if (path) {
          $(btn.dataset.target).value = path;
          invalidatePreviewFor(btn.dataset.target);
          saveSettings();
        }
      } catch (err) {
        setStatus(err.message, "error");
      }
    })
  );
});

// -- Drag & drop archive ----------------------------------------------------

// A drop that misses the dropzone would otherwise navigate the page to the
// file, wiping all UI state (typed passwords, previews).
["dragover", "drop"].forEach((ev) =>
  window.addEventListener(ev, (e) => e.preventDefault())
);

const dz = $("dropzone");
["dragenter", "dragover"].forEach((ev) =>
  dz.addEventListener(ev, (e) => {
    e.preventDefault();
    dz.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((ev) =>
  dz.addEventListener(ev, (e) => {
    e.preventDefault();
    if (ev !== "dragover") dz.classList.remove("dragover");
  })
);
dz.addEventListener("drop", async (e) => {
  const file = e.dataTransfer.files && e.dataTransfer.files[0];
  if (!file) return;
  setStatus(`Uploading ${file.name}…`, "busy");
  try {
    const data = await uploadArchive(file);
    $("import-archive").value = data.path;
    invalidatePreviewFor("import-archive");
    setStatus(`Loaded ${data.name} (${humanSize(data.size)}).`, "ok");
  } catch (err) {
    setStatus(err.message, "error");
  }
});

// -- Settings persistence ---------------------------------------------------

const STORE_KEYS = [
  "export-root",
  "export-scope",
  "export-outdir",
  "export-keep",
  "import-root",
  "import-scope",
];

function saveSettings() {
  try {
    const data = {};
    STORE_KEYS.forEach((id) => (data[id] = $(id).value));
    localStorage.setItem("settings", JSON.stringify(data));
  } catch {}
}

function restoreSettings() {
  let data = null;
  try {
    data = JSON.parse(localStorage.getItem("settings") || "null");
  } catch {}
  if (!data) return;
  STORE_KEYS.forEach((id) => {
    if (data[id] != null && data[id] !== "") $(id).value = data[id];
  });
}

STORE_KEYS.forEach((id) => $(id).addEventListener("change", saveSettings));

// -- Defaults ---------------------------------------------------------------

async function loadDefaults() {
  try {
    const d = await api("/api/defaults");
    $("export-root").value = d.root;
    $("export-outdir").value = d.default_out_dir;
    $("import-root").value = d.root;
  } catch (err) {
    setStatus(`Could not load defaults: ${err.message}`, "error");
  }
  restoreSettings(); // saved values override server defaults
}

// -- Preview rendering (shared) --------------------------------------------

function rowHtml(badge, badgeClass, pathText, metaText, opts = {}) {
  const check = opts.selectable
    ? `<input type="checkbox" class="row-check" data-arc="${escapeHtml(opts.arcname)}"${
        opts.checked ? " checked" : ""
      } aria-label="Select ${escapeHtml(pathText)}" />`
    : "";
  return `<div class="file-row" data-path="${escapeHtml(pathText.toLowerCase())}">
    ${check}<span class="badge ${badgeClass}">${escapeHtml(badge)}</span>
    <span class="path">${escapeHtml(pathText)}</span>
    <span class="meta">${escapeHtml(metaText)}</span>
  </div>`;
}

// Keep a "select all" checkbox in sync with the per-row checkboxes.
function wireSelectAll(box) {
  const all = box.querySelector(".select-all");
  const list = box.querySelector(".file-list");
  if (!all || !list) return;
  const rows = () => [...box.querySelectorAll(".row-check")];
  all.addEventListener("change", () => {
    rows().forEach((c) => {
      if (c.closest(".file-row").style.display !== "none") c.checked = all.checked;
    });
  });
  list.addEventListener("change", (e) => {
    if (!e.target.classList.contains("row-check")) return;
    const cs = rows();
    all.checked = cs.every((c) => c.checked);
    all.indeterminate = !all.checked && cs.some((c) => c.checked);
  });
}

// Checked arcnames, or null when the list has no checkboxes.
function gatherSelection(box) {
  const checks = box.querySelectorAll(".row-check");
  if (!checks.length) return null;
  return [...checks].filter((c) => c.checked).map((c) => c.dataset.arc);
}

function filterRows(listEl, term) {
  const t = term.trim().toLowerCase();
  listEl.querySelectorAll(".file-row").forEach((row) => {
    row.style.display = !t || row.dataset.path.includes(t) ? "" : "none";
  });
}

// -- Preview invalidation -----------------------------------------------------

// A preview (and the selection gathered from it) is only valid for the inputs
// it was computed from. Hide it as soon as any of those inputs changes, so a
// stale selection can never be submitted against a different root/scope/archive.
const PREVIEW_DEPS = {
  "export-preview": ["export-root", "export-scope"],
  "import-preview": ["import-archive", "import-root", "import-scope"],
};

function invalidatePreviewFor(inputId) {
  for (const [boxId, deps] of Object.entries(PREVIEW_DEPS)) {
    if (deps.includes(inputId)) $(boxId).classList.add("hidden");
  }
}

Object.entries(PREVIEW_DEPS).forEach(([, deps]) =>
  deps.forEach((id) =>
    ["input", "change"].forEach((ev) =>
      $(id).addEventListener(ev, () => invalidatePreviewFor(id))
    )
  )
);

// -- Export -----------------------------------------------------------------

function renderExportPreview(data) {
  const box = $("export-preview");
  if (!data.count) {
    box.innerHTML = `<h3>Preview</h3><p class="preview-empty">No Claude Code configuration found for this scope.</p>`;
    box.classList.remove("hidden");
    return;
  }
  const rows = data.entries
    .map((e) =>
      rowHtml(e.scope, e.scope, e.arcname, humanSize(e.size), {
        selectable: true,
        arcname: e.arcname,
        checked: true,
      })
    )
    .join("");
  box.innerHTML = `<h3>Preview</h3>
    <p class="summary">${data.count} file(s), ${humanSize(data.total_size)} total. Uncheck any you want to exclude.</p>
    <div class="preview-toolbar">
      <input class="preview-search" type="search" placeholder="Filter files…" />
      <label class="toggle-skip"><input type="checkbox" class="select-all" checked /> Select all</label>
    </div>
    <div class="file-list selectable">${rows}</div>`;
  box.classList.remove("hidden");
  const search = box.querySelector(".preview-search");
  search.addEventListener("input", () => filterRows(box.querySelector(".file-list"), search.value));
  wireSelectAll(box);
}

function renderExportResult(data) {
  const box = $("export-preview");
  const pruned =
    data.pruned > 0 ? ` Pruned ${data.pruned} older archive(s).` : "";
  box.innerHTML = `<h3>Archive created</h3>
    <p class="summary">${data.count} file(s), ${humanSize(data.total_size)}.${pruned}</p>
    <div class="archive-path"><span>${escapeHtml(data.archive)}</span>
      <button class="btn btn-secondary copy-btn">${ICONS.copy}<span class="btn-text">Copy path</span></button>
    </div>`;
  box.classList.remove("hidden");
  box.querySelector(".copy-btn").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(data.archive);
      setStatus("Archive path copied to clipboard.", "ok");
    } catch {
      setStatus("Could not copy — select the path manually.", "error");
    }
  });
}

$("preview-btn").addEventListener("click", () =>
  withLoading($("preview-btn"), async () => {
    setStatus("Scanning…", "busy");
    try {
      const data = await api("/api/scan", {
        root: $("export-root").value.trim(),
        scope: $("export-scope").value,
      });
      renderExportPreview(data);
      setStatus(`Found ${data.count} file(s).`, "ok");
    } catch (err) {
      setStatus(err.message, "error");
    }
  })
);

$("export-btn").addEventListener("click", () =>
  withLoading($("export-btn"), async () => {
    const pw = $("export-password").value;
    const pw2 = $("export-password2").value;
    if (!pw) {
      setStatus("Please enter a password for the archive.", "error");
      $("export-password").focus();
      return;
    }
    if (pw !== pw2) {
      setStatus("Passwords do not match.", "error");
      $("export-password2").focus();
      return;
    }
    const previewBox = $("export-preview");
    const selection =
      previewBox && !previewBox.classList.contains("hidden")
        ? gatherSelection(previewBox)
        : null;
    if (selection && selection.length === 0) {
      setStatus("No files selected to export.", "error");
      return;
    }
    setStatus("Creating encrypted archive…", "busy");
    try {
      const data = await api("/api/export", {
        root: $("export-root").value.trim(),
        scope: $("export-scope").value,
        out_dir: $("export-outdir").value.trim(),
        password: pw,
        selection,
        keep: $("export-keep").value.trim() || null,
      });
      renderExportResult(data);
      setStatus(`Archive created (${data.count} files, ${humanSize(data.total_size)}).`, "ok");
    } catch (err) {
      setStatus(err.message, "error");
    }
  })
);

// -- Import -----------------------------------------------------------------

function renderImportPreview(data, selectable) {
  const box = $("import-preview");
  const rows = data.items
    .map((i) =>
      rowHtml(i.action, i.action, i.destination, i.scope, {
        // Only actionable (non-skipped) entries are selectable.
        selectable: selectable && i.action !== "skip",
        arcname: i.arcname,
        checked: true,
      })
    )
    .join("");
  const title = data.dry_run ? "Dry run — nothing was written" : "Restore complete";
  const backup = data.backup_dir
    ? `Backup of overwritten files: <code>${escapeHtml(data.backup_dir)}</code>`
    : "No existing files were overwritten.";
  const selectAll = selectable
    ? `<label class="toggle-skip"><input type="checkbox" class="select-all" checked /> Select all</label>`
    : "";
  box.innerHTML = `<h3>${title}</h3>
    <p class="summary">
      ${data.created} to create, ${data.overwritten} to overwrite, ${data.skipped} skipped.<br>${backup}
    </p>
    <div class="preview-toolbar">
      <input class="preview-search" type="search" placeholder="Filter files…" />
      <label class="toggle-skip"><input type="checkbox" class="skip-toggle" checked /> Show skipped</label>
      ${selectAll}
    </div>
    <div class="file-list${selectable ? " selectable" : ""}">${rows}</div>`;
  box.classList.remove("hidden");

  const list = box.querySelector(".file-list");
  const search = box.querySelector(".preview-search");
  const skipToggle = box.querySelector(".skip-toggle");
  const applyFilters = () => {
    const t = search.value.trim().toLowerCase();
    const showSkip = skipToggle.checked;
    list.querySelectorAll(".file-row").forEach((row) => {
      const isSkip = row.querySelector(".badge").classList.contains("skip");
      const matchText = !t || row.dataset.path.includes(t);
      row.style.display = matchText && (showSkip || !isSkip) ? "" : "none";
    });
  };
  search.addEventListener("input", applyFilters);
  skipToggle.addEventListener("change", applyFilters);
  if (selectable) wireSelectAll(box);
}

// Count checked create/overwrite rows in the import preview.
function countSelected(box) {
  let created = 0;
  let overwritten = 0;
  box.querySelectorAll(".row-check:checked").forEach((c) => {
    const badge = c.closest(".file-row").querySelector(".badge");
    if (badge.classList.contains("create")) created++;
    else if (badge.classList.contains("overwrite")) overwritten++;
  });
  return { created, overwritten };
}

function importBody(dryRun, selection) {
  return {
    archive: $("import-archive").value.trim(),
    root: $("import-root").value.trim(),
    scope: $("import-scope").value,
    password: $("import-password").value,
    dry_run: dryRun,
    selection: selection ?? null,
  };
}

function validateImport() {
  if (!$("import-archive").value.trim()) {
    setStatus("Please choose an archive to import.", "error");
    return false;
  }
  if (!$("import-password").value) {
    setStatus("Please enter the archive password.", "error");
    $("import-password").focus();
    return false;
  }
  return true;
}

$("dryrun-btn").addEventListener("click", () =>
  withLoading($("dryrun-btn"), async () => {
    if (!validateImport()) return;
    setStatus("Previewing…", "busy");
    try {
      const data = await api("/api/import", importBody(true));
      renderImportPreview(data, true);
      setStatus(`Dry run: ${data.created} new, ${data.overwritten} to overwrite.`, "ok");
    } catch (err) {
      setStatus(err.message, "error");
    }
  })
);

$("import-btn").addEventListener("click", () =>
  withLoading($("import-btn"), async () => {
    if (!validateImport()) return;

    // Use the current dry-run preview's selection if one is shown; otherwise
    // run a dry-run now to compute the plan and let the user review it.
    const box = $("import-preview");
    let selection = null;
    let counts;
    if (!box.classList.contains("hidden") && box.querySelector(".row-check")) {
      selection = gatherSelection(box);
      if (!selection.length) {
        setStatus("No files selected to restore.", "error");
        return;
      }
      counts = countSelected(box);
    } else {
      setStatus("Analyzing archive…", "busy");
      try {
        const plan = await api("/api/import", importBody(true));
        renderImportPreview(plan, true);
        counts = { created: plan.created, overwritten: plan.overwritten };
      } catch (err) {
        setStatus(err.message, "error");
        return;
      }
    }

    if (counts.created + counts.overwritten === 0) {
      setStatus("Nothing to restore (no files selected for this scope).", "error");
      return;
    }
    const ok = await confirmModal({
      title: "Restore archive?",
      body: `This will write <strong>${counts.created}</strong> new file(s) and
        <strong>overwrite ${counts.overwritten}</strong> existing file(s).
        Overwritten files are backed up first to
        <code>~/.claude-code-sync-backups/</code>.`,
      confirmLabel: "Restore",
    });
    if (!ok) {
      setStatus("Restore cancelled.", "info");
      return;
    }
    setStatus("Restoring…", "busy");
    try {
      const data = await api("/api/import", importBody(false, selection));
      renderImportPreview(data, false);
      setStatus(`Restored: ${data.created} created, ${data.overwritten} overwritten.`, "ok");
    } catch (err) {
      setStatus(err.message, "error");
    }
  })
);

// -- Keyboard submit (Enter = primary action) -------------------------------

// Inputs inside a preview (filter box, row checkboxes) must not trigger the
// primary action: Enter while filtering would create or restore an archive.
function isSubmitInput(e) {
  return e.key === "Enter" && e.target.tagName === "INPUT" && !e.target.closest(".preview");
}

$("tab-export").addEventListener("keydown", (e) => {
  if (isSubmitInput(e)) {
    e.preventDefault();
    $("export-btn").click();
  }
});
$("tab-import").addEventListener("keydown", (e) => {
  if (isSubmitInput(e)) {
    e.preventDefault();
    $("import-btn").click();
  }
});
$("tab-backups").addEventListener("keydown", (e) => {
  if (isSubmitInput(e)) {
    e.preventDefault();
    $("prune-btn").click();
  }
});

// -- Confirmation modal -----------------------------------------------------

function confirmModal({ title, body, confirmLabel }) {
  return new Promise((resolve) => {
    const overlay = $("modal-overlay");
    $("modal-title").textContent = title;
    $("modal-body").innerHTML = body;
    $("modal-confirm").textContent = confirmLabel || "Confirm";
    overlay.classList.remove("hidden");

    const cleanup = (val) => {
      overlay.classList.add("hidden");
      $("modal-confirm").onclick = null;
      $("modal-cancel").onclick = null;
      overlay.onclick = null;
      document.removeEventListener("keydown", onKey);
      resolve(val);
    };
    const onKey = (e) => {
      if (e.key === "Escape") cleanup(false);
      if (e.key === "Enter") cleanup(true);
    };
    $("modal-confirm").onclick = () => cleanup(true);
    $("modal-cancel").onclick = () => cleanup(false);
    overlay.onclick = (e) => {
      if (e.target === overlay) cleanup(false);
    };
    document.addEventListener("keydown", onKey);
    $("modal-confirm").focus();
  });
}

// -- Backups ----------------------------------------------------------------

async function loadBackups() {
  setStatus("Loading backups…", "busy");
  try {
    const data = await api("/api/backups");
    renderBackups(data);
    setStatus(
      data.count ? `${data.count} backup(s), ${humanSize(data.total_size)}.` : "No backups found.",
      "ok"
    );
  } catch (err) {
    setStatus(err.message, "error");
  }
}

function renderBackups(data) {
  const box = $("backups-list");
  if (!data.count) {
    box.innerHTML = `<h3>Backups</h3>
      <p class="preview-empty">No backups in <code>${escapeHtml(data.root)}</code>.</p>`;
    box.classList.remove("hidden");
    return;
  }
  const rows = data.backups
    .map((b) => rowHtml("backup", "skip", b.name, `${b.files} file(s), ${humanSize(b.size)}`))
    .join("");
  box.innerHTML = `<h3>Backups</h3>
    <p class="summary">${data.count} backup(s), ${humanSize(data.total_size)} total in <code>${escapeHtml(data.root)}</code>.</p>
    <div class="file-list">${rows}</div>`;
  box.classList.remove("hidden");
}

function readKeep(inputId) {
  const raw = $(inputId).value.trim();
  if (raw === "") return null;
  const n = Number(raw);
  return Number.isInteger(n) && n >= 0 ? n : NaN;
}

$("refresh-backups-btn").addEventListener("click", () => loadBackups());

$("prune-btn").addEventListener("click", () =>
  withLoading($("prune-btn"), async () => {
    const keep = readKeep("backups-keep");
    if (keep === null || Number.isNaN(keep)) {
      setStatus("Enter a whole number (0 or more) to keep.", "error");
      return;
    }
    let plan;
    try {
      plan = await api("/api/backups/prune", { keep, dry_run: true });
    } catch (err) {
      setStatus(err.message, "error");
      return;
    }
    if (!plan.removed) {
      setStatus("Nothing to prune — fewer backups than the keep count.", "info");
      return;
    }
    const ok = await confirmModal({
      title: "Prune backups?",
      body: `This permanently deletes <strong>${plan.removed}</strong> older backup(s),
        freeing ${humanSize(plan.freed)}. The newest <strong>${keep}</strong> are kept.`,
      confirmLabel: "Delete",
    });
    if (!ok) {
      setStatus("Prune cancelled.", "info");
      return;
    }
    try {
      const data = await api("/api/backups/prune", { keep });
      setStatus(`Removed ${data.removed} backup(s), freed ${humanSize(data.freed)}.`, "ok");
      loadBackups();
    } catch (err) {
      setStatus(err.message, "error");
    }
  })
);

// -- Quit -------------------------------------------------------------------

$("quit-btn").addEventListener("click", async () => {
  try {
    await api("/api/quit", {});
  } catch {}
  $("goodbye").classList.remove("hidden");
  // Best-effort: only works for script-opened windows, hence the fallback screen.
  setTimeout(() => {
    try {
      window.close();
    } catch {}
  }, 400);
});

loadDefaults();
