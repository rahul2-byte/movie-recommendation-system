"""FastAPI and Lambda entrypoint for the bundle-backed recommendation API."""

from dotenv import load_dotenv

load_dotenv()

from api.v1.catalog import router as catalog_router
from api.v1.movies import router as movies_router
from api.v1.recommend import router as recommend_router
from application.lifecycle import get_pipeline
from configuration.settings import settings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from observability.logging import get_logger
from starlette.exceptions import HTTPException as StarletteHTTPException

log = get_logger(__name__)

app = FastAPI(title="Movie Platform API")

# Mangum handler for AWS Lambda
handler = Mangum(app)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Return a stable JSON envelope for expected HTTP failures."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Log unexpected failures without exposing internal details to clients."""
    log.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/ping")
def ping():
    """Provide the lightweight health endpoint used by deployment probes."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.on_event("startup")
def startup():
    """Load the configured recommendation pipeline before serving requests."""
    if str(settings.MODEL_BUNDLE_DIR).strip():
        get_pipeline()


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(movies_router, prefix="/api/v1")
app.include_router(recommend_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
