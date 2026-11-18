"""Reading a job posting from a link (specs/2026-11-18-posting-link-design.md)."""

import pytest

from app.posting_link import MESSAGES, LinkProblem, html_to_text, is_public_address, posting_text, site_kind


def test_greenhouse_links():
    expected = ("greenhouse", {"board": "acme", "job_id": "4012345"})
    assert site_kind("https://boards.greenhouse.io/acme/jobs/4012345") == expected
    assert site_kind("https://job-boards.greenhouse.io/acme/jobs/4012345") == expected


def test_lever_link():
    expected = ("lever", {"company": "acme", "posting_id": "5b1c2d3e-aaaa"})
    assert site_kind("https://jobs.lever.co/acme/5b1c2d3e-aaaa") == expected
    assert site_kind("https://jobs.lever.co/acme/5b1c2d3e-aaaa/apply") == expected


def test_ashby_link():
    expected = ("ashby", {"org": "acme", "job_id": "0f6e-11aa"})
    assert site_kind("https://jobs.ashbyhq.com/acme/0f6e-11aa") == expected
    assert site_kind("https://jobs.ashbyhq.com/acme/0f6e-11aa/application") == expected


def test_workday_link():
    expected = ("workday", {"host": "acme.wd5.myworkdayjobs.com", "tenant": "acme", "site": "External",
                            "path": "job/New-York/Analyst_R123"})
    assert site_kind("https://acme.wd5.myworkdayjobs.com/en-US/External/job/New-York/Analyst_R123") == expected
    assert site_kind("https://acme.wd5.myworkdayjobs.com/External/job/New-York/Analyst_R123") == expected


def test_other_link_is_a_page():
    assert site_kind("https://careers.example.com/jobs/123")[0] == "page"


def test_site_detection_ignores_query_and_spaces():
    assert site_kind("  https://jobs.lever.co/acme/abc?utm_source=linkedin  ")[0] == "lever"


@pytest.mark.parametrize("url", [
    "https://www.linkedin.com/jobs/view/1", "https://www.indeed.com/viewjob?jk=1", "https://nyu.12twenty.com/jobPostings/1",
    "https://app.joinhandshake.com/jobs/1", "https://www.glassdoor.com/job-listing/x", "https://linkedin.com/jobs/view/2"])
def test_blocked_sites(url):
    with pytest.raises(LinkProblem) as problem:
        site_kind(url)
    assert problem.value.code == "blocked_site"
    assert problem.value.message == ("TrueFit can't open LinkedIn, Indeed, or school job boards like 12twenty. "
                                     "Open the posting, click Apply, and paste that link, or paste the posting text.")


@pytest.mark.parametrize("url", ["ftp://x/y", "file:///etc/passwd", "not a link"])
def test_not_a_web_link(url):
    with pytest.raises(LinkProblem) as problem:
        site_kind(url)
    assert problem.value.code == "bad_link"


def test_every_code_has_a_message():
    assert set(MESSAGES) == {"blocked_site", "bad_link", "needs_login", "not_found", "no_job_data", "several_jobs",
                             "too_large", "site_unreachable"}


def test_html_to_text():
    html = "<p>About us</p><ul><li>SQL</li><li>Python &amp; R</li></ul><p>Start: June&nbsp;2027<br>NYC</p>"
    assert html_to_text(html) == "About us\n- SQL\n- Python & R\nStart: June 2027\nNYC"


def test_html_to_text_collapses_blank_lines():
    assert html_to_text("<div><p>A</p></div>\n\n<p></p><p>B</p>") == "A\nB"


def test_posting_text_layout():
    text = posting_text("Analyst", "Acme", "New York, NY", "<p>Build models</p>", ["Employment type: Full-time"])
    assert text == "Analyst\nAcme · New York, NY\nEmployment type: Full-time\n\nBuild models"


def test_posting_text_without_company_or_location():
    assert posting_text("Analyst", None, None, "<p>Build</p>", []) == "Analyst\n\nBuild"


@pytest.mark.parametrize("host", ["127.0.0.1", "10.0.0.5", "169.254.169.254", "localhost", "192.168.1.4", "::1"])
def test_private_addresses(host):
    assert not is_public_address(host)


def test_unresolvable_host_is_not_public():
    assert not is_public_address("no-such-host.invalid")
