# Downloads: clearer spacing, 1-inch margins, fill the page (design)

Nov 18, 2026 · Status: approved Nov 18, built

## Why
Testing the Word and PDF downloads with a real resume (student, Nov 18): the two schools in Education, and the jobs in Experience, run together (each gets only 5 pt above it), and a resume that fits leaves empty space at the bottom of the page. The student wants Word's standard 1-inch margins and a resume that fills the page.

## Goals
- Visible separation between schools and between jobs, in both downloads.
- 1-inch margins whenever the resume fits that way.
- A resume that fits ends at (or very near) the bottom margin, by spreading the spare space between sections and entries.

## Non-goals
- Larger text to fill space (body text stays at most 11 pt).
- Changing what's on the resume, the copy-ready text, or the one-page rules (8 pt floor, name at least 11 pt, never cut bullets).

## Anti-goals
- A Word file that spills onto a second page because the spacing was estimated too generously.
- Huge gaps on a short resume.

## Approaches
- **1. Spread the spacing (chosen).** Keep text size; share spare space between sections and between each school/job, capped at about one blank line per gap.
- 2. Grow text to 12 pt first, then spread. Rejected: 12 pt looks oversized on a resume.

## Decisions
- Spread the spacing, capped (a half-page resume still leaves some space at the bottom).
- Once every section and entry gap is at its cap, up to 2 pt of space between bullets fills more of the page (student's choice, Nov 18, after seeing a same-length-bullet sample leave ~1.3 in).
- Margins (option B): 1 inch at 11, 10.5, and 10 pt text; if it doesn't fit at 1 inch with 10 pt text, margins narrow (0.9, 0.8, 0.7, 0.6, 0.5 inch) before text goes below 10 pt; then text shrinks to the 8 pt floor at 0.5 inch, as today.

## Builder's calls (proposed; the student can correct)
- **Base spacing:** 8 pt above each school or job after the first in a section (was 5 pt), 12 pt above each section heading (was 10 pt). This alone fixes the run-together look even when the page is full.
- **Filling:** spare space is split evenly across those gaps, each gap growing by at most one body line (about 13 pt at 11 pt text); anything left stays at the bottom.
- **Measuring:** the PDF is measured exactly (as today). The Word file can't be measured exactly without Word, so its line wrapping is estimated with real character widths of a slightly wider font than Calibri, which overestimates height: the Word page fills slightly less than the PDF but never spills. Checked by converting sample Word files to PDF with Microsoft Word on this Mac.
- **Docs:** decision row (Nov 18); the Product Page and `AGENTS.md` lines that describe the download layout (0.75-inch margins, 0.5 inch floor).
