import os
import uuid
import logging
from werkzeug.utils import secure_filename
from flask import jsonify, request, current_app
from app.vlm_client import get_vlm_service
from app.trans_client import get_transcription_service

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'flac', 'ogg', 'm4a', 'aac', 'mp4', 'mov', 'avi', 'mkv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_audio_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

def register_routes(app):
    @app.route('/health', methods=['GET'])
    def health_check():
        vlm_service = get_vlm_service()
        vlm_model_info = vlm_service.get_model_info()
        
        trans_service = get_transcription_service()
        trans_model_info = trans_service.get_model_info()
        
        return jsonify({
            'status': 'healthy',
            'service': 'qwen-omni-vlm-backend',
            'vlm_model_loaded': vlm_service.is_loaded(),
            'vlm_model_info': vlm_model_info,
            'transcription_model_loaded': trans_service.is_loaded(),
            'transcription_model_info': trans_model_info
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
                'upload': '/upload',
                'transcription_model_info': '/transcription/model/info',
                'transcription_model_reload': '/transcription/model/reload',
                'upload_audio': '/transcription/upload',
                'transcribe': '/transcription/transcribe',
                'upload_and_transcribe': '/transcription/upload_and_transcribe'
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
    
    # Transcription service routes
    @app.route('/transcription/model/info', methods=['GET'])
    def transcription_model_info():
        trans_service = get_transcription_service()
        return jsonify(trans_service.get_model_info())
    
    @app.route('/transcription/model/reload', methods=['POST'])
    def reload_transcription_model():
        try:
            trans_service = get_transcription_service()
            trans_service.unload_model()
            
            if trans_service.load_model():
                return jsonify({
                    'status': 'success',
                    'message': 'Transcription model reloaded successfully'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Failed to reload transcription model'
                }), 500
                
        except Exception as e:
            logger.error(f"Error reloading transcription model: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/transcription/upload', methods=['POST'])
    def upload_audio_file():
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
                    
                if file and allowed_audio_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    
                    uploaded_files.append({
                        'original_name': filename,
                        'saved_name': unique_filename,
                        'path': unique_filename  # Return relative path for API use
                    })
                    
                    logger.info(f"Audio file uploaded: {unique_filename}")
                else:
                    logger.warning(f"Invalid audio file type: {file.filename}")
            
            if not uploaded_files:
                return jsonify({
                    'status': 'error',
                    'message': 'No valid audio files uploaded'
                }), 400
            
            return jsonify({
                'status': 'success',
                'message': f'Successfully uploaded {len(uploaded_files)} audio files',
                'files': uploaded_files
            })
            
        except Exception as e:
            logger.error(f"Error uploading audio files: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/transcription/transcribe', methods=['POST'])
    def transcribe_audio():
        try:
            trans_service = get_transcription_service()
            
            if not trans_service.is_loaded():
                return jsonify({
                    'status': 'error',
                    'message': 'Transcription model not loaded'
                }), 503
            
            data = request.json
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'JSON data is required'
                }), 400
            
            # Get audio file path
            audio_path = data.get('audio_path', '').strip()
            if not audio_path:
                return jsonify({
                    'status': 'error',
                    'message': 'Audio path is required'
                }), 400
            
            # Get optional parameters
            return_timestamps = data.get('return_timestamps', False)
            batch_size = data.get('batch_size', 8)
            keep_mp3 = data.get('keep_mp3', True)
            
            # Construct full path
            full_audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], audio_path)
            
            if not os.path.exists(full_audio_path):
                return jsonify({
                    'status': 'error',
                    'message': 'Audio file not found'
                }), 404
            
            # Process the audio file
            result = trans_service.process_audio_file(
                input_file_path=full_audio_path,
                output_dir=current_app.config['UPLOAD_FOLDER'],
                return_timestamps=return_timestamps,
                batch_size=batch_size,
                keep_mp3=keep_mp3
            )
            
            return jsonify({
                'status': 'success',
                'transcription_text': result['transcription']['text'],
                'transcription_chunks': result['transcription']['chunks'],
                'mp3_filename': result['mp3_filename'],
                'original_file': audio_path,
                'return_timestamps': return_timestamps
            })
            
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/transcription/upload_and_transcribe', methods=['POST'])
    def upload_and_transcribe():
        """
        Combined endpoint: upload audio file and return transcription text
        This is the main endpoint that the frontend should use to get transcription
        text that can be appended to chat input.
        """
        try:
            trans_service = get_transcription_service()
            
            if not trans_service.is_loaded():
                return jsonify({
                    'status': 'error',
                    'message': 'Transcription model not loaded'
                }), 503
            
            if 'file' not in request.files:
                return jsonify({
                    'status': 'error',
                    'message': 'No audio file provided'
                }), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    'status': 'error',
                    'message': 'No file selected'
                }), 400
            
            if not file or not allowed_audio_file(file.filename):
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid audio file type'
                }), 400
            
            # Get optional parameters
            return_timestamps = request.form.get('return_timestamps', 'false').lower() == 'true'
            batch_size = int(request.form.get('batch_size', 8))
            keep_mp3 = request.form.get('keep_mp3', 'true').lower() == 'true'
            
            # Save uploaded file temporarily
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            temp_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(temp_filepath)
            
            try:
                # Process the audio file
                result = trans_service.process_audio_file(
                    input_file_path=temp_filepath,
                    output_dir=current_app.config['UPLOAD_FOLDER'],
                    return_timestamps=return_timestamps,
                    batch_size=batch_size,
                    keep_mp3=keep_mp3
                )
                
                # Clean up original uploaded file
                os.remove(temp_filepath)
                
                return jsonify({
                    'status': 'success',
                    'transcription_text': result['transcription']['text'],
                    'transcription_chunks': result['transcription']['chunks'] if return_timestamps else None,
                    'mp3_filename': result['mp3_filename'] if keep_mp3 else None,
                    'original_filename': filename,
                    'return_timestamps': return_timestamps
                })
                
            except Exception as e:
                # Clean up temporary file on error
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                raise
            
        except Exception as e:
            logger.error(f"Error in upload_and_transcribe: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
 