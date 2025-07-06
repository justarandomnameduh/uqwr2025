import os
import sys
import logging
from typing import Optional, List, Dict, Any
from threading import Lock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vlm_service import QwenOmniVLMService

logger = logging.getLogger(__name__)

class VLMClient:
    
    def __init__(self):
        self.vlm_service = None
        self.is_model_loaded = False
        self.lock = Lock()
        
    def load_model(self):
        with self.lock:
            if self.is_model_loaded:
                return True
                
            try:
                self.vlm_service = QwenOmniVLMService()
                if self.vlm_service.load_model():
                    self.is_model_loaded = True
                    logger.info("VLM model loaded successfully")
                    return True
                else:
                    logger.error("Failed to load VLM model")
                    return False
                    
            except Exception as e:
                logger.error(f"Error loading VLM model: {e}")
                return False
    
    def unload_model(self):
        with self.lock:
            if self.vlm_service:
                self.vlm_service.unload_model()
                self.vlm_service = None
                self.is_model_loaded = False
                logger.info("VLM model unloaded")
    
    def is_loaded(self):
        return self.is_model_loaded
    
    def get_model_info(self):
        if not self.is_model_loaded or not self.vlm_service:
            return {
                "model_name": "Not loaded",
                "is_loaded": False,
                "supports_images": False,
                "supports_audio": False,
                "supports_video": False,
            }
        
        return self.vlm_service.get_model_info()
    
    def generate_response(self, 
                         text_input,
                         image_paths,
                         max_new_tokens = 512,
                         temperature = 0.7):
        if not self.is_model_loaded or not self.vlm_service:
            raise RuntimeError("Model not loaded")
        
        try:
            with self.lock:
                response = self.vlm_service.generate_response(
                    text_input=text_input,
                    image_paths=image_paths,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature
                )
                return response
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise


_vlm_client = None

def get_vlm_service():
    global _vlm_client
    if _vlm_client is None:
        _vlm_client = VLMClient()
    return _vlm_client 