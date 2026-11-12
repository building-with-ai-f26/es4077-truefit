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

// Status tone and one plain sentence per verdict; the sentence is the exhibit's action title.
const VERDICT_DISPLAY = {
  in_window: { tone: "good", text: "This role starts on or after the month you're available, so the timing works." },
  likely_in_window_vague: { tone: "warn", text: "The posting only gives a rough time, but it looks like it fits. Confirm the exact date with the recruiter." },
  partly_in_window: { tone: "warn", text: "Some start dates in this posting fit and some don't. See each one below." },
  flexible_to_discuss: { tone: "warn", text: "The start date is open, so you can likely agree on one that works for you." },
  outside_window: { tone: "bad", text: "The start date doesn't fit when you can start." },
  likely_too_early: { tone: "warn", text: "No start date is listed, which usually means as soon as possible, before you're available." },
  not_stated: { tone: "none", text: "No start date is listed. That often means as soon as possible; ask the recruiter before you apply." },
};

// Action titles when the posting gives no start date and TrueFit assumes as soon as possible.
const NO_DATE_TITLE = {
  likely_too_early: "This role likely starts before you're available.",
  likely_in_window_vague: "This role likely starts as soon as possible, which fits.",
};

// Status glyphs drawn as SVG, always shown next to a word (never color alone).
const MARK_PATHS = {
  good: '<circle cx="12" cy="12" r="11" fill="#1e7a46"/><path d="M6.5 12.5l3.5 3.5 7.5-8" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>',
  warn: '<circle cx="12" cy="12" r="10" fill="none" stroke="#b7791f" stroke-width="2.4"/><path d="M9.3 9.4a2.8 2.8 0 1 1 3.6 2.7c-.6.2-.9.7-.9 1.3v.6" fill="none" stroke="#b7791f" stroke-width="2.2" stroke-linecap="round"/><circle cx="12" cy="17.2" r="1.3" fill="#b7791f"/>',
  bad: '<circle cx="12" cy="12" r="11" fill="#b42318"/><path d="M8 8l8 8M16 8l-8 8" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/>',
  none: '<circle cx="12" cy="12" r="10" fill="none" stroke="#6b7484" stroke-width="2"/><path d="M8 12h8" stroke="#6b7484" stroke-width="2.4" stroke-linecap="round"/>',
};

function statusCell(tag, tone, label) {
  const cell = el(tag, { class: `status ${tone}` });
  cell.insertAdjacentHTML("afterbegin", `<svg class="mark" viewBox="0 0 24 24" aria-hidden="true">${MARK_PATHS[tone]}</svg>`);
  cell.append(label);
  return cell;
}

function quoted(text, source) {
  const p = el("p", { class: "quote" }, el("mark", {}, `“${text}”`));
  if (source) p.append(el("span", { class: "source" }, source));
  return p;
}

// Underline the tab for the step the student is on.
function setStep(id) {
  for (const tab of document.querySelectorAll(".steps a")) {
    if (tab.getAttribute("href") === `#${id}`) tab.setAttribute("aria-current", "step");
    else tab.removeAttribute("aria-current");
  }
}

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
    setStep("step-resume");
    track("start_date_checked", { verdict: result.verdict, undergrad_warning: Boolean(result.undergrad_warning) });
  } catch (err) {
    // The error is already shown; the saved availability stays as it was.
    track("start_date_check_failed", { error_code: err.code || "network_error" });
  } finally {
    setChecking(false);
  }
}

function renderStartDate(result) {
  const display = VERDICT_DISPLAY[result.verdict] || { tone: "none", text: result.verdict_label };
  // With no quoted date TrueFit assumes ASAP; the server's note explains that in the row.
  const noDate = !result.mentions.length;
  const title = (noDate && NO_DATE_TITLE[result.verdict]) || display.text;
  const rows = el("tbody");

  // One row per quoted start date; several rows when roles or offices start at different times.
  const several = result.mentions.length > 1;
  result.mentions.forEach((mention, i) => {
    const tone = several ? (VERDICT_DISPLAY[mention.verdict]?.tone || "none") : display.tone;
    const label = several ? (mention.verdict_label || result.verdict_label) : result.verdict_label;
    const name = mention.role_hint || (several ? `Start date ${i + 1}` : "Start date");
    rows.append(el("tr", {},
      el("td", { class: "req" }, name),
      statusCell("td", tone, label),
      el("td", {}, quoted(mention.quote, several && mention.note ? mention.note : "Quoted word for word from the posting"))));
  });
  if (!result.mentions.length) {
    rows.append(el("tr", {},
      el("td", { class: "req" }, "Start date"),
      statusCell("td", display.tone, result.verdict_label),
      el("td", {}, el("p", { class: "plain" }, result.note || "The posting doesn't state a start date."))));
  }
  if (result.undergrad_warning) {
    rows.append(el("tr", {},
      el("td", { class: "req" }, "Who it's for"),
      statusCell("td", "warn", "Check"),
      el("td", {}, quoted(result.undergrad_warning.quote,
        "This role looks aimed at undergraduates. TrueFit is built for MBA and graduate roles, so check the posting before applying."))));
  }

  const table = el("table", { class: "exhibit-table fresh" },
    el("thead", {}, el("tr", {},
      el("th", { scope: "col" }, "Requirement"),
      el("th", { scope: "col" }, "Status"),
      el("th", { scope: "col" }, "What the posting says"))),
    rows);

  startDateResult.replaceChildren(
    el("h3", { id: "exhibit-1-title", class: "action-title" }, title),
    el("p", { class: "exhibit-sub" }, `Checked against your availability: ${result.availability.label}.`),
    table);
  if (result.note && !noDate) startDateResult.append(el("p", { class: "exhibit-foot" }, result.note));
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
const resultsHeading = document.getElementById("results-heading");
const copyBlock = document.getElementById("copy-block");
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
    renderTailored(true);
    copyBlock.hidden = false;
    setStep("step-results");
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

function renderTailored(fresh = false) {
  tailoredBox.replaceChildren();
  tailoredBox.classList.toggle("fresh", fresh);
  const contact = [...tailorState.linesById.values()].filter((line) => line.kind === "contact");
  if (contact.length) tailoredBox.append(el("div", { class: "resume-contact" }, ...contact.map((line) => el("div", {}, line.text))));
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
        for (const bullet of entry.bullets) list.append(renderBullet(bullet, entry));
        block.append(list);
      }
      tailoredBox.append(block);
    }
  }
  const bullets = allBullets();
  const kept = bullets.filter((b) => b.included).length;
  const flagged = bullets.filter((b) => b.status === "flagged").length;
  const traced = bullets.length - flagged;
  resultsHeading.classList.remove("empty");
  resultsHeading.textContent = `${traced} of ${bullets.length} bullets trace back to your own writing.`;
  summaryBox.textContent = flagged
    ? `${kept} kept in the copy-ready resume. ${flagged} unverified ${flagged === 1 ? "bullet is" : "bullets are"} left out unless you put ${flagged === 1 ? "it" : "them"} back.`
    : `${kept} kept in the copy-ready resume. Each bullet shows the lines it came from.`;
  plainTextBox.value = renderPlainText(tailorState.sections, tailorState.linesById);
}

function renderBullet(bullet, entry) {
  const traced = bullet.status === "traced";
  const item = el("li", { class: `bullet ${bullet.status}${bullet.included ? "" : " excluded"}` });
  const body = el("div", { class: "bullet-body" }, el("span", { class: "bullet-text" }, bullet.text));
  item.append(statusCell("span", traced ? "good" : "warn", traced ? "Traced" : "Unverified"), body);
  if (!traced && bullet.flag_reason) body.append(el("p", { class: "flag-reason" }, bullet.flag_reason));

  const sources = el("div", { class: "sources" });
  for (const id of bullet.source_line_ids) {
    const line = tailorState.linesById.get(id);
    if (line) sources.append(el("p", { class: "quote" }, `${line.source === "notes" ? "From your writing" : "From your resume"}: “${line.text}”`));
  }
  body.append(sources);

  const controls = el("div", { class: "bullet-controls" });
  const toggle = el("button", { class: "link-button", type: "button" }, bullet.included ? "Remove" : "Put back");
  toggle.addEventListener("click", () => {
    bullet.included = !bullet.included; // a flagged bullet put back stays marked Unverified (FR-012c)
    renderTailored();
  });
  const edit = el("button", { class: "link-button", type: "button" }, "Edit");
  edit.addEventListener("click", () => startEdit(item, bullet, entry));
  controls.append(toggle, edit);
  body.append(controls);
  return item;
}

function startEdit(item, bullet, entry) {
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
        header_line_ids: entry.header_line_ids,
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

const copyButton = document.getElementById("copy-resume");

// Copy inside the click itself (some browsers refuse clipboard writes after an await),
// and only say "Copied" when it worked.
copyButton.addEventListener("click", async () => {
  plainTextBox.focus();
  plainTextBox.select();
  let copied = false;
  try {
    copied = document.execCommand("copy");
  } catch (_) {
    copied = false;
  }
  if (!copied && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(plainTextBox.value);
      copied = true;
    } catch (_) {
      copied = false;
    }
  }
  if (copied) {
    copyStatus.textContent = "Copied. Paste it into the application's resume field.";
    copyButton.textContent = "Copied";
    setTimeout(() => { copyButton.textContent = "Copy"; }, 2000);
    track("resume_copied", { bullets: allBullets().filter((b) => b.included).length });
  } else {
    plainTextBox.select();
    copyStatus.textContent = "Your browser blocked copying. The text is selected: press ⌘C (Ctrl+C on Windows) to copy it.";
    track("resume_copy_failed");
  }
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
  const contact = [...linesById.values()].filter((line) => line.kind === "contact").map((line) => normalizeChars(line.text));
  const blocks = contact.length ? [contact.join("\n")] : [];
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
