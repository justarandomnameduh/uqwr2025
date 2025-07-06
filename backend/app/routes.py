import os
import uuid
import logging
from werkzeug.utils import secure_filename
from flask import jsonify, request, current_app
from app.vlm_client import get_vlm_service

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def register_routes(app):
    @app.route('/health', methods=['GET'])
    def health_check():
        vlm_service = get_vlm_service()
        model_info = vlm_service.get_model_info()
        
        return jsonify({
            'status': 'healthy',
            'service': 'qwen-omni-vlm-backend',
            'model_loaded': vlm_service.is_loaded(),
            'model_info': model_info
        })
    
    @app.route('/', methods=['GET'])
    def index():
        return jsonify({
            'message': 'VLM Chatbot Backend API',
            'version': '1.0.0',
            'endpoints': {
                'health': '/health',
                'model_info': '/model/info',
                'generate': '/generate',
                'upload': '/upload'
            }
        })
    
    @app.route('/model/info', methods=['GET'])
    def model_info():
        vlm_service = get_vlm_service()
        return jsonify(vlm_service.get_model_info())
    
    @app.route('/model/reload', methods=['POST'])
    def reload_model():
        try:
            vlm_service = get_vlm_service()
            vlm_service.unload_model()
            
            if vlm_service.load_model():
                return jsonify({
                    'status': 'success',
                    'message': 'Model reloaded successfully'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to reload model'
                }), 500
                
        except Exception as e:
            logger.error(f"Error reloading model: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/generate', methods=['POST'])
    def generate_response():
        try:
            vlm_service = get_vlm_service()
            
            if not vlm_service.is_loaded():
                return jsonify({
                    'status': 'error',
                    'message': 'VLM model not loaded'
                }), 503
            
            # Get text input
            text_input = request.json.get('text', '').strip()
            if not text_input:
                return jsonify({
                    'status': 'error',
                    'message': 'Text input is required'
                }), 400
            
            # Get optional parameters
            max_new_tokens = request.json.get('max_new_tokens', 512)
            temperature = request.json.get('temperature', 0.7)
            image_paths = request.json.get('image_paths', [])
            
            # Validate image paths
            validated_paths = []
            for path in image_paths:
                full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], path)
                if os.path.exists(full_path):
                    validated_paths.append(full_path)
                else:
                    logger.warning(f"Image not found: {path}")
            
            # Generate response
            response = vlm_service.generate_response(
                text_input=text_input,
                image_paths=validated_paths if validated_paths else None,
                max_new_tokens=max_new_tokens,
                temperature=temperature
            )
            
            return jsonify({
                'status': 'success',
                'response': response,
                'text_input': text_input,
                'images_used': len(validated_paths)
            })
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/upload', methods=['POST'])
    def upload_file():
        try:
            if 'files' not in request.files:
                return jsonify({
                    'status': 'error',
                    'message': 'No files provided'
                }), 400
            
            files = request.files.getlist('files')
            if not files or all(f.filename == '' for f in files):
                return jsonify({
                    'status': 'error',
                    'message': 'No files selected'
                }), 400
            
            uploaded_files = []
            
            for file in files:
                if file.filename == '':
                    continue
                    
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    
                    uploaded_files.append({
                        'original_name': filename,
                        'saved_name': unique_filename,
                        'path': unique_filename  # Return relative path for API use
                    })
                    
                    logger.info(f"File uploaded: {unique_filename}")
                else:
                    logger.warning(f"Invalid file type: {file.filename}")
            
            if not uploaded_files:
                return jsonify({
                    'status': 'error',
                    'message': 'No valid image files uploaded'
                }), 400
            
            return jsonify({
                'status': 'success',
                'message': f'Successfully uploaded {len(uploaded_files)} files',
                'files': uploaded_files
            })
            
        except Exception as e:
            logger.error(f"Error uploading files: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/uploads/<filename>', methods=['GET'])
    def get_uploaded_file(filename):
        try:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(filepath):
                from flask import send_file
                return send_file(filepath)
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'File not found'
                }), 404
                
        except Exception as e:
            logger.error(f"Error serving file: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/uploads/<filename>', methods=['DELETE'])
    def delete_uploaded_file(filename):
        try:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                return jsonify({
                    'status': 'success',
                    'message': 'File deleted successfully'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'File not found'
                }), 404
                
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500 