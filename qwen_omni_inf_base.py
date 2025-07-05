#!/usr/bin/env python3

import os
import sys
import argparse
from typing import List, Optional, Union
from PIL import Image
import torch

from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor
from qwen_omni_utils import process_mm_info


class QwenOmniInference:
    
    def __init__(self, model_name: str = "Qwen/Qwen2.5-Omni-3B", device_map: str = "auto"):

        print(f"Loading model: {model_name}")
        self.model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
            device_map=device_map,
            # attn_implementation="flash_attention_2",
        )
        
        self.processor = Qwen2_5OmniProcessor.from_pretrained(model_name)
        
        self.system_prompt = (
            "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."
        )
    
    def create_conversation(self, 
                          text_input: str, 
                          image_paths: Optional[List[str]] = None) -> List[dict]:

        # System message
        conversation = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": self.system_prompt}
                ],
            }
        ]
        
        # User message content
        user_content = []
        
        # Add images if provided
        if image_paths:
            for img_path in image_paths:
                if os.path.exists(img_path):
                    user_content.append({"type": "image", "image": img_path})
                else:
                    print(f"Warning: Image file not found: {img_path}")
        
        # Add text
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

        conversation = self.create_conversation(text_input, image_paths)
        
        text_prompt = self.processor.apply_chat_template(
            conversation, 
            add_generation_prompt=True, 
            tokenize=False,
        )
        
        # # Process multimedia info
        audios, images, videos = process_mm_info(conversation, use_audio_in_video=False)
        
        # # Prepare model inputs
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
        # Generate response (text only, no audio)
        with torch.no_grad():
            text_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                use_audio_in_video=False,
                # do_sample=True,
                # temperature=temperature,
                return_audio=False,  # Disable audio output
            )

        text = self.processor.batch_decode(text_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        
        return text


def main():
    """Main function to demonstrate the model capabilities."""
    parser = argparse.ArgumentParser(description="Qwen2.5-Omni-3B Inference Demo")
    parser.add_argument("--model", default="Qwen/Qwen2.5-Omni-3B", 
                       help="Model name or path")
    parser.add_argument("--interactive", action="store_true",
                       help="Run in interactive mode")
    parser.add_argument("--test-images", nargs="*", 
                       default=["test_1.jpg", "test_2.jpg"],
                       help="Test image paths")
    
    args = parser.parse_args()
    
    # Initialize model
    model = QwenOmniInference(args.model)
    
    if args.interactive:
        # Interactive mode
        print("\n=== Qwen2.5-Omni Interactive Demo ===")
        print("Commands:")
        print("  text: <your question>")
        print("  image: <path_to_image> <your question>")
        print("  images: <path1> <path2> <your question>")
        print("  quit: exit")
        print()
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if user_input.startswith('text:'):
                    # Text-only input
                    text = user_input[5:].strip()
                    response = model.generate_response(text)
                    print(f"\nResponse: {response}")
                
                elif user_input.startswith('image:'):
                    # Single image input
                    parts = user_input[6:].strip().split(' ', 1)
                    if len(parts) == 2:
                        image_path, text = parts
                        response = model.generate_response(text, [image_path])
                        print(f"\nResponse: {response}")
                    else:
                        print("Usage: image: <path> <question>")
                
                elif user_input.startswith('images:'):
                    # Multiple images input
                    parts = user_input[7:].strip().split()
                    if len(parts) >= 3:
                        # Assume last part is the question
                        image_paths = parts[:-1]
                        text = parts[-1]
                        response = model.generate_response(text, image_paths)
                        print(f"\nResponse: {response}")
                    else:
                        print("Usage: images: <path1> <path2> <question>")
                
                else:
                    # Default: treat as text input
                    response = model.generate_response(user_input)
                    print(f"\nResponse: {response}")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    else:
        # Demo mode with test cases
        print("\n=== Qwen2.5-Omni Demo ===")
        
        # Test 1: Text-only (0 images)
        print("\n1. Text-to-Text (0 images)")
        print("Question: What is artificial intelligence?")
        response = model.generate_response(
            "What is artificial intelligence? Provide a brief explanation."
        )
        print(f"Response: {response}")
        
        # Test 2: Single image (1 image)
        print("\n2. Image-to-Text (1 image)")
        test_img_1 = args.test_images[0] if args.test_images else "test_1.jpg"
        if os.path.exists(test_img_1):
            print(f"Image: {test_img_1}")
            print("Question: Describe what you see in this image.")
            response = model.generate_response(
                "Describe what you see in this image in detail.",
                [test_img_1]
            )
            print(f"Response: {response}")
        else:
            print(f"Test image not found: {test_img_1}")
        
        # Test 3: Image with text question (1 image)
        print("\n3. Image-Text-to-Text (1 image)")
        if os.path.exists(test_img_1):
            print(f"Image: {test_img_1}")
            print("Question: What colors are prominent in this image?")
            response = model.generate_response(
                "What colors are most prominent in this image?",
                [test_img_1]
            )
            print(f"Response: {response}")
        
        # Test 4: Multiple images (2 images)
        print("\n4. Multiple Images-to-Text (2 images)")
        test_img_2 = args.test_images[1] if len(args.test_images) > 1 else "test_2.jpg"
        if os.path.exists(test_img_1) and os.path.exists(test_img_2):
            print(f"Images: {test_img_1}, {test_img_2}")
            print("Question: Compare these two images.")
            response = model.generate_response(
                "Compare these two images. What are the similarities and differences?",
                [test_img_1, test_img_2]
            )
            print(f"Response: {response}")
        else:
            print("One or more test images not found")
        
        # Test 5: Template text for image-only (1 image)
        print("\n5. Image-only with Template Text (1 image)")
        if os.path.exists(test_img_1):
            print(f"Image: {test_img_1}")
            print("Template: Analyze this image and provide insights.")
            response = model.generate_response(
                "Analyze this image and provide insights about its content, composition, and any notable features.",
                [test_img_1]
            )
            print(f"Response: {response}")


if __name__ == "__main__":
    main() 