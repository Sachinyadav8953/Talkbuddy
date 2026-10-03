import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import auth, sessions, dashboard
from app.websocket import router as websocket_router
from app.services.downloader import bootstrap_assets
from app.services.stt_service import stt_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("talkbuddy.main")


import asyncio

async def background_asset_warmup():
    """Background task to download and cache models without blocking port binding."""
    loop = asyncio.get_running_loop()
    try:
        logger.info("Background task: Checking and downloading Piper TTS assets...")
        await loop.run_in_executor(None, bootstrap_assets)
        logger.info("Piper TTS assets are ready.")
    except Exception as e:
        logger.error(f"Startup bootstrap failed: {str(e)}")

    try:
        logger.info("Background task: Pre-loading Whisper STT model...")
        await loop.run_in_executor(None, stt_service.load_model)
        logger.info("Whisper model pre-load complete.")
    except Exception as e:
        logger.error(f"Whisper model pre-load failed: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager — replaces deprecated @app.on_event('startup')."""
    # --- Startup ---
    logger.info("Initializing database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

    # Create temp audio folder if missing
    os.makedirs(settings.TEMP_AUDIO_DIR, exist_ok=True)

    # Schedule heavy model downloads as a non-blocking background task
    # This allows FastAPI to bind to the port immediately so Render health checks succeed!
    asyncio.create_task(background_asset_warmup())

    logger.info("Application startup complete. Ready and listening for incoming connections.")
    yield  # Application runs here

    # --- Shutdown ---
    logger.info("Application shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS middleware configuration
raw_origins = os.getenv("ALLOWED_ORIGINS", "*").strip()
# Clean list of origins
parsed_origins = [o.strip().rstrip("/") for o in raw_origins.split(",") if o.strip()]

# If ALLOWED_ORIGINS is '*' or unset, allow all web origins with allow_origin_regex
if not parsed_origins or "*" in parsed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Always include localhost defaults along with user-specified origins
    default_dev_origins = [
        "http://localhost:5173", "http://localhost:3000",
        "http://127.0.0.1:5173", "http://127.0.0.1:3000"
    ]
    all_allowed = list(set(parsed_origins + default_dev_origins))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=all_allowed,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Register HTTP routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(sessions.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)

# Register WebSocket router
app.include_router(websocket_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Welcome to TalkBuddy AI English Speaking Coach API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


