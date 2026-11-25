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
        noteFiles: Array.isArray(saved.noteFiles)
          ? saved.noteFiles.filter((f) => typeof f?.text === "string")
              .map((f) => ({ name: String(f.name ?? "Word file"), text: f.text, lines: f.text.split("\n").filter((l) => l.trim()).length }))
          : [],
        savedAt: saved.savedAt || null,
      };
    }
  } catch (_) {
    // Corrupt value: treat as nothing saved.
  }
  return { masterResume: "", backgroundNotes: "", availabilityText: "", noteFiles: [], savedAt: null };
}

function saveProfile({ masterResume, backgroundNotes, availabilityText, noteFiles }) {
  const current = loadProfile();
  const profile = {
    masterResume: masterResume ?? current.masterResume,
    backgroundNotes: backgroundNotes ?? current.backgroundNotes,
    availabilityText: availabilityText ?? current.availabilityText,
    noteFiles: noteFiles ?? current.noteFiles, // text read from Word files, never the files
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

// ---- Step 1: eligibility check: start date, then degree, work authorization, years (User Story 1)

const availabilityInput = document.getElementById("availability");
const postingInput = document.getElementById("posting");
const checkButton = document.getElementById("check-start-date");
const startDateResult = document.getElementById("start-date-result");

let lastStartDate = null; // the tailoring step waits for this (FR-008)
let checkedPosting = null; // the posting text that result belongs to

// Tailoring uses the posting in the box, so it must be the posting that was checked. If the student
// changes it after a check (e.g. pastes a different posting), Tailor locks until they check again.
// Spaces and line breaks don't count as a change: deleting an added word often leaves its space behind.
const sameText = (a, b) => a.replace(/\s+/g, " ").trim() === b.replace(/\s+/g, " ").trim();
function postingIsChecked() {
  return lastStartDate !== null && checkedPosting !== null && sameText(postingInput.value, checkedPosting);
}
function syncTailorLock() {
  if (lastStartDate === null || tailorButton.classList.contains("busy")) return;
  const ok = postingIsChecked();
  tailorButton.disabled = !ok;
  tailorHint.textContent = ok ? "" : "The posting changed. Check eligibility again before tailoring.";
  tailorHint.hidden = ok;
}

const SAMPLE_POSTING = `Associate, Corporate Strategy — Summer 2027 Start
Acme Consumer Brands · New York, NY

About the role
Join our Corporate Strategy team to size new markets, build business cases, and present recommendations to the executive team.

Qualifications
- MBA expected by May 2027
- 3+ years of experience in consulting, strategy, or finance
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

// Status tone for the other requirements. Information-only rows (work authorization, years of
// experience) and Not stated never count for or against the student.
const REQUIREMENT_TONE = { meets: "good", doesnt_meet: "bad", unclear: "warn", not_stated: "none", info: "info" };

// Status glyphs drawn as SVG, always shown next to a word (never color alone).
const MARK_PATHS = {
  good: '<circle cx="12" cy="12" r="11" fill="#1e7a46"/><path d="M6.5 12.5l3.5 3.5 7.5-8" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>',
  warn: '<circle cx="12" cy="12" r="10" fill="none" stroke="#b7791f" stroke-width="2.4"/><path d="M9.3 9.4a2.8 2.8 0 1 1 3.6 2.7c-.6.2-.9.7-.9 1.3v.6" fill="none" stroke="#b7791f" stroke-width="2.2" stroke-linecap="round"/><circle cx="12" cy="17.2" r="1.3" fill="#b7791f"/>',
  bad: '<circle cx="12" cy="12" r="11" fill="#b42318"/><path d="M8 8l8 8M16 8l-8 8" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/>',
  none: '<circle cx="12" cy="12" r="10" fill="none" stroke="#6b7484" stroke-width="2"/><path d="M8 12h8" stroke="#6b7484" stroke-width="2.4" stroke-linecap="round"/>',
  info: '<circle cx="12" cy="12" r="10" fill="none" stroke="#14213d" stroke-width="2"/><circle cx="12" cy="7.6" r="1.4" fill="#14213d"/><path d="M12 11v6.2" stroke="#14213d" stroke-width="2.4" stroke-linecap="round"/>',
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
  else checkButton.append("Check eligibility");
}

async function checkStartDate() {
  setChecking(true); // before reading a link too, so a double-click can't start two checks
  try {
    if (linksIn(postingInput.value)) {
      await readPostingLink(); // a link still in the box is read first; the check uses the posting text
      if (linksIn(postingInput.value)) return; // the link couldn't be read; its message is showing
    }
    const result = await api("/api/start-date", {
      posting: postingInput.value,
      availability_text: availabilityInput.value,
    });
    lastStartDate = result;
    checkedPosting = postingInput.value;
    saveProfile({ availabilityText: availabilityInput.value.trim() });
    renderStartDate(result);
    tailorButton.disabled = false; // tailoring waits for a start-date result (FR-008)
    tailorHint.hidden = true;
    setStep("step-resume");
    const tally = eligibilityTally(result);
    track("start_date_checked", {
      verdict: result.verdict,
      undergrad_warning: Boolean(result.undergrad_warning),
      requirements_met: tally.met,
      requirements_not_met: tally.notMet,
      requirements_unclear: tally.check,
    });
  } catch (err) {
    // The error is already shown; the saved availability stays as it was.
    track("start_date_check_failed", { error_code: err.code || "network_error" });
  } finally {
    setChecking(false);
  }
}

// The start date always counts; the other requirements count only when the posting states them.
function eligibilityTally(result) {
  const tones = [VERDICT_DISPLAY[result.verdict]?.tone || "none"];
  for (const req of result.requirements || []) {
    if (req.verdict !== "not_stated" && req.verdict !== "info") tones.push(REQUIREMENT_TONE[req.verdict]);
  }
  const count = (tone) => tones.filter((t) => t === tone).length;
  return { stated: tones.length, met: count("good"), notMet: count("bad"), check: count("warn") + count("none") };
}

function eligibilityTitle({ stated, notMet, check }) {
  if (notMet) return `You don't meet ${notMet} of the ${stated} requirements this posting states.`;
  if (check) return `Nothing rules you out, but ${check} of the ${stated} requirements ${check === 1 ? "needs" : "need"} a closer look.`;
  if (stated === 1) return "You meet the one requirement this posting states.";
  return stated === 2 ? "You meet both requirements this posting states." : `You meet all ${stated} requirements this posting states.`;
}

function renderStartDate(result) {
  const display = VERDICT_DISPLAY[result.verdict] || { tone: "none", text: result.verdict_label };
  // With no quoted date TrueFit assumes ASAP; the server's note explains that in the row.
  const noDate = !result.mentions.length;
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
  // Sponsorship shows only when the posting mentions it: most don't, and a "Not stated" row there was clutter
  // (student's decision, Nov 18). When a posting does mention it, it can decide whether someone can apply.
  const shown = (result.requirements || []).filter((req) => !(req.requirement === "work_authorization" && req.verdict === "not_stated"));
  const sponsorshipShown = shown.some((req) => req.requirement === "work_authorization");
  for (const req of shown) {
    const evidence = req.quote
      ? quoted(req.quote, req.note || "Quoted word for word from the posting")
      : el("p", { class: "plain" }, "The posting doesn't state this.");
    rows.append(el("tr", {},
      el("td", { class: "req" }, req.name),
      statusCell("td", REQUIREMENT_TONE[req.verdict] || "none", req.verdict_label),
      el("td", {}, evidence)));
  }

  const table = el("table", { class: "exhibit-table fresh" },
    el("thead", {}, el("tr", {},
      el("th", { scope: "col" }, "Requirement"),
      el("th", { scope: "col" }, "Status"),
      el("th", { scope: "col" }, "What the posting says"))),
    rows);

  startDateResult.replaceChildren(
    el("h3", { id: "exhibit-1-title", class: "action-title" }, eligibilityTitle(eligibilityTally(result))),
    el("p", { class: "exhibit-sub" }, `Checked against your availability (${result.availability.label}) and an MBA. ${sponsorshipShown ? "Sponsorship and experience are" : "Experience is"} shown for your information.`),
    table);
  if (!noDate) startDateResult.append(el("p", { class: "exhibit-foot" }, `Start date: ${display.text}${result.note ? ` ${result.note.replace(/\.?$/, ".")}` : ""}`));
}

// A link instead of the posting text: the server reads Greenhouse, Lever, Ashby, Workday, or a page's job data.

const postingLinkStatus = document.getElementById("posting-link-status");
const postingLinkName = postingLinkStatus.querySelector(".file-name");
const postingLinkEdit = document.getElementById("posting-link-edit");
const postingLinkError = document.getElementById("posting-link-error");
// Read on paste, or when Check eligibility is clicked. Not on leaving the box: the status row appearing then
// moves the Check button out from under a click that's in progress.
let lastLinkTried = null; // so the same link isn't read twice
let linkReading = null; // the reading in progress, so Check eligibility can wait for it
let linkFailure = null; // why the last link couldn't be read, shown again if Check is clicked
let linkToken = 0; // a reading that finishes after Remove or the sample posting is ignored

// The links in the box when it holds nothing but links, else null (a posting's text can mention links).
function linksIn(value) {
  const parts = value.trim().split(/\s+/);
  return value.trim() && parts.every((part) => /^https?:\/\/\S+$/i.test(part)) ? parts : null;
}

function showPostingLinkError(message, code) {
  postingLinkError.textContent = message;
  postingLinkError.hidden = false;
  track("posting_link_failed", { error_code: code || "unknown" });
}

function resetPostingLink() {
  linkToken += 1;
  linkFailure = null;
  postingInput.readOnly = false;
  postingInput.classList.remove("locked");
  postingLinkStatus.hidden = true;
  postingLinkError.hidden = true;
  lastLinkTried = null;
}

async function readPostingLink() {
  const links = linksIn(postingInput.value);
  if (!links) return;
  postingLinkError.hidden = true;
  if (links.length > 1) return showPostingLinkError("Paste one link at a time.", "one_link");
  const [url] = links;
  if (url === lastLinkTried) {
    if (linkFailure) showPostingLinkError(linkFailure.message, linkFailure.code);
    return linkReading;
  }
  lastLinkTried = url;
  linkFailure = null;
  linkReading = fetchPostingLink(url);
  return linkReading;
}

async function fetchPostingLink(url) {
  const token = ++linkToken;
  postingInput.readOnly = true;
  postingLinkName.textContent = "Reading the posting…";
  postingLinkEdit.hidden = true;
  postingLinkStatus.hidden = false;
  try {
    let response;
    try {
      response = await fetch("/api/posting-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
    } catch (_) {
      throw Object.assign(new Error("Couldn't reach TrueFit. Check that the app is running and try again."), { code: "network_error" });
    }
    const data = await response.json().catch(() => ({}));
    if (token !== linkToken) return; // the student removed the link or chose the sample meanwhile
    if (!response.ok) {
      throw Object.assign(new Error(data?.error?.message || "Couldn't read this link. Paste the posting text."), { code: data?.error?.code });
    }
    postingInput.value = data.text;
    syncTailorLock();
    postingInput.classList.add("locked"); // locked like a resume read from Word; Edit text unlocks it
    postingLinkName.textContent = `✓ Read from ${data.host} · ${data.lines} ${data.lines === 1 ? "line" : "lines"}`;
    postingLinkName.dataset.host = data.host;
    postingLinkEdit.hidden = false;
    track("posting_link_read", { site: data.site, lines: data.lines });
  } catch (err) {
    if (token !== linkToken) return;
    postingInput.readOnly = false;
    postingLinkStatus.hidden = true;
    linkFailure = { message: err.message, code: err.code };
    showPostingLinkError(err.message, err.code);
  }
}

postingInput.addEventListener("input", syncTailorLock);
postingInput.addEventListener("paste", () => {
  lastLinkTried = null; // pasting the same link again tries again
  setTimeout(readPostingLink); // the pasted text is in the box after this event
});
postingLinkEdit.addEventListener("click", () => {
  postingInput.readOnly = false;
  postingInput.classList.remove("locked");
  postingLinkName.textContent = `From ${postingLinkName.dataset.host}`;
  postingLinkEdit.hidden = true;
  postingInput.focus();
});
document.getElementById("posting-link-remove").addEventListener("click", () => {
  resetPostingLink();
  postingInput.value = "";
  syncTailorLock();
  postingInput.focus();
});

checkButton.addEventListener("click", checkStartDate);
document.getElementById("sample-posting").addEventListener("click", () => {
  resetPostingLink();
  postingInput.value = SAMPLE_POSTING;
  syncTailorLock();
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
  noteFiles = profile.noteFiles;
  renderNoteFiles();
  showSavedAt(profile.masterResume || profile.backgroundNotes || noteFiles.length ? profile.savedAt : null);
}

document.getElementById("save-profile").addEventListener("click", () => {
  const profile = saveProfile({ masterResume: masterResumeInput.value, backgroundNotes: notesInput.value, noteFiles });
  forgetUndo();
  showSavedAt(profile.savedAt);
});

// "Clear saved" empties the boxes too, so a mis-tap could lose a pasted resume. Undo puts back
// everything it removed, on the page and on this device, until the student types or saves again.
const undoClearButton = document.getElementById("undo-clear");
let beforeClear = null;

function forgetUndo() {
  beforeClear = null;
  undoClearButton.hidden = true;
}

undoClearButton.addEventListener("click", () => {
  if (!beforeClear) return;
  const b = beforeClear;
  if (b.stored !== null) localStorage.setItem(PROFILE_KEY, b.stored);
  masterResumeInput.value = b.masterResume;
  masterResumeInput.readOnly = b.resumeLocked;
  masterResumeInput.classList.toggle("locked", b.resumeLocked);
  resumeFileStatus.hidden = b.resumeFileHidden;
  resumeFileName.textContent = b.resumeFileName;
  notesInput.value = b.notes;
  noteFiles = b.noteFiles;
  renderNoteFiles();
  availabilityInput.value = b.availability;
  savedAtLabel.textContent = b.savedAtText;
  forgetUndo();
  document.getElementById("clear-profile").focus(); // the Undo button is gone, so keep keyboard focus nearby
});

for (const box of [masterResumeInput, notesInput, availabilityInput]) box.addEventListener("input", forgetUndo);

document.getElementById("clear-profile").addEventListener("click", () => {
  beforeClear = {
    stored: localStorage.getItem(PROFILE_KEY),
    masterResume: masterResumeInput.value,
    resumeLocked: masterResumeInput.readOnly,
    resumeFileHidden: resumeFileStatus.hidden,
    resumeFileName: resumeFileName.textContent,
    notes: notesInput.value,
    noteFiles,
    availability: availabilityInput.value,
    savedAtText: savedAtLabel.textContent,
  };
  clearProfile(); // FR-021: removes the resume, notes, and availability from this device
  clearResumeFile();
  notesInput.value = "";
  noteFiles = [];
  renderNoteFiles();
  clearFileError("notes");
  availabilityInput.value = "";
  savedAtLabel.textContent = "Cleared from this device.";
  undoClearButton.hidden = false;
  track("resume_cleared");
});

// Word files instead of pasting: the server reads the text; only the text is kept, never the file.

const WORD_ONLY = "TrueFit reads Word files (.docx). For a PDF, open it and paste the text.";
const resumeFileInput = document.getElementById("resume-file");
const resumeFileStatus = document.getElementById("resume-file-status");
const resumeFileName = resumeFileStatus.querySelector(".file-name");
const resumeFileEdit = document.getElementById("resume-file-edit");
const notesFileInput = document.getElementById("notes-file");
const noteFilesList = document.getElementById("note-files");
let noteFiles = []; // [{ name, text, lines }] in the order added, sent before the typed notes

// File problems show next to the button that caused them, not in the error box at the top of the page.
const fileErrors = { resume: document.getElementById("resume-file-error"), notes: document.getElementById("notes-file-error") };

function clearFileError(box) {
  fileErrors[box].replaceChildren();
  fileErrors[box].hidden = true;
}

async function readDocx(file, box) {
  try {
    if (!file.name.toLowerCase().endsWith(".docx")) throw Object.assign(new Error(WORD_ONLY), { code: "not_docx" });
    let response;
    try {
      response = await fetch("/api/read-docx", { method: "POST", body: file });
    } catch (_) {
      throw Object.assign(new Error("Couldn't reach TrueFit. Check that the app is running and try again."), { code: "network_error" });
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw Object.assign(new Error(data?.error?.message || "Couldn't read this file. Please paste the text."), { code: data?.error?.code });
    }
    track("file_read", { box, lines: data.lines });
    return data;
  } catch (err) {
    if (fileErrors[box].childNodes.length) fileErrors[box].append(el("br"));
    fileErrors[box].append(`${file.name}: ${err.message}`); // several files can fail at once, so each names its file
    fileErrors[box].hidden = false;
    track("file_read_failed", { box, error_code: err.code || "unknown" });
    throw err;
  }
}

function clearResumeFile() {
  clearFileError("resume");
  masterResumeInput.value = "";
  masterResumeInput.readOnly = false;
  masterResumeInput.classList.remove("locked");
  resumeFileStatus.hidden = true;
}

document.getElementById("resume-file-button").addEventListener("click", () => resumeFileInput.click());
resumeFileInput.addEventListener("change", async () => {
  const file = resumeFileInput.files[0];
  resumeFileInput.value = ""; // choosing the same file again still fires "change"
  if (!file) return;
  clearFileError("resume");
  try {
    const { text, lines } = await readDocx(file, "resume");
    masterResumeInput.value = text;
    masterResumeInput.readOnly = true; // locked so a stray keystroke can't change it
    masterResumeInput.classList.add("locked");
    resumeFileName.textContent = `✓ ${file.name} · ${lines} ${lines === 1 ? "line" : "lines"} read`;
    resumeFileEdit.hidden = false;
    resumeFileStatus.hidden = false;
  } catch (_) {
    // readDocx showed the message; keep whatever was there before
  }
});
resumeFileEdit.addEventListener("click", () => {
  masterResumeInput.readOnly = false;
  masterResumeInput.classList.remove("locked");
  resumeFileName.textContent = `From ${resumeFileName.textContent.replace(/^✓ /, "").split(" · ")[0]}`;
  resumeFileEdit.hidden = true;
  masterResumeInput.focus();
});
document.getElementById("resume-file-remove").addEventListener("click", clearResumeFile);

document.getElementById("notes-file-button").addEventListener("click", () => notesFileInput.click());
notesFileInput.addEventListener("change", async () => {
  const files = [...notesFileInput.files];
  notesFileInput.value = "";
  clearFileError("notes");
  for (const file of files) {
    try {
      const { text, lines } = await readDocx(file, "notes");
      const entry = { name: file.name, text, lines };
      const same = noteFiles.findIndex((f) => f.name === file.name);
      if (same >= 0) noteFiles[same] = entry; // the same file again replaces it, so it isn't counted twice
      else noteFiles.push(entry);
    } catch (_) {
      // message shown; go on with the other files
    }
  }
  renderNoteFiles();
});

function renderNoteFiles() {
  noteFilesList.replaceChildren(...noteFiles.map((file) => {
    const preview = el("pre", { class: "file-preview" }, file.text);
    preview.hidden = true;
    const toggle = el("button", { class: "link-button", type: "button" }, "Preview");
    toggle.addEventListener("click", () => {
      preview.hidden = !preview.hidden;
      toggle.textContent = preview.hidden ? "Preview" : "Hide";
    });
    const remove = el("button", { class: "link-button", type: "button" }, "Remove");
    remove.addEventListener("click", () => {
      noteFiles = noteFiles.filter((f) => f !== file);
      renderNoteFiles();
    });
    return el("li", {}, el("div", { class: "file-row" }, el("span", { class: "file-name" }, `✓ ${file.name} · ${file.lines} ${file.lines === 1 ? "line" : "lines"}`), toggle, remove), preview);
  }));
}

// What TrueFit uses as "More about your experience": each file's text in the order added, then the textbox.
function backgroundNotesText() {
  return [...noteFiles.map((f) => f.text), notesInput.value].filter((t) => t.trim()).join("\n\n");
}

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
  tailorButton.classList.toggle("busy", busy);
  tailorButton.disabled = busy || !postingIsChecked();
  tailorButton.replaceChildren();
  if (busy) tailorButton.append(el("span", { class: "spinner", "aria-hidden": "true" }), "Tailoring…");
  else tailorButton.append("Tailor resume");
}

async function tailorResume() {
  const request = {
    posting: postingInput.value,
    master_resume: masterResumeInput.value,
    background_notes: backgroundNotesText(),
  };
  setTailoring(true);
  try {
    const result = await api("/api/tailor", request);
    tailorState = {
      request,
      linesById: new Map(result.resume_lines.map((line) => [line.id, line])),
      sections: result.resume.sections,
      gaps: result.gaps,
    };
    renderTailored(true);
    renderGaps(result.gaps);
    copyBlock.hidden = false;
    plainTextBox.classList.add("collapsed"); // a new resume starts as a short preview
    setStep("step-results");
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    const bullets = allBullets();
    track("resume_tailored", {
      bullets: bullets.length,
      flagged: bullets.filter((b) => b.status === "flagged").length,
      gaps_required: result.gaps?.required.length ?? 0,
      gaps_preferred: result.gaps?.preferred.length ?? 0,
    });
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

// Mirrors contact_rows in app/plain_text.py: the name, then all other contact details on one line.
function contactRows(linesById) {
  const contact = [...linesById.values()].filter((line) => line.kind === "contact").map((line) => line.text);
  if (contact.length <= 1) return contact;
  return [contact[0], contact.slice(1).map((part) => part.replace(/^[\s|]+|[\s|]+$/g, "")).join(" | ")];
}

// Mirrors header_rows in app/plain_text.py: [left, right] rows, organization | location then title | dates.
function headerRows(entry, linesById) {
  const fields = entry.header_fields || {};
  const rows = [];
  let orgRow = null;
  for (const id of entry.header_line_ids) {
    const line = linesById.get(id);
    if (!line) continue;
    const parts = fields[id];
    if (!parts) { rows.push([line.text, ""]); continue; }
    if (parts.organization || parts.location) {
      if (!orgRow) { orgRow = [parts.organization || "", parts.location || ""]; orgRow.org = true; rows.push(orgRow); }
      else { orgRow[0] = orgRow[0] || parts.organization || ""; orgRow[1] = orgRow[1] || parts.location || ""; }
    }
    if (parts.title) rows.push([parts.title, parts.dates || ""]);
    else if (parts.dates) {
      const last = rows[rows.length - 1];
      if (last && last !== orgRow && !last[1]) last[1] = parts.dates;
      else rows.push(["", parts.dates]);
    }
  }
  return rows;
}

function renderTailored(fresh = false) {
  tailoredBox.replaceChildren();
  tailoredBox.classList.toggle("fresh", fresh);
  const [name, details] = contactRows(tailorState.linesById);
  if (name) tailoredBox.append(el("div", { class: "resume-contact" },
    el("div", { class: "resume-name" }, name), details ? el("div", { class: "resume-contact-details" }, details) : null));
  for (const section of tailorState.sections) {
    // "Only unverified" hides traced bullets, and any job or section left with nothing to decide.
    const shown = (entry) => entry.bullets.filter((b) => !tailorState.onlyUnverified || b.status === "flagged");
    if (tailorState.onlyUnverified && !section.entries.some((e) => shown(e).length)) continue;
    tailoredBox.append(el("h3", { class: "resume-section" }, section.heading));
    for (const entry of section.entries) {
      const bullets = shown(entry);
      if (tailorState.onlyUnverified && !bullets.length) continue;
      const block = el("div", { class: "entry" });
      for (const row of headerRows(entry, tailorState.linesById)) {
        block.append(el("div", { class: `entry-header${row.org ? " org" : ""}` },
          el("span", {}, row[0]), row[1] ? el("span", { class: "entry-header-right" }, row[1]) : null));
      }
      if (bullets.length) {
        // A job can fold to one line once the student has checked it.
        const flaggedHere = bullets.filter((b) => b.status === "flagged").length;
        const fold = el("button", { class: "link-button entry-toggle", type: "button", "aria-expanded": String(!entry.collapsed) },
          entry.collapsed ? "Show bullets" : "Hide bullets");
        fold.addEventListener("click", () => {
          entry.collapsed = !entry.collapsed;
          renderTailored();
        });
        if (entry.collapsed) {
          block.append(el("p", { class: "entry-summary" },
            `${bullets.length} ${bullets.length === 1 ? "bullet" : "bullets"}${flaggedHere ? `, ${flaggedHere} unverified` : ""}`), fold);
        } else {
          const list = el("ul", { class: "bullets" });
          for (const bullet of bullets) list.append(renderBullet(bullet, entry));
          block.append(list, fold);
        }
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
  summaryBox.replaceChildren(flagged
    ? `${kept} kept in the copy-ready resume. ${flagged} unverified ${flagged === 1 ? "bullet is" : "bullets are"} left out unless you put ${flagged === 1 ? "it" : "them"} back.`
    : `${kept} kept in the copy-ready resume. Each bullet shows the lines it came from.`);
  plainTextBox.value = renderPlainText(tailorState.sections, tailorState.linesById);
  updateResultsBar();
}

function renderBullet(bullet, entry) {
  const traced = bullet.status === "traced";
  // Only bullets the student removed are crossed out; unverified ones stay readable while left out.
  const item = el("li", { class: `bullet ${bullet.status}${bullet.removed ? " removed" : ""}` });
  const body = el("div", { class: "bullet-body" }, el("span", { class: "bullet-text" }, bullet.text));
  item.append(statusCell("span", traced ? "good" : "warn", traced ? "Traced" : "Unverified"), body);
  if (!traced && bullet.flag_reason) {
    body.append(el("p", { class: "flag-reason" }, bullet.included || bullet.removed ? bullet.flag_reason : `Left out of your resume. ${bullet.flag_reason.replace(/\.$/, "")}.`));
  }

  // Sources double a bullet's height, so traced bullets hide them behind "Show source";
  // unverified bullets always show them, since that's what the student needs to judge.
  const showSources = !traced || bullet.showSources;
  const sources = el("div", { class: "sources" });
  for (const id of showSources ? bullet.source_line_ids : []) {
    const line = tailorState.linesById.get(id);
    if (line) sources.append(el("p", { class: "quote" }, `${line.source === "notes" ? "From your writing" : "From your resume"}: “${line.text.replace(/^(?:-(?!\d)|[*•●▪◦·–—])\s*/, "")}”`));
  }
  body.append(sources);

  // Remove crosses a bullet out and leaves it out; Put back restores it. Unverified bullets start left out
  // without being crossed out, and a put-back unverified bullet stays marked Unverified (FR-012c).
  const controls = el("div", { class: "bullet-controls" });
  const toggle = el("button", { class: "link-button", type: "button" }, bullet.included ? "Remove" : "Put back");
  toggle.addEventListener("click", () => {
    bullet.included = !bullet.included;
    bullet.removed = !bullet.included; // pressing Remove crosses it out; Put back clears that
    track(bullet.included ? "bullet_put_back" : "bullet_removed", { status: bullet.status });
    renderTailored();
  });
  const edit = el("button", { class: "link-button", type: "button" }, "Edit");
  edit.addEventListener("click", () => startEdit(item, bullet, entry));
  controls.append(toggle, edit);
  if (traced) {
    const source = el("button", { class: "link-button", type: "button" }, bullet.showSources ? "Hide source" : "Show source");
    source.addEventListener("click", () => {
      bullet.showSources = !bullet.showSources;
      renderTailored();
    });
    controls.append(source);
  }
  body.append(controls);
  return item;
}

// ---- Gap list (User Story 3): Required and Preferred, each quoted from the posting ----------------

const gapBlock = document.getElementById("gap-block");
const gapList = document.getElementById("gap-list");

function renderGaps(gaps) {
  gapList.replaceChildren();
  gapBlock.hidden = !gaps;
  if (!gaps) return;
  if (gaps.none_found) { // FR-017: say so plainly
    gapList.append(el("p", { class: "plain" }, "No gaps found: your own lines back every requirement this posting lists."));
    return;
  }
  for (const [group, label] of [["required", "Required"], ["preferred", "Preferred"]]) {
    const rows = gapRows(gaps[group]);
    if (!rows.length) continue;
    gapList.append(el("h4", { class: "resume-section" }, `${label} (${rows.length})`));
    const list = el("ul", { class: "bullets fresh" });
    for (const row of rows) {
      const body = el("div", { class: "bullet-body" }, quoted(row.line, "Quoted word for word from the posting"));
      for (const note of row.notes) body.append(el("p", { class: "gap-note" }, note));
      const related = el("div", { class: "sources" });
      for (const id of row.related) {
        const line = tailorState.linesById.get(id);
        if (line) related.append(el("p", { class: "quote" }, `Closest in your ${line.source === "notes" ? "writing" : "resume"}: “${line.text.replace(/^(?:-(?!\d)|[*•●▪◦·–—])\s*/, "")}”`));
      }
      body.append(related);
      list.append(el("li", { class: "bullet" }, el("span", { class: "gap-name" }, row.names.join(", ")), body));
    }
    gapList.append(list);
  }
}

// Gaps from the same posting bullet share a row, so one bullet doesn't look like several gaps and the
// quoted bullet is easy to find in the posting.
function gapRows(gaps) {
  const rows = new Map();
  for (const gap of gaps) {
    const line = gap.posting_bullet || gap.quote;
    if (!rows.has(line)) rows.set(line, { line, names: [], notes: [], related: [] });
    const row = rows.get(line);
    row.names.push(gap.text);
    if (gap.note && !row.notes.includes(gap.note)) row.notes.push(gap.note);
    for (const id of gap.related_line_ids) if (!row.related.includes(id) && row.related.length < 2) row.related.push(id);
  }
  return [...rows.values()];
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
    plainTextBox.classList.remove("collapsed"); // show the full text once it's copied
    setTimeout(() => { copyButton.textContent = "Copy"; }, 2000);
    track("resume_copied", { bullets: allBullets().filter((b) => b.included).length });
  } else {
    plainTextBox.select();
    copyStatus.textContent = "Your browser blocked copying. The text is selected: press ⌘C (Ctrl+C on Windows) to copy it.";
    track("resume_copy_failed");
  }
});

// ---- Word and PDF downloads (Build 3): the same kept bullets as one-page files built on the server -----

const DOWNLOADS = { docx: "Word", pdf: "PDF" };

for (const [kind, label] of Object.entries(DOWNLOADS)) {
  const button = document.getElementById(`download-${kind}`);
  button.addEventListener("click", () => downloadResume(kind, label, button));
}

async function downloadResume(kind, label, button) {
  clearError();
  button.disabled = true;
  try {
    const response = await fetch(`/api/resume-${kind}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        master_resume: tailorState.request.master_resume,
        background_notes: tailorState.request.background_notes,
        sections: tailorState.sections,
      }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data?.error?.message || `Couldn't build the ${label} file. Please try again.`);
    }
    const fits = response.headers.get("X-Fits-One-Page") === "true";
    const remove = Number(response.headers.get("X-Remove-Bullets") || 0);
    const name = /filename="([^"]+)"/.exec(response.headers.get("Content-Disposition") || "")?.[1] || `Resume.${kind}`;
    const link = el("a", { href: URL.createObjectURL(await response.blob()), download: name });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    copyStatus.textContent = fits
      ? `Downloaded ${name}. It fits on one page.`
      : `Downloaded ${name}, but it runs past one page. Remove about ${remove} ${remove === 1 ? "bullet" : "bullets"} and download again; TrueFit won't cut your content for you.`;
    track("resume_downloaded", { format: kind, fits_one_page: fits, bullets: allBullets().filter((b) => b.included).length });
  } catch (err) {
    showError(err.message === "Failed to fetch" ? "Couldn't reach TrueFit. Check that the app is running and try again." : err.message);
    track("resume_download_failed", { format: kind });
  } finally {
    button.disabled = false;
  }
}

// ---- Jump bar: stays on screen while scrolling; jumps to unverified bullets, gaps, and export -------

const resultsBar = document.getElementById("results-bar");
const jumpUnverified = document.getElementById("jump-unverified");
const jumpGaps = document.getElementById("jump-gaps");
const onlyUnverified = document.getElementById("only-unverified");
let jumpIndex = -1;

function updateResultsBar() {
  const flagged = allBullets().filter((b) => b.status === "flagged").length;
  if (!flagged && tailorState.onlyUnverified) {
    tailorState.onlyUnverified = false; // the last unverified bullet was fixed; show everything again
    renderTailored();
    return;
  }
  resultsBar.hidden = false;
  jumpUnverified.textContent = flagged ? `Next unverified (${flagged})` : "No unverified bullets";
  jumpUnverified.disabled = !flagged;
  onlyUnverified.disabled = !flagged;
  onlyUnverified.checked = Boolean(tailorState.onlyUnverified);
  const gaps = tailorState.gaps;
  const rows = gaps && !gaps.none_found ? gapRows(gaps.required).length + gapRows(gaps.preferred).length : 0;
  jumpGaps.textContent = rows ? `Gaps (${rows})` : "No gaps";
}

// Each press moves to the next unverified bullet, opening any folded job that holds one.
jumpUnverified.addEventListener("click", () => {
  const folded = tailorState.sections.flatMap((s) => s.entries).filter((e) => e.collapsed && e.bullets.some((b) => b.status === "flagged"));
  if (folded.length) {
    folded.forEach((e) => { e.collapsed = false; });
    renderTailored();
  }
  const items = [...tailoredBox.querySelectorAll(".bullet.flagged")];
  if (!items.length) return;
  jumpIndex = (jumpIndex + 1) % items.length;
  items.forEach((item) => item.classList.remove("jumped"));
  items[jumpIndex].classList.add("jumped");
  items[jumpIndex].scrollIntoView({ behavior: "smooth", block: "center" });
});
jumpGaps.addEventListener("click", () => gapBlock.scrollIntoView({ behavior: "smooth", block: "start" }));
document.getElementById("jump-export").addEventListener("click", () => copyBlock.scrollIntoView({ behavior: "smooth", block: "start" }));
onlyUnverified.addEventListener("change", () => {
  tailorState.onlyUnverified = onlyUnverified.checked;
  jumpIndex = -1;
  renderTailored();
  track("only_unverified_toggled", { on: onlyUnverified.checked });
});

// Mirrors app/plain_text.py so edits update the copy-ready text without another server call.
const DATE_RANGE = /(\d{4})\s*[–—-]\s*((?:[A-Z][a-z]{2,8}\.?\s+)?\d{4}|Present|present|Current|current)/g;

function normalizeChars(text) {
  return text
    .replace(/\t/g, " ") // pasted tabs keep words apart instead of gluing them
    .replace(/[‘’]/g, "'").replace(/[“”]/g, '"').replace(/…/g, "...").replace(/ /g, " ")
    .trim()
    .replace(/^(?:-(?!\d)|[*•●▪◦·])\s*/, "") // "-15%" is a minus sign, not a bullet
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
  const contact = contactRows(linesById).map(normalizeChars);
  const blocks = contact.length ? [contact.join("\n")] : [];
  for (const section of sections) {
    const rows = [];
    for (const entry of section.entries) {
      for (const row of headerRows(entry, linesById)) rows.push(row.filter(Boolean).map(normalizeChars).join(" | "));
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

// ---- Leaving the page ------------------------------------------------------
// The browser asks "Leave site?" only when work would be lost: a tailored resume on screen, or a
// resume or notes that differ from what's saved on this device. A pasted posting alone doesn't count.
function hasUnsavedWork() {
  if (tailorState) return true;
  const saved = loadProfile();
  const texts = (files) => JSON.stringify(files.map((f) => f.text));
  return Boolean(
    (masterResumeInput.value.trim() && masterResumeInput.value !== saved.masterResume) ||
    (notesInput.value.trim() && notesInput.value !== saved.backgroundNotes) ||
    (noteFiles.length && texts(noteFiles) !== texts(saved.noteFiles))
  );
}

window.addEventListener("beforeunload", (event) => {
  if (!hasUnsavedWork()) return;
  event.preventDefault();
  event.returnValue = ""; // older browsers need this to show their own "Leave site?" message
});
