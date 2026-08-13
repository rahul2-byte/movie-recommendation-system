from dotenv import load_dotenv

load_dotenv()

from api.v1.catalog import router as catalog_router
from api.v1.movies import router as movies_router
from api.v1.recommend import router as recommend_router
from application.lifecycle import get_pipeline
from common.config import config
from common.logger import get_logger
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from logger.background.tasks import start_background_tasks
from mangum import Mangum
from starlette.exceptions import HTTPException as StarletteHTTPException

log = get_logger(__name__)

app = FastAPI(title="Movie Platform API")

# Mangum handler for AWS Lambda
handler = Mangum(app)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/ping")
def ping():
    return {"status": "ok", "environment": config.settings.ENVIRONMENT}


@app.on_event("startup")
def startup():
    if str(config.settings.MODEL_BUNDLE_DIR).strip():
        get_pipeline()
    # Only start essential lightweight background tasks
    # Heavy model/data loading is now LAZY (occurs on first request)
    start_background_tasks()


app.add_middleware(
    CORSMiddleware,
    allow_origins=config.settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(movies_router, prefix="/api/v1")
app.include_router(recommend_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
