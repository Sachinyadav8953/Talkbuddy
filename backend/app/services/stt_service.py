import os
import logging
import requests
from app.config import settings

logger = logging.getLogger("talkbuddy.stt")

class SpeechToTextService:
    def __init__(self):
        self.model = None

    def _transcribe_with_cloud_api(self, audio_path: str) -> str | None:
        """Transcribe using Groq or OpenAI Whisper API (lightning fast ~0.3s, zero RAM)."""
        api_key = settings.LLM_API_KEY
        if not api_key:
            return None

        # Determine endpoint and model
        if api_key.startswith("gsk_") or (settings.LLM_API_URL and "groq.com" in settings.LLM_API_URL):
            endpoint = "https://api.groq.com/openai/v1/audio/transcriptions"
            model_name = "whisper-large-v3-turbo"
        elif api_key.startswith("sk-"):
            endpoint = "https://api.openai.com/v1/audio/transcriptions"
            model_name = "whisper-1"
        else:
            return None

        logger.info(f"Transcribing audio with Cloud Whisper API ({model_name})...")
        try:
            filename = os.path.basename(audio_path)
            mime = "audio/webm" if filename.endswith(".webm") else "audio/wav"
            
            with open(audio_path, "rb") as f:
                files = {
                    "file": (filename, f, mime)
                }
                data = {
                    "model": model_name,
                    "response_format": "json"
                }
                headers = {
                    "Authorization": f"Bearer {api_key}"
                }
                response = requests.post(endpoint, headers=headers, files=files, data=data, timeout=30)
                
            if response.status_code == 200:
                result = response.json()
                text = result.get("text", "").strip()
                logger.info(f"Cloud transcription success: '{text}'")
                return text
            else:
                logger.warning(f"Cloud Whisper API returned {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Cloud Whisper API call failed: {e}")
            return None

    def load_model(self):
        """Lazy load local Whisper model as a backup when Cloud API is unavailable."""
        if self.model is None:
            logger.info(f"Loading local Whisper model '{settings.WHISPER_MODEL}' on '{settings.WHISPER_DEVICE}'...")
            try:
                from faster_whisper import WhisperModel
                self.model = WhisperModel(
                    settings.WHISPER_MODEL, 
                    device=settings.WHISPER_DEVICE, 
                    compute_type="int8"
                )
                logger.info("Local Whisper model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load local Whisper model: {str(e)}")
                raise e

    def transcribe(self, audio_path: str) -> str:
        # 1. Try Cloud Whisper API first if API key is available
        cloud_text = self._transcribe_with_cloud_api(audio_path)
        if cloud_text is not None:
            return cloud_text

        # 2. Fall back to local faster-whisper model
        logger.info(f"Falling back to local Whisper model for: {audio_path}")
        try:
            self.load_model()
            segments, info = self.model.transcribe(audio_path, beam_size=5)
            transcription = []
            for segment in segments:
                transcription.append(segment.text)
                
            full_text = " ".join(transcription).strip()
            logger.info(f"Local transcription result: '{full_text}' (Language: {info.language}, Probability: {info.language_probability:.2f})")
            return full_text
        except Exception as e:
            logger.error(f"Error during local transcription: {str(e)}")
            return ""

# Single instance to be shared across the application
stt_service = SpeechToTextService()
