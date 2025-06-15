import os

class Config:
    """Konfigurasi dasar"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    UPLOAD_FOLDER = 'static/images/profile'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

class DevelopmentConfig(Config):
    """Konfigurasi untuk development"""
    DEBUG = True
    DATABASE_PATH = 'sparking.db'

class ProductionConfig(Config):
    """Konfigurasi untuk production"""
    DEBUG = False
    DATABASE_PATH = 'sparking.db'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-secret-key-please-change'

# Dictionary untuk memudahkan pemilihan config
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
