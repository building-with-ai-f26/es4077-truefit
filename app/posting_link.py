"""A job posting from a link, so students can paste the link instead of the text.

Greenhouse, Lever, Ashby, and Workday are read through their public job data; any other page only through
the JobPosting data career sites add for Google search, so menus, banners, and other jobs never get in.
LinkedIn, Indeed, and school job boards need a login and are answered without fetching. Nothing here is
stored or logged.
"""

import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urlsplit

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
    if host.endswith(".myworkdayjobs.com") and "job" in path:
        job = path.index("job")
        if job >= 1:  # the career site name sits just before "job" (after an optional locale like en-US)
            return "workday", {"host": host, "tenant": host.split(".")[0], "site": path[job - 1],
                               "path": "/".join(path[job:])}
    return "page", {}


class _TextParser(HTMLParser):
    BLOCKS = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "ul", "ol", "li"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = [""]

    def _new_line(self):
        if self.lines[-1].strip():
            self.lines.append("")

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCKS:
            self._new_line()
        if tag == "li":
            self.lines[-1] = "- "

    def handle_endtag(self, tag):
        if tag in self.BLOCKS:
            self._new_line()

    def handle_data(self, data):
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

