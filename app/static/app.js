// TrueFit page logic. Plain JavaScript, no build step.

// ---- Shared helpers -------------------------------------------------------

const PROFILE_KEY = "truefit.v1"; // the only localStorage key; postings are never stored

function loadProfile() {
  try {
    const saved = JSON.parse(localStorage.getItem(PROFILE_KEY));
    if (saved && typeof saved === "object") {
      return {
        masterResume: typeof saved.masterResume === "string" ? saved.masterResume : "",
        availabilityText: typeof saved.availabilityText === "string" ? saved.availabilityText : "",
        savedAt: saved.savedAt || null,
      };
    }
  } catch (_) {
    // Corrupt value: treat as nothing saved.
  }
  return { masterResume: "", availabilityText: "", savedAt: null };
}

function saveProfile({ masterResume, availabilityText }) {
  const current = loadProfile();
  const profile = {
    masterResume: masterResume ?? current.masterResume,
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
  not_stated: { icon: "?", text: "The posting doesn't say when the role starts. Ask the recruiter before you apply." },
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
  } catch (_) {
    // The error is already shown; the saved availability stays as it was.
  } finally {
    setChecking(false);
  }
}

function renderStartDate(result) {
  startDateResult.replaceChildren();
  startDateResult.className = `result ${result.verdict}`;
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
  postingInput.focus();
});
availabilityInput.value = loadProfile().availabilityText;

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
