from datetime import date

import pytest

from app.availability import parse_availability
from app.errors import ApiError

TODAY = date(2026, 11, 4)


@pytest.mark.parametrize("text", [
    "June 2027 – October 2027",
    "June 2027 - October 2027",
    "June 2027 to October 2027",
    "Jun 2027 – Oct 2027",
    "june 2027 – october 2027",
    "June 2027–October 2027",
])
def test_month_range_forms(text):
    a = parse_availability(text, TODAY)
    assert a.mode == "range"
    assert a.start == date(2027, 6, 1)
    assert a.end == date(2027, 10, 31)
    assert a.label == "June 2027 – October 2027"


def test_empty_is_default_window():
    for text in ("", "   ", None):
        a = parse_availability(text, TODAY)
        assert (a.mode, a.start, a.end) == ("range", date(2027, 6, 1), date(2027, 10, 31))


@pytest.mark.parametrize("text,label", [
    ("Immediate", "Immediate"),
    ("immediate", "Immediate"),
    ("IMMEDIATELY", "Immediate"),
    ("ASAP", "ASAP"),
    ("asap", "ASAP"),
])
def test_immediate_and_asap_are_the_same_mode(text, label):
    a = parse_availability(text, TODAY)
    assert a.mode == "immediate"
    assert a.start == TODAY
    assert a.end is None
    assert a.label == label


@pytest.mark.parametrize("joiner", ["through", "until", "to", "-", "–"])
def test_immediate_with_end_month(joiner):
    a = parse_availability(f"ASAP {joiner} August 2027", TODAY)
    assert a.mode == "immediate"
    assert a.start == TODAY
    assert a.end == date(2027, 8, 31)
    assert a.label == "ASAP through August 2027"


def test_flexible():
    a = parse_availability("Flexible", TODAY)
    assert (a.mode, a.start, a.end, a.label) == ("flexible", None, None, "Flexible")
    assert parse_availability("flexible", TODAY).mode == "flexible"


def test_three_letter_and_sept():
    a = parse_availability("Sept 2027 - Dec 2027", TODAY)
    assert a.start == date(2027, 9, 1) and a.end == date(2027, 12, 31)


def test_end_before_start_rejected():
    with pytest.raises(ApiError) as exc:
        parse_availability("October 2027 – June 2027", TODAY)
    assert exc.value.code == "availability_end_before_start"


def test_immediate_end_in_the_past_rejected():
    with pytest.raises(ApiError) as exc:
        parse_availability("ASAP through August 2026", TODAY)
    assert exc.value.code == "availability_end_before_start"


@pytest.mark.parametrize("text", ["soonish", "Summer 2027", "June – October", "13/2027", "Juno 2027 – Oct 2027"])
def test_unrecognized_rejected_with_accepted_forms(text):
    with pytest.raises(ApiError) as exc:
        parse_availability(text, TODAY)
    assert exc.value.code == "availability_invalid"
    for form in ("June 2027 – October 2027", "Immediate", "ASAP", "Flexible"):
        assert form in exc.value.message
