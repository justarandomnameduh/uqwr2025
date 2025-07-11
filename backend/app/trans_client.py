import os
import sys
import logging
from typing import Optional, Dict, Any
from threading import Lock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from trans_service import WhisperTranscriptionService

logger = logging.getLogger(__name__)

class TranscriptionClient:
    
    def __init__(self):
        self.trans_service = None
        self.is_model_loaded = False
        self.lock = Lock()
        
    def load_model(self):
        with self.lock:
            if self.is_model_loaded:
                return True
                
            try:
                self.trans_service = WhisperTranscriptionService()
                if self.trans_service.load_model():
                    self.is_model_loaded = True
                    logger.info("Transcription model loaded successfully")
                    return True
                else:
                    logger.error("Failed to load transcription model")
                    return False
                    
            except Exception as e:
                logger.error(f"Error loading transcription model: {e}")
                return False
    
    def unload_model(self):
        with self.lock:
            if self.trans_service:
                self.trans_service.unload_model()
                self.trans_service = None
                self.is_model_loaded = False
                logger.info("Transcription model unloaded")
    
    def is_loaded(self):
        return self.is_model_loaded
    
    def get_model_info(self):
        if not self.is_model_loaded or not self.trans_service:
            return {
                "model_name": "Not loaded",
                "is_loaded": False,
                "supports_audio": False,
                "supported_formats": []
            }
        
        return self.trans_service.get_model_info()
    
    def transcribe_audio(self, 
                        audio_file_path: str,
                        return_timestamps: bool = False,
                        batch_size: int = 8):
        """
        Transcribe audio file to text
        
        Returns:
            Dictionary containing transcription results
        """
        if not self.is_model_loaded or not self.trans_service:
            raise RuntimeError("Transcription model not loaded")
        
        try:
            with self.lock:
                result = self.trans_service.transcribe_audio(
                    audio_file_path=audio_file_path,
                    return_timestamps=return_timestamps,
                    batch_size=batch_size
                )
                return result
                
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            raise
    
    def process_audio_file(self,
                          input_file_path: str,
                          output_dir: str,
                          return_timestamps: bool = False,
                          batch_size: int = 8,
                          keep_mp3: bool = True):
        """
        Complete workflow: convert audio file to MP3 and transcribe
        
        Args:
            input_file_path: Path to input audio file
            output_dir: Directory to save converted MP3
            return_timestamps: Whether to return timestamp information
            batch_size: Batch size for processing
            keep_mp3: Whether to keep the converted MP3 file
        
        Returns:
            Dictionary containing transcription results and MP3 path
        """
        if not self.is_model_loaded or not self.trans_service:
            raise RuntimeError("Transcription model not loaded")
        
        try:
            with self.lock:
                result = self.trans_service.process_audio_file(
                    input_file_path=input_file_path,
                    output_dir=output_dir,
                    return_timestamps=return_timestamps,
                    batch_size=batch_size,
                    keep_mp3=keep_mp3
                )
                return result
                
        except Exception as e:
            logger.error(f"Error processing audio file: {e}")
            raise
    
    def convert_audio_to_mp3(self, input_file_path: str, output_dir: str):
        if not self.trans_service:
            temp_service = WhisperTranscriptionService()
            return temp_service.convert_audio_to_mp3(input_file_path, output_dir)
        
        try:
            return self.trans_service.convert_audio_to_mp3(input_file_path, output_dir)
        except Exception as e:
            logger.error(f"Error converting audio file: {e}")
            raise


_trans_client = None

def get_transcription_service():
    global _trans_client
    if _trans_client is None:
        _trans_client = TranscriptionClient()
    return _trans_client 