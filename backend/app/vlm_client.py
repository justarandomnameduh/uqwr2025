import os
import sys
import logging
from typing import Optional, List, Dict, Any, Iterator
from threading import Lock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import all available services
from services.qwen2_5_7b_service import Qwen2_5_7BService
from services.wiswheat_gwen_service import WisWheat_GwenService
from services.wiswheat_llava_next_mistral_7b_service import WisWheat_LLavaNext_Mistral_7BService
logger = logging.getLogger(__name__)

# Available models configuration
AVAILABLE_MODELS = {
    "qwen2.5-7b": {
        "display_name": "Qwen 2.5 VL 7B",
        "description": "",
        "service_class": Qwen2_5_7BService,
        "supports_images": True,
        "supports_video": False,
        "memory_requirements": "~14GB VRAM"
    },
    "wiswheat-gwen-7b": {
        "display_name": "WisWheat Gwen 7B",
        "description": "",
        "service_class": WisWheat_GwenService,
        "service_kwargs": {"model_size": "7b"},
        "supports_images": True,
        "supports_video": False,
        "memory_requirements": "~14GB VRAM"
    },
    "wiswheat-gwen-3b": {
        "display_name": "WisWheat Gwen 3B",
        "description": "",
        "service_class": WisWheat_GwenService,
        "service_kwargs": {"model_size": "3b"},
        "supports_images": True,
        "supports_video": False,
        "memory_requirements": "~6GB VRAM"
    },
    "wiswheat-llava-next-mistral-7b": {
        "display_name": "WisWheat LLavaNext Mistral 7B",
        "description": "",
        "service_class": WisWheat_LLavaNext_Mistral_7BService,
        "supports_images": True,
        "supports_video": False,
        "memory_requirements": "~14GB VRAM"
    }
}

class VLMClient:
    
    def __init__(self):
        self.vlm_service = None
        self.current_model_id = None
        self.is_model_loaded = False
        self.lock = Lock()
        
    def get_available_models(self) -> Dict[str, Any]:
        """Get list of available models with their info"""
        models_info = {}
        for model_id, config in AVAILABLE_MODELS.items():
            models_info[model_id] = {
                "display_name": config["display_name"],
                "description": config["description"],
                "supports_images": config["supports_images"],
                "supports_video": config["supports_video"],
                "memory_requirements": config["memory_requirements"]
            }
        return models_info
        
    def load_model(self, model_id: str = None) -> bool:
        """Load a specific model. Can only load one model per session."""
        with self.lock:
            # If a model is already loaded, prevent switching
            if self.is_model_loaded:
                logger.warning(f"Model {self.current_model_id} already loaded. Cannot switch models in this session.")
                return True
                
            # Default to first available model if none specified
            if model_id is None:
                model_id = list(AVAILABLE_MODELS.keys())[0]
                
            if model_id not in AVAILABLE_MODELS:
                logger.error(f"Unknown model ID: {model_id}")
                return False
                
            try:
                logger.info(f"Loading model: {model_id}")
                model_config = AVAILABLE_MODELS[model_id]
                service_class = model_config["service_class"]
                
                # Get service kwargs if provided
                service_kwargs = model_config.get("service_kwargs", {})
                
                self.vlm_service = service_class(**service_kwargs)
                if self.vlm_service.load_model():
                    self.is_model_loaded = True
                    self.current_model_id = model_id
                    logger.info(f"Model {model_id} loaded successfully")
                    return True
                else:
                    logger.error(f"Failed to load model: {model_id}")
                    self.vlm_service = None
                    return False
                    
            except Exception as e:
                logger.error(f"Error loading model {model_id}: {e}")
                self.vlm_service = None
                return False
    
    def unload_model(self):
        """Unload the current model"""
        with self.lock:
            if self.vlm_service:
                self.vlm_service.unload_model()
                self.vlm_service = None
                self.is_model_loaded = False
                self.current_model_id = None
                logger.info("VLM model unloaded")
    
    def is_loaded(self):
        return self.is_model_loaded
        
    def get_current_model_id(self):
        return self.current_model_id
    
    def get_model_info(self):
        if not self.is_model_loaded or not self.vlm_service:
            return {
                "model_name": "No model loaded",
                "current_model_id": None,
                "is_loaded": False,
                "supports_images": False,
                "supports_video": False,
            }
        
        base_info = self.vlm_service.get_model_info()
        base_info["current_model_id"] = self.current_model_id
        return base_info
    
    def generate_response(self, 
                         text_input,
                         image_paths,
                         conversation_history=None,
                         max_new_tokens = 512,
                         temperature = 0.7):
        if not self.is_model_loaded or not self.vlm_service:
            raise RuntimeError("No model loaded. Please load a model first.")
        
        try:
            with self.lock:
                # Note: Not all services support conversation_history in non-streaming mode
                # Only pass it if the service method supports it
                try:
                    response = self.vlm_service.generate_response(
                        text_input=text_input,
                        image_paths=image_paths,
                        conversation_history=conversation_history,
                        max_new_tokens=max_new_tokens,
                        temperature=temperature
                    )
                except TypeError:
                    # Fallback for services that don't support conversation_history in non-streaming
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
    
    def generate_response_stream(self, 
                               text_input,
                               image_paths,
                               conversation_history=None,
                               max_new_tokens = 512,
                               temperature = 0.7) -> Iterator[str]:
        if not self.is_model_loaded or not self.vlm_service:
            raise RuntimeError("No model loaded. Please load a model first.")
        
        try:
            with self.lock:
                for token in self.vlm_service.generate_response_stream(
                    text_input=text_input,
                    image_paths=image_paths,
                    conversation_history=conversation_history,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature
                ):
                    yield token
                
        except Exception as e:
            logger.error(f"Error generating streaming response: {e}")
            raise


_vlm_client = None

def get_vlm_service():
    global _vlm_client
    if _vlm_client is None:
        _vlm_client = VLMClient()
    return _vlm_client 