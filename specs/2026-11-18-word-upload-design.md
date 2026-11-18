# Word file upload for the master resume and background (design)

Nov 18, 2026 · Build 3 → 4 · Status: approved Nov 18, built

## Why
Pasting a long resume is error-prone: students can miss part of it when copying, and reviewing it in a textbox invites typos, accidental deletions, and stray spaces. Letting them pick the Word file they already keep removes both problems. This reverses the v1 out-of-scope item "uploading PDF or Word files (text paste only)" for Word only.

## Goals
- A student can choose a `.docx` file for **Master resume** and for **More about your experience**, as an alternative to pasting.
- What TrueFit read is shown, locked against accidental edits, with a line count so a missing section stands out.
- The text read from a file goes through exactly the same steps as pasted text (tab fix, line splitting, tracing).

## Non-goals
- PDF files (text extraction breaks line structure; paste stays the path for PDFs).
- Old `.doc` files, Google Docs links. Google Docs users download as .docx.
- Keeping Word formatting (bold, layout): TrueFit only uses text, and downloads rebuild the layout.

## Anti-goals (a failure even if it "works")
- Silently dropping content: a bullet, a section, or the name and contact line, without the student being able to see it.
- Storing or logging the file or its text on the server, or sending the file itself to the model.

## Approaches
- **A. Read on the server in Python (chosen by the student).** File is sent to a new endpoint, a Python library pulls the text out, and the text comes back to the page. Same language as all other checking, testable with sample Word files in `uv run pytest`. Uses python-docx, which TrueFit already has for the Word download, so no new library; the file passes through the server but is never stored (the text already goes there for tailoring).
- B. Read in the browser with a JavaScript library. File never leaves the device, but harder to test and duplicates text cleanup in JS (PR #39 just fixed a bug in such a duplicate).
- Dropped: carrying Word formatting through, because nothing downstream uses it.

## What the student sees (decided: locked preview with Edit)
```
Master resume   [Choose Word file]  or paste
┌──────────────────────────────────────────┐
│ ✓ resume_2027.docx · 42 lines read       │
│   (preview of the text, read-only)       │
│                     [Edit text] [Remove] │
└──────────────────────────────────────────┘
```
- **More about your experience** works differently: files and typed text go together in one submission. Files the student adds are listed below the textbox (file name, line count, a read-only preview, and Remove on each); the textbox itself stays empty and editable for anything else they want to add (notes, a story they haven't written up anywhere). TrueFit uses both: the text from each file, then whatever is in the textbox.
```
More about your experience (optional)   [Add Word file]
┌──────────────────────────────────────────┐
│ Type or paste anything else here         │
└──────────────────────────────────────────┘
✓ cover_letter_acme.docx · 18 lines   [Preview] [Remove]
✓ star_stories.docx · 35 lines        [Preview] [Remove]
```
- On the master resume, **Edit text** turns the preview back into the normal editable textbox (the file name stays as a note). **Remove** clears it and returns to the empty paste box.
- Pasting stays exactly as today when no file is chosen.
- The master resume read from a file is saved on the student's device the same way a pasted one is (only the text, never the file).

## Decisions
- Word files only (`.docx`); anything else gets a plain message ("TrueFit reads Word files (.docx). For a PDF, open it and paste the text.").
- Read on the server in Python; the file and text are never stored or logged.
- Locked preview with line count, Edit text, and Remove for the master resume.
- More about your experience accepts several Word files **and** typed or pasted text in the same submission; files never replace or lock the textbox.

## Builder's calls (proposed; the student can correct)
- **Joining:** file texts in the order added, then the textbox text, separated by blank lines, sent as the existing background notes. Master resume takes one file. Whether files' text is saved on the device like the master resume follows what background notes do today.
- **Reading rules:** paragraphs in document order; Word list items get "- " added so they count as bullets; tables (some templates lay out jobs in tables) read row by row, cells joined by spaces; text in the page header comes first (names and contact lines often sit there); text boxes are read too. Tabs become spaces (existing rule). Empty paragraphs are kept as line breaks.
- **Limits:** 5 MB per file; a file that can't be opened, or yields no text, gets a message instead of an empty preview.
- **PostHog:** one event when a file is read, with which box, line count, and success or error code. Never the file name or text.
- **Docs:** PRD "Also out of scope" line updated (PDF stays out), a decision row dated Nov 18, How it works, `PRODUCT.md`, `AGENTS.md`.
- **Tests:** sample Word files built inside the tests (bullets, tables, header, tabs, empty file, wrong type), plus a browser check with a real resume file.
- Endpoint shape, library choice, and exact wording are left to the builder.
