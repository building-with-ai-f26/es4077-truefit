from app.quotes import quote_in

POSTING = "About the role\nStart date:   July 13,\n2027. Apply by March 1."


def test_exact_match():
    assert quote_in(POSTING, "Apply by March 1.")


def test_whitespace_and_newlines_ignored():
    assert quote_in(POSTING, "Start date: July 13, 2027.")


def test_paraphrase_rejected():
    assert not quote_in(POSTING, "Starts on July 13, 2027")


def test_empty_quote_rejected():
    assert not quote_in(POSTING, "")
    assert not quote_in(POSTING, "   ")


def test_case_difference_rejected():
    assert not quote_in(POSTING, "start date: july 13, 2027.")
