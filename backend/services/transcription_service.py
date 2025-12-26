# services/transcription_service.py - FASTAPI ASYNC VERSION
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from faster_whisper import WhisperModel

from config.settings import settings
from config.logging_config import logger


# ============================================================================
# WHISPER MODEL MANAGER
# ============================================================================

class WhisperModelManager:
    """Manage Whisper model lifecycle"""
    
    def __init__(self):
        self._model: Optional[WhisperModel] = None
        self._model_size: str = settings.WHISPER_MODEL_SIZE
        self._loading_lock = asyncio.Lock()
    
    def get_model_sync(self) -> WhisperModel:
        """Load and cache Faster Whisper model (synchronous)"""
        if self._model is None:
            logger.info(f"⏳ Loading Faster Whisper: {self._model_size}")
            
            try:
                self._model = WhisperModel(
                    self._model_size,
                    device="cpu",
                    compute_type="int8",  # Optimized for CPU
                    num_workers=4,
                    download_root=None  # Use default cache directory
                )
                
                logger.info(f"✅ Faster Whisper loaded (CPU optimized)")
                
            except Exception as e:
                logger.error(f"❌ Failed to load Whisper model: {e}")
                raise
        
        return self._model
    
    async def get_model(self) -> WhisperModel:
        """Get Whisper model (async)"""
        if self._model is None:
            async with self._loading_lock:
                if self._model is None:
                    loop = asyncio.get_event_loop()
                    self._model = await loop.run_in_executor(
                        None,
                        self.get_model_sync
                    )
        
        return self._model
    
    def unload_model(self):
        """Unload model from memory"""
        if self._model is not None:
            logger.info("🗑️  Unloading Whisper model from memory")
            self._model = None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_size": self._model_size,
            "loaded": self._model is not None,
            "device": "cpu",
            "compute_type": "int8"
        }


# Global model manager
whisper_manager = WhisperModelManager()


# ============================================================================
# TRANSCRIPTION SERVICE
# ============================================================================

class TranscriptionService:
    """Audio transcription service using Faster Whisper"""
    
    def __init__(self):
        self.model_manager = whisper_manager
    
    def transcribe_audio_sync(
        self,
        audio_path: str,
        language: str = "en",
        beam_size: int = 1,
        vad_filter: bool = True,
        word_timestamps: bool = False
    ) -> str:
        """
        Transcribe audio using Faster Whisper (synchronous)
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en', 'es', 'fr')
            beam_size: Beam size for decoding (1 is fastest)
            vad_filter: Enable voice activity detection
            word_timestamps: Include word-level timestamps
        
        Returns:
            Transcribed text
        """
        try:
            # Validate audio file
            audio_file = Path(audio_path)
            if not audio_file.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            model = self.model_manager.get_model_sync()
            logger.info(f"🎤 Transcribing audio: {audio_path}")
            
            segments, info = model.transcribe(
                audio_path,
                beam_size=beam_size,
                language=language,
                vad_filter=vad_filter,
                word_timestamps=word_timestamps,
                condition_on_previous_text=False  # Faster
            )
            
            # Combine all segments
            transcript_parts = []
            for segment in segments:
                transcript_parts.append(segment.text)
            
            transcript = " ".join(transcript_parts).strip()
            
            logger.info(f"✅ Transcription complete: {len(transcript)} chars")
            logger.info(f"📊 Language detected: {info.language} (probability: {info.language_probability:.2f})")
            
            return transcript
            
        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            raise
    
    async def transcribe_audio(
        self,
        audio_path: str,
        language: str = "en",
        beam_size: int = 1,
        vad_filter: bool = True,
        word_timestamps: bool = False
    ) -> str:
        """
        Transcribe audio using Faster Whisper (async)
        
        Args:
            audio_path: Path to audio file
            language: Language code
            beam_size: Beam size for decoding
            vad_filter: Enable voice activity detection
            word_timestamps: Include word-level timestamps
        
        Returns:
            Transcribed text
        """
        try:
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(
                None,
                self.transcribe_audio_sync,
                audio_path,
                language,
                beam_size,
                vad_filter,
                word_timestamps
            )
            return transcript
            
        except Exception as e:
            logger.error(f"❌ Async transcription failed: {e}")
            raise
    
    def transcribe_with_timestamps_sync(
        self,
        audio_path: str,
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Transcribe audio with detailed timestamps (synchronous)
        
        Args:
            audio_path: Path to audio file
            language: Language code
        
        Returns:
            List of segments with timestamps
        """
        try:
            audio_file = Path(audio_path)
            if not audio_file.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            model = self.model_manager.get_model_sync()
            logger.info(f"🎤 Transcribing with timestamps: {audio_path}")
            
            segments, info = model.transcribe(
                audio_path,
                beam_size=1,
                language=language,
                vad_filter=True,
                word_timestamps=True
            )
            
            # Format segments with timestamps
            timestamped_segments = []
            for segment in segments:
                timestamped_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "words": [
                        {
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "probability": word.probability
                        }
                        for word in segment.words
                    ] if hasattr(segment, 'words') and segment.words else []
                })
            
            logger.info(f"✅ Transcription with timestamps complete: {len(timestamped_segments)} segments")
            
            return timestamped_segments
            
        except Exception as e:
            logger.error(f"❌ Timestamped transcription failed: {e}")
            raise
    
    async def transcribe_with_timestamps(
        self,
        audio_path: str,
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Transcribe audio with detailed timestamps (async)
        
        Args:
            audio_path: Path to audio file
            language: Language code
        
        Returns:
            List of segments with timestamps
        """
        try:
            loop = asyncio.get_event_loop()
            segments = await loop.run_in_executor(
                None,
                self.transcribe_with_timestamps_sync,
                audio_path,
                language
            )
            return segments
            
        except Exception as e:
            logger.error(f"❌ Async timestamped transcription failed: {e}")
            raise
    
    def detect_language_sync(self, audio_path: str) -> Tuple[str, float]:
        """
        Detect language of audio file (synchronous)
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            Tuple of (language_code, probability)
        """
        try:
            model = self.model_manager.get_model_sync()
            logger.info(f"🌍 Detecting language: {audio_path}")
            
            segments, info = model.transcribe(
                audio_path,
                beam_size=1,
                vad_filter=True
            )
            
            # Consume first segment to get language info
            next(segments, None)
            
            language = info.language
            probability = info.language_probability
            
            logger.info(f"✅ Language detected: {language} ({probability:.2f})")
            
            return language, probability
            
        except Exception as e:
            logger.error(f"❌ Language detection failed: {e}")
            raise
    
    async def detect_language(self, audio_path: str) -> Tuple[str, float]:
        """
        Detect language of audio file (async)
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            Tuple of (language_code, probability)
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.detect_language_sync,
                audio_path
            )
            return result
            
        except Exception as e:
            logger.error(f"❌ Async language detection failed: {e}")
            raise
    
    def transcribe_batch_sync(
        self,
        audio_paths: List[str],
        language: str = "en"
    ) -> List[str]:
        """
        Transcribe multiple audio files (synchronous)
        
        Args:
            audio_paths: List of audio file paths
            language: Language code
        
        Returns:
            List of transcripts
        """
        try:
            logger.info(f"🎤 Batch transcribing {len(audio_paths)} files...")
            
            transcripts = []
            for i, audio_path in enumerate(audio_paths, 1):
                logger.info(f"📄 Processing file {i}/{len(audio_paths)}")
                transcript = self.transcribe_audio_sync(audio_path, language)
                transcripts.append(transcript)
            
            logger.info(f"✅ Batch transcription complete")
            return transcripts
            
        except Exception as e:
            logger.error(f"❌ Batch transcription failed: {e}")
            raise
    
    async def transcribe_batch(
        self,
        audio_paths: List[str],
        language: str = "en"
    ) -> List[str]:
        """
        Transcribe multiple audio files (async)
        
        Args:
            audio_paths: List of audio file paths
            language: Language code
        
        Returns:
            List of transcripts
        """
        try:
            logger.info(f"🎤 Batch transcribing {len(audio_paths)} files (async)...")
            
            # Process sequentially to avoid memory issues
            transcripts = []
            for i, audio_path in enumerate(audio_paths, 1):
                logger.info(f"📄 Processing file {i}/{len(audio_paths)}")
                transcript = await self.transcribe_audio(audio_path, language)
                transcripts.append(transcript)
            
            logger.info(f"✅ Batch transcription complete")
            return transcripts
            
        except Exception as e:
            logger.error(f"❌ Async batch transcription failed: {e}")
            raise


# Global transcription service
transcription_service = TranscriptionService()


# ============================================================================
# CONVENIENCE FUNCTIONS (Backward Compatibility)
# ============================================================================

def get_whisper_model():
    """Load and cache Faster Whisper model (backward compatibility)"""
    return whisper_manager.get_model_sync()


def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio using Faster Whisper (backward compatibility)
    
    Args:
        audio_path: Path to audio file
    
    Returns:
        Transcribed text
    """
    return transcription_service.transcribe_audio_sync(audio_path)


async def transcribe_audio_async(
    audio_path: str,
    language: str = "en",
    beam_size: int = 1
) -> str:
    """
    Transcribe audio (async wrapper)
    
    Args:
        audio_path: Path to audio file
        language: Language code
        beam_size: Beam size for decoding
    
    Returns:
        Transcribed text
    """
    return await transcription_service.transcribe_audio(
        audio_path,
        language,
        beam_size
    )


async def transcribe_with_timestamps_async(
    audio_path: str,
    language: str = "en"
) -> List[Dict[str, Any]]:
    """
    Transcribe with timestamps (async wrapper)
    
    Args:
        audio_path: Path to audio file
        language: Language code
    
    Returns:
        List of timestamped segments
    """
    return await transcription_service.transcribe_with_timestamps(
        audio_path,
        language
    )


async def detect_language_async(audio_path: str) -> Tuple[str, float]:
    """
    Detect audio language (async wrapper)
    
    Args:
        audio_path: Path to audio file
    
    Returns:
        Tuple of (language_code, probability)
    """
    return await transcription_service.detect_language(audio_path)


def get_whisper_model_info() -> Dict[str, Any]:
    """Get Whisper model information"""
    return whisper_manager.get_model_info()
