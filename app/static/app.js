// TrueFit page logic. Plain JavaScript, no build step.

// ---- Shared helpers -------------------------------------------------------

const PROFILE_KEY = "truefit.v1"; // the only localStorage key; postings are never stored

function loadProfile() {
  try {
    const saved = JSON.parse(localStorage.getItem(PROFILE_KEY));
    if (saved && typeof saved === "object") {
      return {
        masterResume: typeof saved.masterResume === "string" ? saved.masterResume : "",
        backgroundNotes: typeof saved.backgroundNotes === "string" ? saved.backgroundNotes : "",
        availabilityText: typeof saved.availabilityText === "string" ? saved.availabilityText : "",
        savedAt: saved.savedAt || null,
      };
    }
  } catch (_) {
    // Corrupt value: treat as nothing saved.
  }
  return { masterResume: "", backgroundNotes: "", availabilityText: "", savedAt: null };
}

function saveProfile({ masterResume, backgroundNotes, availabilityText }) {
  const current = loadProfile();
  const profile = {
    masterResume: masterResume ?? current.masterResume,
    backgroundNotes: backgroundNotes ?? current.backgroundNotes,
    availabilityText: availabilityText ?? current.availabilityText,
    savedAt: new Date().toISOString(),
  };
  localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
  return profile;
}

function clearProfile() {
  localStorage.removeItem(PROFILE_KEY);
}

const errorBox = document.getElementById("error");

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

// Send a funnel event to PostHog if it loaded. Never pass posting or resume text.
function track(event, properties) {
  window.posthog?.capture(event, properties);
}

// POST JSON to the API. Returns the parsed body, or throws an Error whose
// message is the plain-language text from the server (and shows it).
async function api(path, body) {
  clearError();
  let response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (_) {
    const err = new Error("Couldn't reach TrueFit. Check that the app is running and try again.");
    showError(err.message);
    throw err;
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const err = new Error(data?.error?.message || "Something went wrong. Please try again.");
    err.code = data?.error?.code;
    showError(err.message);
    throw err;
  }
  return data;
}

// ---- Step 1: start-date check (User Story 1) ------------------------------

const availabilityInput = document.getElementById("availability");
const postingInput = document.getElementById("posting");
const checkButton = document.getElementById("check-start-date");
const startDateResult = document.getElementById("start-date-result");

let lastStartDate = null; // the tailoring step waits for this (FR-008)

const SAMPLE_POSTING = `Associate, Corporate Strategy — Summer 2027 Start
Acme Consumer Brands · New York, NY

About the role
Join our Corporate Strategy team to size new markets, build business cases, and present recommendations to the executive team.

Qualifications
- MBA expected by May 2027
- Strong financial modeling and Excel skills
- SQL a plus

Start date: July 13, 2027
Applications close December 1, 2026.`;

// Icon and one plain sentence per verdict. Server notes still show underneath.
const VERDICT_DISPLAY = {
  in_window: { icon: "✓", text: "This role starts on or after the month you're available, so the timing works." },
  likely_in_window_vague: { icon: "~", text: "The posting only gives a rough time, but it looks like it fits. Confirm the exact date with the recruiter." },
  partly_in_window: { icon: "~", text: "Some start dates in this posting fit and some don't. See each one below." },
  flexible_to_discuss: { icon: "~", text: "The start date is open, so you can likely agree on one that works for you." },
  outside_window: { icon: "✕", text: "The start date doesn't fit when you can start." },
  not_stated: { icon: "?", text: "No start date is listed. That often means as soon as possible; ask the recruiter before you apply." },
};

function setChecking(checking) {
  checkButton.disabled = checking;
  checkButton.replaceChildren();
  if (checking) checkButton.append(el("span", { class: "spinner", "aria-hidden": "true" }), "Checking…");
  else checkButton.append("Check start date");
}

async function checkStartDate() {
  setChecking(true);
  try {
    const result = await api("/api/start-date", {
      posting: postingInput.value,
      availability_text: availabilityInput.value,
    });
    lastStartDate = result;
    saveProfile({ availabilityText: availabilityInput.value.trim() });
    renderStartDate(result);
    tailorButton.disabled = false; // tailoring waits for a start-date result (FR-008)
    tailorHint.hidden = true;
    track("start_date_checked", { verdict: result.verdict, undergrad_warning: Boolean(result.undergrad_warning) });
  } catch (err) {
    // The error is already shown; the saved availability stays as it was.
    track("start_date_check_failed", { error_code: err.code || "network_error" });
  } finally {
    setChecking(false);
  }
}

function renderStartDate(result) {
  startDateResult.replaceChildren();
  startDateResult.className = `result ${result.verdict}`;
  if (result.undergrad_warning) {
    startDateResult.append(
      el("div", { class: "undergrad-warning", role: "note" },
        el("strong", {}, "This role looks aimed at undergraduates."),
        " TrueFit is built for MBA and graduate roles, so check the posting before applying.",
        el("blockquote", {}, `“${result.undergrad_warning.quote}”`)),
    );
  }
  const display = VERDICT_DISPLAY[result.verdict] || { icon: "?", text: null };
  startDateResult.append(
    el("div", { class: "verdict-head" },
      el("span", { class: "verdict-icon", "aria-hidden": "true" }, display.icon),
      el("span", { class: "verdict" }, result.verdict_label)),
  );
  if (display.text) startDateResult.append(el("p", { class: "explanation" }, display.text));

  if (result.note) startDateResult.append(el("p", { class: "note" }, result.note));

  const several = result.mentions.length > 1;
  for (const mention of result.mentions) {
    const item = el("div", { class: "mention" });
    if (several || mention.role_hint) {
      const heading = [mention.role_hint, several ? mention.verdict_label : null].filter(Boolean).join(": ");
      item.append(el("div", { class: "mention-verdict" }, heading));
    }
    item.append(el("blockquote", {}, `“${mention.quote}”`));
    if (several && mention.note) item.append(el("p", { class: "hint" }, mention.note));
    startDateResult.append(item);
  }

  startDateResult.append(el("p", { class: "checked-against" }, `Checked against your availability: ${result.availability.label}`));
  startDateResult.hidden = false;
}

checkButton.addEventListener("click", checkStartDate);
document.getElementById("sample-posting").addEventListener("click", () => {
  postingInput.value = SAMPLE_POSTING;
  track("sample_posting_used");
  postingInput.focus();
});
availabilityInput.value = loadProfile().availabilityText;

// ---- Step 2: master resume + background notes (User Story 2) --------------

const masterResumeInput = document.getElementById("master-resume");
const notesInput = document.getElementById("background-notes");
const savedAtLabel = document.getElementById("saved-at");
const tailorButton = document.getElementById("tailor");
const tailorHint = document.getElementById("tailor-hint");

function showSavedAt(savedAt) {
  savedAtLabel.textContent = savedAt ? `Saved on this device on ${new Date(savedAt).toLocaleDateString()}` : "";
}

function fillSavedProfile() {
  const profile = loadProfile();
  masterResumeInput.value = profile.masterResume;
  notesInput.value = profile.backgroundNotes;
  showSavedAt(profile.masterResume || profile.backgroundNotes ? profile.savedAt : null);
}

document.getElementById("save-profile").addEventListener("click", () => {
  const profile = saveProfile({ masterResume: masterResumeInput.value, backgroundNotes: notesInput.value });
  showSavedAt(profile.savedAt);
});

document.getElementById("clear-profile").addEventListener("click", () => {
  clearProfile(); // FR-021: removes the resume, notes, and availability from this device
  masterResumeInput.value = "";
  notesInput.value = "";
  availabilityInput.value = "";
  showSavedAt(null);
  track("resume_cleared");
});

fillSavedProfile();

// ---- Step 3: tailored resume ------------------------------------------------

const resultsSection = document.getElementById("step-results");
const tailoredBox = document.getElementById("tailored-resume");
const summaryBox = document.getElementById("tailor-summary");
const plainTextBox = document.getElementById("plain-text");
const copyStatus = document.getElementById("copy-status");

let tailorState = null; // { request, linesById, sections }

function setTailoring(busy) {
  tailorButton.disabled = busy;
  tailorButton.replaceChildren();
  if (busy) tailorButton.append(el("span", { class: "spinner", "aria-hidden": "true" }), "Tailoring…");
  else tailorButton.append("Tailor resume");
}

async function tailorResume() {
  const request = {
    posting: postingInput.value,
    master_resume: masterResumeInput.value,
    background_notes: notesInput.value,
  };
  setTailoring(true);
  try {
    const result = await api("/api/tailor", request);
    tailorState = {
      request,
      linesById: new Map(result.resume_lines.map((line) => [line.id, line])),
      sections: result.resume.sections,
    };
    renderTailored();
    resultsSection.hidden = false;
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    const bullets = allBullets();
    track("resume_tailored", { bullets: bullets.length, flagged: bullets.filter((b) => b.status === "flagged").length });
  } catch (_) {
    // The error is already shown.
  } finally {
    setTailoring(false);
  }
}

tailorButton.addEventListener("click", tailorResume);

function allBullets() {
  return tailorState.sections.flatMap((s) => s.entries.flatMap((e) => e.bullets));
}

function renderTailored() {
  tailoredBox.replaceChildren();
  for (const section of tailorState.sections) {
    tailoredBox.append(el("h3", { class: "resume-section" }, section.heading));
    for (const entry of section.entries) {
      const block = el("div", { class: "entry" });
      for (const id of entry.header_line_ids) {
        const line = tailorState.linesById.get(id);
        if (line) block.append(el("div", { class: "entry-header" }, line.text));
      }
      if (entry.bullets.length) {
        const list = el("ul", { class: "bullets" });
        for (const bullet of entry.bullets) list.append(renderBullet(bullet));
        block.append(list);
      }
      tailoredBox.append(block);
    }
  }
  const bullets = allBullets();
  const kept = bullets.filter((b) => b.included).length;
  const flagged = bullets.filter((b) => b.status === "flagged").length;
  summaryBox.textContent = `${kept} of ${bullets.length} bullets kept · ${flagged} unverified`;
  plainTextBox.value = renderPlainText(tailorState.sections, tailorState.linesById);
}

function renderBullet(bullet) {
  const traced = bullet.status === "traced";
  const item = el("li", { class: `bullet ${bullet.status}${bullet.included ? "" : " excluded"}` });
  item.append(
    el("div", { class: "bullet-row" },
      el("span", { class: `badge ${bullet.status}` }, traced ? "✓ Traced" : "Unverified"),
      el("span", { class: "bullet-text" }, bullet.text)),
  );
  if (!traced && bullet.flag_reason) item.append(el("p", { class: "flag-reason" }, bullet.flag_reason));

  const sources = el("div", { class: "sources" });
  for (const id of bullet.source_line_ids) {
    const line = tailorState.linesById.get(id);
    if (line) sources.append(el("div", {}, `${line.source === "notes" ? "From your notes" : "From your resume"}: “${line.text}”`));
  }
  item.append(sources);

  const controls = el("div", { class: "bullet-controls" });
  const toggle = el("button", { class: "link-button", type: "button" }, bullet.included ? "Remove" : "Put back");
  toggle.addEventListener("click", () => {
    bullet.included = !bullet.included; // a flagged bullet put back stays marked Unverified (FR-012c)
    renderTailored();
  });
  const edit = el("button", { class: "link-button", type: "button" }, "Edit");
  edit.addEventListener("click", () => startEdit(item, bullet));
  controls.append(toggle, edit);
  item.append(controls);
  return item;
}

function startEdit(item, bullet) {
  const box = el("textarea", { class: "bullet-edit", rows: "3", "aria-label": "Edit bullet" });
  box.value = bullet.text;
  const save = el("button", { class: "link-button", type: "button" }, "Save and re-check");
  const cancel = el("button", { class: "link-button", type: "button" }, "Cancel");
  item.querySelector(".bullet-text").replaceWith(box);
  item.querySelector(".bullet-controls").replaceChildren(save, cancel);
  box.focus();
  cancel.addEventListener("click", renderTailored);
  save.addEventListener("click", async () => {
    const text = box.value.trim();
    if (!text) return;
    save.disabled = true;
    save.textContent = "Checking…";
    try {
      const check = await api("/api/verify-bullet", {
        bullet_text: text,
        source_line_ids: bullet.source_line_ids,
        posting: tailorState.request.posting,
        master_resume: tailorState.request.master_resume,
        background_notes: tailorState.request.background_notes,
      });
      Object.assign(bullet, { text, edited: true, status: check.status, flag_reason: check.flag_reason,
                              source_line_ids: check.source_line_ids }); // included is unchanged (FR-012b)
      track("bullet_edited", { status: check.status });
      renderTailored();
    } catch (_) {
      save.disabled = false;
      save.textContent = "Save and re-check";
    }
  });
}

document.getElementById("copy-resume").addEventListener("click", async () => {
  const text = plainTextBox.value;
  try {
    await navigator.clipboard.writeText(text);
  } catch (_) {
    plainTextBox.select(); // older browsers: copy the selected text instead
    document.execCommand("copy");
  }
  copyStatus.textContent = "Copied. Paste it into the application's resume field.";
  track("resume_copied", { bullets: allBullets().filter((b) => b.included).length });
});

// Mirrors app/plain_text.py so edits update the copy-ready text without another server call.
const DATE_RANGE = /(\d{4})\s*[–—-]\s*((?:[A-Z][a-z]{2,8}\.?\s+)?\d{4}|Present|present|Current|current)/g;

function normalizeChars(text) {
  return text
    .replace(/[‘’]/g, "'").replace(/[“”]/g, '"').replace(/…/g, "...").replace(/ /g, " ")
    .trim()
    .replace(/^[-*•●▪◦·]\s*/, "")
    .replace(/\s*[•●▪◦·]\s*/g, " | ")
    .replace(DATE_RANGE, "$1 \u0000 $2")
    .replace(/[–—]/g, "-")
    .normalize("NFKD").replace(/[^\x20-\x7E\u0000]/g, "")
    .replace(/\u0000/g, "–")
    .replace(/ {2,}/g, " ")
    .trim();
}

function titleCase(text) {
  return text.toLowerCase().replace(/(^|[^a-z'])([a-z])/g, (_, before, letter) => before + letter.toUpperCase());
}

function renderPlainText(sections, linesById) {
  const blocks = [];
  for (const section of sections) {
    const rows = [];
    for (const entry of section.entries) {
      for (const id of entry.header_line_ids) if (linesById.has(id)) rows.push(normalizeChars(linesById.get(id).text));
      for (const bullet of entry.bullets) if (bullet.included) rows.push(`- ${normalizeChars(bullet.text)}`);
    }
    if (rows.length) blocks.push([titleCase(normalizeChars(section.heading)), ...rows].join("\n"));
  }
  return blocks.length ? blocks.join("\n\n") + "\n" : "";
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of children) {
    if (child !== null && child !== undefined) node.append(child);
  }
  return node;
}
