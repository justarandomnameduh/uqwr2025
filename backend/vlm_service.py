#!/usr/bin/env python3

import os
import torch
import gc
import logging
from typing import List, Optional, Dict, Any
from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor
from qwen_omni_utils import process_mm_info
from PIL import Image
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QwenOmniVLMService:
    def __init__(self, model_name: str = "Qwen/Qwen2.5-Omni-3B", device_map: str = "auto"):
        self.model_name = model_name
        self.device_map = device_map
        self.model = None
        self.processor = None
        self.is_loaded = False
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        self.system_prompt = (
            "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."
        )
        
    def load_model(self) -> bool:
        if self.is_loaded:
            logger.info("Model already loaded")
            return True
            
        try:
            start_time = time.time()
            logger.info(f"Loading model: {self.model_name}")
            
            self.model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16,
                device_map=self.device_map,
                # attn_implementation="flash_attention_2",  # Uncomment if needed
            )
            
            self.processor = Qwen2_5OmniProcessor.from_pretrained(self.model_name)
            
            self.is_loaded = True
            load_time = time.time() - start_time
            logger.info(f"Model loaded successfully in {load_time:.2f} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            self._cleanup()
            return False
    
    def _cleanup(self):
        if self.model is not None:
            del self.model
            self.model = None
        
        if self.processor is not None:
            del self.processor
            self.processor = None
        
        self.is_loaded = False
        gc.collect()
        
        if self.device == "cuda":
            torch.cuda.empty_cache()
        
        logger.info("Model cleanup completed")
    
    def __del__(self):
        if self.is_loaded:
            self._cleanup()
    
    def unload_model(self):
        self._cleanup()
    
    def _create_conversation(self, 
                            text_input: str, 
                            image_paths: Optional[List[str]] = None) -> List[dict]:
        conversation = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": self.system_prompt}
                ],
            }
        ]
        
        user_content = []
        
        if image_paths:
            for img_path in image_paths:
                if os.path.exists(img_path):
                    user_content.append({"type": "image", "image": img_path})
                else:
                    logger.warning(f"Image file not found: {img_path}")
        
        user_content.append({"type": "text", "text": text_input})
        
        conversation.append({
            "role": "user",
            "content": user_content
        })
        
        return conversation
    
    def generate_response(self, 
                         text_input: str, 
                         image_paths: Optional[List[str]] = None,
                         max_new_tokens: int = 512,
                         temperature: float = 0.7) -> str:
        
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Please call load_model() first.")
        
        try:
            conversation = self._create_conversation(text_input, image_paths)
            text_prompt = self.processor.apply_chat_template(
                conversation, 
                add_generation_prompt=True, 
                tokenize=False,
            )
            
            audios, images, videos = process_mm_info(conversation, use_audio_in_video=False)
            
            inputs = self.processor(
                text=text_prompt,
                audio=audios,
                images=images,
                videos=videos,
                return_tensors="pt",
                padding=True,
                use_audio_in_video=False
            )
            
            inputs = inputs.to(self.model.device).to(self.model.dtype)
            
            # Generate response
            with torch.no_grad():
                text_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    use_audio_in_video=False,
                    return_audio=False,  # Disable audio output
                )
            
            full_response = self.processor.batch_decode(
                text_ids, 
                skip_special_tokens=True, 
                clean_up_tokenization_spaces=False
            )[0]
            
            # Extract only the assistant's response
            if "assistant\n" in full_response:
                response = full_response.split("assistant\n")[-1].strip()
            else:
                response = full_response.strip()
            
            return response
            
        except Exception as e:
            logger.error(f"Error during response generation: {str(e)}")
            raise
    
    def is_model_loaded(self) -> bool:
        return self.is_loaded
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "device": self.device,
            "device_map": self.device_map,
            "is_loaded": self.is_loaded,
            "supports_images": True,
            "supports_audio": True,
            "supports_video": False,  # Update later when have a speech-to-text service
        }


def main():
    service = QwenOmniVLMService()
    
    if not service.load_model():
        logger.error("Failed to load model")
        return
    
    logger.info("Testing text-only generation...")
    text_prompt = "What is artificial intelligence? Provide a brief explanation."
    try:
        response = service.generate_response(text_prompt)
        logger.info(f"Text-only response: {response}")
    except Exception as e:
        logger.error(f"Text generation failed: {str(e)}")
    
    test_images = ["test_1.jpg", "test_2.jpg"]
    existing_images = [img for img in test_images if os.path.exists(img)]
    
    if existing_images:
        logger.info(f"Testing image + text generation with {len(existing_images)} images...")
        image_prompt = "Describe what you see in this image."
        try:
            response = service.generate_response(image_prompt, existing_images[:1])
            logger.info(f"Image + text response: {response}")
        except Exception as e:
            logger.error(f"Image generation failed: {str(e)}")
    else:
        logger.info("No test images found, skipping image test")
    
    logger.info(f"Model info: {service.get_model_info()}")
    
    service.unload_model()
    logger.info("Demo completed")


if __name__ == "__main__":
    main()