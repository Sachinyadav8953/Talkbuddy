import os
import subprocess
import logging
import tempfile
import uuid
from app.config import settings
from app.services.downloader import get_piper_executable_path

logger = logging.getLogger("talkbuddy.tts")

class TextToSpeechService:
    def __init__(self):
        self.piper_path = None
        self.model_path = None

    def initialize(self):
        if not self.piper_path or not self.model_path:
            self.piper_path = get_piper_executable_path()
            self.model_path = os.path.join(settings.MODELS_DIR, f"{settings.PIPER_VOICE}.onnx")
            
            # Double check paths
            if not self.piper_path or not os.path.exists(self.piper_path):
                logger.error("Piper binary is not found. Please run the bootstrapper first.")
                self.piper_path = None
            if not os.path.exists(self.model_path):
                logger.error(f"Voice model ONNX is not found at {self.model_path}. Please run bootstrapper.")
                self.model_path = None

    def generate_speech(self, text: str) -> bytes:
        """
        Synthesizes text to speech WAV audio bytes using the Piper binary.
        Uses a temporary file to guarantee stability and prevent deadlock.
        """
        self.initialize()
        
        if not self.piper_path or not self.model_path:
            logger.error("TTS Service is not fully initialized. Piper or model path is missing.")
            return b""

        # Ensure temp audio directory exists
        os.makedirs(settings.TEMP_AUDIO_DIR, exist_ok=True)
        temp_file_name = f"tts_{uuid.uuid4().hex}.wav"
        temp_wav_path = os.path.join(settings.TEMP_AUDIO_DIR, temp_file_name)

        logger.info(f"Synthesizing speech for text: '{text[:40]}...' to temp WAV: {temp_wav_path}")
        
        try:
            # Build CLI command
            # Command pattern: piper --model <model> --output_file <output_wav>
            # Text is piped in through stdin
            cmd = [
                self.piper_path,
                "--model", self.model_path,
                "--output_file", temp_wav_path
            ]
            
            # Run the process
            # On Windows, we can use startupinfo to prevent spawning a command window popup
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                text=True,
                encoding='utf-8'
            )
            
            # Communication sends the text to stdin and closes it, waiting for completion
            stdout, stderr = process.communicate(input=text)
            
            if process.returncode != 0:
                logger.error(f"Piper execution failed (code {process.returncode}): {stderr}")
                return b""
                
            # Read the generated wav file bytes
            if os.path.exists(temp_wav_path):
                with open(temp_wav_path, "rb") as wav_file:
                    audio_bytes = wav_file.read()
                
                # Delete the temporary file
                os.remove(temp_wav_path)
                logger.info(f"Speech synthesis successful. Generated {len(audio_bytes)} bytes of WAV audio.")
                return audio_bytes
            else:
                logger.error("Piper succeeded but output file was not found.")
                return b""
                
        except Exception as e:
            logger.error(f"Error during speech synthesis: {str(e)}")
            if os.path.exists(temp_wav_path):
                try:
                    os.remove(temp_wav_path)
                except Exception:
                    pass
            return b""

# Single instance to be shared across the application
tts_service = TextToSpeechService()
