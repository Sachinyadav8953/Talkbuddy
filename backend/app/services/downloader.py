import os
import platform
import shutil
import urllib.request
import zipfile
import tarfile
import logging
from app.config import settings

logger = logging.getLogger("talkbuddy.downloader")
logging.basicConfig(level=logging.INFO)

def download_file(url: str, dest_path: str):
    logger.info(f"Downloading {url} -> {dest_path}")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    # Custom User-Agent to avoid issues with some servers
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    logger.info(f"Download complete: {dest_path}")

def get_piper_executable_path() -> str:
    system = platform.system().lower()
    bin_name = "piper.exe" if system == "windows" else "piper"
    
    # Check if piper binary is in PIPER_BIN_DIR/piper/
    target_path = os.path.join(settings.PIPER_BIN_DIR, "piper", bin_name)
    if os.path.exists(target_path):
        return target_path
        
    # Check if piper binary is directly in PIPER_BIN_DIR/
    target_path_direct = os.path.join(settings.PIPER_BIN_DIR, bin_name)
    if os.path.exists(target_path_direct):
        return target_path_direct
        
    return ""

def setup_piper():
    system = platform.system().lower()
    exec_path = get_piper_executable_path()
    
    if exec_path:
        logger.info(f"Piper binary found at {exec_path}")
        return exec_path

    logger.info("Piper binary not found. Initiating platform-aware download...")
    
    # Determine URL based on platform
    if system == "windows":
        url = "https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_windows_amd64.zip"
        archive_name = "piper.zip"
    elif system == "linux":
        url = "https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz"
        archive_name = "piper.tar.gz"
    elif system == "darwin":
        # macOS
        url = "https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_macos_x64.tar.gz"
        archive_name = "piper.tar.gz"
    else:
        raise OSError(f"Unsupported operating system: {system}")

    archive_path = os.path.join(settings.PIPER_BIN_DIR, archive_name)
    
    try:
        download_file(url, archive_path)
        
        logger.info(f"Extracting {archive_name}...")
        if archive_name.endswith(".zip"):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(settings.PIPER_BIN_DIR)
        else:
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                tar_ref.extractall(settings.PIPER_BIN_DIR)
                
        # Remove archive after extraction
        os.remove(archive_path)
        logger.info("Extraction complete. Archive cleaned up.")
        
        # Verify and return binary path
        exec_path = get_piper_executable_path()
        if not exec_path:
            raise FileNotFoundError("Piper executable not found after extraction.")
            
        # On Linux/macOS, ensure binary has execution permission
        if system != "windows":
            os.chmod(exec_path, 0o755)
            
        logger.info(f"Piper successfully configured at: {exec_path}")
        return exec_path
        
    except Exception as e:
        logger.error(f"Failed to setup Piper: {str(e)}")
        if os.path.exists(archive_path):
            os.remove(archive_path)
        raise e

def setup_voice_model():
    model_name = f"{settings.PIPER_VOICE}.onnx"
    config_name = f"{settings.PIPER_VOICE}.onnx.json"
    
    model_path = os.path.join(settings.MODELS_DIR, model_name)
    config_path = os.path.join(settings.MODELS_DIR, config_name)
    
    # Download ONNX Model
    if not os.path.exists(model_path):
        logger.info(f"ONNX Model not found. Downloading voice {settings.PIPER_VOICE}...")
        url = f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
        download_file(url, model_path)
    else:
        logger.info(f"ONNX voice model found: {model_path}")
        
    # Download Config JSON
    if not os.path.exists(config_path):
        logger.info(f"Config JSON not found. Downloading voice config...")
        url = f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
        download_file(url, config_path)
    else:
        logger.info(f"ONNX voice config found: {config_path}")
        
    return model_path, config_path

def bootstrap_assets():
    logger.info("Bootstrapping TalkBuddy assets...")
    piper_path = setup_piper()
    model_path, config_path = setup_voice_model()
    logger.info("Bootstrapping complete! Piper TTS and models are ready.")
    return {
        "piper_path": piper_path,
        "model_path": model_path,
        "config_path": config_path
    }

if __name__ == "__main__":
    bootstrap_assets()
