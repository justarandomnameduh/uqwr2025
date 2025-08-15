import os
import torch
import gc
import logging
from typing import List, Optional, Dict, Any, Iterator
from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration, TextIteratorStreamer

# Compatibility patch for PyTorch versions that don't have torch.compiler.is_compiling
if hasattr(torch, 'compiler') and not hasattr(torch.compiler, 'is_compiling'):
    # Add the missing is_compiling function for compatibility
    def _is_compiling():
        return False
    torch.compiler.is_compiling = _is_compiling
    logger = logging.getLogger(__name__)
    logger.info("Applied compatibility patch for torch.compiler.is_compiling")

from PIL import Image
from threading import Thread
from utils.common import preprocess_image_in_memory

logger = logging.getLogger(__name__)

class WisWheat_LLavaNext_Mistral_7BService:
    def __init__(self, device_map: str = "auto"):
        self.model_name = "llava-hf/llava-v1.6-mistral-7b-hf"
        self.device_map = device_map
        self.model = None
        self.processor = None
        self.is_loaded = False
        
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        logger.info(f"LLavaNext-Mistral-7B using device: {self.device}")
        
        self.system_prompt = "You are a helpful assistant."
        
        self.max_image_size = (1024, 1024)
        self.min_pixels = 256 * 28 * 28
        self.max_pixels = 1280 * 28 * 28
        self.max_images_per_request = 10    # Maximum number of images per request
        
    def load_model(self) -> bool:
        if self.is_loaded:
            logger.info("WisWheat-LLavaNext-Mistral-7B model already loaded")
            return True
        
        try:
            logger.info(f"Loading WisWheat-LLavaNext-Mistral-7B model: {self.model_name}")
            
            self.model = LlavaNextForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map=self.device_map,
                low_cpu_mem_usage=True,
            )
            
            self.processor = LlavaNextProcessor.from_pretrained(
                self.model_name)
            
            self.is_loaded = True
            logger.info(f"WisWheat-LLavaNext-Mistral-7B model loaded successfully with memory optimizations.")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load WisWheat-LLavaNext-Mistral-7B model: {str(e)}")
            self._cleanup()
            return False
        
    def _cleanup(self):
        if self.model is not None:
            del self.model
            self.model = None
            
        if self.processor is not None:
            del self.processor
            self.processor = None
            
    def unload_model(self):
        if self.model is not None:
            del self.model
            self.model = None
            
        if self.processor is not None:
            del self.processor
            self.processor = None
            
    def _create_messages(self, 
                         text_input: str, 
                         image_paths: Optional[List[str]] = None,
                         conversation_history: Optional[List[tuple]] = None,
                         include_system_prompt: bool = False) -> tuple:
        """
        Create messages in LLaVA-Next format using proper conversation structure.
        Includes conversation history as context in text format.
        Returns: (conversation, processed_images)
        """
        processed_images = []
        content = []

        # Process images first if provided
        if image_paths:
            logger.info(f"Processing {len(image_paths)} images for LLaVA-Next")
            for i, img_path in enumerate(image_paths[:self.max_images_per_request]):
                if os.path.exists(img_path):
                    try:
                        # Process image in memory to avoid disk I/O
                        pil_image = preprocess_image_in_memory(img_path, self.max_image_size)
                        processed_images.append(pil_image)
                        # Add image placeholder to content with index for debugging
                        content.append({"type": "image"})
                        logger.info(f"Successfully processed image {i+1}: {img_path}")
                    except Exception as e:
                        logger.warning(f"Failed to process image {img_path}: {e}")
                else:
                    logger.warning(f"Image file not found: {img_path}")
                    
            if len(image_paths) > self.max_images_per_request:
                logger.warning(f"Limited to {self.max_images_per_request} images for memory efficiency. Provided: {len(image_paths)}")
            
            logger.info(f"Total processed images: {len(processed_images)}")
        
        # Build conversation context from history (LLaVA format with combined text)
        enhanced_text = text_input
        if conversation_history:
            context_parts = []
            for user_msg, assistant_msg in conversation_history:
                context_parts.append(f"Previous conversation:\nUser: {user_msg.content}")
                context_parts.append(f"Assistant: {assistant_msg.content}")
            context_text = "\n\n".join(context_parts)
            enhanced_text = f"{context_text}\n\nCurrent conversation:\nUser: {text_input}"
            logger.info(f"Added {len(conversation_history)} conversation pairs as context")
        
        # Add system prompt if requested (for LLaVA, we include it in the text)
        if include_system_prompt:
            if conversation_history:
                enhanced_text = f"{self.system_prompt}\n\n{enhanced_text}"
            else:
                enhanced_text = f"{self.system_prompt}\n\n{text_input}"
        
        # Add text to content
        if processed_images:
            if len(processed_images) > 1:
                # For multiple images, make the prompt more explicit
                enhanced_text = f"I am showing you {len(processed_images)} images. {enhanced_text}"
            
        content.append({"type": "text", "text": enhanced_text})
        
        # Create conversation in the format expected by LLaVA-Next
        conversation = [
            {
                "role": "user",
                "content": content
            }
        ]
        
        logger.info(f"Conversation structure: {len(content)} content items ({len(processed_images)} images + 1 text)")
        logger.info(f"Enhanced text prompt: {enhanced_text}")
        return conversation, processed_images

    def _create_messages_alternative(self, 
                         text_input: str, 
                         image_paths: Optional[List[str]] = None,
                         conversation_history: Optional[List[tuple]] = None,
                         include_system_prompt: bool = False) -> tuple:
        """
        Alternative multi-image conversation structure based on LLaVA-NeXT-Interleave approach.
        Returns: (conversation, processed_images)
        """
        processed_images = []
        content = []

        if image_paths and len(image_paths) > 1:
            logger.info(f"Using alternative multi-image structure for {len(image_paths)} images")
            
            # For multiple images, create an interleaved structure
            for i, img_path in enumerate(image_paths[:self.max_images_per_request]):
                if os.path.exists(img_path):
                    try:
                        # Process image in memory to avoid disk I/O
                        pil_image = preprocess_image_in_memory(img_path, self.max_image_size)
                        processed_images.append(pil_image)
                        
                        # Add image with contextual text
                        content.append({"type": "image"})
                        content.append({"type": "text", "text": f"Image {i+1}: "})
                        
                        logger.info(f"Added image {i+1} to interleaved structure")
                    except Exception as e:
                        logger.warning(f"Failed to process image {img_path}: {e}")
            
            # Build conversation context and add main question at the end
            final_text = text_input
            if conversation_history:
                context_parts = []
                for user_msg, assistant_msg in conversation_history:
                    context_parts.append(f"Previous conversation:\nUser: {user_msg.content}")
                    context_parts.append(f"Assistant: {assistant_msg.content}")
                context_text = "\n\n".join(context_parts)
                final_text = f"{context_text}\n\nCurrent conversation:\nUser: {text_input}"
                logger.info(f"Added {len(conversation_history)} conversation pairs as context (alternative structure)")
            
            content.append({"type": "text", "text": f"\n\nBased on all {len(processed_images)} images above, {final_text}"})
            
        else:
            # Single image or no image - use standard structure
            return self._create_messages(text_input, image_paths, conversation_history, include_system_prompt)

        conversation = [
            {
                "role": "user", 
                "content": content
            }
        ]
        
        logger.info(f"Alternative structure: {len(content)} content items for {len(processed_images)} images")
        return conversation, processed_images

    def generate_response(self, 
                         text_input: str, 
                         image_paths: Optional[List[str]] = None,
                         conversation_history: Optional[List[tuple]] = None,
                         max_new_tokens: int = 512,
                         temperature: float = 0.7,
                         do_sample: bool = True,
                         use_alternative_structure: bool = True,
                         upload_folder: Optional[str] = None) -> str:
        
        if not self.is_loaded:
            raise RuntimeError("LLavaNext-Mistral-7B model not loaded. Please call load_model() first.")
        
        # Choose conversation structure based on number of images
        if image_paths and len(image_paths) > 1 and use_alternative_structure:
            conversation, processed_images = self._create_messages_alternative(text_input, image_paths, conversation_history, include_system_prompt=True)
            logger.info("Using alternative multi-image structure")
        else:
            conversation, processed_images = self._create_messages(text_input, image_paths, conversation_history, include_system_prompt=True)
            logger.info("Using standard conversation structure")
        
        # Apply chat template to get the properly formatted prompt
        prompt = self.processor.apply_chat_template(
            conversation, 
            add_generation_prompt=True,
            add_vision_id=True
        )
        
        logger.info(f"Generated prompt length: {len(prompt)} characters")
        logger.info(f"Number of images being processed: {len(processed_images)}")
        
        # Process inputs - pass images separately if they exist
        if processed_images:
            inputs = self.processor(text=prompt, images=processed_images, return_tensors="pt").to(self.device, dtype=torch.float16)
            logger.info(f"Input tensors shapes: input_ids={inputs['input_ids'].shape}, pixel_values={inputs.get('pixel_values', 'N/A')}")
        else:
            inputs = self.processor(text=prompt, return_tensors="pt").to(self.device, dtype=torch.float16)
            logger.info(f"Input tensors shapes: input_ids={inputs['input_ids'].shape}")

        with torch.inference_mode():
            if do_sample and temperature > 0:
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=True,
                    temperature=temperature,
                    use_cache=True,
                    pad_token_id=self.processor.tokenizer.eos_token_id,
                )
            else:
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                    use_cache=True,
                    pad_token_id=self.processor.tokenizer.eos_token_id,
                )
            
            # Extract only the new tokens (skip the input prompt)
            input_len = inputs["input_ids"].shape[-1]
            generated_tokens = outputs[0][input_len:]
            response = self.processor.decode(generated_tokens, skip_special_tokens=True)
            
            logger.info(f"Generated response length: {len(response)} characters")
            return response
                
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
            },
            "multi_image_support": True,  # Explicitly indicate multi-image support
            "model_type": "LLaVA-NeXT (Mistral-7B)"
        } 
    
    def generate_response_stream(self, 
                               text_input: str, 
                               image_paths: Optional[List[str]] = None,
                               conversation_history: Optional[List[tuple]] = None,
                               max_new_tokens: int = 512,
                               temperature: float = 0.7,
                               do_sample: bool = True,
                               use_alternative_structure: bool = True,
                               upload_folder: Optional[str] = None) -> Iterator[str]:
        
        if not self.is_loaded:
            raise RuntimeError("LLavaNext-Mistral-7B model not loaded. Please call load_model() first.")    
        
        # Choose conversation structure based on number of images
        if image_paths and len(image_paths) > 1 and use_alternative_structure:
            conversation, processed_images = self._create_messages_alternative(text_input, image_paths, conversation_history, include_system_prompt=True)
            logger.info("Using alternative multi-image structure for streaming")
        else:
            conversation, processed_images = self._create_messages(text_input, image_paths, conversation_history, include_system_prompt=True)
            logger.info("Using standard conversation structure for streaming")
        
        # Apply chat template to get the properly formatted prompt
        prompt = self.processor.apply_chat_template(
            conversation, 
            add_generation_prompt=True,
            add_vision_id=True
        )
        
        # Process inputs - pass images separately if they exist  
        if processed_images:
            inputs = self.processor(text=prompt, images=processed_images, return_tensors="pt").to(self.device, dtype=torch.float16)
        else:
            inputs = self.processor(text=prompt, return_tensors="pt").to(self.device, dtype=torch.float16)

        streamer = TextIteratorStreamer(self.processor.tokenizer, skip_prompt=True, skip_special_tokens=True)
        
        generation_kwargs = {
            **inputs,
            "max_new_tokens": max_new_tokens,
            "do_sample": do_sample,
            "use_cache": True,
            "pad_token_id": self.processor.tokenizer.eos_token_id,
            "streamer": streamer,
        }
        
        if do_sample and temperature > 0:
            generation_kwargs["temperature"] = temperature
        
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()
        
        for text in streamer:
            yield text
            
        thread.join()
        