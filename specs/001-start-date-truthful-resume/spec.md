# Feature Specification: Start-Date Check & Truthful Tailored Resume

**Feature Branch**: `001-start-date-truthful-resume`

**Created**: 2026-11-04

**Status**: Draft

**Input**: User description: "Core workflow from PRD v1 (docs/index.html): Paste one job posting and a master resume → get a start-date check against June–Oct 2027, then a tailored, ATS-friendly resume where every claim is verified against the master resume and any gaps are listed."

## Clarifications

### Session 2026-11-04

- Q: When a student returns for a second posting, should TrueFit remember their master resume? → A: Yes, saved only in the student's own browser on their device, and they can clear it anytime. No accounts and no server-side storage.
- Q: Should every student use the fixed June–October 2027 window, or set their own? → A: Default to June 1 – October 31, 2027. The student can replace it with a month range, or type "Immediate" or "ASAP" (available from today) or "Flexible" (any start date works). Saved on their device. *(Superseded by the revised answer below.)*
- Q (revised 2026-11-04): Should availability be a range or a single start? → A: A single "available starting" month, defaulting to June 2027. Any start date in or after that month counts as in window (e.g., October 2027 or later). The student can also type "ASAP" or "Flexible". Ranges and end months are no longer used.
- Q (revised 2026-11-04): Keep "Immediate" as an option? → A: No. Students type "ASAP" instead; "Immediate" gets the accepted-forms message. Postings that say "immediate start" are still recognized.
- Q: What can the student do with the tailored resume before copying it? → A: Remove any bullet, put a flagged bullet back, and edit any bullet's text. Edited text is re-checked against the master resume and flagged if it can't be traced.
- Q: Should the gap list separate required from preferred qualifications? → A: Yes. Two groups, Required and Preferred, based on the posting's wording; unlabeled requirements count as Required.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start-date check (Priority: P1)

A second-year MBA student finds a full-time posting and pastes its full text into TrueFit. Before anything else, TrueFit tells them the role's start date, quoting the posting text it came from. It also gives a clear verdict on whether that date fits when they can start: June 2027 by default, or the month they set instead, or "ASAP" or "Flexible". Any start in or after their month fits. If the posting gives no start date, TrueFit says "not stated" instead of guessing.

**Why this priority**: This decides whether the student should apply at all. It saves the most wasted effort: no more reading whole postings to hunt for a date, applying to roles they can't take, or skipping roles they could. It's useful even without the resume step.

**Independent Test**: Paste a set of real postings with known start dates (explicit, vague, missing). Check that each verdict and quoted snippet matches what a careful human reader would conclude.

**Acceptance Scenarios** (1–4 use the default "available starting June 2027"):

1. **Given** a posting that says "Start date: July 13, 2027", **When** the student submits it, **Then** TrueFit shows the date "July 13, 2027", the quoted source sentence, and the verdict "In window".
2. **Given** a posting that says "Program begins January 2027", **When** submitted, **Then** the verdict is "Outside window" and the quoted text is shown.
3. **Given** a posting that only says "Summer 2027", **When** submitted, **Then** the verdict is "Likely in window (vague)", with the quoted text and a note that the exact date is not specified.
4. **Given** a posting with no start-date information, **When** submitted, **Then** the verdict is "Not stated" and no date is invented.
5. **Given** a student available starting August 2027, **When** they submit a posting that says "Start date: July 13, 2027", **Then** the verdict is "Outside window".
6. **Given** a student whose availability is "ASAP", **When** they submit a posting that says "immediate start" or "start ASAP", **Then** the verdict is "In window" in both cases.
7. **Given** a student whose availability is "Flexible", **When** they submit a posting that says "Start date: January 11, 2027" or "Start date: March 6, 2028", **Then** the verdict is "In window" for both, and the date is still shown.
8. **Given** a student whose availability is "Flexible", **When** they submit a posting with no start date, **Then** the verdict is still "Not stated".
9. **Given** the default availability (starting June 2027), **When** a posting says "Start date: October 4, 2027" (or any later date, e.g., "September 2028"), **Then** the verdict is "In window".

---

### User Story 2 - Truthful tailored resume (Priority: P1)

After the start-date check, the student pastes their master resume (the full version with all their experience). TrueFit produces a resume tailored to the posting. It reorders, selects, and rewords their real experience to match the posting, and adds no skills, titles, employers, dates, or metrics that aren't in the master resume. Every bullet shows which line of the master resume backs it up. Anything that can't be backed up is flagged, not silently included.

**Why this priority**: "100% true" is the product's core promise. It fixes the main pain with existing AI tools: the student has to re-check every line because the AI invents things.

**Independent Test**: Give a master resume and a posting. Check that every bullet in the output links to a real source line. Check that no number, skill, title, or employer appears in the output without appearing in the master resume.

**Acceptance Scenarios**:

1. **Given** a master resume and a posting, **When** the student asks for a tailored resume, **Then** every bullet in the output shows its matching source line(s) from the master resume.
2. **Given** a posting that asks for "SQL" and a master resume that never mentions SQL, **When** the resume is generated, **Then** SQL does not appear as a claimed skill.
3. **Given** a master bullet stating "grew revenue 12%", **When** it's reworded for the posting, **Then** the metric stays "12%" and is never inflated or changed.
4. **Given** a generated line that can't be matched to any master resume line, **When** results are shown, **Then** that line is visibly flagged as unverified and kept out of the copy-ready resume by default.
5. **Given** a tailored resume, **When** the student edits a bullet to add "led a team of 8" and the master resume never mentions a team size, **Then** the edited bullet is flagged as unverified, with a note naming the claim that can't be traced.
6. **Given** a flagged bullet, **When** the student chooses to put it back, **Then** it appears in the copied resume and stays marked as unverified in the review view.

---

### User Story 3 - ATS-ready output and gap list (Priority: P2)

The student copies the tailored resume and pastes it straight into Workday or iCIMS. It arrives clean: one column, standard section headings, plain text, and no tables, columns, icons, or special characters that break parsers. Alongside the resume, TrueFit lists the gaps: requirements in the posting that the master resume doesn't support. That way the student knows what they can't claim and can prepare to address it.

**Why this priority**: The clean paste-in removes the last manual cleanup step. The gap list makes the truthfulness rule useful instead of just restrictive. It depends on Story 2's output.

**Independent Test**: Paste the copied output into a Workday or iCIMS resume field (or a plain-text field), then confirm that sections and bullets keep their order and no garbling appears. Compare the gap list to a human reading of the posting's requirements against the master resume.

**Acceptance Scenarios**:

1. **Given** a generated resume, **When** the student uses the copy action and pastes it into a plain-text field, **Then** the headings, roles, dates, and bullets appear in a readable single-column order with no stray symbols.
2. **Given** a posting with five stated requirements, three of which the master resume supports, **When** results are shown, **Then** the gap list names the two unsupported requirements.
3. **Given** a posting whose unsupported items are "CPA required" and "Python a plus", **When** results are shown, **Then** "CPA" appears under Required and "Python" under Preferred.
4. **Given** a posting where every requirement is supported, **When** results are shown, **Then** the gap list states that no gaps were found.

---

### Edge Cases

- The posting gives several dates (e.g., application deadline, interview dates, start date). Only the start date is used, and the other dates are not confused with it.
- The posting gives a range that crosses the window edge (e.g., "May–July 2027"). The verdict shows partial overlap ("Partly in window") with the quoted text.
- The posting says "immediate", "immediately", "ASAP", or "as soon as possible". These all count as the same immediate start. The verdict is "In window" if the student's availability is ASAP or Flexible. Otherwise it's "Outside window", noting that the role starts before the student is available.
- The student's availability is ASAP or Flexible and a posting gives a start date that has already passed. The verdict is "Outside window", noting that the date has passed.
- The student types something TrueFit doesn't recognize as availability (e.g., "soonish"). They're asked to enter a start month, "ASAP", or "Flexible", and the previous availability stays in place.
- The student types a range (e.g., "June 2027 – October 2027"). They're asked to enter just their start month, since any later start fits.
- The posting says "flexible start date" or "rolling start". The verdict is "Flexible / to discuss", not "In window".
- The posting includes several roles or locations with different start dates. All the dates found are listed, each with its quoted text.
- The pasted text isn't a job posting (empty, very short, or unrelated). The student is told that no posting was recognized.
- The saved master resume is out of date. It's always shown before tailoring so the student can update it, and the edited version replaces the saved copy.
- The master resume is empty or very short. The student is asked for a fuller master resume before tailoring starts.
- The master resume is much longer than one page. The output is still kept to about one page by selecting the most relevant experience.
- The posting is not in English. The student is told that only English postings are supported.
- A posting requirement is implied by the master resume but not stated (e.g., "Excel" for a financial-modeling role). It's listed as a gap with a note, not claimed.

## Requirements *(mandatory)*

### Functional Requirements

**Input**

- **FR-001**: Users MUST be able to paste the full text of one job posting.
- **FR-002**: Users MUST be able to paste the full text of their master resume.
- **FR-003**: System MUST process one posting and one master resume per run.

**Start-date check**

- **FR-004**: System MUST find the role's start date in the posting, or report "Not stated" when the posting has none.
- **FR-005**: System MUST show the exact posting text the start date came from.
- **FR-006**: System MUST classify the start date against the student's availability as one of: In window, Outside window, Partly in window, Likely in window (vague), Flexible / to discuss, or Not stated. A start date in or after the student's start month MUST count as in window; there is no end date.
- **FR-006a**: The student's availability MUST default to "starting June 2027". The student MUST be able to replace it with one of: a start month (e.g., "August 2027", optionally written "Starting August 2027"); "ASAP", meaning available from today; or "Flexible", meaning any future start date works. Matching of these words MUST ignore capitalization. The availability MUST be saved on the student's device with the master resume and shown next to every verdict.
- **FR-006b**: System MUST reject availability that isn't one of the accepted forms in FR-006a with a plain-language message. Ranges get a message asking for just the start month.
- **FR-007**: System MUST NOT invent or infer a specific date that the posting doesn't state.
- **FR-008**: System MUST show the start-date result before the student commits to the resume step, so they can stop if the date doesn't work.

**Tailored resume**

- **FR-009**: System MUST generate a resume tailored to the posting using only facts in the master resume: employers, titles, dates, schools, degrees, skills, and metrics.
- **FR-010**: System MUST link each bullet in the tailored resume to the master resume line(s) that support it, and show that link to the student.
- **FR-011**: System MUST keep every number, percentage, dollar amount, and date exactly as written in the master resume.
- **FR-012**: System MUST flag any generated content it can't link to the master resume, and keep it out of the copy-ready resume unless the student includes it themselves.
- **FR-012a**: Users MUST be able to remove any bullet from the copy-ready resume and put back any removed or flagged bullet.
- **FR-012b**: Users MUST be able to edit the text of any bullet. System MUST re-check edited text against the master resume and show whether it is still traced or now flagged before the student copies the resume.
- **FR-012c**: A flagged bullet the student puts back MUST stay visibly marked as unverified in the review view (the marking isn't included in the copied text).
- **FR-013**: System MUST NOT add skills, tools, certifications, or keywords from the posting unless the master resume supports them.

**ATS-ready output**

- **FR-014**: System MUST produce the tailored resume as plain, single-column text with standard section headings (e.g., Education, Experience, Skills), no tables, columns, graphics, or icons, and only standard bullet and punctuation characters.
- **FR-015**: Users MUST be able to copy the full copy-ready resume in one action.

**Gap list**

- **FR-016**: System MUST list the posting's stated requirements and qualifications that the master resume doesn't support.
- **FR-016a**: System MUST group gaps as Required or Preferred based on the posting's wording (e.g., "required", "must have" vs. "preferred", "nice to have", "a plus"). Requirements the posting doesn't label MUST be grouped as Required.
- **FR-017**: System MUST state explicitly when no gaps were found.

**Errors and privacy**

- **FR-018**: System MUST give a clear, plain-language message when an input is missing, too short, or isn't recognized as a posting or resume.
- **FR-019**: System MUST NOT store the student's resume or posting on any server after a run completes.
- **FR-020**: System MUST let the student save their master resume on their own device and browser only, and pre-fill it on later visits from that device.
- **FR-021**: Users MUST be able to clear the saved master resume from their device in one action. Postings are never saved.

### Key Entities

- **Job Posting**: The pasted posting text. Attributes include the role title and company (if stated), the stated requirements, and any start-date text.
- **Master Resume**: The student's complete source of truth. It can be saved on the student's device and cleared by them; it's never stored on a server. It's made of individual lines (bullets, roles, education entries, skills) that can be referenced.
- **Availability**: When the student can start. It's one of: a start month; ASAP (from today); or Flexible (any future date). There's no end date. Defaults to starting June 2027 and is saved on the student's device.
- **Start-Date Result**: The extracted date or range (or "Not stated"), the quoted source text, the window it was checked against, and the verdict.
- **Tailored Resume**: The ordered sections and bullets generated for one posting. Each bullet links to one or more Master Resume lines or is flagged as unverified. Each bullet also records whether it's included in the copy-ready resume and whether the student edited it.
- **Gap**: A requirement from the posting with no support in the Master Resume. It's grouped as Required or Preferred and can carry an optional note.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A student goes from pasting a posting to seeing the start-date verdict in under 30 seconds, and from pasting the resume to a copy-ready tailored resume in under 2 minutes.
- **SC-002**: On a test set of at least 10 real MBA-recruiting postings, the start-date verdict matches a human reviewer's judgment in at least 9 of 10 cases, and never shows a specific date for a posting that doesn't state one.
- **SC-003**: On a test set of at least 10 posting/resume pairs, 100% of bullets TrueFit puts in the copy-ready resume by default trace to a master resume line, 100% of student edits with untraceable claims get flagged, and zero numbers, skills, titles, or employers appear that aren't in the master resume.
- **SC-004**: When pasted into a Workday or iCIMS resume field, the output keeps its section and bullet order with no garbled characters in at least 9 of 10 tests.
- **SC-005**: The gap list catches at least 80% of the unsupported requirements a human reviewer finds for the same posting and resume, and puts at least 90% of them in the same Required/Preferred group as the reviewer.
- **SC-006**: At least 3 classmates who test the tool say it takes less time than their current workflow and that they don't need to re-check every line for invented content.

## Assumptions

- Users are second-year NYU Stern MBA students graduating May 2027. Most can start from June 2027, so that's the default (FR-006a). A later start is never a problem for them.
- Postings and resumes are in English and pasted as text. Uploading files (PDF, Word) and fetching postings from URLs are out of scope for v1.
- Vague season terms are read as Spring = March–May, Summer = June–August, Fall = September–November. A season entirely in or after the student's start month → Likely in window (vague). A season that begins before it but ends after → Partly in window (vague). A season that ends before it → Outside window. With the default, "Summer 2027" and "Fall 2027" are both Likely in window.
- Rewording is allowed (changing verbs, reordering, combining, or shortening bullets) as long as no new facts are added and all numbers stay exact.
- The tailored resume targets about one page of content.
- No user accounts are needed for v1. The only thing kept between visits is the master resume, saved on the student's own device and browser (FR-020). It doesn't carry over to other devices or browsers.
- Per PRD non-goals, out of scope: scraping job boards, auto-applying or auto-filling Workday/iCIMS forms, application tracking, cover letters, LinkedIn rewrites, interview prep, and designed templates or PDF styling.
