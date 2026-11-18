"""A job posting from a link, so students can paste the link instead of the text.

Greenhouse, Lever, Ashby, and Workday are read through their public job data; any other page only through
the JobPosting data career sites add for Google search, so menus, banners, and other jobs never get in.
LinkedIn, Indeed, and school job boards need a login and are answered without fetching. Nothing here is
stored or logged.
"""

import asyncio
import html
import ipaddress
import json
import logging
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

MESSAGES = {
    "blocked_site": "TrueFit can't open LinkedIn, Indeed, or school job boards like 12twenty. "
                    "Open the posting, click Apply, and paste that link, or paste the posting text.",
    "bad_link": "TrueFit can only open web links (https://…). Paste the posting text.",
    "needs_login": "This page needs a login, so TrueFit can't read it. Paste the posting text.",
    "not_found": "This posting wasn't found. It may have closed. Check the link, or paste the posting text.",
    "no_job_data": "TrueFit couldn't find the job details on this page. Paste the posting text.",
    "several_jobs": "This page lists more than one job. Open the one you want, or paste the posting text.",
    "too_large": "This page is too large to read. Paste the posting text.",
    "site_unreachable": "The job site didn't respond. Try again, or paste the posting text.",
}
BLOCKED_DOMAINS = ("linkedin.com", "indeed.com", "glassdoor.com", "joinhandshake.com", "12twenty.com")
MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 10
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TrueFit job posting reader)", "Accept": "text/html,application/json"}
_LD_JSON = re.compile(r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", re.I | re.S)

_transport: httpx.AsyncBaseTransport | None = None  # tests swap in a fake transport
# httpx and httpcore log every address they request; posting links must never reach the log.
for _name in ("httpx", "httpcore"):
    logging.getLogger(_name).setLevel(logging.WARNING)


class LinkProblem(Exception):
    """A link TrueFit can't read, with the plain-language next step."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
        self.message = MESSAGES[code]


def site_kind(url: str) -> tuple[str, dict]:
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if parts.scheme not in ("http", "https") or not host:
        raise LinkProblem("bad_link")
    if any(host == d or host.endswith("." + d) for d in BLOCKED_DOMAINS):
        raise LinkProblem("blocked_site")
    path = [p for p in parts.path.split("/") if p]
    if host in ("boards.greenhouse.io", "job-boards.greenhouse.io") and len(path) >= 3 and path[1] == "jobs":
        return "greenhouse", {"board": path[0], "job_id": path[2]}
    if host == "jobs.lever.co" and len(path) >= 2:
        return "lever", {"company": path[0], "posting_id": path[1]}
    if host == "jobs.ashbyhq.com" and len(path) >= 2:
        return "ashby", {"org": path[0], "job_id": path[1]}
    if host.endswith(".myworkdayjobs.com") and ("job" in path or "details" in path):
        job = path.index("job") if "job" in path else path.index("details")
        if job >= 1:  # the career site name sits just before "job" (after an optional locale like en-US)
            # Search results link to details/{title}_{id}; Workday's data for it is at job/{title}_{id}.
            job_path = ["job"] + path[job + 1:]
            if "apply" in job_path:  # the Apply page's link still names the job before "/apply"
                job_path = job_path[:job_path.index("apply")]
            return "workday", {"host": host, "tenant": host.split(".")[0], "site": path[job - 1],
                               "path": "/".join(job_path)}
    return "page", {}


class _TextParser(HTMLParser):
    BLOCKS = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "ul", "ol", "li"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = [""]
        self.skipping = 0  # inside <script> or <style>, whose contents are code, not posting text

    def _new_line(self):
        if self.lines[-1].strip():
            self.lines.append("")

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skipping += 1
        if tag in ("td", "th") and self.lines[-1].strip():
            self.lines[-1] += " "  # table cells on one row stay apart ("Base $100k")
        if tag in self.BLOCKS:
            self._new_line()
        if tag == "li":
            self.lines[-1] = "- "

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skipping = max(0, self.skipping - 1)
        if tag in self.BLOCKS:
            self._new_line()

    def handle_data(self, data):
        if self.skipping:
            return
        self.lines[-1] += re.sub(r"\s+", " ", data.replace("\xa0", " "))


def html_to_text(markup: str) -> str:
    parser = _TextParser()
    parser.feed(markup)
    parser.close()
    lines = [re.sub(r" {2,}", " ", line).strip() for line in parser.lines]
    return "\n".join(line for line in lines if line and line != "-")


def posting_text(title: str, company: str | None, location: str | None, description_html: str,
                 extras: list[str]) -> str:
    where = " · ".join(part.strip() for part in (company, location) if part and part.strip())
    head = [title.strip()] + ([where] if where else []) + extras
    return "\n".join(head) + "\n\n" + html_to_text(description_html)


def is_public_address(host: str) -> bool:
    """False for this computer, private networks, cloud metadata addresses, and hosts that don't resolve."""
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except (socket.gaierror, UnicodeError):
        return False
    return bool(addresses) and all(ipaddress.ip_address(a.split("%")[0]).is_global for a in addresses)


_public = is_public_address  # tests swap this so no real address lookups happen


async def read_posting_link(url: str) -> dict:
    url = url.strip()
    kind, ids = site_kind(url)
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, transport=_transport, headers=HEADERS) as client:
        if kind == "greenhouse":
            job = _json(await _get(client, f"https://boards-api.greenhouse.io/v1/boards/{ids['board']}/jobs/{ids['job_id']}"))
            text = posting_text(job.get("title", ""), job.get("company_name"), (job.get("location") or {}).get("name"),
                                html.unescape(job.get("content", "")), [])  # Greenhouse escapes its HTML once
        elif kind == "lever":
            job = _json(await _get(client, f"https://api.lever.co/v0/postings/{ids['company']}/{ids['posting_id']}"))
            categories = job.get("categories") or {}
            lists = "".join(f"<h3>{item.get('text', '')}</h3><ul>{item.get('content', '')}</ul>" for item in job.get("lists") or [])
            text = posting_text(job.get("text", ""), None, categories.get("location"),
                                job.get("description", "") + lists + job.get("additional", ""),
                                _extras(None, categories.get("commitment")))
        elif kind == "ashby":  # Ashby's public data is the whole board at once (3 MB at Ramp); its job page is smaller
            text = _job_data_text(await _get(client, f"https://jobs.ashbyhq.com/{ids['org']}/{ids['job_id']}"))
        elif kind == "workday":
            info = _json(await _get(client, f"https://{ids['host']}/wday/cxs/{ids['tenant']}/{ids['site']}/{ids['path']}"))
            job = info.get("jobPostingInfo") or {}
            # Workday's "startDate" is the day the job was posted, not when it starts, so it's never used.
            text = posting_text(job.get("title", ""), None, _place(job.get("location")), job.get("jobDescription", ""),
                                _extras(None, job.get("timeType")))
        else:
            text = _job_data_text(await _get(client, url))
    if not text.strip() or not html_to_text(text.split("\n\n", 1)[-1]).strip():
        raise LinkProblem("no_job_data")
    lines = len([line for line in text.splitlines() if line.strip()])
    return {"text": text, "lines": lines, "site": "job data" if kind == "page" else kind, "host": urlsplit(url).hostname}


async def _get(client: httpx.AsyncClient, url: str) -> str:
    """The body of a page, following up to 5 redirects by hand so every address is checked first."""
    try:
        for _ in range(MAX_REDIRECTS + 1):
            parts = urlsplit(url)
            if parts.scheme not in ("http", "https") or not parts.hostname:
                raise LinkProblem("bad_link")
            if not await asyncio.to_thread(_public, parts.hostname):
                raise LinkProblem("bad_link")
            async with client.stream("GET", url) as response:
                if response.is_redirect and "location" in response.headers:
                    url = urljoin(url, response.headers["location"])
                    continue
                if response.status_code in (401, 403):
                    raise LinkProblem("needs_login")
                if response.status_code in (404, 410):
                    raise LinkProblem("not_found")
                if response.status_code >= 300:
                    raise LinkProblem("site_unreachable")
                if int(response.headers.get("content-length") or 0) > MAX_BYTES:
                    raise LinkProblem("too_large")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body += chunk
                    if len(body) > MAX_BYTES:
                        raise LinkProblem("too_large")
                return body.decode(response.encoding or "utf-8", errors="replace")
    except httpx.HTTPError as exc:
        raise LinkProblem("site_unreachable") from exc
    raise LinkProblem("site_unreachable")  # redirected too many times


def _json(body: str) -> dict:
    try:
        data = json.loads(body)
    except ValueError as exc:
        raise LinkProblem("no_job_data") from exc
    if not isinstance(data, dict):
        raise LinkProblem("no_job_data")
    return data


def _job_data_text(page: str) -> str:
    """The page's one JobPosting (the data career sites add for Google search), and nothing else from the page."""
    jobs = []
    for block in _LD_JSON.findall(page):
        try:
            jobs += _job_postings(json.loads(block.strip(), strict=False))
        except ValueError:
            continue
    # The same job repeated counts once; two jobs that only share a title (London and New York) don't.
    distinct = {tuple(str(job.get(k, "")).strip() for k in ("title", "url", "description")) for job in jobs}
    if not jobs:
        raise LinkProblem("no_job_data")
    if len(distinct) > 1:
        raise LinkProblem("several_jobs")
    job = jobs[0]
    company = job.get("hiringOrganization")
    company = company.get("name") if isinstance(company, dict) else company
    description = str(job.get("description", ""))
    if "<" not in description and "&lt;" in description:
        description = html.unescape(description)  # some sites escape the HTML inside the data
    return posting_text(str(job.get("title", "")), company if isinstance(company, str) else None,
                        _job_location(job.get("jobLocation")), description,
                        _extras(_start_date(job), job.get("employmentType")))


def _start_date(job: dict):
    """jobStartDate, unless it's on or before the day the job was posted: some sites fill it with that day."""
    start, posted = job.get("jobStartDate"), job.get("datePosted")
    if isinstance(start, str) and isinstance(posted, str) and start[:10] <= posted[:10]:
        return None
    return start


def _job_postings(data) -> list[dict]:
    if isinstance(data, list):
        return [job for item in data for job in _job_postings(item)]
    if not isinstance(data, dict):
        return []
    if "@graph" in data:
        return _job_postings(data["@graph"])
    kinds = data.get("@type")
    kinds = kinds if isinstance(kinds, list) else [kinds]
    return [data] if "JobPosting" in kinds else []


def _job_location(location) -> str | None:
    """Every place the job lists (a job in Seattle and New York is not just a Seattle job), each once."""
    places = []
    for item in location if isinstance(location, list) else [location]:
        address = item.get("address") if isinstance(item, dict) else item
        if isinstance(address, dict):
            address = ", ".join(str(address[k]) for k in ("addressLocality", "addressRegion") if address.get(k))
        if isinstance(address, str) and address.strip() and address.strip() not in places:
            places.append(address.strip())
    return "; ".join(places) or None


def _place(location) -> str | None:
    if isinstance(location, dict):
        return location.get("name") or location.get("descriptor")
    return location if isinstance(location, str) else None


def _extras(start_date, employment_type) -> list[str]:
    """Only what the site gives as its own field; nothing is worked out from the text."""
    extras = [f"Start date: {start_date}"] if isinstance(start_date, str) and start_date.strip() else []
    if isinstance(employment_type, list):
        employment_type = ", ".join(str(t) for t in employment_type if t)
    if isinstance(employment_type, str) and employment_type.strip():
        extras.append(f"Employment type: {employment_type.strip()}")
    return extras
