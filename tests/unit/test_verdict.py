"""The 8 ordered verdict rules from data-model.md, with today fixed at 2026-11-04."""

from datetime import date

import pytest

from app.availability import parse_availability
from app.start_date import compute_verdict, normalize_mention

TODAY = date(2026, 11, 4)
DEFAULT = parse_availability("", TODAY)


def mention(kind, start=None, end=None, season=None, year=None, quote="q"):
    m = normalize_mention({"quote": quote, "kind": kind, "start": start, "end": end,
                           "season": season, "year": year}, TODAY)
    assert m is not None
    return m


def verdict(mentions, availability=DEFAULT):
    return compute_verdict(mentions, availability, TODAY)


# --- Spec User Story 1 acceptance scenarios ---------------------------------

def test_us1_1_exact_date_in_window():
    assert verdict([mention("exact_date", "2027-07-13")]).verdict == "in_window"


def test_us1_2_january_outside_window():
    assert verdict([mention("month", "2027-01")]).verdict == "outside_window"


def test_us1_3_summer_is_likely_vague():
    r = verdict([mention("season", season="summer", year=2027)])
    assert r.verdict == "likely_in_window_vague"
    assert r.note == "Exact date not specified"


def test_us1_4_no_mentions_not_stated():
    r = verdict([])
    assert r.verdict == "not_stated"
    assert r.mentions == []


def test_us1_5_starting_august_vs_july_posting():
    a = parse_availability("August 2027", TODAY)
    assert verdict([mention("exact_date", "2027-07-13")], a).verdict == "outside_window"


@pytest.mark.parametrize("start", ["2027-06-01", "2027-10-04", "2027-12-01", "2028-09-05"])
def test_any_start_on_or_after_default_june_is_in_window(start):
    assert verdict([mention("exact_date", start)]).verdict == "in_window"


def test_october_2027_month_in_window_with_default():
    assert verdict([mention("month", "2027-10")]).verdict == "in_window"


def test_may_2027_before_default_start_is_outside():
    assert verdict([mention("exact_date", "2027-05-31")]).verdict == "outside_window"


def test_us1_6_immediate_posting_vs_asap_student():
    a = parse_availability("ASAP", TODAY)
    assert verdict([mention("immediate")], a).verdict == "in_window"


@pytest.mark.parametrize("start", ["2027-01-11", "2028-03-06"])
def test_us1_7_flexible_student_any_future_date(start):
    a = parse_availability("Flexible", TODAY)
    r = verdict([mention("exact_date", start)], a)
    assert r.verdict == "in_window"
    assert r.mentions[0].start.isoformat() == start


def test_us1_8_flexible_student_no_date_still_not_stated():
    assert verdict([], parse_availability("Flexible", TODAY)).verdict == "not_stated"


# --- Edge cases ------------------------------------------------------------

@pytest.mark.parametrize("availability", ["", "ASAP", "Flexible"])
def test_date_already_passed(availability):
    r = verdict([mention("exact_date", "2026-09-01")], parse_availability(availability, TODAY))
    assert r.verdict == "outside_window"
    assert r.note == "This date has already passed"


def test_immediate_posting_vs_future_start_month():
    r = verdict([mention("immediate")])
    assert r.verdict == "outside_window"
    assert r.note == "The role starts before you're available"


def test_immediate_posting_vs_flexible_student():
    assert verdict([mention("immediate")], parse_availability("Flexible", TODAY)).verdict == "in_window"


def test_immediate_posting_vs_start_month_already_reached():
    a = parse_availability("November 2026", TODAY)
    assert verdict([mention("immediate")], a).verdict == "in_window"


def test_range_crossing_window_edge():
    assert verdict([mention("range", "2027-05", "2027-07")]).verdict == "partly_in_window"


def test_flexible_posting():
    assert verdict([mention("flexible")]).verdict == "flexible_to_discuss"


def test_fall_with_default_is_likely_vague():
    r = verdict([mention("season", season="fall", year=2027)])
    assert r.verdict == "likely_in_window_vague"
    assert r.note == "Exact date not specified"


def test_season_straddling_start_month_is_partly_vague():
    a = parse_availability("July 2027", TODAY)
    r = verdict([mention("season", season="summer", year=2027)], a)
    assert r.verdict == "partly_in_window"
    assert r.note == "Exact date not specified"


def test_spring_is_outside():
    assert verdict([mention("season", season="spring", year=2027)]).verdict == "outside_window"


def test_month_after_start():
    assert verdict([mention("month", "2027-08")]).verdict == "in_window"


def test_bare_year_is_vague_partial():
    r = verdict([mention("season", season="year", year=2027)])
    assert r.verdict == "partly_in_window"
    assert r.mentions[0].is_vague


def test_asap_student_open_ended_includes_far_future():
    assert verdict([mention("exact_date", "2028-01-15")], parse_availability("ASAP", TODAY)).verdict == "in_window"


def test_multiple_mentions_disagree_summary_is_partly():
    r = verdict([mention("exact_date", "2027-07-13", quote="NYC"), mention("month", "2027-01", quote="London")])
    assert r.verdict == "partly_in_window"
    assert [m.verdict for m in r.mentions] == ["in_window", "outside_window"]
    assert "different" in r.note.lower()


def test_multiple_mentions_agree():
    r = verdict([mention("exact_date", "2027-07-13"), mention("month", "2027-08")])
    assert r.verdict == "in_window"


# --- Normalizing model output ----------------------------------------------

@pytest.mark.parametrize("raw", [
    {"quote": "x", "kind": "exact_date", "start": "not a date"},
    {"quote": "x", "kind": "exact_date"},
    {"quote": "x", "kind": "season", "season": "monsoon", "year": 2027},
    {"quote": "x", "kind": "range", "start": "2027-08", "end": "2027-06"},
    {"quote": "x", "kind": "made_up"},
])
def test_unusable_mentions_are_dropped(raw):
    assert normalize_mention(raw, TODAY) is None


def test_month_is_whole_month():
    m = mention("month", "2027-02")
    assert (m.start, m.end) == (date(2027, 2, 1), date(2027, 2, 28))
