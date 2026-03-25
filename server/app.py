"""FastAPI web API for DSN extraction."""

from __future__ import annotations

import pathlib

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

from dsn_extractor.extractors import extract
from dsn_extractor.parser import parse

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

STATIC_DIR = pathlib.Path(__file__).resolve().parent / "static"

app = FastAPI(title="DSN Reader")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error(status: int, detail: str, warnings: list[str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"detail": detail, "warnings": warnings or []},
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@app.post("/api/extract")
async def api_extract(file: UploadFile) -> JSONResponse:
    # 1. Extension check
    filename = file.filename or ""
    if not filename.lower().endswith(".dsn"):
        return _error(422, "Invalid file extension: expected .dsn")

    # 2. Read bytes and enforce size limit
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        return _error(413, "File too large: maximum 10 MB")

    # 3. Decode text (try UTF-8, fall back to Latin-1)
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    # 4. Parse
    parsed = parse(text)

    if len(parsed.all_records) == 0:
        return _error(400, "File contains no valid DSN lines", parsed.warnings)

    # 5. Extract
    try:
        result = extract(parsed, source_file=filename)
    except Exception as exc:
        return _error(500, f"Extraction failed: {exc}", parsed.warnings)

    return JSONResponse(result.model_dump(mode="json"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
