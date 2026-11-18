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


# ---- Reading each kind of site (fake responses; tests never use the network) ----

import asyncio  # noqa: E402
import json  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import httpx  # noqa: E402

from app import posting_link  # noqa: E402
from app.posting_link import read_posting_link  # noqa: E402


@pytest.fixture
def web(monkeypatch):
    """Answers requests from a dict of URL -> response; records every URL asked for."""
    pages, seen = {}, []

    def handler(request):
        url = str(request.url)
        seen.append(url)
        reply = pages.get(url)
        if reply is None:
            return httpx.Response(404)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(posting_link, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(posting_link, "_public", lambda host: host != "internal.example")
    return SimpleNamespace(pages=pages, seen=seen)


def read(url):
    return asyncio.run(read_posting_link(url))


def problem(url):
    with pytest.raises(LinkProblem) as caught:
        read(url)
    return caught.value.code


def ld_page(*objects):
    scripts = "".join(f'<script type="application/ld+json">{json.dumps(o)}</script>' for o in objects)
    return httpx.Response(200, text=f"<html><head>{scripts}</head><body><nav>Menu</nav></body></html>",
                          headers={"Content-Type": "text/html"})


def test_greenhouse_posting(web):
    web.pages["https://boards-api.greenhouse.io/v1/boards/acme/jobs/1"] = httpx.Response(200, json={
        "title": "Analyst", "company_name": "Acme", "location": {"name": "New York, NY"},
        "content": "&lt;p&gt;Build models&lt;/p&gt;&lt;ul&gt;&lt;li&gt;SQL&lt;/li&gt;&lt;/ul&gt;"})
    result = read("https://boards.greenhouse.io/acme/jobs/1")
    assert result["text"] == "Analyst\nAcme · New York, NY\n\nBuild models\n- SQL"
    assert result["site"] == "greenhouse" and result["host"] == "boards.greenhouse.io" and result["lines"] == 4
    assert "&lt;" not in result["text"] and "<p>" not in result["text"]


def test_lever_posting(web):
    web.pages["https://api.lever.co/v0/postings/acme/abc"] = httpx.Response(200, json={
        "text": "Associate", "categories": {"location": "Remote", "commitment": "Full-time"},
        "description": "<p>About the role</p>", "lists": [{"text": "Requirements", "content": "<li>MBA</li>"}],
        "additional": "<p>Benefits</p>"})
    text = read("https://jobs.lever.co/acme/abc")["text"]
    assert text == "Associate\nRemote\nEmployment type: Full-time\n\nAbout the role\nRequirements\n- MBA\nBenefits"


def test_ashby_posting(web):
    """Ashby's public data is the whole job board at once (over 3 MB at Ramp), so the job's own page is read."""
    web.pages["https://jobs.ashbyhq.com/acme/j1"] = ld_page({"@type": "JobPosting", "title": " PM",
        "hiringOrganization": {"name": "Acme"}, "employmentType": "FULL_TIME", "description": "<p>Ship</p>"})
    result = read("https://jobs.ashbyhq.com/acme/j1")
    assert result["text"] == "PM\nAcme\nEmployment type: FULL_TIME\n\nShip"
    assert result["site"] == "ashby"
    assert web.seen == ["https://jobs.ashbyhq.com/acme/j1"]


def test_ashby_job_missing(web):
    assert problem("https://jobs.ashbyhq.com/acme/j1") == "not_found"


def test_job_data_lists_every_location(web):
    web.pages["https://careers.example.com/jobs/8"] = ld_page({"@type": "JobPosting", "title": "Investigator",
        "jobLocation": [{"address": {"addressLocality": "Seattle", "addressRegion": "WA"}},
                        {"address": {"addressLocality": "New York", "addressRegion": "NY"}},
                        {"address": {"addressLocality": "Seattle", "addressRegion": "WA"}}],
        "description": "<p>Investigate</p>"})
    assert read("https://careers.example.com/jobs/8")["text"].splitlines()[1] == "Seattle, WA; New York, NY"


def test_workday_posting(web):
    web.pages["https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/External/job/NYC/Analyst_R1"] = httpx.Response(200, json={
        "jobPostingInfo": {"title": "Analyst", "location": "New York", "timeType": "Full time",
                           "startDate": "2026-11-01", "jobDescription": "<p>Model</p>"}})
    text = read("https://acme.wd5.myworkdayjobs.com/en-US/External/job/NYC/Analyst_R1")["text"]
    assert text == "Analyst\nNew York\nEmployment type: Full time\n\nModel"
    assert "2026-11-01" not in text  # Workday's startDate is the day it was posted, not the job's start


def test_page_with_job_data(web):
    web.pages["https://careers.example.com/jobs/7"] = ld_page({"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "name": "Example"},
        {"@type": "JobPosting", "title": "Strategy Associate", "hiringOrganization": {"name": "Example Co"},
         "jobLocation": [{"address": {"addressLocality": "Chicago", "addressRegion": "IL"}}],
         "employmentType": ["FULL_TIME"], "jobStartDate": "2027-06-01", "description": "<p>Lead projects</p>"}]})
    result = read("https://careers.example.com/jobs/7")
    assert result["text"] == ("Strategy Associate\nExample Co · Chicago, IL\nStart date: 2027-06-01\n"
                              "Employment type: FULL_TIME\n\nLead projects")
    assert result["site"] == "job data"


def test_company_page_without_job_data(web):
    web.pages["https://acme.com/careers?gh_jid=123"] = httpx.Response(200, text="<nav>Menu</nav><p>Join us</p>")
    assert problem("https://acme.com/careers?gh_jid=123") == "no_job_data"


def test_several_jobs_on_a_page(web):
    web.pages["https://careers.example.com/all"] = ld_page(
        [{"@type": "JobPosting", "title": "A", "description": "x"}, {"@type": "JobPosting", "title": "B", "description": "y"}])
    assert problem("https://careers.example.com/all") == "several_jobs"


def test_redirect_to_private_address_refused(web):
    web.pages["https://short.example/x"] = httpx.Response(302, headers={"Location": "https://internal.example/x"})
    assert problem("https://short.example/x") == "bad_link"
    assert not any("internal.example" in url for url in web.seen)


def test_redirect_to_login_page_has_no_job_data(web):
    web.pages["https://careers.example.com/9"] = httpx.Response(302, headers={"Location": "https://login.example.com/"})
    web.pages["https://login.example.com/"] = httpx.Response(200, text="<form>Sign in</form>")
    assert problem("https://careers.example.com/9") == "no_job_data"


def test_too_many_redirects(web):
    web.pages["https://loop.example/a"] = httpx.Response(302, headers={"Location": "https://loop.example/a"})
    assert problem("https://loop.example/a") == "site_unreachable"


@pytest.mark.parametrize("status,code", [(401, "needs_login"), (403, "needs_login"), (404, "not_found"),
                                         (410, "not_found"), (500, "site_unreachable")])
def test_http_errors(web, status, code):
    web.pages["https://careers.example.com/1"] = httpx.Response(status)
    assert problem("https://careers.example.com/1") == code


def test_timeout(web):
    web.pages["https://careers.example.com/slow"] = httpx.ReadTimeout("slow")
    assert problem("https://careers.example.com/slow") == "site_unreachable"


def test_too_large(web):
    web.pages["https://careers.example.com/big"] = httpx.Response(200, content=b"x" * (2 * 1024 * 1024 + 1))
    assert problem("https://careers.example.com/big") == "too_large"


def test_public_check_runs_on_the_first_link(web):
    assert problem("https://internal.example/job") == "bad_link"
    assert web.seen == []
