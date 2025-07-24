#!/usr/bin/env python3

import os
import torch
import gc
import logging
from typing import List, Optional, Dict, Any
from transformers import AutoProcessor, Gemma3ForConditionalGeneration
from PIL import Image
import time

logger = logging.getLogger(__name__)

class Gemma3_12BService:
    def __init__(self, device_map: str = "cuda"):
        self.model_name = "google/gemma-3-12b-it"
        self.device_map = device_map
        self.model = None
        self.processor = None
        self.is_loaded = False
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Gemma3-12B using device: {self.device}")
        
        self.system_prompt = "You are a helpful assistant."
        
    def load_model(self) -> bool:
        if self.is_loaded:
            logger.info("Gemma3-12B model already loaded")
            return True
            
        try:
            logger.info(f"Loading Gemma3-12B model: {self.model_name}")
            
            # Load model and processor with optimizations for larger model
            self.model = Gemma3ForConditionalGeneration.from_pretrained(
                self.model_name, 
                device_map=self.device_map,
                torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,  # Better for larger models
            ).eval()
            
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            torch.set_float32_matmul_precision('high')
            self.is_loaded = True
            logger.info(f"Gemma3-12B model loaded successfully.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load Gemma3-12B model: {str(e)}")
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
        
        # Force garbage collection and clear CUDA cache (important for large model)
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()  # Additional sync for large models
        
        logger.info("Gemma3-12B model cleanup completed")
    
    def unload_model(self):
        self._cleanup()
    
    def _create_messages(self, 
                        text_input: str, 
                        image_paths: Optional[List[str]] = None) -> List[dict]:
        
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": self.system_prompt}]
            }
        ]
        
        user_content = []
        
        # Add images first if provided
        if image_paths:
            for img_path in image_paths:
                if os.path.exists(img_path):
                    try:
                        image = Image.open(img_path).convert('RGB')
                        user_content.append({"type": "image", "image": image})
                    except Exception as e:
                        logger.warning(f"Failed to load image {img_path}: {e}")
                else:
                    logger.warning(f"Image file not found: {img_path}")
        
        # Add text input
        user_content.append({"type": "text", "text": text_input})
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        return messages
    
    def generate_response(self, 
                         text_input: str, 
                         image_paths: Optional[List[str]] = None,
                         max_new_tokens: int = 512,
                         temperature: float = 0.7,
                         do_sample: bool = True) -> str:
        
        if not self.is_loaded:
            raise RuntimeError("Gemma3-12B model not loaded. Please call load_model() first.")
        
        try:
            messages = self._create_messages(text_input, image_paths)
            
            # Apply chat template and tokenize
            inputs = self.processor.apply_chat_template(
                messages, 
                add_generation_prompt=True, 
                tokenize=True,
                return_dict=True, 
                return_tensors="pt"
            ).to(self.model.device, dtype=torch.bfloat16 if self.device == "cuda" else torch.float32)
            
            input_len = inputs["input_ids"].shape[-1]
            
            # Generate response with optimizations for larger model
            with torch.inference_mode():
                if do_sample and temperature > 0:
                    generation = self.model.generate(
                        **inputs, 
                        max_new_tokens=max_new_tokens, 
                        do_sample=True,
                        temperature=temperature,
                        pad_token_id=self.processor.tokenizer.eos_token_id,
                        use_cache=True,  # Important for efficiency with larger models
                    )
                else:
                    generation = self.model.generate(
                        **inputs, 
                        max_new_tokens=max_new_tokens, 
                        do_sample=False,
                        pad_token_id=self.processor.tokenizer.eos_token_id,
                        use_cache=True,
                    )
                
                # Extract only the new tokens
                generation = generation[0][input_len:]
            
            # Decode the response
            response = self.processor.decode(generation, skip_special_tokens=True)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error during Gemma3-12B response generation: {str(e)}")
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
            "supports_video": False,
        } 