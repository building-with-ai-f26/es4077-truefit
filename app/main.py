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
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel
from posthog import Posthog
from posthog.integrations.asgi import PosthogASGIMiddleware

from app import config, start_date, tailor
from app.errors import ApiError, ConfigError, ModelAccountProblem, ModelUnavailable

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


app = FastAPI(title="TrueFit", lifespan=lifespan)
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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log route, status, and timing only. Request bodies hold resumes and are never logged."""
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000)
    model = os.environ.get("OPENROUTER_MODEL", "-") if request.url.path.startswith("/api/") else "-"
    logger.info("%s %s %s %dms model=%s", request.method, request.url.path, response.status_code, duration_ms, model)
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
    check_length(body.background_notes or "", "background_notes", 0, 20_000)
    return await tailor.tailor_resume(body.posting, body.master_resume, body.background_notes)


class VerifyBulletRequest(BaseModel):
    bullet_text: str
    source_line_ids: list[str]
    posting: str
    master_resume: str
    background_notes: str | None = None


@app.post("/api/verify-bullet")
async def post_verify_bullet(body: VerifyBulletRequest):
    check_length(body.bullet_text, "bullet", 1, 600)
    check_length(body.posting, "posting", 100, 20_000)
    check_length(body.master_resume, "master_resume", 200, 20_000)
    check_length(body.background_notes or "", "background_notes", 0, 20_000)
    return await tailor.verify_bullet(body.bullet_text, body.source_line_ids, body.posting,
                                      body.master_resume, body.background_notes)
