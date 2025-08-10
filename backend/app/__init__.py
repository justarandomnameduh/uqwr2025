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
    
    # Database configuration
    db_path = os.environ.get('DATABASE_PATH', 'chat_sessions.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_dir
    
    # Initialize database
    from models import db
    from models.model import ChatSession, ChatMessage
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        logger.info("Database tables created/verified")
    
    CORS(app, 
         origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
         expose_headers=["Content-Type"],
         supports_credentials=True)
    
    # Initialize VLM service (but don't load model yet - user will select)
    from app.vlm_client import get_vlm_service
    vlm_service = get_vlm_service()
    logger.info("VLM service initialized. Model selection available via frontend.")
    
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