import os
from flask import Flask
from flask_cors import CORS
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'TODO')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
    
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_dir
    
    CORS(app, 
         origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"], 
         supports_credentials=True)
    
    # Load VLM service
    from app.vlm_client import get_vlm_service
    
    vlm_service = get_vlm_service()
    
    if vlm_service.load_model():
        logger.info("VLM model loaded successfully")
    else:
        logger.error("Failed to load VLM model")
        logger.warning("The app will start but can't use VLM")
    
    # Load transcription service
    from app.trans_client import get_transcription_service
    
    trans_service = get_transcription_service()
    
    if trans_service.load_model():
        logger.info("Transcription model loaded successfully")
    else:
        logger.error("Failed to load transcription model")
        logger.warning("The app will start but can't use transcription")
    
    from app.routes import register_routes
    register_routes(app)
    
    return app 