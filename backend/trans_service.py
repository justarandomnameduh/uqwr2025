#!/usr/bin/env python3

import os
import torch
import gc
import logging
from typing import Optional, Dict, Any, Union
from transformers import pipeline
from pydub import AudioSegment
import tempfile
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WhisperTranscriptionService:
    def __init__(self, model_name: str = "openai/whisper-large-v3-turbo"):
        self.model_name = model_name
        self.pipeline = None
        self.is_loaded = False
        
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
    def load_model(self) -> bool:
        if self.is_loaded:
            logger.info("Model already loaded")
            return True
            
        try:
            logger.info(f"Loading transcription model: {self.model_name}")
            
            # Create the transcription pipeline
            self.pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model_name,
                chunk_length_s=30,
                device=self.device,
            )
            
            self.is_loaded = True
            logger.info(f"Transcription model loaded successfully.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load transcription model: {str(e)}")
            self._cleanup()
            return False
    
    def _cleanup(self):
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
        self.is_loaded = False
        logger.info("Transcription model cleanup completed")
    
    def __del__(self):
        if self.is_loaded:
            self._cleanup()
    
    def unload_model(self):
        self._cleanup()
    
    def convert_audio_to_mp3(self, input_file_path: str, output_dir: str) -> str:
        try:
            logger.info(f"Converting audio file: {input_file_path}")
            
            unique_id = str(uuid.uuid4())
            original_name = os.path.splitext(os.path.basename(input_file_path))[0]
            mp3_filename = f"{unique_id}_{original_name}.mp3"
            mp3_path = os.path.join(output_dir, mp3_filename)
            
            audio = AudioSegment.from_file(input_file_path)
            audio.export(mp3_path, format="mp3")
            
            logger.info(f"Audio converted successfully to: {mp3_path}")
            return mp3_path
            
        except Exception as e:
            logger.error(f"Failed to convert audio file: {str(e)}")
            raise
    
    def transcribe_audio(self, 
                        audio_file_path: str,
                        return_timestamps: bool = False,
                        batch_size: int = 8) -> Dict[str, Any]:
        """
        Transcribe audio file to text using Whisper

        Returns:
            Dictionary containing transcription results
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded.")
        
        try:
            logger.info(f"Transcribing audio file: {audio_file_path}")
            
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
            
            audio = AudioSegment.from_file(audio_file_path)
            
            # Export to mp3 temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                audio.export(temp_file.name, format="mp3")
                temp_path = temp_file.name
            
            try:
                if return_timestamps:
                    result = self.pipeline(
                        temp_path, 
                        batch_size=batch_size, 
                        return_timestamps=True
                    )
                    transcription = {
                        "text": result.get("text", ""),
                        "chunks": result.get("chunks", [])
                    }
                else:
                    result = self.pipeline(temp_path, batch_size=batch_size)
                    transcription = {
                        "text": result.get("text", ""),
                        "chunks": None
                    }
                
                logger.info(f"Transcription completed successfully")
                return transcription
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            raise
    
    def process_audio_file(self,
                          input_file_path: str,
                          output_dir: str,
                          return_timestamps: bool = False,
                          batch_size: int = 8,
                          keep_mp3: bool = True) -> Dict[str, Any]:
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
        try:
            mp3_path = self.convert_audio_to_mp3(input_file_path, output_dir)
            
            transcription = self.transcribe_audio(
                mp3_path, 
                return_timestamps=return_timestamps,
                batch_size=batch_size
            )
            
            result = {
                "transcription": transcription,
                "mp3_path": mp3_path,
                "mp3_filename": os.path.basename(mp3_path)
            }
            
            if not keep_mp3:
                try:
                    os.unlink(mp3_path)
                    result["mp3_path"] = None
                    result["mp3_filename"] = None
                except:
                    logger.warning(f"Failed to remove temporary MP3 file: {mp3_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing audio file: {str(e)}")
            raise
    
    def is_model_loaded(self) -> bool:
        return self.is_loaded
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "device": self.device,
            "is_loaded": self.is_loaded,
            "supports_audio": True,
            "supported_formats": ["mp3", "wav", "flac", "ogg", "m4a", "aac"]
        }


def main():
    """Test function for the transcription service"""
    service = WhisperTranscriptionService()
    
    if not service.load_model():
        logger.error("Failed to load transcription model")
        return
    
    logger.info("Transcription service loaded successfully!")
    
    test_audio_path = "../assets/test_2.mp3"
    if os.path.exists(test_audio_path):
        try:
            result = service.transcribe_audio(test_audio_path)
            logger.info(f"Transcription result: {result}")
        except Exception as e:
            logger.error(f"Transcription test failed: {str(e)}")


if __name__ == "__main__":
    main() 