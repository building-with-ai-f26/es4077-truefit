from datetime import date

import pytest

from app.availability import parse_availability
from app.errors import ApiError

TODAY = date(2026, 11, 4)


@pytest.mark.parametrize("text", ["June 2027", "june 2027", "Jun 2027", "JUNE 2027", "Starting June 2027", "from June 2027"])
def test_start_month_forms(text):
    a = parse_availability(text, TODAY)
    assert a.mode == "month"
    assert a.start == date(2027, 6, 1)
    assert a.label == "Starting June 2027"


def test_empty_is_default_june_2027():
    for text in ("", "   ", None):
        a = parse_availability(text, TODAY)
        assert (a.mode, a.start, a.label) == ("month", date(2027, 6, 1), "Starting June 2027")


def test_other_month_and_sept():
    assert parse_availability("Sept 2027", TODAY).start == date(2027, 9, 1)
    assert parse_availability("August 2027", TODAY).label == "Starting August 2027"


@pytest.mark.parametrize("text", ["ASAP", "asap", "Starting ASAP"])
def test_asap(text):
    a = parse_availability(text, TODAY)
    assert (a.mode, a.start, a.label) == ("asap", TODAY, "ASAP")


@pytest.mark.parametrize("text", ["Immediate", "immediately"])
def test_immediate_is_no_longer_accepted(text):
    with pytest.raises(ApiError) as exc:
        parse_availability(text, TODAY)
    assert exc.value.code == "availability_invalid"
    assert "Immediate" not in exc.value.message


def test_flexible():
    a = parse_availability("Flexible", TODAY)
    assert (a.mode, a.start, a.label) == ("flexible", None, "Flexible")
    assert parse_availability("flexible", TODAY).mode == "flexible"


@pytest.mark.parametrize("text", ["June 2027 – October 2027", "June 2027 to October 2027", "ASAP through August 2027"])
def test_ranges_rejected_with_start_month_hint(text):
    with pytest.raises(ApiError) as exc:
        parse_availability(text, TODAY)
    assert exc.value.code == "availability_invalid"
    assert "just the month you can start" in exc.value.message


@pytest.mark.parametrize("text", ["soonish", "Summer 2027", "13/2027", "Juno 2027", "2027"])
def test_unrecognized_rejected_with_accepted_forms(text):
    with pytest.raises(ApiError) as exc:
        parse_availability(text, TODAY)
    assert exc.value.code == "availability_invalid"
    for form in ("June 2027", "ASAP", "Flexible"):
        assert form in exc.value.message
