# services/transcription_service.py
from faster_whisper import WhisperModel
from config.settings import settings
from config.logging_config import logger

_model = None

def get_whisper_model():
    """Load and cache Faster Whisper model (optimized for CPU)"""
    global _model
    if _model is None:
        logger.info(f"⏳ Loading Faster Whisper: {settings.WHISPER_MODEL_SIZE}")
        
        _model = WhisperModel(
            settings.WHISPER_MODEL_SIZE,
            device="cpu",
            compute_type="int8",  # Optimized for CPU
            num_workers=4
        )
        
        logger.info(f"✅ Faster Whisper loaded (CPU optimized)")
    return _model

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio using Faster Whisper
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        str: Transcribed text
    """
    try:
        model = get_whisper_model()
        logger.info("🎤 Transcribing audio with Faster Whisper...")
        
        segments, info = model.transcribe(
            audio_path,
            beam_size=1,              # Faster
            language="en",            # Skip language detection
            vad_filter=True,          # Skip silence
            condition_on_previous_text=False  # Faster
        )
        
        # Combine all segments
        transcript = " ".join([segment.text for segment in segments]).strip()
        
        logger.info(f"✅ Transcription complete: {len(transcript)} chars")
        return transcript
        
    except Exception as e:
        logger.error(f"❌ Transcription failed: {e}")
        raise
