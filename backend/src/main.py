import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from src.core.config import settings
from src.core.database import init_db
from src.api.routes.routes import (
    classify_router,
    extract_router,
    documents_router,
    batch_router,
    export_router,
    stats_router,
    health_router,
    templates_router,
)
from src.api.routes.upload import router as upload_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup + shutdown lifecycle."""

    logger.info("Starting AI Document Processor...")

    # Validate required environment variables
    if not settings.secret_key:
        raise RuntimeError("SECRET_KEY is required")

    if settings.app_env.lower() == "production" and not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY required in production")

    # Ensure upload path exists
    settings.upload_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Upload directory: {settings.upload_path.resolve()}")

    # Initialize database
    await init_db()

    logger.info("Database initialized successfully")

    yield

    logger.info("Shutting down AI Document Processor...")


app = FastAPI(
    title="AI Document Processing & OCR Pipeline",
    description=(
        "Production-grade intelligent document extraction platform "
        "powered by Groq Vision + EasyOCR + FastAPI"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={
        "name": "AI Document Processor",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
    },
)


app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # tighten in production
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    try:
        response = await call_next(request)

    except Exception as e:
        logger.error(
            f"Unhandled error during request {request.method} {request.url.path}: {e}",
            exc_info=True,
        )
        raise

    process_time = round(time.time() - start_time, 4)

    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"

    logger.info(
        f"{request.method} {request.url.path} "
        f"Status={response.status_code} "
        f"Time={process_time}s"
    )

    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error: {exc}")

    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Validation failed",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Global exception: {exc}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
        },
    )


app.mount(
    "/uploads",
    StaticFiles(directory=str(settings.upload_path)),
    name="uploads",
)


app.include_router(upload_router)
app.include_router(classify_router)
app.include_router(extract_router)
app.include_router(documents_router)
app.include_router(batch_router)
app.include_router(export_router)
app.include_router(stats_router)
app.include_router(health_router)
app.include_router(templates_router)


@app.get("/")
async def root():
    return {
        "name": "AI Document Processing & OCR Pipeline",
        "version": "1.0.0",
        "environment": settings.app_env,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/health",
        "upload_path": str(settings.upload_path),
        "status": "running",
    }

