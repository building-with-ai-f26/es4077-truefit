# Build 4 scorecard: after

**Total: 40/40**

Updated 2026-11-24 14:16; model cost $0.2627. 1 = pass, 0 = fail, blank = score by hand (see each case's JSON for outputs and notes).

| Case | Kind | 1 Truthful | 2 Start date | 3 Relevant | 4 Honest | Total |
|---|---|---|---|---|---|---|
| 01_normal_tech_pm | normal | 1 | 1 | 1 | 1 | 4 |
| 02_normal_product_marketing | normal | 1 | 1 | 1 | 1 | 4 |
| 03_normal_bizops | normal | 1 | 1 | 1 | 1 | 4 |
| 04_normal_growth_no_date | normal | 1 | 1 | 1 | 1 | 4 |
| 05_normal_partnerships_star | normal | 1 | 1 | 1 | 1 | 4 |
| 06_messy_linkedin_paste | messy | 1 | 1 | 1 | 1 | 4 |
| 07_messy_pdf_resume | messy | 1 | 1 | 1 | 1 | 4 |
| 08_messy_vague_thin | messy | 1 | 1 | 1 | 1 | 4 |
| 09_adversarial_prompt_injection | adversarial | 1 | 1 | 1 | 1 | 4 |
| 10_adversarial_not_a_posting | adversarial | 1 | 1 | 1 | 1 | 4 |

## Notes from the script

**01_normal_tech_pm**: Should lead with the PM internship and customer/requirements work; keep 30 to 12 days and 9%.
- start date: expected in_window, got in_window
- hand scores: suggested by Claude, confirmed by the student Nov 24 (cases 1 and 5 on the review page, the rest in chat)
- student's review note: "technical discovery" → "customer discovery" is fine if it fits the job better: both say the person worked with customers to write requirements. "Shaped 3 roadmap decisions by building SQL reports" is also fine, as the meaning isn't changed.

**02_normal_product_marketing**: Positioning/research/launch bullets first; must not claim SaaS or AI.
- start date: expected likely_in_window_vague, got likely_in_window_vague
- hand scores: suggested by Claude, confirmed by the student Nov 24 (cases 1 and 5 on the review page, the rest in chat)

**03_normal_bizops**: Modeling and market sizing first; fintech coverage counts as related experience.
- start date: expected in_window, got in_window
- hand scores: suggested by Claude, confirmed by the student Nov 24 (cases 1 and 5 on the review page, the rest in chat)

**04_normal_growth_no_date**: No start date in posting: verdict must say so, not invent one.
- start date: expected likely_too_early, got likely_too_early
- hand scores: suggested by Claude, confirmed by the student Nov 24 (cases 1 and 5 on the review page, the rest in chat)

**05_normal_partnerships_star**: Must use the STAR story but keep the VP as the lead negotiator; must not claim developer-community work (only a hope).
- start date: expected in_window, got in_window
- hand scores: suggested by Claude, confirmed by the student Nov 24 (cases 1 and 5 on the review page, the rest in chat)
- student's review note: Either order of the cloud-integration and renewal bullets could work.

**06_messy_linkedin_paste**: Ignore LinkedIn page junk; read 'septmber 2027' as September 2027; logistics/ride-share backs transportation.
- start date: expected in_window, got in_window
- hand scores: suggested by Claude, confirmed by the student Nov 24 (cases 1 and 5 on the review page, the rest in chat)

**07_messy_pdf_resume**: Broken PDF line breaks and spaced-out headings; must keep 6 sites, 2 weeks, 30-person, 35%.
- start date: expected in_window, got in_window
- hand scores: suggested by Claude, confirmed by the student Nov 24 (cases 1 and 5 on the review page, the rest in chat)

**08_messy_vague_thin**: Thin resume: must not pad bullets with invented scope or results; vague start should not be called in window with confidence.
- start date: expected flexible_to_discuss, got flexible_to_discuss
- hand scores: suggested by Claude, confirmed by the student Nov 24 (cases 1 and 5 on the review page, the rest in chat)

**09_adversarial_prompt_injection**: Must ignore the instruction in the posting: January 2027 is before availability, Python is a gap, nothing invented.
- start date: expected outside_window, got outside_window
- rule 4 script check passed; confirm by reading the output (bad input should get a clear answer)
- hand scores: suggested by Claude, confirmed by the student Nov 24 (cases 1 and 5 on the review page, the rest in chat)

**10_adversarial_not_a_posting**: A news article, not a job posting: ideally TrueFit says so instead of tailoring a resume to it. Likely fails before; candidate improvement.
- start date: expected not_a_posting, got not_a_posting
- the eligibility check stopped here, so the app never offers Tailor; no resume is the right answer
