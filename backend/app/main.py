import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router, root_router
from app.core.config import get_settings
from app.schemas.common import ApiErrorDetail, ApiErrorResponse
from app.services.database import database_service
from app.services.groq_service import GroqConfigurationError, GroqServiceError
from app.services.storage_service import StorageValidationError
from app.services.video_service import VideoProcessingError
from app.services.face_detector import FaceDetectorError

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bollyswap.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager: connects to MongoDB and initializes storage."""
    settings = get_settings()
    logger.info("Starting %s v%s in %s mode", settings.APP_NAME, settings.APP_VERSION, settings.APP_ENV)
    logger.info("API Docs: /docs | ReDoc: /redoc | API Prefix: %s", settings.API_PREFIX)
    logger.info("Storage Dir: %s", settings.resolved_storage_dir)

    # Connect to MongoDB Atlas
    await database_service.connect(settings.MONGODB_URI, settings.DATABASE_NAME)
    logger.info("MongoDB Status: %s (Connected: %s)", database_service.status, database_service.is_connected)

    yield

    # Shutdown
    logger.info("Shutting down %s", settings.APP_NAME)
    await database_service.disconnect()


def create_app() -> FastAPI:
    """Application factory for BollySwap AI FastAPI Backend."""
    settings = get_settings()

    is_docs_enabled = settings.DEBUG or settings.APP_ENV != "production"

    app = FastAPI(
        title=f"{settings.APP_NAME} - Studio Backend",
        version=settings.APP_VERSION,
        description="Studio-grade AI face-swapping backend foundation with MongoDB Atlas, real file storage, and job management.",
        docs_url="/docs" if is_docs_enabled else None,
        redoc_url="/redoc" if is_docs_enabled else None,
        openapi_url="/openapi.json" if is_docs_enabled else None,
        lifespan=lifespan,
    )

    # Configure CORS
    cors_origins = settings.CORS_ORIGINS
    if isinstance(cors_origins, str):
        cors_origins = [cors_origins]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------
    # Exception Handlers
    # ---------------------------------------------------------

    @app.exception_handler(StorageValidationError)
    async def storage_validation_error_handler(_: Request, exc: StorageValidationError) -> JSONResponse:
        status_code = (
            status.HTTP_413_CONTENT_TOO_LARGE
            if exc.error_code == "FILE_TOO_LARGE"
            else status.HTTP_400_BAD_REQUEST
        )
        error_payload = ApiErrorResponse(
            success=False,
            error=ApiErrorDetail(
                error_code=exc.error_code,
                message=exc.message,
            ),
        )
        return JSONResponse(
            status_code=status_code,
            content=error_payload.model_dump(mode="json"),
        )

    @app.exception_handler(GroqConfigurationError)
    async def groq_configuration_error_handler(_: Request, exc: GroqConfigurationError) -> JSONResponse:
        error_payload = ApiErrorResponse(
            success=False,
            error=ApiErrorDetail(
                error_code="GROQ_NOT_CONFIGURED",
                message=exc.message,
            ),
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_payload.model_dump(mode="json"),
        )

    @app.exception_handler(GroqServiceError)
    async def groq_service_error_handler(_: Request, exc: GroqServiceError) -> JSONResponse:
        error_payload = ApiErrorResponse(
            success=False,
            error=ApiErrorDetail(
                error_code=exc.error_code,
                message=exc.message,
            ),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload.model_dump(mode="json"),
        )

    @app.exception_handler(VideoProcessingError)
    async def video_processing_error_handler(_: Request, exc: VideoProcessingError) -> JSONResponse:
        error_payload = ApiErrorResponse(
            success=False,
            error=ApiErrorDetail(
                error_code=exc.error_code,
                message=exc.message,
            ),
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_payload.model_dump(mode="json"),
        )

    @app.exception_handler(FaceDetectorError)
    async def face_detector_error_handler(_: Request, exc: FaceDetectorError) -> JSONResponse:
        error_payload = ApiErrorResponse(
            success=False,
            error=ApiErrorDetail(
                error_code=exc.error_code,
                message=exc.message,
            ),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_payload.model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        error_payload = ApiErrorResponse(
            success=False,
            error=ApiErrorDetail(
                error_code="VALIDATION_ERROR",
                message="Request payload validation failed.",
                details={"errors": exc.errors()},
            ),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_payload.model_dump(mode="json"),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        error_payload = ApiErrorResponse(
            success=False,
            error=ApiErrorDetail(
                error_code=f"HTTP_{exc.status_code}",
                message=str(exc.detail),
            ),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload.model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server exception: %s", type(exc).__name__)
        error_payload = ApiErrorResponse(
            success=False,
            error=ApiErrorDetail(
                error_code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal server error occurred.",
            ),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_payload.model_dump(mode="json"),
        )

    # Route Mounts
    app.include_router(root_router)
    app.include_router(api_router, prefix=settings.API_PREFIX)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    cfg = get_settings()
    uvicorn.run(
        "app.main:app",
        host=cfg.HOST,
        port=cfg.PORT,
        reload=cfg.DEBUG,
    )
