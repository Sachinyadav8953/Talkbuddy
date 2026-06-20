import logging
from faster_whisper import WhisperModel
from app.config import settings

logger = logging.getLogger("talkbuddy.stt")

class SpeechToTextService:
    def __init__(self):
        self.model = None

    def load_model(self):
        if self.model is None:
            logger.info(f"Loading Whisper model '{settings.WHISPER_MODEL}' on '{settings.WHISPER_DEVICE}'...")
            try:
                # Load WhisperModel (lazy load)
                # compute_type="int8" is optimized for CPU execution
                self.model = WhisperModel(
                    settings.WHISPER_MODEL, 
                    device=settings.WHISPER_DEVICE, 
                    compute_type="int8"
                )
                logger.info("Whisper model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {str(e)}")
                raise e

    def transcribe(self, audio_path: str) -> str:
        self.load_model()
        logger.info(f"Transcribing audio file: {audio_path}")
        try:
            segments, info = self.model.transcribe(audio_path, beam_size=5)
            transcription = []
            for segment in segments:
                transcription.append(segment.text)
                
            full_text = " ".join(transcription).strip()
            logger.info(f"Transcription result: '{full_text}' (Language: {info.language}, Probability: {info.language_probability:.2f})")
            return full_text
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            return ""

# Single instance to be shared across the application
stt_service = SpeechToTextService()
