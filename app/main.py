"""TrueFit web app: serves the page and the JSON API."""

import atexit
import html
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel
from posthog import Posthog
from posthog.integrations.asgi import PosthogASGIMiddleware

from app import config, rate_limit, start_date, tailor
from app.docx_resume import build_docx, file_name, resume_blocks
from app.docx_text import NotDocx, read_docx_text, unpacks_too_large
from app.errors import ApiError, ConfigError, ModelAccountProblem, ModelUnavailable
from app.pdf_resume import build_pdf
from app.posting_link import LinkProblem, read_posting_link
from app.resume_lines import split_lines

STATIC_DIR = Path(__file__).resolve().parent / "static"

logger = logging.getLogger("truefit")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def create_posthog_client() -> Posthog | None:
    """Create the process-wide PostHog client when its optional config is present."""
    config._load_env_file()
    token = os.environ.get("POSTHOG_PROJECT_TOKEN")
    host = os.environ.get("POSTHOG_HOST")
    missing = [
        name
        for name, value in (("POSTHOG_PROJECT_TOKEN", token), ("POSTHOG_HOST", host))
        if not value
    ]
    if missing:
        if os.environ.get("ENVIRONMENT") != "production":
            for name in missing:
                logger.warning(
                    "%s variable required by PostHog is missing or un-configured, this causes events to be silently missed. "
                    "This error stops appearing once %s is configured",
                    name,
                    name,
                )
        return None

    return Posthog(project_api_key=token, host=host, enable_exception_autocapture=True)


posthog_client = create_posthog_client()
if posthog_client is not None:
    atexit.register(posthog_client.shutdown)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    missing = config.missing_settings()
    if missing:
        logger.warning("Missing %s in .env; model calls will fail until set.", ", ".join(missing))
    yield
    if posthog_client is not None:
        try:
            posthog_client.flush()
        except Exception:
            logger.warning("PostHog flush failed during shutdown", exc_info=True)


# No /docs, /redoc, or /openapi.json: they'd list every route for anyone, and the page doesn't use them.
app = FastAPI(title="TrueFit", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
if posthog_client is not None:
    app.add_middleware(PosthogASGIMiddleware, client=posthog_client)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def revalidate_static(request: Request, call_next):
    """Make browsers check for a newer app.js/styles.css on every load instead of reusing a stale copy."""
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


MAX_REQUEST_BYTES = 21 * 1024 * 1024  # the largest real request is a 20 MB Word file


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Refuse an oversized request from its declared size, before reading the body."""
    try:
        size = int(request.headers.get("content-length") or 0)
    except ValueError:
        size = 0
    if size > MAX_REQUEST_BYTES:
        return JSONResponse(status_code=413, content={"error": {"code": "request_too_large",
                                                                "message": "That's too large to send. Paste less text."}})
    return await call_next(request)


@app.middleware("http")
async def limit_requests(request: Request, call_next):
    """Refuse API calls over the per-visitor and site-wide limits before they reach a route (see app/rate_limit.py)."""
    who = rate_limit.visitor(request.headers.get("cf-connecting-ip"), request.headers.get("x-forwarded-for"),
                             request.client.host if request.client else None)
    refused = rate_limit.check(request.url.path, who)
    if refused:
        return JSONResponse(status_code=429, content={"error": {"code": refused, "message": rate_limit.MESSAGES[refused]}})
    return await call_next(request)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log route, status, and timing only. Request bodies hold resumes and are never logged."""
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000)
    model = os.environ.get("OPENROUTER_MODEL", "-") if request.url.path.startswith("/api/") else "-"
    logger.info("%s %s %s %dms model=%s", request.method, request.url.path, response.status_code, duration_ms, model)
    return response


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",  # browsers use the declared file type, never a guessed one
    "X-Frame-Options": "DENY",  # no other site can show TrueFit inside a frame (clickjacking)
    "Referrer-Policy": "strict-origin-when-cross-origin",  # other sites see only truefit's address, never a full path
}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Added last, so it wraps every response, including refusals from the limits above."""
    response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    return response


@app.exception_handler(ApiError)
async def handle_api_error(_request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}})


@app.exception_handler(ModelUnavailable)
async def handle_model_unavailable(_request: Request, _exc: ModelUnavailable):
    return JSONResponse(
        status_code=502,
        content={"error": {"code": "model_unavailable",
                           "message": "The AI service didn't respond in time. Please try again in a minute."}},
    )


@app.exception_handler(ModelAccountProblem)
async def handle_model_account_problem(_request: Request, exc: ModelAccountProblem):
    logger.error("OpenRouter: %s", exc.code)
    return JSONResponse(status_code=502, content={"error": {"code": exc.code, "message": exc.message}})


@app.exception_handler(ConfigError)
async def handle_config_error(_request: Request, exc: ConfigError):
    logger.error("%s", exc)  # names the missing variable only
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "not_configured",
                           "message": "TrueFit isn't set up yet: add your OpenRouter key and model to .env, then restart."}},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request: Request, _exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "invalid_request", "message": "Something was missing from the request. Please try again."}},
    )


def check_length(text: str, field: str, minimum: int, maximum: int) -> None:
    """Reject inputs outside the allowed size with a plain-language message (FR-018)."""
    length = len((text or "").strip())
    label = field.replace("_", " ")
    if length < minimum:
        raise ApiError(422, f"{field}_too_short", f"The {label} looks too short. Paste the full text.")
    if length > maximum:
        raise ApiError(422, f"{field}_too_long", f"The {label} is too long. Keep it under {maximum:,} characters.")


@app.get("/", include_in_schema=False)
async def index():
    """Serve the page with the PostHog token and host filled in (empty if unset)."""
    page = (STATIC_DIR / "index.html").read_text()
    for name in ("POSTHOG_PROJECT_TOKEN", "POSTHOG_HOST"):
        page = page.replace("{{" + name + "}}", html.escape(os.environ.get(name, ""), quote=True))
    return HTMLResponse(page)


class StartDateRequest(BaseModel):
    posting: str
    availability_text: str | None = None


@app.post("/api/start-date")
async def post_start_date(body: StartDateRequest):
    check_length(body.posting, "posting", 100, 20_000)
    result = await start_date.check_start_date(body.posting, body.availability_text)
    return result.to_dict()


class TailorRequest(BaseModel):
    posting: str
    master_resume: str
    background_notes: str | None = None


@app.post("/api/tailor")
async def post_tailor(body: TailorRequest):
    check_length(body.posting, "posting", 100, 20_000)
    check_length(body.master_resume, "master_resume", 200, 20_000)
    check_length(body.background_notes or "", "background_writing", 0, 50_000)
    return await tailor.tailor_resume(body.posting, body.master_resume, body.background_notes)


MAX_DOCX_BYTES = 20 * 1024 * 1024  # text-only resumes reach 5-20 MB when Word embeds fonts


@app.post("/api/read-docx")
async def post_read_docx(request: Request):
    """The text of a Word file the student chose instead of pasting. The file and text are never stored or logged."""
    data = await request.body()
    if len(data) > MAX_DOCX_BYTES:
        raise ApiError(413, "file_too_large", "This file is over 20 MB. In Word, turn off \"Embed fonts in the file\" "
                                              "(Word settings, Save) and save a copy, or paste the text.")
    if unpacks_too_large(data):
        raise ApiError(413, "file_too_large", "This file's text is too large to read. Paste the text instead.")
    try:
        text = read_docx_text(data)
    except NotDocx:
        raise ApiError(415, "not_docx", "TrueFit reads Word files (.docx). For a PDF, open it and paste the text.")
    lines = len([line for line in text.splitlines() if line.strip()])
    if not lines:
        raise ApiError(422, "docx_empty",
                       "TrueFit couldn't find any text in this file. Check it's the right file, or paste the text.")
    return {"text": text, "lines": lines}


class PostingLinkRequest(BaseModel):
    url: str


@app.post("/api/posting-link")
async def post_posting_link(body: PostingLinkRequest):
    """The text of a job posting the student linked to. The link and text are never stored or logged."""
    try:
        if len(body.url) > 2_000:
            raise LinkProblem("bad_link")
        return await read_posting_link(body.url)
    except LinkProblem as problem:
        raise ApiError(422, problem.code, problem.message)


DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class ResumeDocxRequest(BaseModel):
    master_resume: str
    background_notes: str | None = None
    sections: list  # the tailored sections as shown in the browser, with the student's edits


@app.post("/api/resume-docx")
async def post_resume_docx(body: ResumeDocxRequest):
    return _resume_file(body, "docx")


@app.post("/api/resume-pdf")
async def post_resume_pdf(body: ResumeDocxRequest):
    return _resume_file(body, "pdf")


def _resume_file(body: ResumeDocxRequest, kind: str) -> Response:
    """The kept bullets as a one-page Word or PDF file. Nothing is stored or logged."""
    check_length(body.master_resume, "master_resume", 200, 20_000)
    check_length(body.background_notes or "", "background_writing", 0, 50_000)
    lines = split_lines(body.master_resume, body.background_notes)
    if kind == "pdf":
        content, layout = build_pdf(resume_blocks(body.sections, lines))
        media_type = "application/pdf"
    else:
        content, layout = build_docx(body.sections, lines)
        media_type = DOCX_TYPE
    name = file_name({line.id: line for line in lines}).replace(".docx", f".{kind}")
    return Response(content, media_type=media_type, headers={
        "Content-Disposition": f'attachment; filename="{name}"',
        "X-Fits-One-Page": "true" if layout.fits_one_page else "false",
        "X-Remove-Bullets": str(layout.remove_bullets),
    })


class VerifyBulletRequest(BaseModel):
    bullet_text: str
    source_line_ids: list[str]
    header_line_ids: list[str] = []  # the role the bullet sits under
    posting: str
    master_resume: str
    background_notes: str | None = None


@app.post("/api/verify-bullet")
async def post_verify_bullet(body: VerifyBulletRequest):
    check_length(body.bullet_text, "bullet", 1, 600)
    check_length(body.posting, "posting", 100, 20_000)
    check_length(body.master_resume, "master_resume", 200, 20_000)
    check_length(body.background_notes or "", "background_writing", 0, 50_000)
    return await tailor.verify_bullet(body.bullet_text, body.source_line_ids, body.posting,
                                      body.master_resume, body.background_notes, body.header_line_ids)
