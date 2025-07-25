#!/usr/bin/env python3

import os
import torch
import requests
import gc
import logging
from typing import List, Optional, Dict, Any, Iterator
from transformers import AutoProcessor, Gemma3ForConditionalGeneration, TextIteratorStreamer
from PIL import Image
import time
from threading import Thread

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Gemma3VLMService:
    def __init__(self, model_name: str = "google/gemma-3-4b-it", device_map: str = "cuda"):
        self.model_name = model_name
        self.device_map = device_map
        self.model = None
        self.processor = None
        self.is_loaded = False
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        self.system_prompt = (
            "You are a helpful assistant."
        )
        
    def load_model(self) -> bool:
        if self.is_loaded:
            logger.info("Model already loaded")
            return True
            
        try:
            logger.info(f"Loading model: {self.model_name}")
            
            # Load model and processor directly
            self.model = Gemma3ForConditionalGeneration.from_pretrained(
                self.model_name, 
                device_map=self.device_map,
                torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
            ).eval()
            
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            
            self.is_loaded = True
            logger.info(f"Model loaded successfully.")
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
        
        logger.info("Model cleanup completed")
    
    def __del__(self):
        try:
            if self.is_loaded:
                self._cleanup()
        except:
            pass  # Ignore cleanup errors during destruction
    
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
            raise RuntimeError("Model not loaded. Please call load_model() first.")
        
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
            
            # Generate response
            with torch.inference_mode():
                if do_sample and temperature > 0:
                    generation = self.model.generate(
                        **inputs, 
                        max_new_tokens=max_new_tokens, 
                        do_sample=True,
                        temperature=temperature
                    )
                else:
                    generation = self.model.generate(
                        **inputs, 
                        max_new_tokens=max_new_tokens, 
                        do_sample=False
                    )
                
                # Extract only the new tokens
                generation = generation[0][input_len:]
            
            # Decode the response
            response = self.processor.decode(generation, skip_special_tokens=True)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error during response generation: {str(e)}")
            raise
    
    def generate_response_stream(self, 
                               text_input: str, 
                               image_paths: Optional[List[str]] = None,
                               max_new_tokens: int = 512,
                               temperature: float = 0.7,
                               do_sample: bool = True) -> Iterator[str]:
        """
        Generate streaming response using TextIteratorStreamer.
        Yields tokens as they are generated.
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Please call load_model() first.")
        
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
            
            # Create streamer
            streamer = TextIteratorStreamer(tokenizer=self.processor.tokenizer, skip_prompt=True, skip_special_tokens=True)
            
            # Set up generation arguments
            generation_kwargs = {
                **inputs,
                "max_new_tokens": max_new_tokens,
                "streamer": streamer,
                "do_sample": do_sample,
            }
            
            if do_sample and temperature > 0:
                generation_kwargs["temperature"] = temperature
            
            # Start generation in a separate thread
            thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.start()
            
            # Yield tokens as they are generated
            for token in streamer:
                yield token
            
            # Wait for generation to complete
            thread.join()
            
        except Exception as e:
            logger.error(f"Error during streaming generation: {str(e)}")
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


def main():
    service = Gemma3VLMService()
    
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
    
    test_images = ["../assets/test_1.jpg", "../assets/test_2.jpg"]
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