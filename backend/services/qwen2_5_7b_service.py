#!/usr/bin/env python3

import os
import torch
import gc
import json
import logging
from typing import List, Optional, Dict, Any, Iterator
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, TextIteratorStreamer

# Compatibility patch for PyTorch versions that don't have torch.compiler.is_compiling
if hasattr(torch, 'compiler') and not hasattr(torch.compiler, 'is_compiling'):
    # Add the missing is_compiling function for compatibility
    def _is_compiling():
        return False
    torch.compiler.is_compiling = _is_compiling
    logger = logging.getLogger(__name__)
    logger.info("Applied compatibility patch for torch.compiler.is_compiling")

from qwen_vl_utils import process_vision_info
from PIL import Image
import time
from threading import Thread
from flask import current_app
from utils.common import preprocess_image_in_memory

logger = logging.getLogger(__name__)

class Qwen2_5_7BService:
    def __init__(self, device_map: str = "cuda"):
        self.model_name = "Qwen/Qwen2.5-VL-7B-Instruct"
        self.device_map = device_map
        self.model = None
        self.processor = None
        self.is_loaded = False
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Qwen2.5-7B using device: {self.device}")
        
        self.system_prompt = "You are a helpful assistant."
        
        # Memory optimization settings
        self.max_image_size = (1024, 1024)  # Limit image size to reduce memory usage
        self.min_pixels = 256 * 28 * 28     # Reduce minimum pixels for memory efficiency
        self.max_pixels = 1280 * 28 * 28    # Reduce maximum pixels for memory efficiency
        self.max_images_per_request = 10    # Maximum number of images per request
        
    def load_model(self) -> bool:
        if self.is_loaded:
            logger.info("Qwen2.5-7B model already loaded")
            return True
            
        try:
            logger.info(f"Loading Qwen2.5-7B model: {self.model_name}")
            
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
                max_pixels=self.max_pixels
            )
            
            self.is_loaded = True
            logger.info(f"Qwen2.5-7B model loaded successfully with memory optimizations.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load Qwen2.5-7B model: {str(e)}")
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
        
        logger.info("Qwen2.5-7B model cleanup completed")
    
    def unload_model(self):
        self._cleanup()
    
    def _create_messages(self, 
                        text_input: str, 
                        image_paths: Optional[List[str]] = None,
                        conversation_history: Optional[List[tuple]] = None,
                        include_system_prompt: bool = False,
                        upload_folder: Optional[str] = None) -> tuple:
        """
        Create messages in Qwen format with user content and conversation history.
        Returns: (messages, processed_images_for_cleanup)
        """
        # Start with system message if requested
        messages = []
        if include_system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # Add conversation history for context
        if conversation_history:
            for user_msg, assistant_msg in conversation_history:
                # Add historical user message
                historical_user_content = [{"type": "text", "text": user_msg.content}]
                
                # Add historical images if any
                if user_msg.images and upload_folder:
                    try:
                        historical_image_paths = json.loads(user_msg.images)
                        for img_path in historical_image_paths[:self.max_images_per_request]:
                            full_img_path = os.path.join(upload_folder, img_path)
                            if os.path.exists(full_img_path):
                                try:
                                    processed_image = preprocess_image_in_memory(full_img_path, self.max_image_size)
                                    historical_user_content.insert(0, {  # Insert images before text
                                        "type": "image",
                                        "image": processed_image
                                    })
                                except Exception as e:
                                    logger.warning(f"Failed to process historical image {full_img_path}: {e}")
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode images JSON for historical message: {user_msg.images}")
                
                messages.append({
                    "role": "user",
                    "content": historical_user_content
                })
                
                # Add historical assistant message
                messages.append({
                    "role": "assistant", 
                    "content": assistant_msg.content
                })
            
            logger.info(f"Added {len(conversation_history)} conversation pairs as context")
        
        # Create user message content
        user_content = []
        processed_images_for_cleanup = []
        
        # Add images first if provided
        if image_paths:
            for i, img_path in enumerate(image_paths[:self.max_images_per_request]):
                if os.path.exists(img_path):
                    try:
                        # Process image in memory to avoid disk I/O
                        processed_image = preprocess_image_in_memory(img_path, self.max_image_size)
                        
                        user_content.append({
                            "type": "image",
                            "image": processed_image
                        })
                    except Exception as e:
                        logger.warning(f"Failed to process image {img_path}: {e}")
                else:
                    logger.warning(f"Image file not found: {img_path}")
            
            if len(image_paths) > self.max_images_per_request:
                logger.warning(f"Limited to {self.max_images_per_request} images for memory efficiency. Provided: {len(image_paths)}")
        
        # Add text input
        user_content.append({
            "type": "text", 
            "text": text_input
        })
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        return messages, processed_images_for_cleanup
    
    def generate_response(self, 
                         text_input: str, 
                         image_paths: Optional[List[str]] = None,
                         conversation_history: Optional[List[tuple]] = None,
                         max_new_tokens: int = 512,
                         temperature: float = 0.7,
                         do_sample: bool = True,
                         upload_folder: Optional[str] = None) -> str:
        
        if not self.is_loaded:
            raise RuntimeError("Qwen2.5-7B model not loaded. Please call load_model() first.")
        
        try:
            
            messages, _ = self._create_messages(text_input, image_paths, conversation_history, include_system_prompt=True, upload_folder=upload_folder)
            
            # Apply chat template to get text
            text = self.processor.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True,
                add_vision_id=True  # Add vision IDs like "Picture 1:", "Picture 2:", etc.
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
            
            # Move inputs to device with correct dtype
            inputs = inputs.to(self.model.device, dtype=torch.float16)
            
            # Generate response with memory optimizations
            with torch.inference_mode():
                if do_sample and temperature > 0:
                    generated_ids = self.model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
                        do_sample=True,
                        temperature=temperature,
                        use_cache=True,
                        pad_token_id=self.processor.tokenizer.eos_token_id,
                    )
                else:
                    generated_ids = self.model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
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
            
            # No cleanup needed - images processed in memory
            
            # Clear cache after processing
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Return the first (and should be only) response
            return output_text[0].strip() if output_text else ""
            
        except Exception as e:
            logger.error(f"Error during Qwen2.5-7B response generation: {str(e)}")
            # Clear cache on error
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            raise
    
    def generate_response_stream(self, 
                               text_input: str, 
                               image_paths: Optional[List[str]] = None,
                               conversation_history: Optional[List[tuple]] = None,
                               max_new_tokens: int = 512,
                               temperature: float = 0.7,
                               do_sample: bool = True,
                               upload_folder: Optional[str] = None) -> Iterator[str]:
        """
        Generate streaming response using TextIteratorStreamer.
        Yields tokens as they are generated.
        """
        if not self.is_loaded:
            raise RuntimeError("Qwen2.5-7B model not loaded. Please call load_model() first.")
        
        try:
            # Use consolidated message creation with system prompt for streaming
            messages, _ = self._create_messages(text_input, image_paths, conversation_history, include_system_prompt=True, upload_folder=upload_folder)
            
            # Prepare inputs using the processor
            text_prompt = self.processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
                add_vision_id=True  # Add vision IDs like "Picture 1:", "Picture 2:", etc.
            )
            
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.processor(
                text=[text_prompt],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            )
            # Fix data type mismatch - use correct dtype when moving to device
            inputs = inputs.to(self.device, dtype=torch.float16)
            
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
            logger.error(f"Error during Qwen2.5-7B streaming generation: {str(e)}")
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
                "max_images_per_request": self.max_images_per_request
            }
        } 