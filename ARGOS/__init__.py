"""
ARGOS - Face Recognition Microservice
High-precision facial recognition using DeepFace with ArcFace backend (99.8% accuracy)
"""

from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# DeepFace Configuration
MODEL_NAME = "ArcFace"
DISTANCE_METRIC = "cosine"
DETECTOR_BACKEND = "opencv"
VERIFICATION_THRESHOLD = 0.68

# Initialize logger
from ARGOS.logger import logger
logger.info("ARGOS Flask application initialized")

import ARGOS.views
