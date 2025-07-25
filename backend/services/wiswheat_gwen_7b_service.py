#!/usr/bin/env python3

import os
import torch
import gc
import logging
from typing import List, Optional, Dict, Any, Iterator
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, TextIteratorStreamer
from qwen_vl_utils import process_vision_info
from PIL import Image
import time
from threading import Thread

logger = logging.getLogger(__name__)

class WisWheat_Gwen_7BService:
    def __init__(self, device_map: str = "cuda"):
        self.model_name = "WisWheat/WisWheat_Qwen-7B"
        self.device_map = device_map
        self.model = None
        self.processor = None
        self.is_loaded = False
                
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"WisWheat-Gwen-7B using device: {self.device}")
        
        self.system_prompt = "You are a helpful assistant."
        
        self.max_image_size = (1024, 1024)  
        self.min_pixels = 256 * 28 * 28     
        self.max_pixels = 1280 * 28 * 28    
        
        
    def _preprocess_image(self, image_path: str) -> str:
        """Preprocess image to reduce memory usage"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize image if it's too large
                if img.size[0] > self.max_image_size[0] or img.size[1] > self.max_image_size[1]:
                    img.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)
                    logger.info(f"Resized image from {image_path} to {img.size}")
                
                # Save processed image temporarily
                processed_path = image_path.replace('.', '_processed.')
                img.save(processed_path, quality=85, optimize=True)
                return processed_path
        except Exception as e:
            logger.warning(f"Failed to preprocess image {image_path}: {e}")
            return image_path
        
    def load_model(self) -> bool:
        if self.is_loaded:
            logger.info("WisWheat-Gwen-7B model already loaded")
            return True
            
        try:
            logger.info(f"Loading WisWheat-Gwen-7B model: {self.model_name}")
            
            # Set memory optimization environment variable
            os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
            
            # Load model with memory optimizations
            self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,  # Use float16 for memory efficiency
                device_map=self.device_map,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
            ).eval()
            
            # Load processor with reduced pixel limits
            self.processor = AutoProcessor.from_pretrained(
                self.model_name,
                min_pixels=self.min_pixels,
                max_pixels=self.max_pixels,
            )
            
            self.is_loaded = True
            logger.info(f"WisWheat-Gwen-7B model loaded successfully with memory optimizations.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load WisWheat-Gwen-7B model: {str(e)}")
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
        
        # Aggressive memory cleanup
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        logger.info("WisWheat-Gwen-7B model cleanup completed")
    
    def unload_model(self):
        self._cleanup()
    
    def _create_messages(self, 
                        text_input: str, 
                        image_paths: Optional[List[str]] = None) -> List[dict]:
        """
        Create messages in Qwen format with system prompt and user content.
        """
        # Start with system message (commented out for memory efficiency)
        messages = [
            # {
            #     "role": "system",
            #     "content": self.system_prompt
            # }
        ]
        
        # Create user message content
        user_content = []
        
        # Add images first if provided (limit to 2 images max for memory)
        if image_paths:
            processed_images = []
            for i, img_path in enumerate(image_paths[:2]):  # Limit to 2 images
                if os.path.exists(img_path):
                    try:
                        # Preprocess image to reduce memory usage
                        processed_path = self._preprocess_image(img_path)
                        processed_images.append(processed_path)
                        
                        user_content.append({
                            "type": "image",
                            "image": processed_path
                        })
                    except Exception as e:
                        logger.warning(f"Failed to process image {img_path}: {e}")
                else:
                    logger.warning(f"Image file not found: {img_path}")
            
            if len(image_paths) > 2:
                logger.warning(f"Limited to 2 images for memory efficiency. Provided: {len(image_paths)}")
        
        # Add text input
        user_content.append({
            "type": "text", 
            "text": text_input
        })
        
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
            raise RuntimeError("WisWheat-Gwen-7B model not loaded. Please call load_model() first.")
        
        try:
            # Clear cache before processing
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            messages = self._create_messages(text_input, image_paths)
            
            # Apply chat template to get text
            text = self.processor.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
            
            # Process vision information
            image_inputs, video_inputs = process_vision_info(messages)
            
            # Prepare inputs with memory-efficient settings
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            )
            
            # Move inputs to device
            inputs = inputs.to(self.model.device, dtype=torch.float16)
            
            # Generate response with memory optimizations
            with torch.inference_mode():
                # Reduce max_new_tokens further if needed
                effective_max_tokens = min(max_new_tokens, 256)
                
                if do_sample and temperature > 0:
                    generated_ids = self.model.generate(
                        **inputs,
                        max_new_tokens=effective_max_tokens,
                        do_sample=True,
                        temperature=temperature,
                        use_cache=True,
                        pad_token_id=self.processor.tokenizer.eos_token_id,
                    )
                else:
                    generated_ids = self.model.generate(
                        **inputs,
                        max_new_tokens=effective_max_tokens,
                        do_sample=False,
                        use_cache=True,
                        pad_token_id=self.processor.tokenizer.eos_token_id,
                    )
                
                # Extract only the new tokens
                generated_ids_trimmed = [
                    out_ids[len(in_ids):] 
                    for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
                ]
            
            # Decode the response
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, 
                skip_special_tokens=True, 
                clean_up_tokenization_spaces=False
            )
            
            # Clean up processed images
            if image_paths:
                for img_path in image_paths:
                    processed_path = img_path.replace('.', '_processed.')
                    if os.path.exists(processed_path) and processed_path != img_path:
                        try:
                            os.remove(processed_path)
                        except:
                            pass
            
            # Clear cache after processing
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Return the first (and should be only) response
            return output_text[0].strip() if output_text else ""
            
        except Exception as e:
            logger.error(f"Error during WisWheat-Gwen-7B response generation: {str(e)}")
            # Clear cache on error
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
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
            raise RuntimeError("WisWheat-Gwen-7B model not loaded. Please call load_model() first.")
        
        try:
            # Create messages
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add user message with images if provided
            user_content = []
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
            
            user_content.append({"type": "text", "text": text_input})
            messages.append({"role": "user", "content": user_content})
            
            # Prepare inputs using the processor
            text_input = self.processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.processor(
                text=[text_input],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            )
            inputs = inputs.to(self.device)
            
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
            
            # Clear cache after generation
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
        except Exception as e:
            logger.error(f"Error during WisWheat-Gwen-7B streaming generation: {str(e)}")
            # Clear cache on error
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
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
            "memory_optimizations": {
                "max_image_size": self.max_image_size,
                "min_pixels": self.min_pixels,
                "max_pixels": self.max_pixels,
                "max_images_per_request": 2
            }
        } 