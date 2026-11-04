"""TrueFit web app: serves the page and the JSON API."""

import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

from app import config, start_date
from app.errors import ApiError, ConfigError, ModelAccountProblem, ModelUnavailable

STATIC_DIR = Path(__file__).resolve().parent / "static"

logger = logging.getLogger("truefit")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    missing = config.missing_settings()
    if missing:
        logger.warning("Missing %s in .env; model calls will fail until set.", ", ".join(missing))
    yield


app = FastAPI(title="TrueFit", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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
    return FileResponse(STATIC_DIR / "index.html")


class StartDateRequest(BaseModel):
    posting: str
    availability_text: str | None = None


@app.post("/api/start-date")
async def post_start_date(body: StartDateRequest):
    check_length(body.posting, "posting", 100, 20_000)
    result = await start_date.check_start_date(body.posting, body.availability_text)
    return result.to_dict()
