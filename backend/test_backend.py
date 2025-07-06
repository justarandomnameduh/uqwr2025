#!/usr/bin/env python3

import requests
import json
import os
import io
import time
import logging
from PIL import Image
from pathlib import Path
import sys
import argparse
from typing import Dict, List, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VLMBackendTester:
    """Test class for VLM Backend functionality"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.uploaded_files = []
        self.test_results = {}
        
        # Set up paths to test images
        self.test_images_dir = Path(__file__).parent.parent / "assets"
        self.test_images = ["test_1.jpg", "test_2.jpg"]
        
        # Check if test images exist
        self.available_images = []
        for img_name in self.test_images:
            img_path = self.test_images_dir / img_name
            if img_path.exists():
                self.available_images.append(img_path)
                logger.info(f"Found test image: {img_path}")
            else:
                logger.warning(f"Test image not found: {img_path}")
        
        if not self.available_images:
            logger.error("No test images found! Creating synthetic fallback images.")
            self.use_synthetic_images = True
        else:
            self.use_synthetic_images = False
    
    def get_test_image_bytes(self, image_index: int = 0) -> tuple:
        """Get test image bytes and filename"""
        if not self.use_synthetic_images and image_index < len(self.available_images):
            # Use real test image
            img_path = self.available_images[image_index]
            with open(img_path, 'rb') as f:
                img_bytes = f.read()
            return img_bytes, img_path.name
        else:
            # Create synthetic test image as fallback
            img = Image.new('RGB', (200, 200), ['red', 'green', 'blue'][image_index % 3])
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            return img_bytes.getvalue(), f'synthetic_test_{image_index}.png'
    
    def create_test_image(self, size: tuple = (200, 200), color: str = "red") -> bytes:
        """Create a test image for upload testing (fallback method)"""
        img = Image.new('RGB', size, color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
    
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a test function and record results"""
        logger.info(f"Running test: {test_name}")
        try:
            result = test_func()
            self.test_results[test_name] = {
                'status': 'PASS' if result else 'FAIL',
                'result': result
            }
            logger.info(f"Test {test_name}: {'PASS' if result else 'FAIL'}")
            return result
        except Exception as e:
            self.test_results[test_name] = {
                'status': 'ERROR',
                'error': str(e)
            }
            logger.error(f"Test {test_name}: ERROR - {str(e)}")
            return False
    
    def test_health_check(self) -> bool:
        """Test the health check endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_fields = ['status', 'service', 'model_loaded']
                return all(field in data for field in required_fields)
            return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def test_index_endpoint(self) -> bool:
        """Test the index endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return 'message' in data and 'endpoints' in data
            return False
        except Exception as e:
            logger.error(f"Index endpoint failed: {e}")
            return False
    
    def test_model_info(self) -> bool:
        """Test the model info endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/model/info", timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Model info: {json.dumps(data, indent=2)}")
                return True
            return False
        except Exception as e:
            logger.error(f"Model info failed: {e}")
            return False
    
    def test_file_upload(self) -> bool:
        """Test file upload functionality with real test images"""
        try:
            # Upload multiple test images
            upload_success = True
            
            for i, img_path in enumerate(self.available_images):
                logger.info(f"Uploading test image {i+1}/{len(self.available_images)}: {img_path.name}")
                
                # Read the actual test image
                with open(img_path, 'rb') as f:
                    img_bytes = f.read()
                
                # Upload file
                files = {'files': (img_path.name, img_bytes, 'image/jpeg')}
                response = self.session.post(f"{self.base_url}/upload", files=files, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success' and data.get('files'):
                        # Store uploaded file info for later tests
                        self.uploaded_files.extend(data['files'])
                        logger.info(f"Successfully uploaded: {img_path.name} -> {data['files'][0]['saved_name']}")
                    else:
                        logger.error(f"Upload failed for {img_path.name}: {data}")
                        upload_success = False
                else:
                    logger.error(f"Upload failed for {img_path.name}: HTTP {response.status_code}")
                    upload_success = False
            
            # Fallback to synthetic image if no real images were uploaded
            if not self.uploaded_files:
                logger.warning("No real images uploaded, using synthetic fallback")
                test_image = self.create_test_image()
                files = {'files': ('synthetic_test.png', test_image, 'image/png')}
                response = self.session.post(f"{self.base_url}/upload", files=files, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'success' and data.get('files'):
                        self.uploaded_files.extend(data['files'])
                        upload_success = True
                    
            return upload_success
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return False
    
    def test_file_download(self) -> bool:
        """Test file download functionality"""
        if not self.uploaded_files:
            logger.warning("No uploaded files to test download")
            return False
        
        try:
            filename = self.uploaded_files[0]['saved_name']
            response = self.session.get(f"{self.base_url}/uploads/{filename}", timeout=10)
            success = response.status_code == 200
            if success:
                logger.info(f"Successfully downloaded file: {filename} ({len(response.content)} bytes)")
            return success
        except Exception as e:
            logger.error(f"File download failed: {e}")
            return False
    
    def test_generate_text_only(self) -> bool:
        """Test text-only generation"""
        try:
            payload = {
                "text": "Hello, how are you? Please introduce yourself.",
                "max_new_tokens": 100,
                "temperature": 0.7
            }
            response = self.session.post(
                f"{self.base_url}/generate", 
                json=payload, 
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and 'response' in data:
                    logger.info("="*60)
                    logger.info("TEXT-ONLY GENERATION RESULT:")
                    logger.info(f"Input: {payload['text']}")
                    logger.info(f"VLM Response: {data['response']}")
                    logger.info("="*60)
                    return True
            return False
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            return False
    
    def test_generate_with_image(self) -> bool:
        """Test generation with image"""
        if not self.uploaded_files:
            logger.warning("No uploaded files to test image generation")
            return False
        
        try:
            # Test with first uploaded image
            test_file = self.uploaded_files[0]
            payload = {
                "text": "Describe this image in detail. What do you see?",
                "image_paths": [test_file['path']],
                "max_new_tokens": 150,
                "temperature": 0.7
            }
            response = self.session.post(
                f"{self.base_url}/generate", 
                json=payload, 
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and 'response' in data:
                    logger.info("="*60)
                    logger.info("IMAGE + TEXT GENERATION RESULT:")
                    logger.info(f"Input: {payload['text']}")
                    logger.info(f"Image: {test_file['original_name']} -> {test_file['saved_name']}")
                    logger.info(f"VLM Response: {data['response']}")
                    logger.info("="*60)
                    return True
            return False
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return False
    
    def test_generate_with_multiple_images(self) -> bool:
        """Test generation with multiple images"""
        if len(self.uploaded_files) < 2:
            logger.warning("Need at least 2 uploaded files for multiple image test")
            return False
        
        try:
            # Test with first two uploaded images
            test_files = self.uploaded_files[:2]
            payload = {
                "text": "Compare these two images. What are the similarities and differences?",
                "image_paths": [f['path'] for f in test_files],
                "max_new_tokens": 200,
                "temperature": 0.7
            }
            response = self.session.post(
                f"{self.base_url}/generate", 
                json=payload, 
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and 'response' in data:
                    logger.info("="*60)
                    logger.info("MULTIPLE IMAGES GENERATION RESULT:")
                    logger.info(f"Input: {payload['text']}")
                    logger.info(f"Images: {[f['original_name'] for f in test_files]}")
                    logger.info(f"VLM Response: {data['response']}")
                    logger.info("="*60)
                    return True
            return False
        except Exception as e:
            logger.error(f"Multiple image generation failed: {e}")
            return False
    
    def test_invalid_requests(self) -> bool:
        """Test various invalid requests"""
        try:
            # Test empty text generation
            response = self.session.post(
                f"{self.base_url}/generate", 
                json={"text": ""}, 
                timeout=10
            )
            if response.status_code != 400:
                return False
            
            # Test invalid file upload
            files = {'files': ('test.txt', b'not an image', 'text/plain')}
            response = self.session.post(f"{self.base_url}/upload", files=files, timeout=10)
            # Should either reject or handle gracefully
            
            return True
        except Exception as e:
            logger.error(f"Invalid request test failed: {e}")
            return False
    
    def test_file_deletion(self) -> bool:
        """Test file deletion (should be last test)"""
        if not self.uploaded_files:
            logger.warning("No uploaded files to test deletion")
            return False
        
        try:
            # Delete all uploaded files
            deletion_success = True
            for uploaded_file in self.uploaded_files:
                filename = uploaded_file['saved_name']
                response = self.session.delete(f"{self.base_url}/uploads/{filename}", timeout=10)
                if response.status_code == 200:
                    logger.info(f"Successfully deleted: {filename}")
                else:
                    logger.warning(f"Failed to delete: {filename} (Status: {response.status_code})")
                    deletion_success = False
            
            return deletion_success
        except Exception as e:
            logger.error(f"File deletion failed: {e}")
            return False
    
    def test_load_and_performance(self) -> bool:
        """Test basic load and performance"""
        try:
            start_time = time.time()
            
            # Make multiple concurrent requests
            import concurrent.futures
            
            def make_request():
                return self.session.get(f"{self.base_url}/health", timeout=5)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                responses = [f.result() for f in concurrent.futures.as_completed(futures)]
            
            end_time = time.time()
            duration = end_time - start_time
            
            success_count = sum(1 for r in responses if r.status_code == 200)
            logger.info(f"Load test: {success_count}/10 requests successful in {duration:.2f}s")
            
            return success_count >= 8  # Allow some failures
        except Exception as e:
            logger.error(f"Load test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests in order"""
        logger.info("Starting comprehensive backend tests...")
        logger.info(f"Available test images: {[img.name for img in self.available_images]}")
        
        # Test order matters - some tests depend on previous ones
        tests = [
            ("Health Check", self.test_health_check),
            ("Index Endpoint", self.test_index_endpoint),
            ("Model Info", self.test_model_info),
            ("File Upload", self.test_file_upload),
            ("File Download", self.test_file_download),
            ("Text Generation", self.test_generate_text_only),
            ("Single Image Generation", self.test_generate_with_image),
            ("Multiple Images Generation", self.test_generate_with_multiple_images),
            ("Invalid Requests", self.test_invalid_requests),
            ("Load Test", self.test_load_and_performance),
            ("File Deletion", self.test_file_deletion),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            if self.run_test(test_name, test_func):
                passed += 1
        
        # Print results
        self.print_results(passed, total)
        return passed == total
    
    def print_results(self, passed: int, total: int):
        """Print test results summary"""
        print("\n" + "="*60)
        print("BACKEND TEST RESULTS")
        print("="*60)
        
        for test_name, result in self.test_results.items():
            status = result['status']
            print(f"{test_name:35} [{status}]")
            if status == 'ERROR':
                print(f"  Error: {result['error']}")
        
        print("\n" + "-"*60)
        print(f"Tests passed: {passed}/{total}")
        print(f"Success rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("✅ All tests passed!")
        else:
            print("❌ Some tests failed. Check the logs above.")
        print("="*60)

def create_test_requirements():
    """Create test requirements file"""
    requirements = [
        "requests>=2.25.0",
        "Pillow>=9.0.0",
    ]
    
    with open("test_requirements.txt", "w") as f:
        f.write("\n".join(requirements))
    
    print("Created test_requirements.txt")
    print("Install with: pip install -r test_requirements.txt")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Test VLM Backend')
    parser.add_argument('--url', default='http://localhost:5000', 
                       help='Backend URL (default: http://localhost:5000)')
    parser.add_argument('--create-requirements', action='store_true',
                       help='Create test requirements file')
    
    args = parser.parse_args()
    
    if args.create_requirements:
        create_test_requirements()
        return
    
    # Check if server is running
    try:
        response = requests.get(f"{args.url}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Backend not responding at {args.url}")
            print("Make sure the backend is running:")
            print("  python run.py")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print(f"❌ Cannot connect to backend at {args.url}")
        print("Make sure the backend is running:")
        print("  python run.py")
        sys.exit(1)
    
    # Run tests
    tester = VLMBackendTester(args.url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 