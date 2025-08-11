import os
import uuid
import logging
import json
import time
import threading
from collections import defaultdict
from werkzeug.utils import secure_filename
from flask import jsonify, request, current_app, Response
from app.vlm_client import get_vlm_service
from app.trans_client import get_transcription_service
from models import db
from models.model import ChatSession, ChatMessage

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'flac', 'ogg', 'm4a', 'aac', 'mp4', 'mov', 'avi', 'mkv'}

# In-memory cache for request deduplication (hash -> timestamp)
_request_cache = {}
_cache_lock = threading.Lock()

def _cleanup_request_cache():
    """Remove old entries from request cache"""
    current_time = time.time()
    with _cache_lock:
        keys_to_remove = [
            key for key, timestamp in _request_cache.items()
            if current_time - timestamp > 60  # Remove entries older than 60 seconds
        ]
        for key in keys_to_remove:
            del _request_cache[key]

def _is_duplicate_request(content_hash):
    """Check if this request is a duplicate within the last 10 seconds"""
    current_time = time.time()
    with _cache_lock:
        if content_hash in _request_cache:
            if current_time - _request_cache[content_hash] < 10:  # 10 second window
                return True
        
        _request_cache[content_hash] = current_time
        return False

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
                'available_models': '/model/available',
                'switch_model': '/model/switch',
                'generate': '/generate',
                'upload': '/upload',
                'transcription_model_info': '/transcription/model/info',
                'transcription_model_reload': '/transcription/model/reload',
                'upload_audio': '/transcription/upload',
                'transcribe': '/transcription/transcribe',
                'upload_and_transcribe': '/transcription/upload_and_transcribe',
                'log_assistant_message': '/log/assistant_message',
                'create_session': '/sessions',
                'list_sessions': '/sessions',
                'get_session': '/sessions/{session_id}',
                'delete_session': '/sessions/{session_id}'
            }
        })
    
    @app.route('/model/available', methods=['GET'])
    def get_available_models():
        """Get list of available models and current status"""
        try:
            vlm_service = get_vlm_service()
            available_models = vlm_service.get_available_models()
            current_model_id = vlm_service.get_current_model_id()
            
            return jsonify({
                'status': 'success',
                'available_models': available_models,
                'current_model_id': current_model_id,
                'is_task_running': False  # For compatibility with frontend
            })
            
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/model/switch', methods=['POST'])
    def switch_model():
        """Load a specific model (only if no model is currently loaded)"""
        try:
            data = request.json
            if not data or 'model_id' not in data:
                return jsonify({
                    'status': 'error',
                    'message': 'model_id is required'
                }), 400
            
            model_id = data['model_id']
            vlm_service = get_vlm_service()
            
            # Check if a model is already loaded
            if vlm_service.is_loaded():
                return jsonify({
                    'status': 'error',
                    'message': f'Model {vlm_service.get_current_model_id()} is already loaded. Cannot switch models in this session. Please restart the backend to load a different model.'
                }), 400
            
            # Try to load the requested model
            if vlm_service.load_model(model_id):
                return jsonify({
                    'status': 'success',
                    'message': f'Model {model_id} loaded successfully',
                    'current_model_id': model_id
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'Failed to load model {model_id}'
                }), 500
                
        except Exception as e:
            logger.error(f"Error switching model: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/model/info', methods=['GET'])
    def model_info():
        vlm_service = get_vlm_service()
        return jsonify(vlm_service.get_model_info())
    
    @app.route('/model/reload', methods=['POST'])
    def reload_model():
        try:
            vlm_service = get_vlm_service()
            current_model_id = vlm_service.get_current_model_id()
            
            if not current_model_id:
                return jsonify({
                    'status': 'error',
                    'message': 'No model is currently loaded'
                }), 400
            
            vlm_service.unload_model()
            
            if vlm_service.load_model(current_model_id):
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
                    'message': 'No VLM model loaded. Please select and load a model first.'
                }), 503
            
            # Get and validate session_id
            session_id = request.json.get('session_id', '').strip()
            if not session_id:
                return jsonify({
                    'status': 'error',
                    'message': 'Session ID is required'
                }), 400
            
            # Verify session exists
            session = ChatSession.query.filter_by(id=session_id).first()
            if not session:
                return jsonify({
                    'status': 'error',
                    'message': 'Session not found'
                }), 404
            
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
    
    @app.route('/generate/stream', methods=['POST'])
    def generate_response_stream():
        try:
            vlm_service = get_vlm_service()
            
            if not vlm_service.is_loaded():
                return jsonify({
                    'status': 'error',
                    'message': 'No VLM model loaded. Please select and load a model first.'
                }), 503
            
            # Get and validate session_id
            session_id = request.json.get('session_id', '').strip()
            if not session_id:
                return jsonify({
                    'status': 'error',
                    'message': 'Session ID is required'
                }), 400
            
            # Verify session exists
            session = ChatSession.query.filter_by(id=session_id).first()
            if not session:
                return jsonify({
                    'status': 'error',
                    'message': 'Session not found'
                }), 404
            
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
            
            # Store user message in database BEFORE starting streaming
            try:
                user_message = ChatMessage(
                    session_id=session_id,
                    message_type='user',
                    content=text_input,
                    images=json.dumps(image_paths) if image_paths else None,
                    images_used=len(validated_paths)
                )
                # Generate and set content hash for user message too
                user_message.content_hash = user_message.generate_content_hash()
                db.session.add(user_message)
                
                # Update session timestamp
                session.updated_at = db.func.now()
                db.session.commit()
                
            except Exception as e:
                logger.error(f"Error storing user message: {e}")
                db.session.rollback()
                return jsonify({
                    'status': 'error',
                    'message': f'Failed to store message: {str(e)}'
                }), 500
            
            # Retrieve conversation history for context (after storing current user message)
            conversation_history = ChatMessage.get_conversation_history(session_id, limit_pairs=5)
            logger.info(f"Retrieved {len(conversation_history)} conversation pairs for context")
            
            def generate():
                try:
                    # Send initial metadata
                    yield f"data: {json.dumps({'type': 'start', 'text_input': text_input, 'images_used': len(validated_paths)})}\n\n"
                    
                    # Stream tokens
                    for token in vlm_service.generate_response_stream(
                        text_input=text_input,
                        image_paths=validated_paths if validated_paths else None,
                        conversation_history=conversation_history,
                        max_new_tokens=max_new_tokens,
                        temperature=temperature
                    ):
                        yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                    
                    # Send completion signal
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    
                except Exception as e:
                    logger.error(f"Error during streaming generation: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            
            return Response(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                }
            )
            
        except Exception as e:
            logger.error(f"Error setting up streaming response: {e}")
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
    
    # Session management endpoints
    @app.route('/sessions', methods=['POST'])
    def create_session():
        """Create a new chat session"""
        try:
            data = request.json
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'JSON data is required'
                }), 400
            
            # Validate required fields
            name = data.get('name', '').strip()
            model_id = data.get('model_id', '').strip()
            
            if not name:
                return jsonify({
                    'status': 'error',
                    'message': 'Session name is required'
                }), 400
                
            if not model_id:
                return jsonify({
                    'status': 'error',
                    'message': 'Model ID is required'
                }), 400
            
            # Create new session
            session = ChatSession(name=name, model_id=model_id)
            db.session.add(session)
            db.session.commit()
            
            logger.info(f"Created new session: {session.id} - {session.name} - {session.model_id}")
            
            return jsonify({
                'status': 'success',
                'session': session.to_dict(),
                'message': f'Session "{name}" created successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating session: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/sessions', methods=['GET'])
    def list_sessions():
        """List all chat sessions"""
        try:
            sessions = ChatSession.query.order_by(ChatSession.updated_at.desc()).all()
            return jsonify({
                'status': 'success',
                'sessions': [session.to_dict() for session in sessions]
            })
            
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/sessions/<session_id>', methods=['GET'])
    def get_session(session_id):
        """Get session details with messages"""
        try:
            session = ChatSession.query.filter_by(id=session_id).first()
            if not session:
                return jsonify({
                    'status': 'error',
                    'message': 'Session not found'
                }), 404
            
            # Get messages for this session
            messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.created_at.asc()).all()
            
            return jsonify({
                'status': 'success',
                'session': session.to_dict(),
                'messages': [message.to_dict() for message in messages]
            })
            
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/sessions/<session_id>', methods=['DELETE'])
    def delete_session(session_id):
        """Delete a chat session and all its messages"""
        try:
            session = ChatSession.query.filter_by(id=session_id).first()
            if not session:
                return jsonify({
                    'status': 'error',
                    'message': 'Session not found'
                }), 404
            
            session_name = session.name
            db.session.delete(session)
            db.session.commit()
            
            logger.info(f"Deleted session: {session_id} - {session_name}")
            
            return jsonify({
                'status': 'success',
                'message': f'Session "{session_name}" deleted successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting session {session_id}: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @app.route('/log/assistant_message', methods=['POST'])
    def log_assistant_message():
        """
        Endpoint to receive and store assistant messages in database
        after text streaming is complete
        """
        try:
            data = request.json
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'JSON data is required'
                }), 400
            
            # Get and validate session_id
            session_id = data.get('session_id', '').strip()
            if not session_id:
                return jsonify({
                    'status': 'error',
                    'message': 'Session ID is required'
                }), 400
            
            # Verify session exists
            session = ChatSession.query.filter_by(id=session_id).first()
            if not session:
                return jsonify({
                    'status': 'error',
                    'message': 'Session not found'
                }), 404
            
            # Get message data
            message_id = data.get('message_id', 'unknown')
            content = data.get('content', '')
            timestamp = data.get('timestamp', '')
            user_input = data.get('user_input', '')
            images_used = data.get('images_used', 0)
            
            if not content.strip():
                return jsonify({
                    'status': 'error',
                    'message': 'Message content cannot be empty'
                }), 400
            
            # First check: if we have a valid message_id, check if we've already processed it
            if message_id != 'unknown':
                existing_message_by_id = ChatMessage.query.filter_by(
                    id=message_id,
                    session_id=session_id,
                    message_type='assistant'
                ).first()
                
                if existing_message_by_id:
                    logger.warning(f"Message with ID {message_id} already exists in session {session_id}, skipping storage")
                    return jsonify({
                        'status': 'success',
                        'message': 'Message already exists, skipped storage',
                        'existing_message_id': existing_message_by_id.id
                    })
            
            # Create temporary message to generate content hash
            temp_message = ChatMessage(
                session_id=session_id,
                message_type='assistant',
                content=content
            )
            content_hash = temp_message.generate_content_hash()
            
            # Clean up old cache entries periodically
            _cleanup_request_cache()
            
            # Third check: request-level deduplication using in-memory cache
            if _is_duplicate_request(content_hash):
                logger.warning(f"Duplicate request detected for session {session_id} (hash: {content_hash[:8]}...), skipping storage")
                return jsonify({
                    'status': 'success',
                    'message': 'Duplicate request detected, skipped storage'
                })
            
            # Check for duplicate assistant messages using content hash and recent timestamp
            # Use SELECT FOR UPDATE to prevent race conditions
            import datetime
            thirty_seconds_ago = datetime.datetime.utcnow() - datetime.timedelta(seconds=30)
            
            existing_message = ChatMessage.query.filter(
                ChatMessage.session_id == session_id,
                ChatMessage.message_type == 'assistant',
                ChatMessage.content_hash == content_hash,
                ChatMessage.created_at >= thirty_seconds_ago
            ).with_for_update().first()
            
            if existing_message:
                logger.warning(f"Duplicate assistant message detected for session {session_id} (hash: {content_hash[:8]}...), skipping storage")
                return jsonify({
                    'status': 'success',
                    'message': 'Duplicate message detected, skipped storage',
                    'duplicate_message_id': existing_message.id
                })
            
            # Store assistant message in database
            assistant_message = ChatMessage(
                session_id=session_id,
                message_type='assistant',
                content=content,
                content_hash=content_hash,
                images_used=images_used,
                user_input=user_input
            )
            
            # Use the frontend message ID if available and valid
            if message_id != 'unknown' and message_id.strip():
                assistant_message.id = message_id
            db.session.add(assistant_message)
            
            # Update session timestamp
            session.updated_at = db.func.now()
            db.session.commit()
            
            # Log the assistant message
            logger.info("=" * 80)
            logger.info("ASSISTANT MESSAGE RECEIVED")
            logger.info("=" * 80)
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Message ID: {message_id}")
            logger.info(f"Timestamp: {timestamp}")
            logger.info(f"User Input: {user_input}")
            logger.info(f"Images Used: {images_used}")
            logger.info("-" * 40)
            logger.info("Assistant Response:")
            logger.info(content)
            logger.info("=" * 80)
            
            return jsonify({
                'status': 'success',
                'message': 'Assistant message logged and stored successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error logging assistant message: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
 