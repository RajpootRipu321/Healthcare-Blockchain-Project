"""Configuration settings for Healthcare Blockchain System."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

    # File Upload
    UPLOAD_FOLDER = 'uploads'
    DOWNLOAD_FOLDER = 'downloads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'dcm', 'dicom'}  # Medical image formats

    # Encryption
    BUFFER_SIZE = 64 * 1024  # 64KB buffer for AES

    # IPFS (Infura)
    INFURA_PROJECT_ID = os.getenv('INFURA_PROJECT_ID')
    INFURA_PROJECT_SECRET = os.getenv('INFURA_PROJECT_SECRET')

    # Blockchain
    GENESIS_NODE = '127.0.0.1:5000'
    DIFFICULTY = 4  # Number of leading zeros for proof of work
    BLOCKCHAIN_DATA_FILE = os.getenv('BLOCKCHAIN_DATA_FILE', 'data/blockchain_state.json')

    # AI Model
    MODEL_PATH = os.getenv('MODEL_PATH', 'models/disease_model.h5')
    # Optional JSON map: {"brain_mri": "models/brain_mri_model.keras", "mri": "models/brain_mri_model.keras"}
    AI_MODEL_REGISTRY = os.getenv('AI_MODEL_REGISTRY', '')
    IMAGE_SIZE = (224, 224)  # Standard size for MobileNet

    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///healthcare.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
