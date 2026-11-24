"""Tailored bullets end the way the student's own bullets do (Build 4: cases 5 and 7 mixed both)."""

from app.resume_lines import split_lines
from app.tailor import match_bullet_endings

NO_PERIODS = "EXPERIENCE\nAnalyst, Contoso | 2019 – 2025\n- Built models\n- Cut costs 35%\n- Ran reviews"
PERIODS = "EXPERIENCE\nAnalyst, Contoso | 2019 – 2025\n- Built models.\n- Cut costs 35%.\n- Ran reviews"


def endings(resume, texts):
    bullets = [{"text": t} for t in texts]
    match_bullet_endings(bullets, split_lines(resume))
    return [b["text"] for b in bullets]


def test_periods_removed_when_the_student_uses_none():
    assert endings(NO_PERIODS, ["Cut the defect backlog by 35%.", "Ran weekly risk reviews", "Led the launch."]) == [
        "Cut the defect backlog by 35%", "Ran weekly risk reviews", "Led the launch"]


def test_periods_added_when_most_student_bullets_have_them():
    assert endings(PERIODS, ["Cut costs 35%", "Built models.", "Grew sales (2 regions)"]) == [
        "Cut costs 35%.", "Built models.", "Grew sales (2 regions)."]


def test_abbreviations_and_ellipses_keep_their_periods():
    assert endings(NO_PERIODS, ["Sold to Contoso Inc.", "Expanded across the U.S.", "Wait..."]) == [
        "Sold to Contoso Inc.", "Expanded across the U.S.", "Wait..."]


def test_no_resume_bullets_means_no_periods():
    assert endings("EXPERIENCE\nAnalyst, Contoso | 2019 – 2025", ["Built models."]) == ["Built models"]
