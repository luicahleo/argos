"""
ARGOS - Face Recognition Microservice
Run this script to start the development server.
"""

import os
from ARGOS import app, MODEL_NAME
from ARGOS.logger import logger, log_model_operation
from deepface import DeepFace

if __name__ == '__main__':
    # Preload ArcFace model on startup
    logger.info("Preloading ArcFace model...")
    try:
        DeepFace.build_model(MODEL_NAME)
        log_model_operation("build_model", MODEL_NAME)
        logger.info(f"{MODEL_NAME} model loaded successfully!")
    except Exception as e:
        logger.warning(f"Model preload warning: {e}")
    
    HOST = os.environ.get('SERVER_HOST', '0.0.0.0')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5000'))
    except ValueError:
        PORT = 5000
    
    ICARUS_API_URL = os.environ.get('ICARUS_API_URL', 'http://localhost:5090')
    
    logger.info(f"ARGOS Face Recognition starting on http://{HOST}:{PORT}")
    logger.info(f"ICARUS.API URL: {ICARUS_API_URL}")
    
    app.run(HOST, PORT, debug=False)
