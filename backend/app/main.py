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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager — replaces deprecated @app.on_event('startup')."""
    # --- Startup ---
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    # Create temp audio folder if missing
    os.makedirs(settings.TEMP_AUDIO_DIR, exist_ok=True)

    # Download Piper + voice model binaries
    try:
        bootstrap_assets()
        logger.info("All startup requirements validated successfully.")
    except Exception as e:
        logger.error(f"Startup bootstrap failed: {str(e)}")
        # Allow application to run so it returns meaningful error messages

    # Pre-load Whisper model at startup to avoid first-request latency
    try:
        stt_service.load_model()
    except Exception as e:
        logger.error(f"Whisper model pre-load failed: {str(e)}")

    logger.info("Application startup complete.")
    yield  # Application runs here

    # --- Shutdown ---
    logger.info("Application shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS middleware configuration
# allow_origins=["*"] is invalid when allow_credentials=True per the CORS spec.
# Set ALLOWED_ORIGINS env var to a comma-separated list of allowed frontend URLs.
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register HTTP routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(sessions.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)

# Register WebSocket router
app.include_router(websocket_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {"message": "Welcome to TalkBuddy AI English Speaking Coach API"}
